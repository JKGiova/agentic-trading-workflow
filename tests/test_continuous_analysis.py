import asyncio
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import update

from tradebot.analysis_memory import AnalysisMemory, cycles, events, outbox, tasks
from tradebot.analysts import AgentTurn, Finding
from tradebot.contracts import Category, Coverage, Forecast, SearchAttempt, utcnow
from tradebot.models import DemoModel
from tradebot.research import make_evidence
from tradebot.service import TradeService
from tradebot.settings import Credentials
from tradebot.supervisor import AnalysisSupervisor
from tradebot.telegram import DemoNotifier


class Clock:
    def __init__(self):
        self.now = utcnow()

    def __call__(self):
        return self.now


class Sources:
    def __init__(self, clock, empty=False):
        self.clock, self.empty, self.calls = clock, empty, []
        self.date = clock() - timedelta(minutes=5)

    async def collect(self, instrument, cutoff):
        self.calls.append(instrument.symbol)
        items = (
            []
            if self.empty
            else [
                make_evidence(
                    "fixture",
                    "one",
                    instrument.symbol,
                    Category.COMPANY,
                    "Announcement",
                    "Original source",
                    "https://example.com/release",
                    self.date,
                )
            ]
        )
        attempts = [
            SearchAttempt(
                stock=instrument.symbol,
                category=category,
                source="fixture",
                query=instrument.symbol,
                start=cutoff - timedelta(hours=3),
                cutoff=cutoff,
                completed_at=cutoff,
                coverage=Coverage.RESULTS if items else Coverage.EMPTY,
                evidence_ids=[x.id for x in items],
                reason="Executed fixture",
            )
            for category in Category
        ]
        return items, attempts

    async def execute(self, request, task, context, now):
        return {"status": "EXECUTED", "evidence": context["evidence"]}


@pytest.fixture
def clock():
    return Clock()


def supervisor(store, policy, clock, model=None, source=None):
    return AnalysisSupervisor(
        policy, store, model or DemoModel(), source or Sources(clock), DemoNotifier(), clock=clock
    )


async def drain(team):
    while await team.work_one():
        pass


@pytest.mark.parametrize("failed", [False, True])
async def test_busy_cycle_synthesis_is_bounded_citation_checked_and_recoverable(
    store, policy, clock, failed
):
    import json

    team = supervisor(store, policy, clock)
    cycle = team.current()
    evidence, _ = await team.research.collect(policy.instruments[0], clock())
    source_id = evidence[0].id
    findings = [
        Finding(
            summary=f"Item {index}: " + "Detailed assessment " * 40,
            direction="mixed",
            evidence_ids=[source_id],
            opposing_evidence=["An independent disagreement remains"],
            gaps=["Missing numerical company facts"],
            claims=[{"text": "Original announcement", "evidence_ids": [source_id]}],
        ).model_dump(mode="json")
        for index in range(80)
    ]
    before = json.dumps(findings)
    if failed:

        async def forged(role, contract, context):
            team.model.calls.append((role, context))
            return finish_turn(["fabricated"]).report

        team.model.structured = forged
    summary = await team.summarize_role(cycle, "AAPL", "company", findings, evidence)
    assert len(json.dumps(summary).encode()) <= 4500
    assert all(set(row["evidence_ids"]) <= {source_id} for row in summary)
    assert json.dumps(findings) == before  # Compaction never replaces original assessments.
    if failed:
        assert any("incomplete" in gap for row in summary for gap in row["gaps"])
    calls = len(team.model.calls)
    assert calls > 1
    assert all(len(json.dumps(context).encode()) < 30000 for _, context in team.model.calls)
    restarted = supervisor(store, policy, clock)
    assert await restarted.summarize_role(cycle, "AAPL", "company", findings, evidence) == summary
    assert not restarted.model.calls  # Committed summaries survive process replacement.


def finish_turn(ids=()):
    return AgentTurn(
        action="FINISH",
        report=Finding(
            summary="Assessment",
            direction="mixed",
            evidence_ids=list(ids),
            opposing_evidence=["Dissent"],
            gaps=[],
            questions=["Material gap?"],
        ),
    )


