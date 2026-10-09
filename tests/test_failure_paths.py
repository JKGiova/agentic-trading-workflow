import asyncio
from datetime import timedelta

import httpx
import pytest

from tradebot.broker import AlpacaReadOnly, BrokerError
from tradebot.contracts import Category, Evidence, utcnow
from tradebot.models import DemoModel, ModelError, OpenRouter
from tradebot.research import DemoResearch
from tradebot.service import TradeService
from tradebot.settings import Credentials, Policy
from tradebot.workflow import StockState, Workflow, gathered


async def test_independent_failed_role_waits_for_other_calls():
    finished = []

    async def failed():
        raise RuntimeError("role failed")

    async def delayed():
        await asyncio.sleep(0.01)
        finished.append(True)
        return "finished"

    with pytest.raises(RuntimeError):
        await gathered(failed(), delayed())
    assert finished == [True]


async def test_session_timeout_releases_database_lease(store, policy):
    class Slow(DemoResearch):
        async def collect(self, *args):
            await asyncio.sleep(10)

    short = policy.model_copy(update={"session_timeout_seconds": 1})
    with pytest.raises(TimeoutError):
        await Workflow(short, store, DemoModel(), Slow()).run()
    assert store.acquire("decision-session", "after-timeout", 5)
    assert store.snapshot().cash == 9000


async def test_cached_stage_reuse_rejects_changed_input(store, policy):
    from tradebot.contracts import Report

    sid = store.start_session(utcnow())
    state = StockState(
        stock="AAPL",
        session_id=sid,
        evidence=[],
        cutoff=utcnow().isoformat(),
        reference_price="100",
    )
    model = DemoModel()
    flow = Workflow(policy, store, model, DemoResearch())
    result = await flow.invoke(state, "market", "market_analyst", Report, {"evidence": []})
    cached = await flow.invoke(state, "market", "market_analyst", Report, {"evidence": []})
    assert result == cached and len(model.calls) == 1
    with pytest.raises(ValueError, match="input changed"):
        await flow.invoke(
            state, "market", "market_analyst", Report, {"evidence": [], "changed": True}
        )


async def test_chat_inspects_explicit_unheld_ticker(store, policy):
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True)
    captured = []

    async def answer(question, context, history):
        captured.append(context)
        return "Answer from stored context"

    service.model.answer = answer
    await service.ask("Explain MSFT", "AAPL")
    assert captured[0]["selected"] == "MSFT"
    await service.close()


async def test_chat_error_persists_failure_without_executing(store, policy):
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True)

    async def failed(*_):
        raise ModelError("Unavailable")

    service.model.answer = failed
    with pytest.raises(ModelError):
        await service.ask("Close everything", "AAPL")
    assert "no action" in store.chat_history()[-1]["content"]
    assert store.snapshot().cash == 9000
    await service.close()


async def test_broker_quote_and_unknown_order_handling(policy):
    credentials = Credentials(alpaca_api_key="test", alpaca_secret_key="test")

    def handler(request):
        if request.url.host == "data.alpaca.markets":
            assert request.url.params["feed"] == "iex"
            return httpx.Response(200, json={"quote": {"ap": 101, "bp": 99}})
        if request.url.path == "/v2/account":
            return httpx.Response(200, json={"cash": "1000", "equity": "1000"})
        if request.url.path == "/v2/positions":
            return httpx.Response(200, json=[])
        return httpx.Response(
            200, json=[{"symbol": "AAPL", "side": "buy", "qty": "1", "filled_qty": "0"}]
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        broker = AlpacaReadOnly(credentials, policy, client)
        assert await broker.quote("AAPL") == 100
        assert not (await broker.snapshot(None)).reconciled
        await broker.close()  # Does not close the injected HTTP client.
        assert not client.is_closed


async def test_broker_failure_and_missing_credentials_are_safe(policy):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(401, text="credentials invalid"))
    ) as client:
        broker = AlpacaReadOnly(
            Credentials(alpaca_api_key="test", alpaca_secret_key="test"), policy, client
        )
        with pytest.raises(BrokerError, match="read failed"):
            await broker.get("/v2/account")
        with pytest.raises(BrokerError, match="unavailable"):
            await broker.quote("AAPL")
        missing = AlpacaReadOnly(Credentials(_env_file=None), policy, client)
        with pytest.raises(BrokerError, match="credentials missing"):
            await missing.get("/v2/account")
        with pytest.raises(BrokerError, match="credential missing"):
            await missing.quote("AAPL")


async def test_malformed_model_cost_retains_budget_and_tool_call_refused(store, policy):
    def handler(_):
        return httpx.Response(
            200,
            json={
                "usage": {"cost": "not-a-number"},
                "choices": [
                    {
                        "message": {
                            "tool_calls": [{"function": {"name": "submit_order"}}],
                            "content": "no",
                        }
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = OpenRouter(Credentials(openrouter_api_key="test"), policy, store, client)
        with pytest.raises(ModelError, match="Unexpected model tool call"):
            await model.answer("Trade", {}, [])
    assert store.model_spend() > 0


def test_timezone_and_duplicate_watchlist_validation(policy):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Evidence(
            id="e",
            stock="AAPL",
            category=Category.COMPANY,
            source="test",
            title="test",
            text="test",
            url="https://example.com",
            published_at=utcnow().replace(tzinfo=None),
            retrieved_at=utcnow(),
        )
    with pytest.raises(ValidationError):
        Policy(instruments=[policy.instruments[0], policy.instruments[0]])


def test_future_snapshot_and_mode_separation(store, policy):
    from tradebot.contracts import Allocation
    from tradebot.risk import preview

    snapshot = store.snapshot().model_copy(update={"as_of": utcnow() + timedelta(hours=1)})
    result = preview(
        "AAPL",
        "technology",
        Allocation(action="CLOSE", requested_notional=0, rationale="test"),
        snapshot,
        None,
        policy.risk,
        snapshot.positions[0].price,
        True,
        True,
        False,
    )
    assert not result.accepted
    with pytest.raises(ValueError, match="separate databases"):
        TradeService(store, policy, Credentials(_env_file=None), demo=False)
