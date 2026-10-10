import asyncio
import io
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from tradebot import agentreach_worker
from tradebot.agentreach_sources import AgentReachSources
from tradebot.analysis_memory import AnalysisMemory
from tradebot.analysts import AgentTurn
from tradebot.contracts import Category, utcnow
from tradebot.news_sources import NewsSources
from tradebot.research import make_evidence
from tradebot.settings import Credentials


def access():
    return Credentials(_env_file=None, x_auth_token="private-auth", x_ct0="private-csrf")


def tweet(now, **updates):
    return {
        "id": "101",
        "text": "AAPL company announcement",
        "author": {"id": "42", "screenName": "Approved"},
        "createdAtISO": now.isoformat(),
        **updates,
    }


async def test_x_enforces_ids_handles_exact_window_dedup_and_no_score_filter(policy):
    now = utcnow()
    policy = policy.model_copy(update={"approved_x_authors": {"42": "approved"}})
    rows = [
        tweet(now),
        tweet(now),
        tweet(now, author={"id": "99", "screenName": "approved"}),
        tweet(now, author={"id": "42", "screenName": "renamed"}),
        tweet(now, createdAtISO=(now + timedelta(seconds=1)).isoformat()),
        tweet(now, createdAtISO=(now - timedelta(hours=4)).isoformat()),
        tweet(now, createdAtISO="2026-10-10T12:00:00"),
        tweet(now, isRetweet=True),
        tweet(now, isPromoted=True),
        tweet(now, text="Unrelated news"),
        {},
        tweet(now, id="not-numeric"),
        tweet(now, text=""),
    ]
    requests = []

    async def runner(payload):
        requests.append(payload)
        return {"tweets": rows, "capped": False}

    source = AgentReachSources(access(), policy, runner)
    items, complete = await source.social(policy.instruments[0], now - timedelta(hours=3), now)
    assert len(items) == 1 and not complete
    assert items[0].author_id == "42" and items[0].source == "agentreach_x"
    assert items[0].url == "https://x.com/approved/status/101"
    assert "from:approved" in requests[0]["query"] and "since:" in requests[0]["query"]
    assert "score" not in requests[0] and "confidence" not in requests[0]
    assert "private-auth" not in json.dumps(items[0].model_dump(mode="json"))
    assert source.capabilities()["x_cookies_configured"]
    assert not source.capabilities()["network_verified"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ({"tweets": []}, True),
        ({"tweets": [], "capped": True}, False),
        ({"tweets": "broken"}, None),
        ({"tweets": [{}] * 51}, None),
    ],
)
async def test_x_empty_sample_cap_and_schema_failure(policy, raw, expected):
    now = utcnow()
    policy = policy.model_copy(update={"approved_x_authors": {"42": "approved"}})

    async def runner(payload):
        return raw

    source = AgentReachSources(access(), policy, runner)
    if expected is None:
        with pytest.raises(ValueError):
            await source.social(policy.instruments[0], now - timedelta(hours=3), now)
    else:
        assert (await source.social(policy.instruments[0], now - timedelta(hours=3), now))[
            1
        ] == expected


async def test_x_missing_access_and_large_query_do_not_invoke_backend(policy):
    async def forbidden(payload):
        raise AssertionError("No lookup authorized")

    now = utcnow()
    source = AgentReachSources(Credentials(_env_file=None), policy, forbidden)
    with pytest.raises(ValueError, match="missing"):
        await source.social(policy.instruments[0], now, now)
    source.credentials = access()
    source.policy = policy.model_copy(
        update={"approved_x_authors": {str(n): "handle" + str(n) for n in range(100)}}
    )
    with pytest.raises(ValueError, match="limit"):
        await source.social(policy.instruments[0], now, now)


@pytest.mark.parametrize(
    "text",
    [
        "URL Source: https://other.com\nMarkdown Content: body",
        "No source provenance",
        "URL Source: https://example.com/release\nMarkdown Content: ",
        "URL Source: https://example.com/release\nMarkdown Content: Subscribe to continue",
        "URL Source: https://example.com/release\nMarkdown Content: Requiring CAPTCHA",
        "x" * 2_000_001,
        None,
    ],
)
async def test_web_rejects_redirect_paywall_challenge_oversize_and_empty(policy, text):
    async def runner(payload):
        assert payload == {"operation": "web", "url": "https://example.com/release"}
        return {"text": text}

    with pytest.raises(ValueError):
        await AgentReachSources(access(), policy, runner).read("https://example.com/release")


