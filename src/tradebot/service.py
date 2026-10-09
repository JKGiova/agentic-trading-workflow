"""Application services consumed by the terminal; no model receives mutation tools."""

import asyncio
import re
from decimal import Decimal

from tradebot.broker import AlpacaReadOnly
from tradebot.contracts import Position, Snapshot, utcnow
from tradebot.models import DemoModel, OpenRouter
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
    def __init__(self, store: Store, policy: Policy, credentials: Credentials, demo: bool = False):
        self.store, self.policy, self.demo = store, policy, demo
        existing = store.snapshot()
        if existing and existing.source.startswith("DEMO") != demo:
            raise ValueError("Demo and provider data require separate databases")
        self.broker = None if demo else AlpacaReadOnly(credentials, policy)
        self.model = DemoModel() if demo else OpenRouter(credentials, policy, store)
        self.research = DemoResearch() if demo else Research(credentials, policy)
        self.workflow = Workflow(policy, store, self.model, self.research, self.broker)
        self.refresh_lock = asyncio.Lock()
        self.chat_lock = asyncio.Lock()
        self.session_lock = asyncio.Lock()
        self.closed = False

    async def close(self):
        if self.closed:
            return
        self.closed = True
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
            else:
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
        return {
            "mode": "DEMO" if self.demo else "RESEARCH_ONLY",
            "selected": selected,
            "snapshot": snapshot.model_dump(mode="json") if snapshot else None,
            "selected_reports": excerpts,
            "evidence": [{**x, "text": x["text"][:500]} for x in research.get("evidence", [])[:8]],
            "coverage": research.get("coverage", []),
            "orders": "Disabled. All proposals are nonexecutable previews.",
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
