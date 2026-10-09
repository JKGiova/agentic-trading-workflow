"""Explicit LangGraph research stages, fair debate queue and a separate Allocator."""

import asyncio
import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from tradebot.contracts import (
    Action,
    Allocation,
    Case,
    Category,
    Coverage,
    Evidence,
    Forecast,
    Report,
    SearchAttempt,
    Snapshot,
    Verdict,
    utcnow,
)
from tradebot.risk import preview
from tradebot.settings import Instrument, Policy
from tradebot.storage import Store


class StockState(TypedDict, total=False):
    stock: str
    instrument: Instrument
    evidence: list[Evidence]
    attempts: list[SearchAttempt]
    snapshot: Snapshot
    session_id: str
    cutoff: str
    reference_price: str
    reports: dict[str, dict]
    initial: dict
    debate: dict


def complete_coverage(attempts: list[SearchAttempt]) -> bool:
    for category in Category:
        group = [x for x in attempts if x.category == category]
        if not group or any(x.coverage in {Coverage.DEGRADED, Coverage.FAILED} for x in group):
            return False
    return True


async def gathered(*coroutines):
    """Await every independent role even when one fails; leave no orphaned model calls."""
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException):
            raise result
    return results


class Workflow:
    def __init__(self, policy: Policy, store: Store, model, research, broker=None):
        self.policy, self.store = policy, store
        self.model, self.research, self.broker = model, research, broker
        graph = StateGraph(StockState)
        graph.add_node("independent_analysts", self._analysts)
        graph.add_node("lead_synthesis", self._lead)
        graph.add_edge(START, "independent_analysts")
        graph.add_edge("independent_analysts", "lead_synthesis")
        graph.add_edge("lead_synthesis", END)
        self.analysis_graph = graph.compile()
        debate = StateGraph(StockState)
        debate.add_node("bull_bear_debate", self._debate)
        debate.add_node("orchestrator_judgment", self._judge)
        debate.add_edge(START, "bull_bear_debate")
        debate.add_edge("bull_bear_debate", "orchestrator_judgment")
        debate.add_edge("orchestrator_judgment", END)
        self.debate_graph = debate.compile()

    def context(self, state: StockState) -> dict:
        position = state["snapshot"].position(state["stock"])
        selected = {}
        for category in Category:
            for item in [x for x in state["evidence"] if x.category == category][:3]:
                selected[item.id] = item
        snippets = []
        for item in selected.values():
            data = item.model_dump(mode="json")
            data["text"] = data["text"][:700]
            snippets.append(data)
        return {
            "stock": state["stock"],
            "company": state["instrument"].name,
            "information_cutoff": state["cutoff"],
            "reference_price": state["reference_price"],
            "outcome": "positive forward net total return",
            "horizon_trading_days": self.policy.horizon_trading_days,
            "cost_allowance_fraction": self.policy.risk.cost_buffer,
            "benchmark_outperformance": "Not estimated by v0.1; do not equate with positive return",
            "evidence": snippets,
            "coverage": [x.model_dump(mode="json") for x in state["attempts"]],
            "holding": position.model_dump(mode="json") if position else None,
            "initial": state.get("initial"),
        }

    async def invoke(self, state, stage, role, contract, context):
        digest = hashlib.sha256(
            json.dumps(context, sort_keys=True, default=str).encode()
        ).hexdigest()
        existing = self.store.stage(state["session_id"], state["stock"], stage)
        if existing:
            if existing.get("context_hash") != digest:
                raise ValueError("Immutable stage input changed; create a new session")
            return contract.model_validate(existing["output"])
        result = await self.model.structured(role, contract, context)
        valid_ids = {x["id"] for x in context["evidence"]}
        citations = getattr(result, "evidence_ids", [])
        if isinstance(result, Verdict):
            citations = result.forecast.evidence_ids
        if not set(citations).issubset(valid_ids):
            raise ValueError(f"{role} cited evidence outside the frozen record")
        if isinstance(result, Case) and not set(result.verification_ids).issubset(valid_ids):
            raise ValueError(
                "Verification requested outside frozen evidence; defer to later collection"
            )
        data = result.model_dump(mode="json")
        self.store.save_stage(
            state["session_id"],
            state["stock"],
            stage,
            {
                "output": data,
                "context_hash": digest,
                "prompt_version": "v0.1",
                "model": self.policy.model,
                "schema": contract.__name__,
                "cutoff": state["cutoff"],
                "reference_price": state["reference_price"],
            },
        )
        return result

    async def _analysts(self, state):
        async def independent(category):
            context = self.context(state)
            context["task"] = f"Independently analyze {category} news and stock relevance."
            # Independent calls see frozen evidence, never another analyst's conclusions.
            result = await self.invoke(
                state, f"analyst_{category}", f"{category}_analyst", Report, context
            )
            return category.value, result.model_dump(mode="json")

        reports = dict(await gathered(*(independent(category) for category in Category)))
        return {"reports": reports}

    async def _lead(self, state):
        context = self.context(state)
        context.update(
            reports=state["reports"],
            task="Synthesize conflicting reports without averaging votes; "
            "duplicate evidence URLs/events are not independent confirmation.",
        )
        result = await self.invoke(state, "initial_forecast", "analyst_lead", Forecast, context)
        return {"initial": result.model_dump(mode="json")}

    async def _debate(self, state):
        context = self.context(state)
        context["reports"] = state["reports"]
        transcript = {}
        # Openings and final cases are independent within each round.
        for phase in ("opening", "challenge", "rebuttal", "final"):

            async def side_case(side, phase=phase):
                view = dict(context)
                view["phase"] = phase
                view["prior_rounds"] = dict(transcript)
                if phase == "rebuttal":
                    ids = set()
                    for case in transcript["challenge"].values():
                        ids.update(case["verification_ids"])
                    view["verified_records"] = [
                        x.model_dump(mode="json") for x in state["evidence"] if x.id in ids
                    ]
                    view["verification_limit"] = (
                        "Bounded reread of frozen evidence only; "
                        "requests requiring new external facts must remain unresolved."
                    )
                view["task"] = (
                    f"Provide the {side} {phase}; evaluate confidence and upside against losses, "
                    "costs, liquidity, volatility, uncertainty and alternative scenarios. "
                    "Challenge at most three claims. Do not use share price as proof of upside. "
                    "No forced consensus; expose anything this bounded record cannot verify."
                )
                result = await self.invoke(
                    state, f"{side}_{phase}", f"{side}_researcher", Case, view
                )
                return side, result.model_dump(mode="json")

            transcript[phase] = dict(await gathered(*(side_case(x) for x in ("bull", "bear"))))
        return {"debate": transcript}

    async def _judge(self, state):
        context = self.context(state)
        context.update(
            reports=state["reports"],
            debate=state["debate"],
            task="Judge both final cases. Define revised probability/scenarios and dissent. "
            "APPROVE/DEFER/REJECT is a reasoned research verdict, never a numeric gate.",
        )
        verdict = await self.invoke(state, "verdict", "orchestrator", Verdict, context)
        forecast = verdict.forecast
        if verdict.decision == "APPROVE":
            supported = (
                forecast.probability is not None
                and forecast.stressed_loss is not None
                and bool(forecast.evidence_ids)
                and not forecast.gaps
            )
            nonsocial = {
                x.id for x in state["evidence"] if x.source != "x" and x.category != Category.SOCIAL
            }
            unresolved = any(case["unresolved"] for case in state["debate"]["final"].values())
            if (
                not supported
                or not set(forecast.evidence_ids).intersection(nonsocial)
                or unresolved
            ):
                verdict = verdict.model_copy(
                    update={
                        "decision": "DEFER",
                        "rationale": "Runtime deferred unsupported final evidence/scenarios "
                        "or unresolved verification. " + verdict.rationale,
                    }
                )
        self.store.save_stage(
            state["session_id"],
            state["stock"],
            "effective_verdict",
            verdict.model_dump(mode="json"),
        )
        return {"debate": {**state["debate"], "verdict": verdict.model_dump(mode="json")}}

    async def _allocate(self, state, verdict=None):
        context = self.context(state)
        context.update(
            reports=state["reports"],
            portfolio=state["snapshot"].model_dump(mode="json"),
            risk_policy=self.policy.risk.model_dump(mode="json"),
            verdict=verdict,
            task="Choose action and requested investment separately from research judgment. "
            "Without an approved entry debate only HOLD/REDUCE/CLOSE/NO_ACTION are admissible. "
            "Source failure alone is not an exit thesis. No averaging down. "
            "This is a nonexecutable preview; no broker orders can be sent.",
        )
        stage = "allocation" if verdict else "holding_review"
        allocation = await self.invoke(state, stage, "portfolio_allocator", Allocation, context)
        if not verdict and allocation.action in {Action.OPEN, Action.REINFORCE}:
            allocation = Allocation(
                action=Action.HOLD,
                requested_notional=0,
                rationale="Addition deferred until approved debate",
            )
        forecast = Forecast.model_validate(verdict["forecast"]) if verdict else None
        snapshot = state["snapshot"]
        # v0.1 previews conservatively stress other holdings/pending buys at 100% loss.
        existing_stress = sum(
            (p.value for p in snapshot.positions if p.symbol != state["stock"]), Decimal(0)
        )
        existing_stress += sum(
            (v for sym, v in snapshot.pending_buys.items() if sym != state["stock"]), Decimal(0)
        )
        check = preview(
            state["stock"],
            state["instrument"].sector,
            allocation,
            snapshot,
            forecast,
            self.policy.risk,
            Decimal(state["reference_price"]),
            state["stock"] in {x.symbol for x in self.policy.instruments},
            complete_coverage(state["attempts"]),
            bool(verdict and verdict["decision"] == "APPROVE"),
            existing_stress,
        )
        self.store.save_stage(
            state["session_id"],
            state["stock"],
            stage + "_preview",
            {
                "allocation": allocation.model_dump(mode="json"),
                "validation": check.model_dump(mode="json"),
                "executable": False,
            },
        )

    async def run(self, notify=lambda _text: None) -> dict:
        owner = hashlib.sha256(str(utcnow()).encode()).hexdigest()
        if not self.store.acquire(
            "decision-session", owner, self.policy.session_timeout_seconds + 60
        ):
            raise ValueError("A decision session is already running")
        session_id = None
        try:
            async with asyncio.timeout(self.policy.session_timeout_seconds):
                snapshot = self.store.snapshot()
                if not snapshot:
                    raise ValueError("Refresh a portfolio snapshot before research")
                cutoff = utcnow()
                session_id = self.store.start_session(cutoff)
                instruments = {x.symbol: x for x in self.policy.instruments}
                for holding in snapshot.positions:
                    instruments.setdefault(
                        holding.symbol,
                        Instrument(
                            symbol=holding.symbol, name=holding.symbol, sector=holding.sector
                        ),
                    )
                states = {}
                errors = []
                held_symbols = {x.symbol for x in snapshot.positions}
                ordered = sorted(instruments, key=lambda sym: (sym not in held_symbols, sym))
                for symbol in ordered:
                    notify(f"Researching {symbol}: mandatory source tasks")
                    instrument = instruments[symbol]
                    items, attempts = await self.research.collect(instrument, cutoff)
                    self.store.record_research(session_id, items, attempts)
                    historical = self.store.history(
                        symbol, cutoff, cutoff - timedelta(days=self.policy.history_days)
                    )
                    evidence = list({x.id: x for x in [*historical, *items]}.values())
                    # Prefer recent evidence; retain full search logs separately.
                    evidence.sort(key=lambda x: x.published_at, reverse=True)
                    position = snapshot.position(symbol)
                    price = position.price if position else Decimal(0)
                    if not position and self.broker:
                        try:
                            price = await self.broker.quote(symbol)
                        except RuntimeError:
                            pass
                    if not position and self.broker is None:
                        price = Decimal(100)  # Explicit synthetic demo only.
                    state = StockState(
                        stock=symbol,
                        instrument=instrument,
                        evidence=evidence,
                        attempts=attempts,
                        snapshot=snapshot,
                        session_id=session_id,
                        cutoff=utcnow().isoformat(),
                        reference_price=str(price),
                    )
                    self.store.save_stage(
                        session_id,
                        symbol,
                        "research",
                        {
                            "evidence": [x.model_dump(mode="json") for x in evidence],
                            "coverage": [x.model_dump(mode="json") for x in attempts],
                            "complete": complete_coverage(attempts),
                            "reference_price": str(price),
                            "information_cutoff": state["cutoff"],
                        },
                    )
                    try:
                        state = await self.analysis_graph.ainvoke(state)
                        states[symbol] = state
                        if position:
                            notify(f"Reviewing holding {symbol} against its thesis")
                            await self._allocate(state)
                    except (ValueError, RuntimeError) as exc:
                        errors.append(symbol)
                        self.store.save_stage(session_id, symbol, "error", {"reason": str(exc)})
                # Admission is source/instrument eligibility only; never p_initial or EV.
                eligible = [
                    symbol
                    for symbol in states
                    if symbol in {x.symbol for x in self.policy.instruments}
                ]
                self.store.enqueue(eligible)
                candidates = self.store.fair_candidates(eligible, self.policy.max_debates)
                for symbol in candidates:
                    notify(f"Debating {symbol}: Bull/Bear, verification, Orchestrator")
                    try:
                        state = await self.debate_graph.ainvoke(states[symbol])
                        verdict = state["debate"]["verdict"]
                        await self._allocate(state, verdict)
                        self.store.debated(symbol, cutoff)
                    except (ValueError, RuntimeError) as exc:
                        errors.append(symbol)
                        self.store.save_stage(session_id, symbol, "error", {"reason": str(exc)})
                incomplete = errors or any(
                    not complete_coverage(x["attempts"]) for x in states.values()
                )
                status = "INCOMPLETE" if incomplete else "COMPLETE"
                self.store.finish_session(session_id, status, ",".join(sorted(set(errors))))
                notify(f"Session {status}; {len(candidates)} debates; orders disabled")
                return {
                    "session_id": session_id,
                    "status": status,
                    "debated": candidates,
                    "pending": sorted(set(eligible) - set(candidates)),
                }
        except BaseException as exc:
            if session_id:
                self.store.finish_session(session_id, "FAILED", type(exc).__name__)
            raise
        finally:
            self.store.release("decision-session", owner)
