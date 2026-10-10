import asyncio
import json
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest

from tradebot.analysis_memory import AnalysisMemory, outbox
from tradebot.analysts import AgentTurn
from tradebot.contracts import Category, Report, utcnow
from tradebot.models import ModelError, NvidiaNIM, model_client
from tradebot.news_sources import NewsSources
from tradebot.research import make_evidence
from tradebot.settings import Credentials
from tradebot.telegram import TelegramNotifier, split_message


def credentials(**kwargs):
    return Credentials(
        _env_file=None,
        nvidia_api_key="private-nvidia",
        telegram_bot_token="private-telegram",
        **kwargs,
    )


def report():
    return Report(
        summary="Valid", direction="mixed", evidence_ids=[], opposing_evidence=[], gaps=[]
    )


async def test_nvidia_request_contract_local_schema_and_unknown_billing(store, policy):
    requests = []

    def handler(request):
        assert request.url.host == "integrate.api.nvidia.com"
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer private-nvidia"
        body = json.loads(request.content)
        requests.append(body)
        assert body["model"] == "deepseek-ai/deepseek-v4.1-flash"
        assert "provider" not in body and "response_format" not in body
        content = "invalid" if len(requests) == 1 else report().model_dump_json()
        return httpx.Response(
            200,
            json={
                "model": policy.model,
                "id": "id",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                "choices": [{"finish_reason": "stop", "message": {"content": content}}],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = NvidiaNIM(credentials(), policy, store, client)
        assert await model.structured("company_analyst", Report, {}) == report()
        assert "schema" in requests[0]["messages"][0]["content"]
        assert len(requests) == 2
        assert store.model_spend() > 0
        assert "private-nvidia" not in json.dumps(requests)
        await model.close()
    configured = model_client(credentials(), policy, store)
    assert isinstance(configured, NvidiaNIM)
    await configured.close()


@pytest.mark.parametrize("failure", ["model", "length", "tool", "empty", "shape", "reasoning"])
async def test_nvidia_rejects_wrong_identity_incomplete_and_unsupported_outputs(
    store, policy, failure
):
    data = {
        "model": policy.model,
        "choices": [{"finish_reason": "stop", "message": {"content": "hello"}}],
    }
    if failure == "model":
        data["model"] = "different-model"
    elif failure == "length":
        data["choices"][0]["finish_reason"] = "length"
    elif failure == "tool":
        data["choices"][0]["message"]["tool_calls"] = [{"name": "unapproved"}]
    elif failure == "empty":
        data["choices"][0]["message"]["content"] = " "
    elif failure == "shape":
        data = []
    else:
        data["choices"][0]["message"] = {"reasoning_content": "unfinished reasoning"}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
    ) as client:
        with pytest.raises(ModelError) as error:
            await NvidiaNIM(credentials(), policy, store, client).answer("test", {}, [])
        assert "private-nvidia" not in str(error.value)
        assert store.model_spend() > 0


async def test_nvidia_missing_key_and_legacy_provider_factory(store, policy):
    model = NvidiaNIM(Credentials(_env_file=None), policy, store)
    with pytest.raises(ModelError, match="credential missing"):
        await model.answer("test", {}, [])
    await model.close()
    legacy = model_client(
        Credentials(_env_file=None),
        policy.model_copy(update={"model_provider": "openrouter"}),
        store,
    )
    assert legacy.provider_name == "openrouter"
    await legacy.close()
    assert credentials().analysis_missing(policy) == []
    assert "telegram_bot_token" in Credentials(_env_file=None).analysis_missing(
        policy, telegram=True
    )


def yahoo_row(now, **updates):
    content = {
        "title": "Company event",
        "summary": "Summary",
        "pubDate": (now - timedelta(minutes=5)).isoformat(),
        "canonicalUrl": {"url": "https://example.com/release"},
    }
    content.update(updates)
    return {"id": "event", "content": content}


async def test_yfinance_discovery_once_categories_macro_and_missing_social(store, policy):
    now, calls = utcnow(), []

    def ticker(stock):
        calls.append(stock)
        return SimpleNamespace(get_news=lambda **kwargs: [yahoo_row(now)])

    def search(query, news_count):
        assert news_count == 10
        return SimpleNamespace(news=[yahoo_row(now)])

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(500))
    ) as client:
        source = NewsSources(
            Credentials(_env_file=None),
            policy,
            AnalysisMemory(store),
            client,
            ticker_factory=ticker,
            search_factory=search,
        )
        items, attempts = await source.collect(policy.instruments[0], now)
        assert calls == ["AAPL"]
        assert {a.category for a in attempts} == set(Category)
        assert next(a for a in attempts if a.category == Category.SOCIAL).coverage == "FAILED"
        assert (
            next(a for a in attempts if a.category == Category.MARKET).source == "yfinance_search"
        )
        assert len(items) == 2
        assert len({item.id for item in items}) == 1  # One physical source, several role views.
        await source.close()


