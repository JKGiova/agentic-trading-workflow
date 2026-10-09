from decimal import Decimal

import pytest

from tradebot.contracts import Coverage, Forecast, Verdict
from tradebot.models import DemoModel
from tradebot.research import DemoResearch
from tradebot.service import TradeService
from tradebot.settings import Credentials
from tradebot.workflow import Workflow, complete_coverage


async def test_full_session_keeps_low_initial_confidence_and_separate_allocator(store, policy):
    model = DemoModel()
    flow = Workflow(policy, store, model, DemoResearch())
    result = await flow.run()
    assert result["status"] == "COMPLETE"
    assert "NVDA" in result["debated"]
    nvda = store.latest("NVDA")
    assert nvda["initial_forecast"]["output"]["probability"] == 0.25
    assert nvda["effective_verdict"]["forecast"]["probability"] == 0.6
    assert nvda["allocation_preview"]["executable"] is False
    roles = {role for role, _ in model.calls}
    assert {
        "market_analyst",
        "financial_analyst",
        "company_analyst",
        "social_analyst",
        "analyst_lead",
        "bull_researcher",
        "bear_researcher",
        "orchestrator",
        "portfolio_allocator",
    } <= roles
    for role, context in model.calls:
        if role.endswith("_analyst"):
            assert "reports" not in context
    first_debate = next(i for i, (r, _) in enumerate(model.calls) if r == "bull_researcher")
    holding_calls = [
        i
        for i, (r, c) in enumerate(model.calls)
        if r == "portfolio_allocator" and c.get("verdict") is None
    ]
    assert len(holding_calls) == 2 and max(holding_calls) < first_debate
    assert store.snapshot().cash == 9000  # Research cannot mutate financial state.


async def test_all_holdings_researched_when_removed_from_watchlist(store, policy):
    policy = policy.model_copy(update={"instruments": [policy.instruments[0]]})
    model = DemoModel()
    result = await Workflow(policy, store, model, DemoResearch()).run()
    assert "NVDA" not in result["debated"]
    nvda = store.latest("NVDA")
    assert len(nvda["research"]["coverage"]) == 4
    assert "holding_review_preview" in nvda
    assert "allocation_preview" not in nvda


async def test_session_limit_retains_pending_and_rotates_fairly(store, policy):
    policy = policy.model_copy(update={"max_debates": 1})
    flow = Workflow(policy, store, DemoModel(), DemoResearch())
    first = await flow.run()
    second = await flow.run()
    third = await flow.run()
    assert first["debated"] == ["AAPL"]
    assert second["debated"] == ["MSFT"]
    assert third["debated"] == ["NVDA"]
    assert len(first["pending"]) == 2


async def test_missing_initial_estimates_still_reach_debate(store, policy):
    class UnknownInitial(DemoModel):
        async def structured(self, role, contract, context):
            if role == "analyst_lead":
                return Forecast(
                    probability=None,
                    scenarios=[],
                    stressed_loss=None,
                    evidence_ids=[],
                    rationale="Unknown",
                    gaps=["Initial information gap"],
                )
            return await super().structured(role, contract, context)

    model = UnknownInitial()
    result = await Workflow(policy, store, model, DemoResearch()).run()
    assert len(result["debated"]) == 3
    assert any(role == "orchestrator" for role, _ in model.calls)


async def test_unsupported_final_forecast_deferred(store, policy):
    class UnsupportedJudge(DemoModel):
        async def structured(self, role, contract, context):
            if contract is Verdict:
                return Verdict(
                    decision="APPROVE",
                    forecast=Forecast(
                        probability=None,
                        scenarios=[],
                        stressed_loss=None,
                        evidence_ids=[],
                        rationale="Unknown",
                        gaps=["Missing verification"],
                    ),
                    rationale="Mistaken approval",
                    dissent="",
                )
            return await super().structured(role, contract, context)

    await Workflow(policy, store, UnsupportedJudge(), DemoResearch()).run()
    stages = store.latest("AAPL")
    assert stages["effective_verdict"]["decision"] == "DEFER"
    assert not stages["allocation_preview"]["validation"]["accepted"]


async def test_failed_source_blocks_added_exposure_but_does_not_force_exit(store, policy):
    class MissingSocial(DemoResearch):
        async def collect(self, instrument, cutoff):
            items, attempts = await super().collect(instrument, cutoff)
            attempts[-1] = attempts[-1].model_copy(update={"coverage": Coverage.FAILED})
            return items, attempts

    result = await Workflow(policy, store, DemoModel(), MissingSocial()).run()
    stages = store.latest("AAPL")
    assert result["status"] == "INCOMPLETE"
    assert not stages["research"]["complete"]
    assert not complete_coverage([])
    assert stages["holding_review_preview"]["allocation"]["action"] == "HOLD"
    assert not stages["allocation_preview"]["validation"]["accepted"]


async def test_unknown_citation_is_recorded_as_error(store, policy):
    class ForgedCitations(DemoModel):
        async def structured(self, role, contract, context):
            result = await super().structured(role, contract, context)
            if role == "analyst_lead":
                return result.model_copy(update={"evidence_ids": ["fabricated-news"]})
            return result

    result = await Workflow(policy, store, ForgedCitations(), DemoResearch()).run()
    assert result["status"] == "INCOMPLETE"
    assert result["debated"] == []
    assert "frozen record" in store.latest("AAPL")["error"]["reason"]


async def test_session_lease_blocks_concurrent_run(store, policy):
    store.acquire("decision-session", "another-process", 100)
    with pytest.raises(ValueError, match="already running"):
        await Workflow(policy, store, DemoModel(), DemoResearch()).run()


async def test_model_failure_keeps_cash_and_releases_lease(store, policy):
    class Broken(DemoModel):
        async def structured(self, *args):
            raise RuntimeError("Provider unavailable")

    result = await Workflow(policy, store, Broken(), DemoResearch()).run()
    assert result["status"] == "INCOMPLETE"
    assert store.snapshot().cash == Decimal("9000")
    assert store.acquire("decision-session", "next-process", 10)


async def test_chat_has_read_only_context_and_persistence(store, policy):
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True)
    reply = await service.ask("Explain the thesis", "AAPL")
    assert "DEMO" in reply
    assert service.chat_context("AAPL")["orders"].startswith("Disabled")
    assert len(store.chat_history()) == 2
    with pytest.raises(ValueError):
        await service.ask(" ", "AAPL")
    await service.close()
