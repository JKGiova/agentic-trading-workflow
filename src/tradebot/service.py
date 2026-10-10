"""Application services consumed by the terminal; no model receives mutation tools."""

import asyncio
import re
from decimal import Decimal

from tradebot.broker import AlpacaReadOnly
from tradebot.contracts import Position, Snapshot, utcnow
from tradebot.models import DemoModel, model_client
from tradebot.research import DemoResearch, Research
from tradebot.settings import Credentials, Instrument, Policy
from tradebot.storage import Store
from tradebot.workflow import Workflow


def demo_policy() -> Policy:
    return Policy(
        instruments=[
            Instrument(symbol="AAPL", name="Apple", sector="technology"),
            Instrument(symbol="NVDA", name="NVIDIA", sector="technology"),
            Instrument(symbol="MSFT", name="Microsoft", sector="technology"),
        ],
        risk={"portfolio_stress_budget": "2000"},
    )


def demo_snapshot() -> Snapshot:
    return Snapshot(
        as_of=utcnow(),
        cash=9000,
        positions=[
            Position(
                symbol="AAPL",
                quantity=2,
                average_price=230,
                price=250,
                sector="technology",
                thesis="DEMO: synthetic earnings-growth thesis",
            ),
            Position(
                symbol="NVDA",
                quantity=4,
                average_price=110,
                price=125,
                sector="technology",
                thesis="DEMO: synthetic datacenter-growth thesis",
            ),
        ],
        baseline_equity=9500,
        daily_start_equity=10000,
        source="DEMO — synthetic fixtures, no real positions or returns",
        reconciled=True,
    )


