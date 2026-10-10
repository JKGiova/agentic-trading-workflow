"""Durable analyst task leases, immutable findings and frozen cycle manifests."""

import hashlib
import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import JSON, Column, Integer, String, Table, insert, select, update

from tradebot.storage import metadata

cycles = Table(
    "analysis_cycles",
    metadata,
    Column("id", String, primary_key=True),
    Column("start", String, nullable=False),
    Column("end", String, nullable=False),
    Column("status", String, nullable=False),
    Column("payload", JSON, nullable=False),
)
events = Table(
    "analysis_events",
    metadata,
    Column("id", String, primary_key=True),
    Column("stock", String, nullable=False, index=True),
    Column("observed", String, nullable=False),
    Column("family", String, nullable=False, index=True),
    Column("predecessor", String, nullable=False),
    Column("payload", JSON, nullable=False),
)
tasks = Table(
    "analysis_tasks",
    metadata,
    Column("id", String, primary_key=True),
    Column("cycle", String, nullable=False, index=True),
    Column("stock", String, nullable=False),
    Column("role", String, nullable=False),
    Column("event", String, nullable=False),
    Column("phase", String, nullable=False),
    Column("priority", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("owner", String, nullable=False),
    Column("expires", String, nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("created", String, nullable=False),
    Column("completed", String, nullable=False),
    Column("payload", JSON, nullable=False),
)
outbox = Table(
    "analysis_outbox",
    metadata,
    Column("id", String, primary_key=True),
    Column("cycle", String, nullable=False),
    Column("status", String, nullable=False),
    Column("retry_at", String, nullable=False),
    Column("payload", JSON, nullable=False),
)
settings = Table(
    "analysis_settings",
    metadata,
    Column("name", String, primary_key=True),
    Column("payload", JSON, nullable=False),
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class AnalysisMemory:
    def __init__(self, store):
        self.store = store
        metadata.create_all(store.engine)

    def rows(self, table, *conditions):
        with self.store.engine.connect() as conn:
            query = select(table).where(*conditions)
            return [dict(row._mapping) for row in conn.execute(query)]

    def setting(self, name):
        rows = self.rows(settings, settings.c.name == name)
        return rows[0]["payload"] if rows else None

    def set_setting(self, name, payload):
        with self.store.transaction() as conn:
            self.store._ensure(conn, settings, {"name": name, "payload": payload})
            conn.execute(update(settings).where(settings.c.name == name).values(payload=payload))

    def open_cycle(self, now, hours, stocks, policy_hash):
        spent = str(self.store.model_spend())
        with self.store.transaction() as conn:
            row = conn.execute(select(cycles).where(cycles.c.status == "OPEN")).mappings().first()
            if row:
                if row["payload"]["policy_hash"] != policy_hash:
                    raise ValueError(
                        "Open research cycle policy changed; restore its configuration"
                    )
                return dict(row)
            cid = str(uuid.uuid4())
            previous = conn.execute(
                select(cycles.c.end).order_by(cycles.c.end.desc()).limit(1)
            ).scalar()
            start, skipped = now, 0
            if previous:
                boundary = datetime.fromisoformat(previous)
                skipped = max(0, int((now - boundary).total_seconds() // (hours * 3600)))
                start = boundary + timedelta(hours=hours * skipped)
            payload = {
                "stocks": sorted(set(stocks)),
                "policy_hash": policy_hash,
                "coverage": [],
                "manifest": [],
                "reports": {},
                "spent_at_start": spent,
                "downtime_windows": skipped,
                "deferred_events": [],
            }
            values = {
                "id": cid,
                "start": start.isoformat(),
                "end": (start + timedelta(hours=hours)).isoformat(),
                "status": "OPEN",
                "payload": payload,
            }
            conn.execute(insert(cycles).values(**values))
            return values

    def cycle(self, cid):
        return self.rows(cycles, cycles.c.id == cid)[0]

    def remember(self, items, now):
        with self.store.transaction() as conn:
            for item in items:
                key = digest([item.stock, item.id])
                family = digest([item.stock, item.id.rsplit(":", 1)[0]])
                previous = conn.execute(
                    select(events.c.id)
                    .where(events.c.family == family)
                    .order_by(events.c.observed.desc(), events.c.id)
                    .limit(1)
                ).scalar()
                self.store._ensure(
                    conn,
                    events,
                    {
                        "id": key,
                        "stock": item.stock,
                        "observed": now.isoformat(),
                        "family": family,
                        "predecessor": previous if previous and previous != key else "",
                        "payload": item.model_dump(mode="json"),
                    },
                )

    def evidence(self, stock, cutoff, since=None):
        from tradebot.contracts import Evidence

        result = []
        for row in self.rows(events, events.c.stock == stock):
            item = Evidence.model_validate(row["payload"])
            if row["observed"] <= cutoff.isoformat() and item.published_at <= cutoff:
                if since is None or item.published_at >= since:
                    result.append(item)
        return sorted(result, key=lambda item: (item.published_at, item.id), reverse=True)

    def ingest(self, cycle, stock, items, attempts, now, limit, held=False):
        if not cycle["start"] <= now.isoformat() < cycle["end"]:
            return False
        self.remember(items, now)
        with self.store.transaction() as conn:
            row = conn.execute(select(cycles).where(cycles.c.id == cycle["id"])).mappings().one()
            if row["status"] != "OPEN":
                return False
            payload = dict(row["payload"])
            payload["stocks"] = sorted(set(payload["stocks"]) | {stock})
            # Latest executed source attempt per stock/category/source, not a claimed model search.
            coverage = {(a["stock"], a["category"], a["source"]): a for a in payload["coverage"]}
            coverage.update(
                {(a.stock, a.category.value, a.source): a.model_dump(mode="json") for a in attempts}
            )
            payload["coverage"] = list(coverage.values())
            conn.execute(update(cycles).where(cycles.c.id == cycle["id"]).values(payload=payload))
            count = len(conn.execute(select(tasks.c.id).where(tasks.c.cycle == cycle["id"])).all())
            assignments = []
            for item in items:
                roles = {item.category.value}
                if item.category.value in {"company", "financial"}:
                    roles.update({"company", "financial"})
                assignments.extend((role, item.id) for role in sorted(roles))
            # One gap/coverage task per role/cycle; it is not regenerated on every empty poll.
            assignments.extend((role, "") for role in ("market", "financial", "company", "social"))
            for role, eid in assignments:
                key = digest([cycle["id"], stock, role, eid, "original"])
                if conn.execute(select(tasks.c.id).where(tasks.c.id == key)).scalar():
                    continue
                # Always retain four-category holding/watchlist coverage even at the optional cap.
                if count >= limit and eid:
                    payload["deferred_events"] = sorted(set(payload["deferred_events"]) | {eid})
                    continue
                self.store._ensure(
                    conn,
                    tasks,
                    {
                        "id": key,
                        "cycle": cycle["id"],
                        "stock": stock,
                        "role": role,
                        "event": eid,
                        "phase": "original",
                        "priority": 0 if not eid else 1 if held else 2,
                        "status": "PENDING",
                        "owner": "",
                        "expires": "",
                        "attempts": 0,
                        "created": now.isoformat(),
                        "completed": "",
                        "payload": {"checkpoint": {}, "error": ""},
                    },
                )
                count += 1
            conn.execute(update(cycles).where(cycles.c.id == cycle["id"]).values(payload=payload))
        return True

    def carry(self, previous, current, now, limit):
        """Advance unfinished event work to a new cutoff; preserve the original tasks."""
        from tradebot.contracts import Evidence

        marker = "backlog_carried:" + previous["id"]
        if self.setting(marker):
            return
        unfinished = self.rows(tasks, tasks.c.cycle == previous["id"], tasks.c.status != "DONE")
        by_stock = {}
        for task in unfinished:
            if task["event"]:
                by_stock.setdefault(task["stock"], set()).add(task["event"])
        for row in self.rows(events):
            if row["payload"]["id"] in previous["payload"].get("deferred_events", []):
                by_stock.setdefault(row["stock"], set()).add(row["payload"]["id"])
        for stock, ids in by_stock.items():
            items = [
                Evidence.model_validate(row["payload"])
                for row in self.rows(events, events.c.stock == stock)
                if row["payload"]["id"] in ids
            ]
            self.ingest(current, stock, items, [], now, limit)
        self.set_setting(marker, {"to": current["id"]})

    def claim(self, now, seconds, max_attempts):
        with self.store.transaction() as conn:
            conn.execute(
                update(tasks)
                .where(
                    tasks.c.status == "WORKING",
                    tasks.c.expires <= now.isoformat(),
                    tasks.c.attempts >= max_attempts,
                )
                .values(status="FAILED", owner="", expires="")
            )
            row = (
                conn.execute(
                    select(tasks)
                    .join(cycles, tasks.c.cycle == cycles.c.id)
                    .where(
                        cycles.c.status == "OPEN",
                        cycles.c.end > now.isoformat(),
                        tasks.c.attempts < max_attempts,
                        ((tasks.c.status == "PENDING") & (tasks.c.expires <= now.isoformat()))
                        | ((tasks.c.status == "WORKING") & (tasks.c.expires <= now.isoformat())),
                    )
                    .order_by(tasks.c.attempts, tasks.c.priority, tasks.c.created, tasks.c.id)
                    .limit(1)
                )
                .mappings()
                .first()
            )
            if not row:
                return None
            values = dict(row)
            values.update(
                status="WORKING",
                owner=str(uuid.uuid4()),
                expires=(now + timedelta(seconds=seconds)).isoformat(),
                attempts=row["attempts"] + 1,
            )
            conn.execute(update(tasks).where(tasks.c.id == row["id"]).values(**values))
            return values

    def checkpoint(self, task, checkpoint, now):
        with self.store.transaction() as conn:
            result = conn.execute(
                update(tasks)
                .where(
                    tasks.c.id == task["id"],
                    tasks.c.owner == task["owner"],
                    tasks.c.status == "WORKING",
                    tasks.c.expires > now.isoformat(),
                )
                .values(payload={"checkpoint": checkpoint, "error": ""})
            )
            if result.rowcount != 1:
                raise ValueError("Research task lease expired or was reclaimed")
        task["payload"] = {"checkpoint": checkpoint, "error": ""}

    def finish(self, task, result, now):
        with self.store.transaction() as conn:
            cycle = (
                conn.execute(select(cycles).where(cycles.c.id == task["cycle"])).mappings().one()
            )
            status = (
                "DONE" if cycle["status"] == "OPEN" and now.isoformat() < cycle["end"] else "LATE"
            )
            changed = conn.execute(
                update(tasks)
                .where(
                    tasks.c.id == task["id"],
                    tasks.c.owner == task["owner"],
                    tasks.c.status == "WORKING",
                    tasks.c.expires > now.isoformat(),
                )
                .values(
                    status=status,
                    completed=now.isoformat(),
                    payload={**task["payload"], "result": result, "error": ""},
                    owner="",
                    expires="",
                )
            )
            if changed.rowcount != 1:
                raise ValueError("Stale research worker cannot commit")
        return status

    def fail(self, task, now, max_attempts, error):
        with self.store.transaction() as conn:
            conn.execute(
                update(tasks)
                .where(
                    tasks.c.id == task["id"],
                    tasks.c.owner == task["owner"],
                    tasks.c.status == "WORKING",
                )
                .values(
                    status="PENDING" if task["attempts"] < max_attempts else "FAILED",
                    owner="",
                    expires=(now + timedelta(seconds=min(60, 2 ** task["attempts"]))).isoformat(),
                    payload={**task["payload"], "error": error},
                )
            )

    def peer_tasks(self, task, now):
        with self.store.transaction() as conn:
            cycle = (
                conn.execute(select(cycles).where(cycles.c.id == task["cycle"])).mappings().one()
            )
            if cycle["status"] != "OPEN" or now.isoformat() >= cycle["end"]:
                return
            originals = (
                conn.execute(
                    select(tasks).where(
                        tasks.c.cycle == task["cycle"],
                        tasks.c.stock == task["stock"],
                        tasks.c.event == task["event"],
                        tasks.c.phase == "original",
                    )
                )
                .mappings()
                .all()
            )
            if any(row["status"] not in {"DONE", "FAILED"} for row in originals):
                return
            for row in originals:
                if row["status"] != "DONE":
                    continue
                key = digest([row["id"], "peer"])
                self.store._ensure(
                    conn,
                    tasks,
                    {
                        **dict(row),
                        "id": key,
                        "phase": "peer",
                        "status": "PENDING",
                        "owner": "",
                        "expires": "",
                        "attempts": 0,
                        "created": now.isoformat(),
                        "completed": "",
                        "payload": {"checkpoint": {}, "error": ""},
                    },
                )

    def findings(self, stock, cutoff, cycle=None, phase=None):
        conditions = [
            tasks.c.stock == stock,
            tasks.c.status.in_(["DONE", "LATE"]),
            tasks.c.completed <= cutoff.isoformat(),
        ]
        if cycle:
            conditions.append(tasks.c.cycle == cycle)
        if phase:
            conditions.append(tasks.c.phase == phase)
        return self.rows(tasks, *conditions)

    def freeze(self, cid, now):
        with self.store.transaction() as conn:
            row = conn.execute(select(cycles).where(cycles.c.id == cid)).mappings().one()
            if row["status"] != "OPEN":
                return dict(row)
            if now.isoformat() < row["end"]:
                raise ValueError("Cannot close an unexpired cycle")
            completed = (
                conn.execute(
                    select(tasks.c.id).where(
                        tasks.c.cycle == cid,
                        tasks.c.status == "DONE",
                        tasks.c.completed < row["end"],
                    )
                )
                .scalars()
                .all()
            )
            payload = dict(row["payload"])
            payload["manifest"] = list(completed)
            payload["evidence_manifest"] = list(
                conn.execute(select(events.c.id).where(events.c.observed < row["end"])).scalars()
            )
            payload["unfinished"] = [
                dict(r)
                for r in conn.execute(
                    select(tasks.c.id, tasks.c.stock, tasks.c.role, tasks.c.status).where(
                        tasks.c.cycle == cid, tasks.c.status != "DONE"
                    )
                ).mappings()
            ]
            conn.execute(
                update(cycles).where(cycles.c.id == cid).values(status="CLOSING", payload=payload)
            )
            return {**dict(row), "status": "CLOSING", "payload": payload}

    def save_report(self, cid, stock, report):
        with self.store.transaction() as conn:
            row = conn.execute(select(cycles).where(cycles.c.id == cid)).mappings().one()
            payload = dict(row["payload"])
            reports = dict(payload["reports"])
            if stock in reports and reports[stock] != report:
                raise ValueError("Closed report is immutable")
            reports[stock] = report
            payload["reports"] = reports
            conn.execute(update(cycles).where(cycles.c.id == cid).values(payload=payload))

    def queue_summary(self, cid, parts, now):
        with self.store.transaction() as conn:
            for index, text in enumerate(parts):
                self.store._ensure(
                    conn,
                    outbox,
                    {
                        "id": f"{cid}:{index:04d}",
                        "cycle": cid,
                        "status": "PENDING",
                        "retry_at": now.isoformat(),
                        "payload": {"text": text, "attempts": 0},
                    },
                )
            conn.execute(update(cycles).where(cycles.c.id == cid).values(status="CLOSED"))

    def delivery_result(self, row, status, now, **details):
        with self.store.transaction() as conn:
            conn.execute(
                update(outbox)
                .where(outbox.c.id == row["id"])
                .values(
                    status=status, retry_at=now.isoformat(), payload={**row["payload"], **details}
                )
            )

    def claim_delivery(self, row, now):
        with self.store.transaction() as conn:
            result = conn.execute(
                update(outbox)
                .where(
                    outbox.c.id == row["id"],
                    outbox.c.status == "PENDING",
                    outbox.c.retry_at <= now.isoformat(),
                )
                .values(status="SENDING")
            )
            return result.rowcount == 1
