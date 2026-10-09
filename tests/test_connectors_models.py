import json
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from tradebot.broker import AlpacaReadOnly, BrokerError
from tradebot.contracts import Category, Coverage, Report, utcnow
from tradebot.models import ModelError, OpenRouter, strict_schema
from tradebot.research import Research
from tradebot.settings import Credentials, Instrument


def credentials():
    return Credentials(
        openrouter_api_key="private-model",
        alpaca_api_key="private-key",
        alpaca_secret_key="private-secret",
        x_bearer_token="private-x",
        tavily_api_key="private-search",
        sec_user_agent="Test test@example.com",
    )


async def test_x_author_whitelist_and_pagination(policy):
    cutoff = utcnow()
    calls = []

    def handler(request):
        calls.append(request)
        token = request.url.params.get("next_token")
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "2" if token else "1",
                        "author_id": "42",
                        "text": "AAPL update",
                        "created_at": (cutoff - timedelta(minutes=5)).isoformat(),
                    }
                ],
                "meta": {} if token else {"next_token": "next"},
            },
        )

    policy = policy.model_copy(update={"approved_x_authors": {"42": "approved"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        research = Research(credentials(), policy, client)
        result = await research._social(policy.instruments[0], cutoff - timedelta(hours=3), cutoff)
    assert result[1]
    assert len(result[0]) == 2
    assert len(calls) == 2
    assert "from:approved" in calls[0].url.params["query"]
    assert calls[0].url.params["tweet.fields"].startswith("author_id")


async def test_unapproved_x_author_never_claims_success(policy):
    cutoff = utcnow()

    def handler(request):
        if request.url.host == "api.x.com":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "1",
                            "author_id": "999",
                            "text": "rumor",
                            "created_at": cutoff.isoformat(),
                        }
                    ]
                },
            )
        if request.url.host == "data.alpaca.markets":
            return httpx.Response(200, json={"news": []})
        return httpx.Response(200, json={"results": []})

    policy = policy.model_copy(
        update={"approved_x_authors": {"42": "approved"}, "market_domains": ["example.com"]}
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        items, attempts = await Research(credentials(), policy, client).collect(
            policy.instruments[0], cutoff
        )
    social = next(x for x in attempts if x.category == Category.SOCIAL)
    assert social.coverage == Coverage.FAILED
    assert not any(x.source == "x" for x in items)
    financial = next(x for x in attempts if x.category == Category.FINANCIAL)
    assert financial.coverage == Coverage.EMPTY


async def test_news_dates_and_truncated_pagination(policy):
    cutoff = utcnow()

    def handler(request):
        return httpx.Response(
            200,
            json={
                "news": [
                    {
                        "id": "1",
                        "headline": "future",
                        "summary": "future",
                        "url": "https://example.com",
                        "created_at": (cutoff + timedelta(hours=1)).isoformat(),
                    }
                ],
                "next_page_token": "more",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        _, attempts = await Research(credentials(), policy, client).collect(
            policy.instruments[0], cutoff
        )
    for attempt in attempts:
        if attempt.source == "alpaca_news":
            assert attempt.coverage == Coverage.DEGRADED
            assert attempt.evidence_ids == []


async def test_market_search_authorized_domains_and_unknown_dates(policy):
    policy = policy.model_copy(update={"market_domains": ["example.com"]})

    def handler(request):
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "bad",
                        "url": "https://evil.test/story",
                        "published_date": utcnow().isoformat(),
                    },
                    {"title": "unknown date", "url": "https://example.com/story"},
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        items, complete = await Research(credentials(), policy, client)._market(
            "AAPL", utcnow() - timedelta(hours=3), utcnow()
        )
    assert items == [] and not complete


async def test_sec_and_ir_metadata_not_invented_full_content(policy):
    cutoff = utcnow()
    instrument = Instrument(symbol="AAPL", name="Apple", sector="technology", cik="320193")

    def handler(request):
        assert "CIK0000320193.json" in str(request.url)
        assert "User-Agent" in request.headers
        return httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {
                        "accessionNumber": ["0000320193-26-000001"],
                        "form": ["8-K"],
                        "primaryDocument": ["report.htm"],
                        "filingDate": [cutoff.date().isoformat()],
                        "acceptanceDateTime": [(cutoff - timedelta(minutes=30)).isoformat()],
                    }
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        items, complete = await Research(credentials(), policy, client)._sec(
            instrument, cutoff - timedelta(hours=3), cutoff
        )
    assert complete and len(items) == 1
    assert "metadata only" in items[0].text
    assert "320193" in items[0].url


async def test_missing_credentials_coverage_is_failure(policy):
    research = Research(Credentials(_env_file=None), policy)
    try:
        items, attempts = await research.collect(policy.instruments[0], utcnow())
        assert not items
        assert len(attempts) == 4
        assert all(x.coverage == Coverage.FAILED for x in attempts)
    finally:
        await research.close()


async def test_rss_reads_only_configured_feed(policy):
    cutoff = utcnow()
    body = f"""<rss version="2.0"><channel><title>IR</title><link>https://example.com</link>
    <description>IR</description><item><title>Release</title><link>https://example.com/release</link>
    <pubDate>{(cutoff - timedelta(minutes=15)).strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
    <description>Company announcement</description></item></channel></rss>"""
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body))
    ) as client:
        research = Research(credentials(), policy, client)
        items, complete = await research._rss(
            policy.instruments[0], "https://example.com/feed", cutoff - timedelta(hours=3), cutoff
        )
        assert complete and len(items) == 1
        with pytest.raises(ValueError):
            await research._rss(policy.instruments[0], "http://example.com/feed", cutoff, cutoff)


