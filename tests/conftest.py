import pytest

from tradebot.service import demo_policy, demo_snapshot
from tradebot.storage import Store


@pytest.fixture(autouse=True)
def isolate_provider_secrets(monkeypatch):
    """No offline test may inherit an owner's real provider credentials or dotenv."""
    for name in (
        "NVIDIA_API_KEY",
        "OPENROUTER_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "X_BEARER_TOKEN",
        "X_AUTH_TOKEN",
        "X_CT0",
        "TAVILY_API_KEY",
        "SEC_USER_AGENT",
    ):
        monkeypatch.setenv("TRADEBOT_" + name, "")


@pytest.fixture
def store(tmp_path):
    result = Store(f"sqlite:///{tmp_path / 'state.db'}")
    result.save_snapshot(demo_snapshot())
    yield result
    result.close()


@pytest.fixture
def policy():
    return demo_policy()
