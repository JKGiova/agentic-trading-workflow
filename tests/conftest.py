import pytest

from tradebot.service import demo_policy, demo_snapshot
from tradebot.storage import Store


@pytest.fixture
def store(tmp_path):
    result = Store(f"sqlite:///{tmp_path / 'state.db'}")
    result.save_snapshot(demo_snapshot())
    yield result
    result.close()


@pytest.fixture
def policy():
    return demo_policy()