async def test_continuous_cycle_cross_review_reports_and_overlap(store, policy, clock):
    team = supervisor(store, policy, clock)
    first = team.current()
    await team.collect()
    await drain(team)
    rows = team.memory.rows(tasks)
    assert {row["role"] for row in rows} == {c.value for c in Category}
    assert {row["phase"] for row in rows} == {"original", "peer"}
    calls = team.model.calls
    originals = [view for _, view in calls if view.get("phase") == "original"]
    assert all(not view["peer_originals"] for view in originals)
    assert any(view["peer_originals"] for _, view in calls if view.get("phase") == "peer")
    count = len(rows)
    await team.collect()
    await drain(team)
    assert len(team.memory.rows(tasks)) == count  # Same event/version is not repeatedly reanalyzed.
    clock.now += timedelta(hours=policy.session_hours)
    next_cycle = team.rollover()
    assert next_cycle["start"] == first["end"]
    assert next_cycle["id"] != first["id"]
    assert team.memory.cycle(first["id"])["status"] == "CLOSING"
    await team.close_pending()
    closed = team.memory.cycle(first["id"])
    assert closed["status"] == "CLOSED"
    assert set(closed["payload"]["reports"]) == {"AAPL", "NVDA", "MSFT"}
    assert all(r["debate_status"] == "PENDING" for r in closed["payload"]["reports"].values())
    assert {x["stock"] for x in store.queue_status()} == {"AAPL", "NVDA", "MSFT"}
    assert team.memory.rows(outbox)
    assert "confidence" in team.summary(closed)
    assert "Dissent" in team.summary(closed)
    assert team.latest_report("AAPL")["cutoff"] == first["end"]
    assert team.latest_report("UNKNOWN") is None
    assert team.status()["cycle"] == next_cycle["id"]
    calls_before = len(team.model.calls)
    await team.close_pending()
    assert len(team.model.calls) == calls_before


async def test_zero_results_no_paid_idle_spin_and_holding_outside_watchlist(store, policy, clock):
    policy = policy.model_copy(update={"instruments": policy.instruments[:1]})
    source = Sources(clock, empty=True)
    team = supervisor(store, policy, clock, source=source)
    await team.collect()
    await drain(team)
    calls = len(team.model.calls)
    assert {"AAPL", "NVDA"} <= set(source.calls)
    for _ in range(3):
        await team.collect()
        await drain(team)
    assert len(team.model.calls) == calls
    assert not await team.work_one()
    clock.now += timedelta(hours=3)
    first = team.memory.rows(cycles, cycles.c.status == "OPEN")[0]
    team.rollover()
    await team.close_pending()
    assert set(team.memory.cycle(first["id"])["payload"]["reports"]) == {"AAPL", "NVDA"}


def test_event_corrections_cutoff_and_future_observation(store, policy, clock):
    memory = AnalysisMemory(store)
    old = make_evidence(
        "fixture",
        "event",
        "AAPL",
        Category.COMPANY,
        "Initial",
        "old",
        "https://example.com",
        clock() - timedelta(minutes=1),
    )
    memory.remember([old], clock())
    cutoff = clock()
    clock.now += timedelta(seconds=1)
    corrected = make_evidence(
        "fixture",
        "event",
        "AAPL",
        Category.COMPANY,
        "Amended",
        "new",
        "https://example.com",
        old.published_at,
    )
    memory.remember([corrected], clock())
    assert [x.id for x in memory.evidence("AAPL", cutoff)] == [old.id]
    versions = memory.rows(events)
    assert len(versions) == 2
    assert any(row["predecessor"] for row in versions)
    assert len(memory.evidence("AAPL", clock())) == 2
    assert not memory.evidence("AAPL", clock(), clock() + timedelta(hours=1))


def test_task_lease_fencing_expiry_and_final_retry(store, policy, clock):
    memory = AnalysisMemory(store)
    cycle = memory.open_cycle(clock(), 3, ["AAPL"], "policy")
    memory.ingest(cycle, "AAPL", [], [], clock(), 100)
    first = memory.claim(clock(), 1, 2)
    cp = {"context": {"evidence": []}, "rounds": 1}
    memory.checkpoint(first, cp, clock())
    clock.now += timedelta(seconds=2)
    second = memory.claim(clock(), 20, 2)
    # Fairness claims unattempted tasks first; explicitly reclaim after exhausting those.
    others = [second]
    for _ in range(2):
        others.append(memory.claim(clock(), 20, 2))
    reclaimed = memory.claim(clock(), 1, 2)
    assert reclaimed["id"] == first["id"]
    assert reclaimed["payload"]["checkpoint"] == cp
    with pytest.raises(ValueError, match="expired|reclaimed"):
        memory.checkpoint(first, {}, clock())
    with pytest.raises(ValueError, match="Stale"):
        memory.finish(first, {}, clock())
    clock.now += timedelta(seconds=2)
    assert memory.claim(clock(), 1, 2) is None
    assert memory.rows(tasks, tasks.c.id == first["id"])[0]["status"] == "FAILED"
    memory.fail(first, clock(), 2, "stale")
    assert memory.rows(tasks, tasks.c.id == first["id"])[0]["status"] == "FAILED"


