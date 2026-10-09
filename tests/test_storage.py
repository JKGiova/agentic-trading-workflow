from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal

import pytest

from tradebot.contracts import Category, utcnow
from tradebot.research import make_evidence
from tradebot.storage import Store


def test_persistence_and_immutable_stages(store, tmp_path):
    sid = store.start_session(utcnow())
    store.save_stage(sid, "AAPL", "forecast", {"probability": 0.4})
    store.save_stage(sid, "AAPL", "forecast", {"probability": 0.9})
    assert store.stage(sid, "AAPL", "forecast") == {"probability": 0.4}
    assert store.latest("AAPL")["forecast"]["probability"] == 0.4
    reopened = Store(f"sqlite:///{tmp_path / 'state.db'}")
    assert reopened.snapshot().cash == 9000
    assert reopened.latest("AAPL")["forecast"]["probability"] == 0.4
    reopened.close()


def test_atomic_lease_and_owner_fencing(store):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: store.acquire("decision-session", str(i), 60), range(8)))
    assert sum(results) == 1
    store.release("decision-session", "wrong-owner")
    assert not store.acquire("decision-session", "new", 60)
    store.release("decision-session", str(results.index(True)))
    assert store.acquire("decision-session", "new", 60)


def test_atomic_operating_budget(store):
    def reserve(_):
        try:
            return store.reserve_model("test", Decimal("1"), Decimal("3"))
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve, range(8)))
    assert sum(x is not None for x in results) == 3
    assert store.model_spend() == 3
    first = next(x for x in results if x)
    store.settle_model(first, Decimal(".5"), {})
    assert store.model_spend() == Decimal("2.5")
    store.settle_model(first, None, {"ambiguous": True})
    assert store.model_spend() == 3


def test_queue_is_fair_and_has_no_confidence_priority(store):
    store.enqueue(["NVDA", "AAPL", "MSFT"])
    assert store.fair_candidates(["NVDA", "AAPL", "MSFT"], 2) == ["AAPL", "MSFT"]
    store.debated("AAPL", utcnow())
    store.enqueue(["AAPL", "MSFT", "NVDA"])
    assert store.fair_candidates(["AAPL", "MSFT", "NVDA"], 2) == ["MSFT", "NVDA"]


def test_history_respects_publication_and_observation_cutoffs(store):
    cutoff = utcnow()
    old = make_evidence(
        "test",
        "old",
        "AAPL",
        Category.COMPANY,
        "old",
        "old",
        "https://example.com",
        cutoff - timedelta(hours=1),
    ).model_copy(update={"retrieved_at": cutoff - timedelta(minutes=1)})
    future = old.model_copy(update={"id": "future", "published_at": cutoff + timedelta(minutes=1)})
    later_seen = old.model_copy(
        update={"id": "later-seen", "retrieved_at": cutoff + timedelta(minutes=1)}
    )
    store.record_research("s", [old, future, later_seen], [])
    assert [x.id for x in store.history("AAPL", cutoff, cutoff - timedelta(days=1))] == [old.id]


def test_chat_roundtrip(store):
    store.append_chat("user", "question")
    store.append_chat("assistant", "answer")
    assert [x["role"] for x in store.chat_history()] == ["user", "assistant"]
    store.purge_chat()
    assert store.chat_history() == []


@pytest.mark.postgres
def test_postgres_ledger(tmp_path):
    import os

    url = os.environ.get("TRADEBOT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TRADEBOT_TEST_DATABASE_URL for isolated PostgreSQL integration")
    from sqlalchemy import create_engine

    from tradebot.storage import metadata

    engine = create_engine(url)
    metadata.drop_all(engine)
    engine.dispose()
    db = Store(url)
    try:
        test_atomic_lease_and_owner_fencing(db)
        test_atomic_operating_budget(db)
        test_queue_is_fair_and_has_no_confidence_priority(db)
    finally:
        db.close()
