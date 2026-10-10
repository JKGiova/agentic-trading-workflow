import asyncio
import hashlib
import json
import stat
from datetime import timedelta
from pathlib import Path

import pytest
from textual.message_pump import MessagePump
from textual.widgets import Input, Static

from tradebot.onboarding import REQUIRED_STEPS, SetupController, SetupError, save_token
from tradebot.settings import Credentials, Policy
from tradebot.setup_terminal import SecretInput, SetupTerminal


@pytest.fixture
def providers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in (
        "NVIDIA_API_KEY",
        "OPENROUTER_API_KEY",
        "X_AUTH_TOKEN",
        "X_CT0",
        "SEC_USER_AGENT",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "X_BEARER_TOKEN",
        "TAVILY_API_KEY",
        "TELEGRAM_BOT_TOKEN",
    ):
        monkeypatch.delenv("TRADEBOT_" + name)
    controller = SetupController()
    yield controller
    controller.close()


def test_provider_access_roundtrip_preserves_policy_and_keeps_secrets_out_of_metadata(
    providers, policy
):
    controller = providers
    Path("config.local.json").write_text(policy.model_dump_json())
    controller.save_access("model_access", {"nvidia_api_key": "private-nvidia"})
    controller.save_news_access(
        "auth_token=private-auth; ct0=private-csrf; guest_id=ignored",
        "42:@approved",
        {
            "sec_user_agent": "TestCompany contact@example.com",
            "alpaca_api_key": "private-alpaca",
            "alpaca_secret_key": "private-alpaca-secret",
            "x_bearer_token": "private-official",
            "tavily_api_key": "private-tavily",
        },
        "Example.com, example.com, www.sec.gov",
    )
    assert controller.pending_steps() == ["telegram", "report_schedule"]
    loaded = Credentials()
    assert loaded.nvidia_api_key.get_secret_value() == "private-nvidia"
    assert loaded.x_auth_token.get_secret_value() == "private-auth"
    assert loaded.x_ct0.get_secret_value() == "private-csrf"
    assert loaded.sec_user_agent == "TestCompany contact@example.com"
    saved = controller.policy()
    assert saved.instruments == policy.instruments and saved.risk == policy.risk
    assert saved.approved_x_authors == {"42": "approved"}
    assert saved.article_domains == ["example.com", "www.sec.gov"]
    private = Path(".tradebot/credentials.env")
    assert stat.S_IMODE(private.stat().st_mode) == 0o600
    state = json.dumps(controller.memory.setting("onboarding"))
    assert "private-" not in state and "private-" not in Path("config.local.json").read_text()
    assert "guest_id" not in private.read_text()
    reopened = SetupController()
    try:
        assert reopened.pending_steps() == ["telegram", "report_schedule"]
        reopened.save_access("model_access", {"nvidia_api_key": ""})
        assert reopened.credentials.nvidia_api_key.get_secret_value() == "private-nvidia"
    finally:
        reopened.close()


@pytest.mark.parametrize(
    "step,values",
    [
        ("model_access", {}),
        ("model_access", {"nvidia_api_key": "secret\nINJECT=x"}),
        ("model_access", {"unknown": "private-secret"}),
        ("news_access", {"x_auth_token": "private-auth"}),
        ("news_access", {"alpaca_api_key": "private-alpaca"}),
        ("news_access", {"sec_user_agent": "missing email"}),
        ("news_access", {"sec_user_agent": "Company x@example.com\r\nHeader: value"}),
    ],
)
def test_invalid_credentials_are_redacted_and_not_saved(providers, step, values):
    with pytest.raises(SetupError) as error:
        providers.save_access(step, values)
    assert "private-" not in str(error.value)
    assert not Path(".tradebot/credentials.env").exists()