async def test_yahoo_normalization_missing_dates_future_invalid_and_sample_cap(store, policy):
    now = utcnow()
    source = NewsSources(Credentials(_env_file=None), policy, AnalysisMemory(store))
    rows = [
        yahoo_row(now),
        yahoo_row(now, pubDate=None),
        yahoo_row(now, pubDate="bad-date"),
        yahoo_row(now, pubDate=(now + timedelta(hours=1)).isoformat()),
        yahoo_row(now, canonicalUrl={}),
        {"content": None},
    ]
    items, gaps = source.normalize(policy.instruments[0], rows, now)
    assert len(items) == 1 and gaps
    rows = [
        {
            "title": "Macro",
            "link": "https://example.com",
            "providerPublishTime": int(now.timestamp()),
        }
    ]
    assert len(source.normalize(policy.instruments[0], rows, now)[0]) == 1
    assert source.normalize(policy.instruments[0], [yahoo_row(now)] * 30, now)[1]
    await source.close()


async def test_source_failures_sec_and_ir_are_recorded(store, policy):
    def ticker(stock):
        raise ValueError("no access")

    def search(*args, **kwargs):
        raise RuntimeError("no access")

    policy = policy.model_copy(
        update={
            "instruments": [
                policy.instruments[0].model_copy(
                    update={"cik": "320193", "ir_feeds": ["https://example.com/feed"]}
                )
            ]
        }
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(401))
    ) as client:
        source = NewsSources(
            Credentials(_env_file=None),
            policy,
            AnalysisMemory(store),
            client,
            ticker_factory=ticker,
            search_factory=search,
        )
        items, attempts = await source.collect(policy.instruments[0], utcnow())
        assert not items
        assert len(attempts) == 6
        assert all(a.coverage == "FAILED" for a in attempts)


async def test_scoped_tools_read_search_and_article_policy(store, policy, monkeypatch):
    now = utcnow()
    item = make_evidence(
        "fixture",
        "one",
        "AAPL",
        Category.COMPANY,
        "Release",
        "summary",
        "https://example.com/release",
        now,
    )
    memory = AnalysisMemory(store)
    context = {"evidence": [item.model_dump(mode="json")]}
    task = {"stock": "AAPL", "role": "company", "payload": {"checkpoint": {}}}

    def ticker(stock):
        return SimpleNamespace(get_news=lambda **kwargs: [yahoo_row(now)])

    queries = []

    def search(query, news_count):
        queries.append(query)
        return SimpleNamespace(news=[yahoo_row(now)])

    async def addresses(*args):
        return [(2, 1, 6, "", ("8.8.8.8", 443))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", addresses)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                text="<html><script>bad</script><article>Original announcement</article></html>",
            )
        )
    ) as client:
        source = NewsSources(
            Credentials(_env_file=None),
            policy,
            memory,
            client,
            ticker_factory=ticker,
            search_factory=search,
        )
        result = await source.execute(
            AgentTurn(action="READ_EVIDENCE", evidence_id=item.id), task, context, now
        )
        assert result["evidence"][0]["id"] == item.id
        with pytest.raises(ValueError, match="unknown"):
            await source.execute(
                AgentTurn(action="READ_EVIDENCE", evidence_id="forged"), task, context, now
            )
        with pytest.raises(ValueError, match="policy"):
            await source.execute(
                AgentTurn(action="READ_PAGE", evidence_id=item.id), task, context, now
            )
        source.policy = policy.model_copy(update={"article_domains": ["example.com"]})
        result = await source.execute(
            AgentTurn(action="READ_PAGE", evidence_id=item.id), task, context, now
        )
        assert result["content_level"] == "bounded page text"
        assert "Original announcement" in result["evidence"][0]["text"]
        assert "bad" not in result["evidence"][0]["text"]
        result = await source.execute(
            AgentTurn(action="SEARCH_NEWS", query="CES guidance"), task, context, now
        )
        assert result["attempts"][-1]["query"] == "AAPL CES guidance"
        assert queries[-1].startswith("AAPL ")
        assert memory.evidence("AAPL", now)
        # Removed-watchlist holding keeps a bounded stock identity.
        task["stock"] = "OTHER"
        await source.execute(AgentTurn(action="SEARCH_NEWS"), task, {"evidence": []}, now)