async def test_checkpoint_recovery_does_not_repeat_completed_model_or_tool(store, policy, clock):
    team = supervisor(store, policy, clock)
    await team.collect()
    task = team.memory.claim(clock(), 300, 2)
    context = team.context(task)
    # Simulate a crash after committing the model's next tool request.
    cp = {
        "context": context,
        "pending": AgentTurn(
            action="READ_EVIDENCE", evidence_id=context["evidence"][0]["id"]
        ).model_dump(mode="json"),
    }
    team.memory.checkpoint(task, cp, clock())
    tool_calls = []

    async def execute(*args):
        tool_calls.append(args[0].action)
        return {"status": "EXECUTED", "evidence": context["evidence"]}

    team.research.execute = execute
    result = await team.agent.run(task, context)
    assert result["summary"].startswith("DEMO")
    assert tool_calls == ["READ_EVIDENCE"]
    calls = len(team.model.calls)
    await team.agent.run(task, context)
    assert len(team.model.calls) == calls
    assert tool_calls == ["READ_EVIDENCE"]


async def test_tool_loops_budget_unavailability_and_forged_citations(store, policy, clock):
    team = supervisor(store, policy, clock)
    await team.collect()
    task = team.memory.claim(clock(), 300, 2)
    context = team.context(task)

    class AlwaysSearch:
        async def structured(self, *args):
            return AgentTurn(action="SEARCH_NEWS", query="guidance")

    team.agent.model = AlwaysSearch()

    async def failed_tool(*args):
        raise RuntimeError("unavailable")

    team.research.execute = failed_tool
    result = await team.agent.run(task, context)
    assert result["direction"] == "unknown"
    assert len(task["payload"]["checkpoint"]["tools"]) == policy.agent_tool_rounds
    assert task["payload"]["checkpoint"]["tools"][0]["status"] == "UNAVAILABLE"
    task2 = team.memory.claim(clock(), 300, 2)
    context2 = team.context(task2)

    class Forged:
        async def structured(self, *args):
            return finish_turn(["invented"])

    team.agent.model = Forged()
    with pytest.raises(ValueError, match="cited"):
        await team.agent.run(task2, context2)


async def test_late_completion_and_news_boundary_cannot_change_manifest(store, policy, clock):
    team = supervisor(store, policy, clock)
    cycle = team.current()
    await team.collect()
    task = team.memory.claim(clock(), 4 * 3600, 2)
    context = team.context(task)
    result = await team.agent.run(task, context)
    clock.now += timedelta(hours=3)
    team.rollover()
    before = team.memory.cycle(cycle["id"])["payload"]
    assert team.memory.finish(task, result, clock()) == "LATE"
    assert team.memory.cycle(cycle["id"])["payload"] == before
    late = make_evidence(
        "fixture", "late", "AAPL", Category.COMPANY, "Late", "late", "https://example.com", clock()
    )
    team.memory.remember([late], clock())
    await team.close_pending()
    report = team.memory.cycle(cycle["id"])["payload"]["reports"]["AAPL"]
    assert late.id not in {x["id"] for x in report["evidence"]}
    assert task["id"] not in before["manifest"]
    assert report["unfinished"]


async def test_source_failure_budget_exhaustion_and_incomplete_synthesis(store, policy, clock):
    policy = policy.model_copy(update={"cycle_model_budget": Decimal(0)})
    source = Sources(clock)

    async def unavailable(*args):
        raise RuntimeError("source access missing")

    source.collect = unavailable
    team = supervisor(store, policy, clock, source=source)
    cycle = team.current()
    await team.collect()
    await drain(team)
    clock.now += timedelta(seconds=3)
    await drain(team)
    assert all(row["status"] == "FAILED" for row in team.memory.rows(tasks))

    class BrokenLead:
        async def structured(self, role, contract, context):
            if role == "analyst_lead":
                raise RuntimeError("model unavailable")

    team.model = BrokenLead()
    clock.now += timedelta(hours=3)
    team.rollover()
    await team.close_pending()
    report = team.memory.cycle(cycle["id"])["payload"]["reports"]["AAPL"]
    assert report["forecast"]["probability"] is None
    assert all(a["coverage"] == "FAILED" for a in report["coverage"])
    assert "No completed" in report["roles"]["market"][0]["summary"]
    with pytest.raises(ValueError, match="immutable"):
        team.memory.save_report(cycle["id"], "AAPL", {"changed": True})