@pytest.mark.parametrize(
    "cookies,authors,domains",
    [
        ("auth_token=private-auth", "42:approved", "example.com"),
        (
            "auth_token=private-auth; auth_token=again; ct0=private-csrf",
            "42:approved",
            "example.com",
        ),
        ("auth_token=private-auth; ct0=", "42:approved", "example.com"),
        ("auth_token=private-auth; ct0=private-csrf", "", "example.com"),
        ("", "42:approved,42:other", "example.com"),
        ("", "wrong", "example.com"),
        ("", "invalid:approved", "example.com"),
        ("", "42:bad/handle", "example.com"),
        ("", "42:approved", "https://example.com"),
        ("", "42:approved", "localhost"),
    ],
)
def test_invalid_source_form_does_not_write_keys_or_policy(providers, cookies, authors, domains):
    with pytest.raises(SetupError):
        providers.save_news_access(cookies, authors, {}, domains)
    assert not Path(".tradebot/credentials.env").exists() and not Path("config.local.json").exists()


@pytest.mark.parametrize("exported", ["", "another-key"])
def test_environment_override_conflict_is_explained_and_never_saved(
    providers, monkeypatch, exported
):
    monkeypatch.setenv("TRADEBOT_NVIDIA_API_KEY", exported)
    with pytest.raises(SetupError, match="exported"):
        providers.save_access("model_access", {"nvidia_api_key": "private-nvidia"})
    assert not Path(".tradebot/credentials.env").exists()


def test_credential_rotation_invalidates_only_provider_step(providers, monkeypatch):
    providers.save_access("model_access", {"nvidia_api_key": "private-nvidia"})
    providers.complete_access("news_access", deferred=True)
    monkeypatch.setenv("TRADEBOT_NVIDIA_API_KEY", "rotated-key")
    reopened = SetupController()
    try:
        assert (
            "model_access" in reopened.pending_steps()
            and "news_access" not in reopened.pending_steps()
        )
    finally:
        reopened.close()


def pair_fixture(controller):
    save_token("123:fixture")
    controller.credentials = Credentials()
    owner = {"chat_id": "42", "bot_fingerprint": hashlib.sha256(b"123:fixture").hexdigest()}
    controller.memory.set_setting("telegram_owner", owner)
    controller.memory.set_setting("onboarding", {"version": 2, "steps": {"telegram": owner}})
    controller.save_schedule(3)


@pytest.mark.parametrize("size", [(80, 24), (120, 36)])
async def test_v2_migration_model_news_ui_secret_redaction_and_relaunch(
    providers, monkeypatch, size
):
    pair_fixture(providers)
    events = []
    original = MessagePump._dispatch_message

    async def dispatch(self, message):
        if isinstance(message, (Input.Changed, Input.Submitted)) and isinstance(
            message.input, SecretInput
        ):
            events.append(repr(message))
        return await original(self, message)

    monkeypatch.setattr(MessagePump, "_dispatch_message", dispatch)
    app = SetupTerminal(providers)
    async with app.run_test(size=size) as pilot:
        assert app.query_one("#model-form").display and not app.query_one("#token-form").display
        field = app.query_one("#nvidia_api_key", Input)
        field.value = "private-nvidia"
        assert field.password and "private-nvidia" not in app.export_screenshot()
        await pilot.press("enter")
        await pilot.pause()
        assert app.query_one("#news-form").display
        assert field.value == ""
        cookies = app.query_one("#x-cookies", Input)
        cookies.value = "auth_token=private-auth; ct0=private-csrf"
        app.query_one("#x-authors", Input).value = "42:approved"
        app.query_one("#article-domains", Input).value = "example.com"
        cookies.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert app.query_one("#home").display
        assert providers.pending_steps() == [] and cookies.value == ""
        assert "private-" not in app.export_screenshot()
        await pilot.click("#model")
        assert field.value == ""  # Saved keys are never revealed or prefilled.
        field.value = "bad\nkey"
        await pilot.press("enter")
        await pilot.pause()
        assert "valid" in str(app.query_one("#status", Static).content)
        field.value = "private-updated"
        await pilot.press("enter")
        await pilot.pause()
        assert app.query_one("#home").display
    assert events and "private-" not in " ".join(events)
    assert all("<hidden>" in item for item in events)
    reopened = SetupTerminal(providers)
    async with reopened.run_test(size=size):
        assert reopened.query_one("#home").display
        assert "private-" not in reopened.export_screenshot()