class TradeService:
    def __init__(
        self,
        store: Store,
        policy: Policy,
        credentials: Credentials,
        demo: bool = False,
        continuous: bool = False,
    ):
        self.store, self.policy, self.demo = store, policy, demo
        existing = store.snapshot()
        if existing and existing.source.startswith("DEMO") != demo:
            raise ValueError("Demo and provider data require separate databases")
        self.continuous = continuous
        has_broker = bool(
            credentials.alpaca_api_key.get_secret_value()
            and credentials.alpaca_secret_key.get_secret_value()
        )
        self.broker = (
            None if demo or (continuous and not has_broker) else AlpacaReadOnly(credentials, policy)
        )
        self.model = DemoModel() if demo else model_client(credentials, policy, store)
        self.supervisor = None
        self.supervisor_task = None
        if continuous:
            from tradebot.analysis_memory import AnalysisMemory
            from tradebot.news_sources import NewsSources
            from tradebot.supervisor import AnalysisSupervisor
            from tradebot.telegram import DemoNotifier, TelegramNotifier

            memory = AnalysisMemory(store)
            self.research = DemoResearch() if demo else NewsSources(credentials, policy, memory)
            notifier = DemoNotifier() if demo else TelegramNotifier(credentials, memory)
            self.supervisor = AnalysisSupervisor(policy, store, self.model, self.research, notifier)
        else:
            self.research = DemoResearch() if demo else Research(credentials, policy)
        self.workflow = Workflow(policy, store, self.model, self.research, self.broker)
        self.refresh_lock = asyncio.Lock()
        self.chat_lock = asyncio.Lock()
        self.session_lock = asyncio.Lock()
        self.closed = False
        if self.supervisor:
            self.supervisor.refresh_positions = self.refresh

    async def close(self):
        if self.closed:
            return
        self.closed = True
        if self.supervisor:
            self.supervisor.stop.set()
            if self.supervisor_task:
                await asyncio.gather(self.supervisor_task, return_exceptions=True)
            await self.supervisor.notifier.close()
        await asyncio.gather(
            self.model.close(),
            self.research.close(),
            *([self.broker.close()] if self.broker else []),
        )
        self.store.close()

    async def refresh(self):
        if self.refresh_lock.locked():
            return
        async with self.refresh_lock:
            if self.demo:
                self.store.save_snapshot(demo_snapshot())
            elif self.broker:
                self.store.save_snapshot(await self.broker.snapshot(self.store.snapshot()))

    async def run_session(self, notify=lambda _message: None):
        if self.session_lock.locked():
            raise ValueError("A session is already running")
        async with self.session_lock:
            await self.refresh()
            return await self.workflow.run(notify)

    def chat_context(self, selected: str | None) -> dict:
        snapshot = self.store.snapshot()
        latest = self.store.latest(selected) if selected else {}
        excerpts = {}
        for stage in (
            "initial_forecast",
            "effective_verdict",
            "holding_review_preview",
            "allocation_preview",
        ):
            if stage in latest:
                excerpts[stage] = latest[stage]
        research = latest.get("research", {})
        continuous_report = (
            self.supervisor.latest_report(selected) if self.supervisor and selected else None
        )
        if continuous_report:
            role_summaries = continuous_report.get("synthesis_roles", continuous_report["roles"])
            continuous_report = {
                **{
                    key: value
                    for key, value in continuous_report.items()
                    if key != "synthesis_roles"
                },
                "evidence": [
                    {**item, "text": item["text"][:500]}
                    for item in continuous_report["evidence"][:6]
                ],
                "roles": {role: findings[-2:] for role, findings in role_summaries.items()},
            }
        return {
            "mode": "DEMO" if self.demo else "RESEARCH_ONLY",
            "selected": selected,
            "snapshot": snapshot.model_dump(mode="json") if snapshot else None,
            "selected_reports": excerpts,
            "evidence": [{**x, "text": x["text"][:500]} for x in research.get("evidence", [])[:8]],
            "coverage": research.get("coverage", []),
            "orders": "Disabled. All proposals are nonexecutable previews.",
            "continuous_report": continuous_report,
        }

    async def ask(self, question: str, selected: str | None) -> str:
        question = question.strip()
        if not question:
            raise ValueError("Enter a question")
        async with self.chat_lock:
            # An explicit single ticker/name can inspect a researched stock not currently held.
            mentions = []
            for instrument in self.policy.instruments:
                names = [instrument.symbol, instrument.name, *instrument.aliases]
                if any(
                    re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", question, re.IGNORECASE)
                    for name in names
                ):
                    mentions.append(instrument.symbol)
            context_stock = mentions[0] if len(mentions) == 1 else selected
            history = self.store.chat_history()
            self.store.append_chat("user", question[:2000])
            try:
                reply = await self.model.answer(
                    question[:2000], self.chat_context(context_stock), history
                )
            except (ValueError, RuntimeError):
                self.store.append_chat("assistant", "Request failed; no action performed.")
                raise
            self.store.append_chat("assistant", reply)
            return reply

    def performance(self) -> dict:
        snapshot = self.store.snapshot()
        if not snapshot:
            return {"status": "No snapshot; refresh or configure provider access"}
        pnl = snapshot.equity - snapshot.baseline_equity
        return {
            "equity": snapshot.equity,
            "cash": snapshot.cash,
            "reserved": snapshot.reserved,
            "gross": sum((p.value for p in snapshot.positions), Decimal(0)),
            "unrealized": sum((p.unrealized for p in snapshot.positions), Decimal(0)),
            "since_first_snapshot": pnl,
            "change_percent": pnl / snapshot.baseline_equity * 100
            if snapshot.baseline_equity
            else 0,
            "model_spend": self.store.model_spend(),
            "as_of": snapshot.as_of,
            "source": snapshot.source,
            "reconciled": snapshot.reconciled,
            "caveat": "Equity change includes deposits/withdrawals; not a time-weighted return.",
        }

    async def run_supervisor(self, notify=lambda _: None):
        if not self.supervisor:
            raise ValueError("Continuous analysis was not enabled")
        self.supervisor.notify = notify
        if self.supervisor_task:
            raise ValueError("Supervisor already started")
        await self.refresh()
        self.supervisor_task = asyncio.create_task(self.supervisor.run())
        await self.supervisor_task

    async def run_analysis_cycle(self):
        """One completed cycle; demo uses an injected clock rather than waiting hours."""
        if not self.supervisor:
            raise ValueError("Continuous analysis was not enabled")
        await self.refresh()
        supervisor = self.supervisor
        if self.demo:
            from datetime import datetime, timedelta

            from tradebot.contracts import utcnow

            now = utcnow()
            supervisor.clock = lambda: now
            supervisor.agent.clock = lambda: now
            cycle = supervisor.current()
            await supervisor.collect()
            while await supervisor.work_one():
                pass
            now = datetime.fromisoformat(cycle["end"]) + timedelta(microseconds=1)
            supervisor.rollover()
            await supervisor.close_pending()
            return supervisor.memory.cycle(cycle["id"])
        initial = supervisor.current()["id"]
        running = asyncio.create_task(self.run_supervisor())
        try:
            while supervisor.memory.cycle(initial)["status"] != "CLOSED":
                if running.done():
                    await running
                    raise RuntimeError("Supervisor stopped before report closure")
                await asyncio.sleep(0.5)
            return supervisor.memory.cycle(initial)
        finally:
            supervisor.stop.set()
            await running