async def test_pending_reports_restart_and_policy_change(store, policy, clock):
    team = supervisor(store, policy, clock)
    first = team.current()
    await team.collect()
    await drain(team)
    clock.now += timedelta(hours=3)
    team.rollover()
    other = supervisor(store, policy, clock)
    await other.close_pending()
    assert other.memory.cycle(first["id"])["status"] == "CLOSED"
    with pytest.raises(ValueError, match="policy changed"):
        AnalysisMemory(store).open_cycle(clock(), 3, ["AAPL"], "changed")
    current = other.current()
    clock.now += timedelta(hours=10)
    next_cycle = other.rollover()
    assert next_cycle["payload"]["downtime_windows"] == 2
    assert next_cycle["start"] > current["end"]


async def test_real_run_shutdown_single_supervisor_and_delivery_recovery(store, policy, clock):
    team = supervisor(store, policy, clock)
    team.memory.queue_summary("old", ["pending"], clock())
    row = team.memory.rows(outbox)[0]
    team.memory.delivery_result(row, "SENDING", clock())
    job = asyncio.create_task(team.run())
    for _ in range(50):
        await asyncio.sleep(0.01)
        if team.memory.rows(tasks):
            break
    competing = supervisor(store, policy, clock)
    with pytest.raises(ValueError, match="Another"):
        await competing.run()
    team.stop.set()
    await asyncio.wait_for(job, 3)
    assert team.memory.rows(outbox)[0]["status"] == "UNKNOWN"
    assert store.acquire("analysis-supervisor", "new", 60) is not False
    store.release("analysis-supervisor", "new")


async def test_loop_error_and_lease_loss_stop_cleanly(store, policy, clock):
    team = supervisor(store, policy, clock)
    messages = []
    team.notify = messages.append

    async def bad():
        team.stop.set()
        raise RuntimeError("fail")

    await team._loop(bad, 0.001)
    assert messages
    team.stop.clear()
    job = asyncio.create_task(team.run())
    await asyncio.sleep(0.05)
    from tradebot.storage import leases

    with store.transaction() as conn:
        conn.execute(
            update(leases).where(leases.c.name == "analysis-supervisor").values(owner="other")
        )
    await asyncio.wait_for(job, 3)
    assert team.stop.is_set()


def test_task_cap_and_cycle_freeze_validation(store, clock):
    memory = AnalysisMemory(store)
    cycle = memory.open_cycle(clock(), 3, ["AAPL"], "fixed")
    with pytest.raises(ValueError, match="unexpired"):
        memory.freeze(cycle["id"], clock())
    items = [
        make_evidence(
            "fixture",
            str(i),
            "AAPL",
            Category.COMPANY,
            str(i),
            "content",
            "https://example.com",
            clock() - timedelta(seconds=1),
        )
        for i in range(8)
    ]
    memory.ingest(cycle, "AAPL", items, [], clock(), 4)
    assert len(memory.rows(tasks)) >= 4
    assert memory.cycle(cycle["id"])["payload"]["deferred_events"]
    clock.now += timedelta(hours=3)
    frozen = memory.freeze(cycle["id"], clock())
    assert memory.freeze(cycle["id"], clock()) == frozen
    memory.ingest(cycle, "OTHER", items, [], clock(), 4)
    assert "OTHER" not in memory.cycle(cycle["id"])["payload"]["stocks"]


async def test_service_continuous_demo_cycle_chat_and_close(store, policy):
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True, continuous=True)
    cycle = await service.run_analysis_cycle()
    assert cycle["status"] == "CLOSED"
    assert service.chat_context("AAPL")["continuous_report"]
    assert (await service.ask("Explain NVIDIA", None)).startswith("DEMO")
    await service.close()
    await service.close()