async def test_telegram_only_setup_can_defer_model_and_x(providers):
    pair_fixture(providers)
    app = SetupTerminal(providers)
    async with app.run_test() as pilot:
        await pilot.click("#skip-model")
        await pilot.pause()
        assert app.query_one("#news-form").display
        await pilot.click("#skip-news")
        await pilot.pause()
        assert app.query_one("#home").display and not providers.pending_steps()
        assert "nvidia_api_key" in providers.credentials.analysis_missing(Policy())
        assert "Deferred" in str(app.query_one("#status", Static).content)
    assert REQUIRED_STEPS == ("telegram", "report_schedule", "model_access", "news_access")


def test_source_storage_failure_stays_incomplete_and_retryable(providers, monkeypatch):
    original = providers.save_authors

    def failure(*args):
        raise OSError("private-auth should never be shown")

    monkeypatch.setattr(providers, "save_authors", failure)
    with pytest.raises(OSError):
        providers.save_news_access("auth_token=private-auth; ct0=private-csrf", "42:approved", {})
    assert "news_access" in providers.pending_steps()
    monkeypatch.setattr(providers, "save_authors", original)
    providers.save_news_access("", "42:approved", {})
    assert "news_access" not in providers.pending_steps()


@pytest.mark.parametrize("interrupted", [False, True, "rollover"])
def test_source_policy_changes_are_staged_and_preserve_open_cycle_on_restart(
    providers, policy, interrupted
):
    from decimal import Decimal
    from types import SimpleNamespace

    from tradebot.analysis_memory import digest
    from tradebot.contracts import utcnow
    from tradebot.models import DemoModel
    from tradebot.supervisor import AnalysisSupervisor
    from tradebot.telegram import DemoNotifier

    now = utcnow()
    Path("config.local.json").write_text(policy.model_dump_json())
    cycle = providers.memory.open_cycle(
        now, 3, ["AAPL"], digest(policy.model_dump(mode="json")), policy.model_dump(mode="json")
    )
    providers.save_news_access(
        "auth_token=private-auth; ct0=private-csrf", "42:approved", {}, "example.com"
    )
    if interrupted == "rollover":
        now += timedelta(hours=3)
        providers.memory.freeze(cycle["id"], now)
        cycle = providers.memory.open_cycle(
            now, 3, ["AAPL"], digest(policy.model_dump(mode="json")), policy.model_dump(mode="json")
        )
    elif interrupted:
        transition = providers.memory.setting("news_policy_transition")
        providers.memory.set_setting("news_policy_transition", {**transition, "ready": False})
    changed = providers.policy()
    team = AnalysisSupervisor(
        changed, providers.store, DemoModel(), SimpleNamespace(), DemoNotifier(), clock=lambda: now
    )
    restored = team.current()
    assert restored["id"] == cycle["id"] and restored["end"] == cycle["end"]
    assert not team.research.policy.approved_x_authors and not team.research.policy.article_domains
    different = changed.model_copy(update={"cycle_model_budget": Decimal("1")})
    broken = AnalysisSupervisor(
        different,
        providers.store,
        DemoModel(),
        SimpleNamespace(),
        DemoNotifier(),
        clock=lambda: now,
    )
    with pytest.raises(ValueError, match="restore"):
        broken.current()
    now += timedelta(hours=3)
    providers.memory.freeze(cycle["id"], now)
    new = team.current()
    assert new["id"] != cycle["id"]
    assert team.research.policy.approved_x_authors == {"42": "approved"}
    assert team.research.policy.article_domains == ["example.com"]
    assert providers.memory.setting("news_policy_transition") is None


async def test_invalid_existing_policy_can_defer_news_setup_without_crashing(providers):
    pair_fixture(providers)
    providers.complete_access("model_access", deferred=True)
    await asyncio.to_thread(Path("config.local.json").write_text, '{"broken":true}')
    app = SetupTerminal(providers)
    async with app.run_test() as pilot:
        assert app.query_one("#news-form").display
        assert "Repair" in str(app.query_one("#status", Static).content)
        await pilot.click("#skip-news")
        await pilot.pause()
        assert app.query_one("#home").display