async def test_registered_page_uses_agent_reach_and_remembers_provenance(
    store, policy, monkeypatch
):
    now = utcnow()
    policy = policy.model_copy(update={"article_domains": ["example.com"]})
    calls = []

    async def runner(payload):
        calls.append(payload)
        return {
            "text": "Title: Official\nURL Source: https://example.com/release\n"
            "Markdown Content:\nOriginal announcement"
        }

    async def dns(*args):
        return [(2, 1, 6, "", ("8.8.8.8", 443))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", dns)
    memory = AnalysisMemory(store)
    source = NewsSources(
        access(), policy, memory, agentreach=AgentReachSources(access(), policy, runner)
    )
    item = make_evidence(
        "yfinance",
        "1",
        "AAPL",
        Category.COMPANY,
        "Announcement",
        "Lead",
        "https://example.com/release",
        now,
    )
    task = {"stock": "AAPL", "role": "company", "payload": {"checkpoint": {}}}
    try:
        result = await source.execute(
            AgentTurn(action="READ_PAGE", evidence_id=item.id),
            task,
            {"evidence": [item.model_dump(mode="json")]},
            now,
        )
        found = result["evidence"][0]
        assert found["source"] == "agentreach_web" and found["text"] == "Original announcement"
        assert found["published_at"] == item.model_dump(mode="json")["published_at"]
        assert "Jina" in result["content_level"] and memory.evidence("AAPL", now)
        assert len(calls) == 1
    finally:
        await source.close()


async def test_worker_real_process_fails_safely_and_never_echoes_secrets(policy):
    source = AgentReachSources(access(), policy)
    with pytest.raises(ValueError) as error:
        await source.run({"operation": "forbidden", "secret": "private-cookie"})
    assert "private-cookie" not in str(error.value)


@pytest.mark.parametrize("case", ["timeout", "cancel", "shape", "oversize", "exit"])
async def test_worker_timeout_cancellation_and_invalid_output_are_bounded(
    policy, monkeypatch, case
):
    started = asyncio.Event()

    class Process:
        returncode = None
        killed = False

        async def communicate(self, body):
            assert json.loads(body)["auth_token"] == "private-auth"
            started.set()
            if case in {"timeout", "cancel"}:
                await asyncio.Event().wait()
            self.returncode = 1 if case == "exit" else 0
            return (
                b"[]" if case == "shape" else b"x" * 2_000_001 if case == "oversize" else b"{}"
            ), None

        def kill(self):
            self.killed = True
            self.returncode = -9

        async def wait(self):
            return self.returncode

    process = Process()

    async def spawn(*args, **kwargs):
        assert args[1:] == ("-m", "tradebot.agentreach_worker")
        assert "private-auth" not in repr(args) + repr(kwargs)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    source = AgentReachSources(access(), policy, timeout=0.01)
    task = asyncio.create_task(source.run({"auth_token": "private-auth"}))
    if case == "cancel":
        await started.wait()
        task.cancel()
    with pytest.raises(
        asyncio.CancelledError
        if case == "cancel"
        else TimeoutError
        if case == "timeout"
        else ValueError
    ):
        await task
    assert process.killed == (case in {"timeout", "cancel"})


def test_worker_calls_pinned_backends_without_browser_auth_loader(monkeypatch):
    from agent_reach.channels.web import WebChannel
    from twitter_cli.client import TwitterClient
    from twitter_cli.models import Author, Metrics, Tweet

    monkeypatch.setattr(WebChannel, "read", lambda self, url: "Source markdown")
    assert agentreach_worker.execute({"operation": "web", "url": "https://example.com"}) == {
        "text": "Source markdown"
    }

    def init(self, auth, ct0, **kwargs):
        assert auth == "private-auth" and ct0 == "private-csrf"
        assert kwargs["rate_limit_config"]["maxRetries"] == 0

    def search(self, query, count, product):
        assert count == 50 and product == "Latest"
        return [
            Tweet(
                "101",
                "AAPL news",
                Author("42", "Company", "approved"),
                Metrics(),
                utcnow().isoformat(),
            )
        ]

    def forbidden(*args, **kwargs):
        raise AssertionError("Never harvest a browser profile")

    monkeypatch.setattr(TwitterClient, "__init__", init)
    monkeypatch.setattr(TwitterClient, "fetch_search", search)
    monkeypatch.setattr("twitter_cli.auth.get_cookies", forbidden)
    output = agentreach_worker.execute(
        {"operation": "x", "auth_token": "private-auth", "ct0": "private-csrf", "query": "AAPL"}
    )
    assert output["tweets"][0]["author"]["id"] == "42" and not output["capped"]
    with pytest.raises(ValueError):
        agentreach_worker.execute({"operation": "write"})


def test_worker_main_validates_input_and_bounds_output(monkeypatch):
    stdin = SimpleNamespace(buffer=io.BytesIO(b'{"operation":"fixture"}'))
    buffer = io.BytesIO()
    stdout = SimpleNamespace(buffer=buffer, write=lambda text: buffer.write(text.encode()))
    monkeypatch.setattr(agentreach_worker.sys, "stdin", stdin)
    monkeypatch.setattr(agentreach_worker.sys, "stdout", stdout)
    monkeypatch.setattr(agentreach_worker, "execute", lambda _: {"text": "public"})
    assert agentreach_worker.main() == 0
    assert json.loads(buffer.getvalue())["text"] == "public"
    stdin.buffer = io.BytesIO(b"x" * 16_385)
    buffer.seek(0)
    buffer.truncate()
    assert agentreach_worker.main() == 1
    assert "failed" in json.loads(buffer.getvalue())["error"]
    stdin.buffer = io.BytesIO(b"{}")
    buffer.seek(0)
    buffer.truncate()
    monkeypatch.setattr(agentreach_worker, "execute", lambda _: {"text": "x" * 2_000_001})
    assert agentreach_worker.main() == 1