@pytest.mark.parametrize("action", ["FINISH", "READ_PAGE", "READ_EVIDENCE"])
def test_typed_tool_invalid_requests(action):
    with pytest.raises(ValueError):
        AgentTurn(action=action)
    if action != "FINISH":
        with pytest.raises(ValueError):
            AgentTurn(action=action, evidence_id="id", report=finish_turn().report)


def test_cycle_budget_reservation_atomic_and_lineage_preserved(store):
    scope = {"cycle": "one", "kind": "research", "cap": Decimal(".05")}
    cid = store.reserve_model("company", Decimal(".04"), Decimal(30), scope)
    store.settle_model(cid, None, {"usage": {"prompt_tokens": 10}})
    with pytest.raises(ValueError, match="Cycle"):
        store.reserve_model("market", Decimal(".02"), Decimal(30), scope)
    assert store.reserve_model("lead", Decimal(".02"), Decimal(30), {**scope, "kind": "closing"})


def test_parallel_task_claims_and_outbox_claims_are_unique(store, clock):
    from concurrent.futures import ThreadPoolExecutor

    memory = AnalysisMemory(store)
    cycle = memory.open_cycle(clock(), 3, ["AAPL"], "fixed")
    memory.ingest(cycle, "AAPL", [], [], clock(), 40)
    with ThreadPoolExecutor(max_workers=8) as pool:
        claimed = list(pool.map(lambda _: memory.claim(clock(), 60, 2), range(8)))
    claimed = [row for row in claimed if row]
    assert len(claimed) == len({row["id"] for row in claimed}) == 4
    memory.queue_summary(cycle["id"], ["summary"], clock())
    row = memory.rows(outbox)[0]
    with ThreadPoolExecutor(max_workers=8) as pool:
        sent = list(pool.map(lambda _: memory.claim_delivery(row, clock()), range(8)))
    assert sum(sent) == 1


@pytest.mark.postgres
def test_postgres_continuous_memory_claims_and_cycle_cap(clock):
    import os
    import uuid

    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    from tradebot.storage import Store

    url = os.environ.get("TRADEBOT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TRADEBOT_TEST_DATABASE_URL for isolated PostgreSQL integration")
    schema = "analysis_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    db_url = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
    db = Store(db_url.render_as_string(hide_password=False))
    try:
        test_parallel_task_claims_and_outbox_claims_are_unique(db, clock)
        test_cycle_budget_reservation_atomic_and_lineage_preserved(db)
        memory = AnalysisMemory(db)
        # queue_summary in the outbox check already closed its cycle.
        clock.now += timedelta(hours=3)
        cycle = memory.open_cycle(clock(), 3, ["AAPL"], "fixed")
        assert cycle["status"] == "OPEN"
        clock.now += timedelta(hours=3)
        assert memory.freeze(cycle["id"], clock())["status"] == "CLOSING"
    finally:
        db.close()
        with admin.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


async def test_unfinished_news_carries_across_boundary_and_restart(store, policy, clock):
    team = supervisor(store, policy, clock)
    first = team.current()
    await team.collect()
    original_events = {row["event"] for row in team.memory.rows(tasks) if row["event"]}
    clock.now += timedelta(hours=3)
    # Crash between freezing the old cycle and opening/carrying the next one.
    team.memory.freeze(first["id"], clock())
    recovered = supervisor(store, policy, clock)
    current = recovered.rollover()
    carried = {
        row["event"]
        for row in recovered.memory.rows(tasks, tasks.c.cycle == current["id"])
        if row["event"]
    }
    assert carried == original_events
    count = len(recovered.memory.rows(tasks))
    recovered.memory.carry(recovered.memory.cycle(first["id"]), current, clock(), 240)
    assert len(recovered.memory.rows(tasks)) == count
    await drain(recovered)
    assert recovered.memory.findings("AAPL", clock(), cycle=current["id"], phase="original")


async def test_forecast_citation_forgery_is_incomplete_not_an_approval(store, policy, clock):
    team = supervisor(store, policy, clock)
    first = team.current()
    await team.collect()
    await drain(team)

    class ForgedLead(DemoModel):
        async def structured(self, role, contract, context):
            forecast = await super().structured(role, contract, context)
            return forecast.model_copy(update={"evidence_ids": ["made-up"]})

    team.model = ForgedLead()
    clock.now += timedelta(hours=3)
    team.rollover()
    await team.close_pending()
    assert (
        team.memory.cycle(first["id"])["payload"]["reports"]["AAPL"]["forecast"]["probability"]
        is None
    )


