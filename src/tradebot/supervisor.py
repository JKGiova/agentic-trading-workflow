"""Continuous research supervisor: scheduling, memory, peer review and cycle reports."""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update

from tradebot.analysis_memory import AnalysisMemory, cycles, digest, events, outbox, tasks
from tradebot.analysts import AnalystAgent, Finding
from tradebot.contracts import Category, Coverage, Evidence, Forecast, SearchAttempt, utcnow
from tradebot.models import model_budget_scope
from tradebot.settings import Instrument
from tradebot.storage import leases
from tradebot.telegram import split_message


class AnalysisSupervisor:
    def __init__(
        self, policy, store, model, research, notifier, clock=utcnow, notify=lambda _: None
    ):
        self.policy, self.store, self.model, self.research = policy, store, model, research
        self.memory = AnalysisMemory(store)
        self.notifier, self.clock, self.notify = notifier, clock, notify
        self.agent = AnalystAgent(policy, self.memory, model, research, clock)
        self.stop = asyncio.Event()
        self.owner = str(uuid.uuid4())
        self.policy_hash = digest(policy.model_dump(mode="json"))
        self.report_lock = asyncio.Lock()
        self.collect_lock = asyncio.Lock()
        self.runner = None
        self.refresh_positions = None
        self.collection_requested = asyncio.Event()
        self.recovered_backlog = False

    def instruments(self):
        configured = {item.symbol: item for item in self.policy.instruments}
        snapshot = self.store.snapshot()
        if snapshot:
            for holding in snapshot.positions:
                configured.setdefault(
                    holding.symbol,
                    Instrument(symbol=holding.symbol, name=holding.symbol, sector=holding.sector),
                )
        return list(configured.values())

    def current(self):
        return self.memory.open_cycle(
            self.clock(),
            self.policy.session_hours,
            [item.symbol for item in self.instruments()],
            self.policy_hash,
        )

    def rollover(self):
        now = self.clock()
        cycle = self.current()
        if now.isoformat() >= cycle["end"]:
            closed = self.memory.freeze(cycle["id"], now)
            self.notify(f"Cycle closed: {cycle['id'][:8]}; preparing reports")
            # The next research cycle is opened before any reporting/model call.
            cycle = self.current()
            self.memory.carry(closed, cycle, now, self.policy.max_cycle_tasks)
            self.collection_requested.set()
        if not self.recovered_backlog:
            for old in self.memory.rows(cycles, cycles.c.status != "OPEN"):
                self.memory.carry(old, cycle, now, self.policy.max_cycle_tasks)
            self.recovered_backlog = True
        return cycle

    async def collect(self):
        async with self.collect_lock:
            if self.refresh_positions:
                try:
                    await self.refresh_positions()
                except (ValueError, RuntimeError, OSError, TimeoutError) as exc:
                    self.notify(
                        f"Portfolio refresh failed: {type(exc).__name__}; "
                        "researching stored holdings"
                    )
            cycle = self.rollover()
            instruments = self.instruments()

            async def one(instrument):
                cutoff = self.clock()
                try:
                    async with asyncio.timeout(120):
                        items, attempts = await self.research.collect(instrument, cutoff)
                    observed = self.clock()
                    current = self.rollover()
                    snapshot = self.store.snapshot()
                    accepted = self.memory.ingest(
                        current,
                        instrument.symbol,
                        items,
                        attempts,
                        observed,
                        self.policy.max_cycle_tasks,
                        held=bool(snapshot and snapshot.position(instrument.symbol)),
                    )
                    if not accepted:
                        self.memory.ingest(
                            self.rollover(),
                            instrument.symbol,
                            items,
                            attempts,
                            self.clock(),
                            self.policy.max_cycle_tasks,
                        )
                except (RuntimeError, ValueError, OSError, TimeoutError) as exc:
                    now = self.clock()
                    attempts = [
                        SearchAttempt(
                            stock=instrument.symbol,
                            category=category,
                            source="collector",
                            query=instrument.symbol,
                            start=now - timedelta(hours=self.policy.news_hours),
                            cutoff=now,
                            completed_at=now,
                            coverage=Coverage.FAILED,
                            evidence_ids=[],
                            reason=f"Collector failed ({type(exc).__name__})",
                        )
                        for category in Category
                    ]
                    self.memory.ingest(
                        self.rollover(),
                        instrument.symbol,
                        [],
                        attempts,
                        now,
                        self.policy.max_cycle_tasks,
                    )
                    self.notify(
                        f"Collection deferred for {instrument.symbol}: {type(exc).__name__}"
                    )

            await asyncio.gather(*(one(item) for item in instruments))
            self.notify(f"Collected {len(instruments)} stocks in cycle {cycle['id'][:8]}")

    def context(self, task):
        now = self.clock()
        cp = task["payload"]["checkpoint"]
        if "context" in cp:
            return cp["context"]
        cycle = self.memory.cycle(task["cycle"])
        evidence = self.memory.evidence(
            task["stock"], now, now - timedelta(days=self.policy.history_days)
        )
        # A focal event plus category evidence and opposing history. IDs are stable.
        focal = [item for item in evidence if item.id == task["event"]]
        scoped = [item for item in evidence if item.category.value == task["role"]]
        if task["role"] == "company":
            scoped += [item for item in evidence if item.category == Category.FINANCIAL]
        selected = list({x.id: x for x in [*focal, *scoped, *evidence[:2]]}.values())[:8]
        past = self.memory.findings(task["stock"], now)
        private = [
            row
            for row in past
            if row["role"] == task["role"]
            and (row["cycle"] != task["cycle"] or row["event"] != task["event"])
        ]
        peers = []
        if task["phase"] == "peer":
            peers = [
                row
                for row in past
                if row["cycle"] == task["cycle"]
                and row["event"] == task["event"]
                and row["phase"] == "original"
            ]
        snapshot = self.store.snapshot()
        holding = snapshot.position(task["stock"]) if snapshot else None
        context = {
            "stock": task["stock"],
            "role": task["role"],
            "information_cutoff": now.isoformat(),
            "cycle_end": cycle["end"],
            "evidence": [{**x.model_dump(mode="json"), "text": x.text[:700]} for x in selected],
            "coverage": [a for a in cycle["payload"]["coverage"] if a["stock"] == task["stock"]],
            "private_memory": [row["payload"]["result"] for row in private[-3:]],
            "peer_originals": [
                {"role": row["role"], "finding": row["payload"]["result"]} for row in peers
            ],
            "holding": holding.model_dump(mode="json") if holding else None,
            "prompt_version": "continuous-v1",
            "language": self.policy.report_language,
        }
        # Freeze each task's input on first invocation for deterministic crash recovery.
        cp = {**cp, "context": context}
        self.memory.checkpoint(task, cp, now)
        return context

    async def work_one(self):
        task = self.memory.claim(
            self.clock(), self.policy.agent_timeout_seconds + 30, self.policy.task_retries
        )
        if not task:
            return False
        try:
            spent = self.store.scoped_spend(task["cycle"], "research")
            if spent >= self.policy.cycle_model_budget * Decimal("0.7"):
                raise ValueError("Cycle operating budget exhausted")
            token = model_budget_scope.set(
                {
                    "cycle": task["cycle"],
                    "kind": "research",
                    "cap": self.policy.cycle_model_budget * Decimal("0.7"),
                }
            )
            try:
                result = await self.agent.run(task, self.context(task))
            finally:
                model_budget_scope.reset(token)
            status = self.memory.finish(task, result, self.clock())
            if status == "DONE" and task["phase"] == "original":
                self.memory.peer_tasks(task, self.clock())
            self.notify(f"{task['stock']} / {task['role']} / {task['phase']}: {status}")
        except (RuntimeError, ValueError, OSError, TimeoutError) as exc:
            self.memory.fail(task, self.clock(), self.policy.task_retries, type(exc).__name__)
            if task["phase"] == "original":
                self.memory.peer_tasks(task, self.clock())
            self.notify(f"{task['stock']} / {task['role']}: deferred ({type(exc).__name__})")
        return True

    async def report_cycle(self, cycle):
        end = datetime.fromisoformat(cycle["end"])
        manifest = sorted(
            self.memory.rows(tasks, tasks.c.id.in_(cycle["payload"]["manifest"])),
            key=lambda row: (row["completed"], row["id"]),
        )
        for stock in cycle["payload"]["stocks"]:
            saved = self.memory.cycle(cycle["id"])["payload"]["reports"]
            if stock in saved:
                self.store.enqueue([stock])
                continue
            findings = [row for row in manifest if row["stock"] == stock]
            role_reports = {}
            for role in Category:
                group = [row for row in findings if row["role"] == role.value]
                summaries = [row["payload"]["result"] for row in group]
                role_reports[role.value] = summaries or [
                    Finding(
                        summary="No completed specialist assessment by cycle deadline",
                        direction="unknown",
                        evidence_ids=[],
                        opposing_evidence=[],
                        gaps=["Incomplete role coverage"],
                    ).model_dump(mode="json")
                ]
            evidence = [
                Evidence.model_validate(row["payload"])
                for row in self.memory.rows(
                    events,
                    events.c.stock == stock,
                    events.c.id.in_(cycle["payload"]["evidence_manifest"]),
                )
            ]
            evidence = sorted(
                (
                    x
                    for x in evidence
                    if end - timedelta(days=self.policy.history_days) <= x.published_at < end
                ),
                key=lambda x: (x.published_at, x.id),
                reverse=True,
            )
            synthesis_roles = {}
            for role, findings in role_reports.items():
                synthesis_roles[role] = await self.summarize_role(
                    cycle, stock, role, findings, evidence
                )
            cited = {
                eid
                for findings in synthesis_roles.values()
                for finding in findings
                for eid in [
                    *finding["evidence_ids"],
                    *(eid for claim in finding.get("claims", []) for eid in claim["evidence_ids"]),
                ]
            }
            selected = sorted(evidence, key=lambda item: item.id not in cited)[:20]
            # All available evidence was first observed before the frozen cutoff.
            context = {
                "stock": stock,
                "evidence": [{**x.model_dump(mode="json"), "text": x.text[:500]} for x in selected],
                "reports": synthesis_roles,
                "information_cutoff": cycle["end"],
                "horizon_trading_days": self.policy.horizon_trading_days,
                "outcome": "positive forward net total return",
                "reference_price": "unavailable",
                "cost_allowance_fraction": self.policy.risk.cost_buffer,
                "coverage": [a for a in cycle["payload"]["coverage"] if a["stock"] == stock],
                "language": self.policy.report_language,
                "task": "Synthesize findings and dissent without voting. Mark absent prices, "
                "source coverage and uncompleted work as gaps; confidence is uncalibrated.",
            }
            try:
                token = model_budget_scope.set(
                    {
                        "cycle": cycle["id"],
                        "kind": "closing",
                        "cap": self.policy.cycle_model_budget * Decimal("0.3"),
                    }
                )
                try:
                    forecast = await self.model.structured("analyst_lead", Forecast, context)
                finally:
                    model_budget_scope.reset(token)
                if not set(forecast.evidence_ids) <= {x["id"] for x in context["evidence"]}:
                    raise ValueError("Report forecast fabricated a citation")
            except (RuntimeError, ValueError, OSError, TimeoutError):
                forecast = Forecast(
                    probability=None,
                    scenarios=[],
                    stressed_loss=None,
                    evidence_ids=[],
                    rationale="Synthesis unavailable; report preserves completed findings",
                    gaps=["No validated model forecast"],
                )
            report = {
                "cycle": cycle["id"],
                "stock": stock,
                "cutoff": cycle["end"],
                "roles": role_reports,
                "synthesis_roles": synthesis_roles,
                "forecast": forecast.model_dump(mode="json"),
                "coverage": context["coverage"],
                "evidence": context["evidence"],
                "unfinished": [
                    x for x in cycle["payload"].get("unfinished", []) if x["stock"] == stock
                ],
                "debate_status": "PENDING",
                "reference_price": "unavailable",
            }
            self.memory.save_report(cycle["id"], stock, report)
            # Every report, including unknown/low-confidence, creates a durable obligation.
            self.store.enqueue([stock])
        complete = self.memory.cycle(cycle["id"])
        text = self.summary(complete)
        self.memory.queue_summary(cycle["id"], split_message(text), self.clock())
        self.notify(f"Cycle {cycle['id'][:8]}: reports complete; Telegram summary queued")

    async def summarize_role(self, cycle, stock, role, findings, evidence):
        """Hierarchical summaries retain all original findings without an unbounded prompt."""
        import json

        working = findings
        known = {item.id: item for item in evidence}
        for level in range(6):
            if len(json.dumps(working, ensure_ascii=False).encode()) <= 4500:
                return working
            chunks, chunk, size = [], [], 0
            for finding in working:
                encoded = len(json.dumps(finding, ensure_ascii=False).encode())
                if chunk and size + encoded > 8000:
                    chunks.append(chunk)
                    chunk, size = [], 0
                chunk.append(finding)
                size += encoded
            if chunk:
                chunks.append(chunk)
            reduced = []
            for index, chunk in enumerate(chunks):
                key = f"role-summary:{cycle['id']}:{stock}:{role}:{level}:{index}:{digest(chunk)}"
                cached = self.memory.setting(key)
                if cached:
                    reduced.append(cached)
                    continue
                ids = list(
                    dict.fromkeys(
                        eid
                        for finding in chunk
                        for eid in [
                            *finding["evidence_ids"],
                            *(
                                eid
                                for claim in finding.get("claims", [])
                                for eid in claim["evidence_ids"]
                            ),
                        ]
                    )
                )
                selected = [known[eid] for eid in ids if eid in known][:32]
                context = {
                    "stock": stock,
                    "evidence": [
                        {**item.model_dump(mode="json"), "text": item.text[:200]}
                        for item in selected
                    ],
                    "findings": chunk,
                    "information_cutoff": cycle["end"],
                    "language": self.policy.report_language,
                    "task": "Compress this specialist's findings, preserving material changes, "
                    "contradictions, source gaps and open questions. Do not average votes. "
                    "Use at most eight source IDs and keep the summary under 500 characters.",
                }
                token = model_budget_scope.set(
                    {
                        "cycle": cycle["id"],
                        "kind": "closing",
                        "cap": self.policy.cycle_model_budget * Decimal("0.3"),
                    }
                )
                try:
                    result = await self.model.structured(f"{role}_cycle_summary", Finding, context)
                    citations = set(result.evidence_ids)
                    citations.update(eid for claim in result.claims for eid in claim.evidence_ids)
                    if not citations <= {item.id for item in selected}:
                        raise ValueError("Role summary fabricated a citation")
                    compact = result.model_dump(mode="json")
                    compact["summary"] = compact["summary"][:500]
                    compact["evidence_ids"] = compact["evidence_ids"][:8]
                    compact["claims"] = compact["claims"][:2]
                except (ValueError, RuntimeError, OSError, TimeoutError):
                    compact = Finding(
                        summary="; ".join(x["summary"] for x in chunk)[:500],
                        direction="unknown",
                        evidence_ids=[x.id for x in selected[:8]],
                        opposing_evidence=list(
                            dict.fromkeys(note for x in chunk for note in x["opposing_evidence"])
                        )[:3],
                        gaps=["Role summary incomplete; original findings retained"],
                        questions=list(
                            dict.fromkeys(note for x in chunk for note in x.get("questions", []))
                        )[:3],
                    ).model_dump(mode="json")
                finally:
                    model_budget_scope.reset(token)
                self.memory.set_setting(key, compact)
                reduced.append(compact)
            working = reduced
        return [
            Finding(
                summary="Role synthesis reached its depth bound; original findings retained",
                direction="unknown",
                evidence_ids=[],
                opposing_evidence=[],
                gaps=["Incomplete role synthesis"],
            ).model_dump(mode="json")
        ]

    def summary(self, cycle):
        language = self.policy.report_language.lower()
        italian = language.startswith("it")
        header = "Riepilogo ricerca" if italian else "Research summary"
        text = f"{header} — {cycle['id'][:8]}\n{cycle['start']} → {cycle['end']}\n"
        text += (
            "RESEARCH ONLY · nessun ordine · confidence non calibrata\n"
            if italian
            else "RESEARCH ONLY · no orders · uncalibrated confidence\n"
        )
        if cycle["payload"].get("deferred_events"):
            text += (
                f"Research capacity: {len(cycle['payload']['deferred_events'])} events deferred\n"
            )
        if cycle["payload"].get("downtime_windows"):
            text += f"Downtime: {cycle['payload']['downtime_windows']} missed windows\n"
        for stock, report in sorted(cycle["payload"]["reports"].items()):
            forecast = report["forecast"]
            confidence = (
                "unknown" if forecast["probability"] is None else f"{forecast['probability']:.0%}"
            )
            label = "confidence iniziale" if italian else "initial confidence"
            text += f"\n{stock} · {label} {confidence}\n{forecast['rationale']}\n"
            for role, findings in report.get("synthesis_roles", report["roles"]).items():
                originals = [row for row in findings if row.get("summary")]
                text += f"{role}: " + "; ".join(x["summary"][:200] for x in originals[:3]) + "\n"
                dissent = [note for x in findings for note in x["opposing_evidence"]]
                if dissent:
                    text += "Dissent: " + "; ".join(dict.fromkeys(dissent))[:400] + "\n"
            gaps = forecast["gaps"] + [
                f"{a['category']}/{a['source']}: {a['coverage']}"
                for a in report["coverage"]
                if a["coverage"] in {"FAILED", "DEGRADED"}
            ]
            gaps += [
                f"{role}: {gap}"
                for role, findings in report["roles"].items()
                for finding in findings
                for gap in finding["gaps"]
            ]
            gaps = list(dict.fromkeys(gaps))
            if report["unfinished"]:
                gaps.append(f"{len(report['unfinished'])} unfinished tasks")
            if gaps:
                text += "Gaps: " + "; ".join(gaps) + "\n"
            sources = {x["url"] for x in report["evidence"][:3]}
            text += "\n".join(sorted(sources)) + "\nDebate: PENDING\n"
        return text

    async def close_pending(self):
        async with self.report_lock:
            pending = sorted(
                self.memory.rows(cycles, cycles.c.status == "CLOSING"),
                key=lambda cycle: cycle["end"],
            )
            for cycle in pending:
                await self.report_cycle(cycle)

    def latest_report(self, stock):
        with self.store.engine.connect() as connection:
            for payload in connection.execute(
                select(cycles.c.payload).order_by(cycles.c.end.desc())
            ).scalars():
                if stock in payload["reports"]:
                    return payload["reports"][stock]
        return None

    def status(self):
        active = self.memory.rows(cycles, cycles.c.status == "OPEN")
        queued = self.memory.rows(
            tasks,
            tasks.c.status.in_(["PENDING", "WORKING"]),
            tasks.c.cycle.in_([row["id"] for row in active]),
        )
        return {
            "cycle": active[0]["id"] if active else None,
            "pending_tasks": len(queued),
            "telegram_bound": bool(getattr(self.notifier, "chat_id", "")),
            "telegram": {
                status: len(self.memory.rows(outbox, outbox.c.status == status))
                for status in ("PENDING", "SENT", "UNKNOWN", "FAILED")
            },
        }

    async def _loop(self, operation, interval):
        while not self.stop.is_set():
            try:
                await operation()
            except (RuntimeError, ValueError, OSError, TimeoutError) as exc:
                self.notify(f"Supervisor operation deferred: {type(exc).__name__}")
            try:
                await asyncio.wait_for(self.stop.wait(), timeout=interval)
            except TimeoutError:
                pass

    async def run(self):
        with self.store.transaction() as conn:
            self.store._ensure(
                conn, leases, {"name": "analysis-supervisor", "owner": "", "expires": ""}
            )
        if not self.store.acquire("analysis-supervisor", self.owner, 60):
            raise ValueError("Another supervisor owns this database")
        # An interrupted send has an unknown outcome. Reports/tasks remain recoverable.
        for row in self.memory.rows(outbox, outbox.c.status == "SENDING"):
            self.memory.delivery_result(
                row, "UNKNOWN", self.clock(), error="Interrupted Telegram send"
            )

        async def maintain():
            with self.store.transaction() as conn:
                renewed = conn.execute(
                    update(leases)
                    .where(leases.c.name == "analysis-supervisor", leases.c.owner == self.owner)
                    .values(expires=(utcnow() + timedelta(seconds=60)).isoformat())
                )
                if renewed.rowcount != 1:
                    self.stop.set()
                    raise ValueError("Supervisor lease lost")
            self.rollover()

        async def worker():
            while await self.work_one():
                if self.stop.is_set():
                    break

        async def deliver():
            await self.notifier.deliver(self.clock())

        async def collection_loop():
            while not self.stop.is_set():
                self.collection_requested.clear()
                try:
                    await self.collect()
                except (ValueError, RuntimeError, OSError, TimeoutError) as exc:
                    self.notify(f"Collection deferred: {type(exc).__name__}")
                try:
                    await asyncio.wait_for(
                        self.collection_requested.wait(), timeout=self.policy.collection_seconds
                    )
                except TimeoutError:
                    pass

        jobs = [
            asyncio.create_task(self._loop(maintain, 1)),
            asyncio.create_task(collection_loop()),
            asyncio.create_task(self._loop(self.close_pending, 1)),
            asyncio.create_task(self._loop(deliver, 2)),
        ]
        jobs += [
            asyncio.create_task(self._loop(worker, 0.5))
            for _ in range(self.policy.model_concurrency)
        ]
        stopped = asyncio.create_task(self.stop.wait())
        try:
            done, _ = await asyncio.wait([stopped, *jobs], return_when=asyncio.FIRST_COMPLETED)
            for job in done:
                if job is not stopped and not self.stop.is_set():
                    error = job.exception()
                    name = type(error).__name__ if error else "unexpected completion"
                    raise RuntimeError(
                        f"Supervisor worker stopped ({name}); restart from durable state"
                    ) from None
        finally:
            stopped.cancel()
            for job in jobs:
                job.cancel()
            await asyncio.gather(stopped, *jobs, return_exceptions=True)
            self.store.release("analysis-supervisor", self.owner)
