"""Small durable ledger, compatible with SQLite locally and PostgreSQL for deployment.

No LLM checkpoint is a financial transaction. v0.1 stores research checkpoints and
read-only broker snapshots; only the explicitly labelled demo simulator edits cash.
"""

import json
import uuid
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    event,
    insert,
    select,
    update,
)
from sqlalchemy.pool import StaticPool

from tradebot.contracts import Evidence, SearchAttempt, Snapshot, utcnow

metadata = MetaData()
snapshots = Table(
    "snapshots",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("payload", JSON, nullable=False),
)
sessions = Table(
    "sessions",
    metadata,
    Column("id", String, primary_key=True),
    Column("cutoff", String, nullable=False),
    Column("status", String, nullable=False),
    Column("reason", Text, nullable=False),
)
stages = Table(
    "stages",
    metadata,
    Column("key", String, primary_key=True),
    Column("session_id", String, nullable=False, index=True),
    Column("stock", String, nullable=False, index=True),
    Column("stage", String, nullable=False),
    Column("payload", JSON, nullable=False),
)
evidence = Table(
    "evidence",
    metadata,
    Column("version_id", String, primary_key=True),
    Column("stock", String, nullable=False, index=True),
    Column("payload", JSON, nullable=False),
)
searches = Table(
    "searches",
    metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False, index=True),
    Column("stock", String, nullable=False, index=True),
    Column("payload", JSON, nullable=False),
)
queue = Table(
    "debate_queue",
    metadata,
    Column("stock", String, primary_key=True),
    Column("last_debated", String, nullable=False),
    Column("status", String, nullable=False),
)
leases = Table(
    "leases",
    metadata,
    Column("name", String, primary_key=True),
    Column("owner", String, nullable=False),
    Column("expires", String, nullable=False),
)
usage = Table(
    "usage",
    metadata,
    Column("id", String, primary_key=True),
    Column("month", String, nullable=False, index=True),
    Column("role", String),
    Column("reserved", String, nullable=False),
    Column("actual", String),
    Column("status", String, nullable=False),
    Column("payload", JSON, nullable=False),
)
chat = Table(
    "chat",
    metadata,
    Column("id", String, primary_key=True),
    Column("at", String, nullable=False),
    Column("role", String, nullable=False),
    Column("text", Text, nullable=False),
)