async def test_refresh_failure_keeps_mandatory_holdings(store, policy, clock):
    team = supervisor(store, policy.model_copy(update={"instruments": []}), clock)
    messages = []
    team.notify = messages.append

    async def failed():
        raise RuntimeError("broker unavailable")

    team.refresh_positions = failed
    await team.collect()
    assert set(team.research.calls) == {"AAPL", "NVDA"}
    assert any("stored holdings" in message for message in messages)


async def test_nvidia_team_to_telegram_end_to_end_http_contracts(store, policy, clock):
    import json

    import httpx

    from tradebot.models import NvidiaNIM
    from tradebot.telegram import TelegramNotifier

    calls, delivered = [], []
    fixtures = DemoModel()

    async def handler(request):
        body = json.loads(request.content)
        if request.url.host == "api.telegram.org":
            delivered.append(body)
            return httpx.Response(200, json={"ok": True, "result": {"message_id": len(delivered)}})
        assert request.url.host == "integrate.api.nvidia.com"
        role = (
            body["messages"][0]["content"].split(" in an auditable")[0].removeprefix("You are the ")
        )
        context = json.loads(body["messages"][1]["content"])
        calls.append((role, context))
        contract = (
            Forecast
            if role == "analyst_lead"
            else Finding
            if role.endswith("_cycle_summary")
            else AgentTurn
        )
        output = await fixtures.structured(role, contract, context)
        return httpx.Response(
            200,
            json={
                "model": policy.model,
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                "choices": [
                    {"finish_reason": "stop", "message": {"content": output.model_dump_json()}}
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        creds = Credentials(
            _env_file=None,
            nvidia_api_key="private-nvidia",
            telegram_bot_token="private-telegram",
            telegram_chat_id="42",
        )
        model = NvidiaNIM(creds, policy, store, client)
        memory = AnalysisMemory(store)
        notifier = TelegramNotifier(creds, memory, client)
        team = AnalysisSupervisor(policy, store, model, Sources(clock), notifier, clock=clock)
        first = team.current()
        await team.collect()
        await drain(team)
        clock.now += timedelta(hours=3)
        team.rollover()
        await team.close_pending()
        await notifier.deliver(clock())
        assert team.memory.cycle(first["id"])["status"] == "CLOSED"
        assert {
            "market_analyst",
            "financial_analyst",
            "company_analyst",
            "social_analyst",
            "analyst_lead",
        } <= {role for role, _ in calls}
        assert delivered and all(message["chat_id"] == "42" for message in delivered)
        assert all(row["status"] == "SENT" for row in memory.rows(outbox))
        assert store.model_spend() > 0


async def test_provider_service_one_cycle_and_shutdown(tmp_path, policy):
    from tradebot.storage import Store

    # NVIDIA and yfinance access are explicitly replaced by validated fixture implementations.
    db = Store(f"sqlite:///{tmp_path / 'provider.db'}")
    policy = policy.model_copy(update={"session_hours": 0.00002})
    service = TradeService(
        db, policy, Credentials(_env_file=None, nvidia_api_key="fixture"), continuous=True
    )
    await service.model.close()
    await service.research.close()
    fixture = DemoModel()
    source = Sources(utcnow)

    async def close():
        pass

    source.close = close
    service.model = service.supervisor.model = service.supervisor.agent.model = fixture
    service.research = service.supervisor.research = service.supervisor.agent.tools = source
    try:
        result = await asyncio.wait_for(service.run_analysis_cycle(), 4)
        assert result["status"] == "CLOSED"
        with pytest.raises(ValueError, match="already started"):
            await service.run_supervisor()
    finally:
        await service.close()


async def test_noncontinuous_service_rejects_supervisor_operations(store, policy):
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True)
    with pytest.raises(ValueError, match="not enabled"):
        await service.run_supervisor()
    with pytest.raises(ValueError, match="not enabled"):
        await service.run_analysis_cycle()
    await service.close()


async def test_unexpected_background_failure_stops_and_releases_lease(store, policy, clock):
    team = supervisor(store, policy, clock)

    async def unexpected():
        raise LookupError("Unexpected subsystem error")

    team.collect = unexpected
    with pytest.raises(RuntimeError, match="LookupError"):
        await asyncio.wait_for(team.run(), 2)
    assert store.acquire("analysis-supervisor", "new", 1)
    store.release("analysis-supervisor", "new")