@pytest.mark.parametrize("case", ["private", "oversize", "redirect", "empty"])
async def test_page_reader_rejects_private_large_redirect_empty(store, policy, monkeypatch, case):
    now = utcnow()
    policy = policy.model_copy(update={"article_domains": ["example.com"]})
    item = make_evidence(
        "fixture", "one", "AAPL", Category.COMPANY, "Source", "", "https://example.com", now
    )

    async def addresses(*args):
        return [(2, 1, 6, "", ("127.0.0.1" if case == "private" else "8.8.8.8", 443))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", addresses)
    response = (
        httpx.Response(302, headers={"location": "https://unapproved.com"})
        if case == "redirect"
        else httpx.Response(
            200, content=b"x" * 2_000_001 if case == "oversize" else b"<script>only</script>"
        )
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)) as client:
        source = NewsSources(Credentials(_env_file=None), policy, AnalysisMemory(store), client)
        with pytest.raises((ValueError, httpx.HTTPError)):
            await source.execute(
                AgentTurn(action="READ_PAGE", evidence_id=item.id),
                {"stock": "AAPL", "role": "company", "payload": {"checkpoint": {}}},
                {"evidence": [item.model_dump(mode="json")]},
                now,
            )


def test_telegram_split_unicode_units_and_plain_text():
    parts = split_message("📰" * 6000 + "<not markup>")
    assert len(parts) >= 4
    assert all(len(part.encode("utf-16-le")) // 2 <= 4096 for part in parts)
    assert "<not markup>" in parts[-1]


async def test_telegram_pair_exact_nonce_private_sender_and_stored_identity(store):
    memory = AnalysisMemory(store)
    messages = []

    def handler(request):
        if request.url.path.endswith("getMe"):
            return httpx.Response(200, json={"ok": True, "result": {"username": "ownerbot"}})
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "text": "/start wrong",
                            "chat": {"id": 42, "type": "private"},
                            "from": {"id": 42},
                        },
                    },
                    {
                        "update_id": 2,
                        "message": {
                            "text": "/start nonce",
                            "chat": {"id": 99, "type": "group"},
                            "from": {"id": 99},
                        },
                    },
                    {
                        "update_id": 3,
                        "message": {
                            "text": "/start nonce",
                            "chat": {"id": 42, "type": "private"},
                            "from": {"id": 99},
                        },
                    },
                    {
                        "update_id": 4,
                        "message": {
                            "text": "/start nonce",
                            "chat": {"id": 42, "type": "private"},
                            "from": {"id": 42},
                        },
                    },
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        notifier = TelegramNotifier(credentials(), memory, client)
        assert await notifier.pair(messages.append, nonce="nonce") == "42"
        assert "nonce" in messages[0]
        assert notifier.chat_id == "42"
        await notifier.close()
    paired = TelegramNotifier(credentials(), memory)
    assert paired.chat_id == "42"
    await paired.close()
    different = TelegramNotifier(Credentials(_env_file=None, telegram_bot_token="other"), memory)
    assert different.chat_id == ""
    await different.close()
    assert "private-telegram" not in json.dumps(memory.setting("telegram_owner"))


async def test_telegram_outbox_success_no_duplicate_and_unpaired_wait(store):
    memory = AnalysisMemory(store)
    now = utcnow()
    memory.queue_summary("cycle", split_message("Summary"), now)
    sends = []

    def handler(request):
        body = json.loads(request.content)
        sends.append(body)
        assert body["chat_id"] == "42"
        assert "parse_mode" not in body
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 100}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        notifier = TelegramNotifier(credentials(), memory, client)
        await notifier.deliver(now)
        assert not sends
        notifier.chat_id = "42"
        await asyncio.gather(notifier.deliver(now), notifier.deliver(now))
        await notifier.deliver(now)
    assert len(sends) == 1
    assert memory.rows(outbox)[0]["status"] == "SENT"


async def test_telegram_quota_retry_and_unknown_send_no_resend(store):
    memory = AnalysisMemory(store)
    now = utcnow()
    memory.queue_summary("cycle", ["part1", "part2"], now)
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, json={"parameters": {"retry_after": 2}})
        raise httpx.ReadTimeout("private-telegram", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        notifier = TelegramNotifier(credentials(telegram_chat_id="42"), memory, client)
        await notifier.deliver(now)
        await notifier.deliver(now)
        assert len(calls) == 1  # Subsequent part cannot bypass its delayed predecessor.
        await notifier.deliver(now + timedelta(seconds=3))
        await notifier.deliver(now + timedelta(seconds=10))
    assert len(calls) == 2
    rows = memory.rows(outbox)
    assert rows[0]["status"] == "UNKNOWN"
    assert "private-telegram" not in json.dumps(rows)


async def test_telegram_api_failure_redacted_missing_and_invalid_chat(store):
    memory = AnalysisMemory(store)
    notifier = TelegramNotifier(Credentials(_env_file=None), memory)
    with pytest.raises(ValueError, match="token missing"):
        await notifier.call("getMe", {})
    await notifier.close()
    with pytest.raises(ValueError, match="numeric"):
        TelegramNotifier(credentials(telegram_chat_id="@someone"), memory)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": False}))
    ) as client:
        notifier = TelegramNotifier(credentials(), memory, client)
        with pytest.raises(RuntimeError):
            await notifier.call("getMe", {})