async def test_model_schema_repair_bounded_and_cost_accounted(store, policy):
    calls = []
    valid = Report(
        summary="brief", direction="mixed", evidence_ids=[], opposing_evidence=[], gaps=[]
    )

    def handler(request):
        calls.append(json.loads(request.content))
        content = "bad JSON" if len(calls) == 1 else valid.model_dump_json()
        return httpx.Response(
            200,
            json={
                "id": "response",
                "model": "test",
                "usage": {"cost": 0.01},
                "choices": [{"message": {"content": content}}],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = OpenRouter(credentials(), policy, store, client)
        result = await model.structured("market_analyst", Report, {"evidence": []})
    assert result == valid
    assert len(calls) == 2
    assert calls[0]["response_format"]["json_schema"]["strict"]
    assert calls[0]["provider"]["require_parameters"]
    assert store.model_spend() == Decimal(".02")
    schema = strict_schema(Report.model_json_schema())
    assert schema["additionalProperties"] is False


async def test_invalid_model_output_stops_after_one_repair(store, policy):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "bad"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ModelError, match="after one repair"):
            await OpenRouter(credentials(), policy, store, client).structured("lead", Report, {})
    assert len(calls) == 2
    assert store.model_spend() > 0


async def test_model_transport_error_retains_reservation_and_redacts(store, policy):
    def handler(request):
        return httpx.Response(401, text="private-model is invalid")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ModelError) as exc:
            await OpenRouter(credentials(), policy, store, client).answer("test", {}, [])
    assert "private-model" not in str(exc.value)
    assert store.model_spend() > 0


async def test_model_budget_and_input_bound_prevent_calls(store, policy):
    def handler(_):
        raise AssertionError("No request should be sent")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        zero_budget = policy.model_copy(update={"monthly_model_budget": Decimal(0)})
        with pytest.raises(ValueError, match="budget"):
            await OpenRouter(credentials(), zero_budget, store, client).answer("test", {}, [])
        with pytest.raises(ModelError, match="token bound"):
            await OpenRouter(credentials(), policy, store, client).answer(
                "test", {"huge": "x" * 100000}, []
            )


async def test_alpaca_adapter_is_paper_read_only_and_pending_orders_count(policy):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.url.host == "paper-api.alpaca.markets"
        if request.url.path == "/v2/account":
            return httpx.Response(
                200, json={"cash": "1000", "equity": "1100", "last_equity": "1100"}
            )
        if request.url.path == "/v2/positions":
            return httpx.Response(
                200,
                json=[
                    {
                        "symbol": "AAPL",
                        "qty": "1",
                        "side": "long",
                        "avg_entry_price": "90",
                        "current_price": "100",
                    }
                ],
            )
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "AAPL",
                    "side": "buy",
                    "qty": "3",
                    "filled_qty": "1",
                    "limit_price": "100",
                }
            ],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        broker = AlpacaReadOnly(credentials(), policy, client)
        result = await broker.snapshot(None)
    assert result.pending_buys["AAPL"] == 200
    assert result.cash == 1000 and result.equity == 1100
    assert result.reconciled
    assert len(requests) == 3
    assert not hasattr(broker, "submit_order")


async def test_short_broker_positions_rejected(policy):
    def handler(request):
        if request.url.path == "/v2/account":
            return httpx.Response(200, json={"cash": "1000", "equity": "900"})
        if request.url.path == "/v2/positions":
            return httpx.Response(200, json=[{"symbol": "AAPL", "qty": "-1", "side": "short"}])
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BrokerError, match="Short"):
            await AlpacaReadOnly(credentials(), policy, client).snapshot(None)