class Store:
    def __init__(self, url: str):
        kwargs = {}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 10}
            if url in {"sqlite://", "sqlite:///:memory:"}:
                kwargs["poolclass"] = StaticPool
        self.engine = create_engine(url, **kwargs)
        if url.startswith("sqlite"):

            @event.listens_for(self.engine, "connect")
            def setup(dbapi, _):
                dbapi.execute("PRAGMA busy_timeout=10000")
                dbapi.execute("PRAGMA journal_mode=WAL")

        metadata.create_all(self.engine)
        with self.engine.begin() as conn:
            self._ensure(conn, snapshots, {"id": 1, "payload": {}})
            for name in ("decision-session", "model-budget", "demo-portfolio"):
                self._ensure(conn, leases, {"name": name, "owner": "", "expires": ""})

    @staticmethod
    def _ensure(conn, table, values):
        # ON CONFLICT is available in both supported dialects; no race on startup.
        if conn.dialect.name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as upsert
        else:
            from sqlalchemy.dialects.postgresql import insert as upsert
        conn.execute(upsert(table).values(**values).on_conflict_do_nothing())

    @contextmanager
    def transaction(self):
        with self.engine.connect() as conn:
            if conn.dialect.name == "sqlite":
                conn.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                conn.begin()
                # All mutable v0.1 ledger operations share this row lock.
                conn.execute(select(snapshots.c.id).where(snapshots.c.id == 1).with_for_update())
            try:
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    def close(self):
        self.engine.dispose()

    def save_snapshot(self, value: Snapshot):
        with self.transaction() as conn:
            conn.execute(
                update(snapshots)
                .where(snapshots.c.id == 1)
                .values(payload=value.model_dump(mode="json"))
            )

    def snapshot(self) -> Snapshot | None:
        with self.engine.connect() as conn:
            data = conn.execute(select(snapshots.c.payload).where(snapshots.c.id == 1)).scalar()
        return Snapshot.model_validate(data) if data else None

    def acquire(self, name: str, owner: str, seconds: int) -> bool:
        now = utcnow()
        with self.transaction() as conn:
            result = conn.execute(
                update(leases)
                .where(
                    leases.c.name == name,
                    (leases.c.owner == "") | (leases.c.expires < now.isoformat()),
                )
                .values(owner=owner, expires=(now + timedelta(seconds=seconds)).isoformat())
            )
        return result.rowcount == 1

    def release(self, name: str, owner: str):
        with self.transaction() as conn:
            conn.execute(
                update(leases)
                .where(leases.c.name == name, leases.c.owner == owner)
                .values(owner="", expires="")
            )

    def start_session(self, cutoff) -> str:
        session_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                insert(sessions).values(
                    id=session_id, cutoff=cutoff.isoformat(), status="RUNNING", reason=""
                )
            )
        return session_id

    def finish_session(self, session_id: str, status: str, reason: str = ""):
        with self.engine.begin() as conn:
            conn.execute(
                update(sessions)
                .where(sessions.c.id == session_id)
                .values(status=status, reason=reason)
            )

    def save_stage(self, session_id: str, stock: str, stage: str, payload: dict):
        with self.engine.begin() as conn:
            self._ensure(
                conn,
                stages,
                {
                    "key": f"{session_id}:{stock}:{stage}",
                    "session_id": session_id,
                    "stock": stock,
                    "stage": stage,
                    "payload": payload,
                },
            )

    def stage(self, session_id: str, stock: str, stage: str) -> dict | None:
        with self.engine.connect() as conn:
            return conn.execute(
                select(stages.c.payload).where(stages.c.key == f"{session_id}:{stock}:{stage}")
            ).scalar()

    def latest(self, stock: str) -> dict[str, dict]:
        with self.engine.connect() as conn:
            sid = conn.execute(
                select(stages.c.session_id)
                .join(sessions, stages.c.session_id == sessions.c.id)
                .where(stages.c.stock == stock)
                .order_by(sessions.c.cutoff.desc())
                .limit(1)
            ).scalar()
            if not sid:
                return {}
            rows = conn.execute(
                select(stages.c.stage, stages.c.payload).where(
                    stages.c.stock == stock, stages.c.session_id == sid
                )
            ).all()
        return dict(rows)

    def record_research(
        self, session_id: str, items: list[Evidence], attempts: list[SearchAttempt]
    ):
        import hashlib

        with self.engine.begin() as conn:
            for item in items:
                data = item.model_dump(mode="json")
                version = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
                self._ensure(
                    conn, evidence, {"version_id": version, "stock": item.stock, "payload": data}
                )
            for attempt in attempts:
                conn.execute(
                    insert(searches).values(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        stock=attempt.stock,
                        payload=attempt.model_dump(mode="json"),
                    )
                )

    def history(self, stock: str, cutoff, since) -> list[Evidence]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(evidence.c.payload).where(evidence.c.stock == stock)
            ).scalars()
            found = [Evidence.model_validate(row) for row in rows]
        result = {}
        for item in sorted(found, key=lambda x: x.retrieved_at):
            if since <= item.published_at <= cutoff and item.retrieved_at <= cutoff:
                result[item.id] = item
        return list(result.values())

    def enqueue(self, stocks: list[str]):
        with self.engine.begin() as conn:
            for stock in stocks:
                self._ensure(conn, queue, {"stock": stock, "last_debated": "", "status": "PENDING"})
                conn.execute(update(queue).where(queue.c.stock == stock).values(status="PENDING"))

    def fair_candidates(self, eligible: list[str], limit: int) -> list[str]:
        with self.engine.connect() as conn:
            return list(
                conn.execute(
                    select(queue.c.stock)
                    .where(queue.c.stock.in_(eligible), queue.c.status == "PENDING")
                    .order_by(queue.c.last_debated, queue.c.stock)
                    .limit(limit)
                ).scalars()
            )

    def debated(self, stock: str, cutoff):
        with self.engine.begin() as conn:
            conn.execute(
                update(queue)
                .where(queue.c.stock == stock)
                .values(last_debated=cutoff.isoformat(), status="REVIEWED")
            )

    def queue_status(self) -> list[dict]:
        with self.engine.connect() as conn:
            return [dict(x._mapping) for x in conn.execute(select(queue))]

    def reserve_model(self, role: str, estimate: Decimal, monthly_cap: Decimal, scope=None) -> str:
        month = utcnow().strftime("%Y-%m")
        with self.transaction() as conn:
            rows = conn.execute(select(usage).where(usage.c.month == month)).all()
            used = sum(
                (Decimal(r.actual if r.actual is not None else r.reserved) for r in rows),
                Decimal(0),
            )
            if used + estimate > monthly_cap:
                raise ValueError("Monthly model budget exhausted; work remains deferred")
            if scope:
                scope_rows = conn.execute(
                    select(usage).where(
                        usage.c.payload["cycle"].as_string() == scope["cycle"],
                        usage.c.payload["kind"].as_string() == scope["kind"],
                    )
                ).all()
                scoped = sum(
                    (
                        Decimal(r.actual if r.actual is not None else r.reserved)
                        for r in scope_rows
                        if r.payload.get("cycle") == scope["cycle"]
                        and r.payload.get("kind") == scope["kind"]
                    ),
                    Decimal(0),
                )
                if scoped + estimate > Decimal(str(scope["cap"])):
                    raise ValueError("Cycle model budget exhausted; work remains deferred")
            call_id = str(uuid.uuid4())
            conn.execute(
                insert(usage).values(
                    id=call_id,
                    month=month,
                    role=role,
                    reserved=str(estimate),
                    actual=None,
                    status="RESERVED",
                    payload={"cycle": scope["cycle"], "kind": scope["kind"]} if scope else {},
                )
            )
        return call_id

    def settle_model(self, call_id: str, actual: Decimal | None, payload: dict):
        with self.transaction() as conn:
            previous = (
                conn.execute(select(usage.c.payload).where(usage.c.id == call_id)).scalar() or {}
            )
            conn.execute(
                update(usage)
                .where(usage.c.id == call_id)
                .values(
                    actual=str(actual) if actual is not None else None,
                    status="BILLED" if actual is not None else "UNKNOWN",
                    payload={**previous, **payload},
                )
            )

    def model_spend(self) -> Decimal:
        with self.engine.connect() as conn:
            rows = conn.execute(select(usage).where(usage.c.month == utcnow().strftime("%Y-%m")))
            return sum(
                (Decimal(r.actual if r.actual is not None else r.reserved) for r in rows),
                Decimal(0),
            )

    def scoped_spend(self, cycle: str, kind: str) -> Decimal:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(usage).where(
                    usage.c.payload["cycle"].as_string() == cycle,
                    usage.c.payload["kind"].as_string() == kind,
                )
            )
            return sum(
                (Decimal(r.actual if r.actual is not None else r.reserved) for r in rows),
                Decimal(0),
            )

    def append_chat(self, role: str, text: str):
        with self.engine.begin() as conn:
            conn.execute(
                insert(chat).values(
                    id=str(uuid.uuid4()), at=utcnow().isoformat(), role=role, text=text
                )
            )

    def chat_history(self, limit: int = 20) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(chat.c.role, chat.c.text).order_by(chat.c.at.desc()).limit(limit)
            ).all()
        return [{"role": r.role, "content": r.text} for r in reversed(rows)]

    def purge_chat(self):
        with self.engine.begin() as conn:
            conn.execute(delete(chat))
