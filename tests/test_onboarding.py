import asyncio
import json
import os
import stat
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from dotenv import dotenv_values
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from textual.widgets import Input, Static

from tradebot.analysis_memory import cycles, outbox, tasks
from tradebot.cli import main
from tradebot.contracts import utcnow
from tradebot.onboarding import TOKEN_NAME, SetupController, SetupError, save_token
from tradebot.onboarding import test_status as status_text
from tradebot.service import demo_policy
from tradebot.settings import Credentials
from tradebot.setup_terminal import SetupTerminal
from tradebot.telegram import TelegramNotifier

TOKEN = "123456789:TEST_ONLY_secret_abc"


class TelegramAPI:
    def __init__(self):
        self.calls, self.clients = [], []
        self.failure = ""
        self.started, self.release = asyncio.Event(), asyncio.Event()

    async def handle(self, request):
        method = request.url.path.rsplit("/", 1)[-1]
        payload = json.loads(request.content)
        self.calls.append((method, payload))
        if method == "getMe":
            if self.failure == "bad_token":
                return httpx.Response(401, json={"ok": False, "description": TOKEN})
            if self.failure == "not_bot":
                return httpx.Response(200, json={"ok": True, "result": {"is_bot": False}})
            return httpx.Response(
                200, json={"ok": True, "result": {"is_bot": True, "username": "fixture_bot"}}
            )
        if method == "getUpdates":
            if self.failure == "blocked_pair":
                self.started.set()
                await self.release.wait()

            def message(uid, cid, sender, text, kind="private"):
                return {
                    "update_id": uid,
                    "message": {
                        "chat": {"id": cid, "type": kind},
                        "from": {"id": sender},
                        "text": text,
                    },
                }

            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": [
                        message(1, -8, 42, "/start fixture_nonce", "group"),
                        message(2, 55, 42, "/start fixture_nonce"),
                        message(3, 42, 42, "/start wrong_nonce"),
                        message(4, 42, 42, "/start fixture_nonce"),
                    ],
                },
            )
        assert method == "sendMessage"
        assert payload["chat_id"] == "42"
        if self.failure == "quota":
            return httpx.Response(429, json={"parameters": {"retry_after": 5}})
        if self.failure == "timeout":
            raise httpx.ReadTimeout("Response URL contains " + TOKEN, request=request)
        if self.failure == "blocked_send":
            self.started.set()
            await self.release.wait()
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 77}})

    def factory(self, credentials, memory):
        client = httpx.AsyncClient(transport=httpx.MockTransport(self.handle))
        self.clients.append(client)
        notifier = TelegramNotifier(credentials, memory, client)
        notifier.owns_client = True
        return notifier


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(TOKEN_NAME)
    monkeypatch.setattr("tradebot.telegram.secrets.token_hex", lambda _: "fixture_nonce")
    api = TelegramAPI()
    controller = SetupController(notifier_factory=api.factory)
    # These legacy Telegram tests explicitly defer the new provider steps.
    controller.complete_access("model_access", deferred=True)
    controller.complete_access("news_access", deferred=True)
    yield controller, api
    controller.close()


async def test_first_run_pairs_sends_and_resumes_without_reentering_secrets(setup):
    controller, api = setup
    assert controller.pending_steps() == ["telegram", "report_schedule"]
    progress = []
    result = await controller.connect(TOKEN, progress.append)
    assert result["status"] == "SENT"
    assert controller.pending_steps() == ["report_schedule"]
    controller.save_schedule("0.5")
    assert controller.pending_steps() == []
    assert controller.connection()["chat_id"] == "42"
    assert any("/start fixture_nonce" in text for text in progress)
    assert TOKEN not in " ".join(progress)
    assert Credentials().telegram_bot_token.get_secret_value() == TOKEN
    assert not await asyncio.to_thread(Path(".env").exists)
    assert not await asyncio.to_thread(Path("config.local.json").exists)
    assert not controller.memory.rows(cycles)
    assert not controller.memory.rows(tasks)
    assert all(client.is_closed for client in api.clients)
    credentials = Path(".tradebot/credentials.env")
    if os.name != "nt":
        assert stat.S_IMODE((await asyncio.to_thread(credentials.stat)).st_mode) == 0o600
        assert stat.S_IMODE((await asyncio.to_thread(credentials.parent.stat)).st_mode) == 0o700
    reopened = SetupController(notifier_factory=api.factory)
    try:
        calls = len(api.calls)
        assert reopened.pending_steps() == []
        assert reopened.schedule().report_hours == 0.5
        assert reopened.connection()["chat_id"] == "42"
        assert len(api.calls) == calls  # Loading saved setup never makes a network call.
        await reopened.test()
        assert len(api.calls) == calls + 1
        assert api.calls[-1][0] == "sendMessage"
    finally:
        reopened.close()


@pytest.mark.parametrize("failure", ["bad_token", "not_bot"])
async def test_invalid_token_is_not_saved_or_paired(setup, failure):
    controller, api = setup
    api.failure = failure
    with pytest.raises(RuntimeError) as error:
        await controller.connect(TOKEN, lambda _: None)
    assert TOKEN not in str(error.value)
    assert not await asyncio.to_thread(Path(".tradebot/credentials.env").exists)
    assert not controller.connection()
    assert controller.pending_steps() == ["telegram", "report_schedule"]
    assert all(client.is_closed for client in api.clients)


@pytest.mark.parametrize("token", ["wrong", "123:x/y", "123:token\nother=value", "9:" + "x" * 600])
async def test_invalid_token_shape_is_rejected_without_api_calls(setup, token):
    controller, api = setup
    with pytest.raises(ValueError):
        await controller.connect(token)
    assert not api.calls


def test_private_storage_preserves_other_credentials_and_owner_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(TOKEN_NAME)
    Path(".env").write_text("TRADEBOT_TELEGRAM_BOT_TOKEN=111:old\n# owner configuration\n")
    secret = Path(".tradebot/credentials.env")
    secret.parent.mkdir()
    secret.write_text("TRADEBOT_NVIDIA_API_KEY='keep_this_key'\n")
    save_token(TOKEN)
    assert dotenv_values(secret)["TRADEBOT_NVIDIA_API_KEY"] == "keep_this_key"
    assert Credentials().telegram_bot_token.get_secret_value() == TOKEN
    assert "111:old" in Path(".env").read_text()
    monkeypatch.setenv(TOKEN_NAME, "999:explicit_environment")
    assert Credentials().telegram_bot_token.get_secret_value() == "999:explicit_environment"


def test_secret_file_replacement_failure_preserves_prior_contents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_token(TOKEN)
    original = Path(".tradebot/credentials.env").read_text()

    def fail(*_):
        raise OSError("Controlled disk failure")

    monkeypatch.setattr("tradebot.onboarding.os.replace", fail)
    with pytest.raises(OSError):
        save_token("987654321:new_token")
    assert Path(".tradebot/credentials.env").read_text() == original
    assert not list(Path(".tradebot").glob("credentials-*"))


def test_secret_file_symlinks_and_invalid_keys_are_rejected(tmp_path):
    target = tmp_path / "private.env"
    target.write_text("DO_NOT_CHANGE=yes")
    link = tmp_path / "link.env"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symbolic"):
        save_token(TOKEN, link)
    assert target.read_text() == "DO_NOT_CHANGE=yes"
    target.write_text("invalid-key=value")
    with pytest.raises(ValueError, match="credential name"):
        save_token(TOKEN, target)
    assert "invalid-key" in target.read_text()


async def test_exported_token_conflict_is_not_silently_saved(setup, monkeypatch):
    controller, api = setup
    monkeypatch.setenv(TOKEN_NAME, "other:environment_token")
    with pytest.raises(ValueError, match="environment"):
        await controller.connect(TOKEN)
    assert not api.calls
    assert not await asyncio.to_thread(Path(".tradebot/credentials.env").exists)


async def test_new_bot_requires_new_pairing_and_keeps_completed_future_steps(setup, monkeypatch):
    controller, api = setup
    await controller.connect(TOKEN, lambda _: None)
    controller.save_schedule(3)
    state = controller.memory.setting("onboarding")
    state["steps"]["settings"] = {"selected": True}
    controller.memory.set_setting("onboarding", state)
    monkeypatch.setattr(
        "tradebot.onboarding.REQUIRED_STEPS", ("telegram", "report_schedule", "settings", "wallet")
    )
    assert controller.pending_steps() == ["wallet"]
    pair_count = sum(method == "getUpdates" for method, _ in api.calls)
    result = await controller.connect("222222:new_bot_secret", lambda _: None)
    assert result["status"] == "SENT"
    assert sum(method == "getUpdates" for method, _ in api.calls) == pair_count + 1
    assert controller.pending_steps() == ["wallet"]
    assert controller.memory.setting("onboarding")["steps"]["settings"] == {"selected": True}


async def test_telegram_test_isolates_research_outbox_and_quota_retry(setup):
    controller, api = setup
    now = utcnow()
    cycle = controller.memory.open_cycle(now, 3, ["AAPL"], "fixed")
    controller.memory.queue_summary(cycle["id"], ["private research report"], now)
    api.failure = "quota"
    result = await controller.connect(TOKEN, lambda _: None)
    assert result["status"] == "PENDING"
    assert controller.pending_steps() == ["telegram", "report_schedule"]
    research = controller.memory.rows(outbox, outbox.c.cycle == cycle["id"])[0]
    assert research["status"] == "PENDING"
    assert all(payload.get("text") != "private research report" for _, payload in api.calls)
    calls = len(api.calls)
    retry = await controller.test()
    assert retry["id"] == result["id"] and retry["status"] == "PENDING"
    assert len(api.calls) == calls  # Repeated clicks respect the server's retry time.
    with controller.store.transaction() as connection:
        connection.execute(
            update(outbox)
            .where(outbox.c.id == result["id"])
            .values(retry_at=(now - timedelta(seconds=1)).isoformat())
        )
    api.failure = ""
    retry = await controller.test()
    assert retry["id"] == result["id"] and retry["status"] == "SENT"
    controller.save_schedule(3)
    assert controller.pending_steps() == []


async def test_unknown_delivery_never_replays_on_launch_or_in_research_loop(setup):
    controller, api = setup
    api.failure = "timeout"
    result = await controller.connect(TOKEN, lambda _: None)
    assert result["status"] == "UNKNOWN"
    assert controller.pending_steps() == ["telegram", "report_schedule"]
    assert TOKEN not in json.dumps(result)
    calls = len(api.calls)
    notifier = api.factory(controller.credentials, controller.memory)
    await notifier.deliver(utcnow() + timedelta(hours=1))
    await notifier.close()
    assert len(api.calls) == calls
    api.failure = ""
    retry = await controller.test()  # Only an explicit new test creates a new send.
    assert retry["id"] != result["id"] and retry["status"] == "SENT"


async def test_unpaired_test_has_no_network_side_effects(setup):
    controller, api = setup
    with pytest.raises(ValueError, match="Connect"):
        await controller.test()
    assert not api.calls


@pytest.mark.parametrize("size", [(80, 24), (120, 36)])
async def test_onboarding_terminal_masks_token_pairs_and_reopens_as_home(setup, size):
    controller, api = setup
    app = SetupTerminal(controller)
    async with app.run_test(size=size) as pilot:
        field = app.query_one("#token", Input)
        assert field.password and app.focused is field
        for widget_id in ("token", "connect", "status", "exit"):
            widget = app.query_one("#" + widget_id)
            assert 0 <= widget.region.x < widget.region.right <= size[0]
            assert 0 <= widget.region.y < widget.region.bottom <= size[1] - 1
        field.value = TOKEN
        assert TOKEN not in app.export_screenshot()
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert not app.query_one("#token-form").display
        assert app.query_one("#schedule-form").display
        assert "delivered" in str(app.query_one("#status", Static).content)
        assert field.value == ""
        for widget_id in ("report-hours", "save-schedule", "status", "exit"):
            widget = app.query_one("#" + widget_id)
            assert 0 <= widget.region.x < widget.region.right <= size[0]
            assert 0 <= widget.region.y < widget.region.bottom <= size[1] - 1
        app.query_one("#report-hours", Input).value = "0.5"
        await pilot.click("#save-schedule")
        await pilot.pause()
        assert app.query_one("#home").display
        assert "0.5 hours" in str(app.query_one("#schedule-summary", Static).content)
        assert controller.pending_steps() == []
        assert not controller.memory.rows(tasks)
        await pilot.click("#test")
        await app.workers.wait_for_complete()
        await pilot.click("#change")
        assert field.value == TOKEN and field.password
        assert TOKEN not in app.export_screenshot()
    assert all(client.is_closed for client in api.clients)
    calls = len(api.calls)
    reopened = SetupTerminal(controller)
    async with reopened.run_test(size=size) as pilot:
        assert reopened.query_one("#home").display
        assert not reopened.query_one("#token-form").display
        assert len(api.calls) == calls
        await pilot.click("#exit")


async def test_exiting_during_pairing_cancels_request_and_does_not_save_token(setup):
    controller, api = setup
    api.failure = "blocked_pair"
    app = SetupTerminal(controller)
    async with app.run_test() as pilot:
        app.query_one("#token", Input).value = TOKEN
        await pilot.press("enter")
        await asyncio.wait_for(api.started.wait(), 2)
        assert TOKEN not in repr(list(app.workers))
        await pilot.press("ctrl+q")
    assert all(client.is_closed for client in api.clients)
    assert not await asyncio.to_thread(Path(".tradebot/credentials.env").exists)
    assert not controller.connection()


async def test_token_is_redacted_from_input_events_and_debug_descriptions(setup, monkeypatch):
    controller, _ = setup
    app = SetupTerminal(controller)
    observed = []
    from textual.message_pump import MessagePump

    original = MessagePump._dispatch_message

    async def inspect_message(self, message):
        if isinstance(message, (Input.Changed, Input.Submitted)) and message.input.id == "token":
            observed.append(repr(message))
        return await original(self, message)

    monkeypatch.setattr(MessagePump, "_dispatch_message", inspect_message)
    async with app.run_test() as pilot:
        app.query_one("#token", Input).value = TOKEN
        await pilot.press("enter")
        await app.workers.wait_for_complete()
    assert observed and TOKEN not in " ".join(observed)
    assert all("<hidden>" in item for item in observed)


async def test_failed_pair_and_test_ui_remain_retryable_without_secret_leaks(setup):
    controller, api = setup
    app = SetupTerminal(controller)
    async with app.run_test() as pilot:
        field = app.query_one("#token", Input)
        field.value = TOKEN
        api.failure = "bad_token"
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        assert "Connection failed" in str(app.query_one("#status", Static).content)
        assert TOKEN not in app.export_screenshot()
        assert not field.disabled
        api.failure = ""
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.click("#save-schedule")
        api.failure = "timeout"
        await pilot.click("#test")
        await app.workers.wait_for_complete()
        assert "could not be confirmed" in str(app.query_one("#status", Static).content)
        assert TOKEN not in app.export_screenshot()


def test_cli_default_opens_setup_without_policy_model_or_broker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("tradebot.cli.sys.stdin", SimpleNamespace(isatty=lambda: True))
    shown = []

    def run(self):
        shown.append(self.force)
        assert self.controller.pending_steps() == [
            "telegram",
            "report_schedule",
            "model_access",
            "news_access",
        ]

    def forbidden(*args, **kwargs):
        raise AssertionError("Setup cannot create a research service")

    monkeypatch.setattr(SetupTerminal, "run", run)
    monkeypatch.setattr("tradebot.cli.TradeService", forbidden)
    assert main([]) == 0
    assert main(["--onboard"]) == 0
    assert shown == [False, True]
    assert not Path("config.local.json").exists()


def test_cli_standalone_test_and_noninteractive_setup_paths(setup, monkeypatch, capsys):
    controller, api = setup
    monkeypatch.setattr("tradebot.cli.sys.stdin", SimpleNamespace(isatty=lambda: False))
    assert main([]) == 1
    assert "interactive terminal" in capsys.readouterr().out
    assert main(["--telegram-test"]) == 1
    asyncio.run(controller.connect(TOKEN, lambda _: None))
    real_controller = SetupController
    monkeypatch.setattr(
        "tradebot.onboarding.SetupController",
        lambda database: real_controller(database, notifier_factory=api.factory),
    )
    assert main(["--telegram-test"]) == 0
    assert "delivered" in capsys.readouterr().out
    assert main(["--onboard", "--demo"]) == 1
    api.failure = "timeout"
    assert main(["--telegram-test"]) == 1
    assert TOKEN not in capsys.readouterr().out


def test_status_messages_handle_incomplete_delivery():
    assert "delivered" in status_text({"status": "SENT"})
    assert "rate limiting" in status_text({"status": "PENDING"})
    assert "could not be confirmed" in status_text({"status": "SENDING"})


@pytest.mark.parametrize("hours", [0, -1, float("nan"), float("inf"), "", "abc", 1e-10, 8761])
def test_invalid_report_intervals_preserve_saved_setup(setup, hours):
    controller, api = setup
    controller.save_schedule(2.5)
    state = controller.memory.setting("onboarding")
    with pytest.raises(SetupError, match="interval"):
        controller.save_schedule(hours)
    assert controller.schedule().report_hours == 2.5
    assert controller.memory.setting("onboarding") == state
    assert not api.calls and not controller.memory.rows(tasks)


async def test_v1_setup_adds_interval_without_repairing_and_can_edit_it(setup):
    controller, api = setup
    await controller.connect(TOKEN, lambda _: None)
    state = controller.memory.setting("onboarding")
    state["version"] = 1
    controller.memory.set_setting("onboarding", state)
    calls = len(api.calls)
    app = SetupTerminal(controller)
    async with app.run_test(size=(80, 24)) as pilot:
        assert app.query_one("#schedule-form").display
        assert not app.query_one("#token-form").display
        field = app.query_one("#report-hours", Input)
        field.value = "2"
        await pilot.press("enter")
        await pilot.pause()
        assert controller.pending_steps() == []
        assert controller.memory.setting("onboarding")["version"] == 3
        await pilot.click("#schedule")
        assert field.value == "2"
        field.value = "-1"
        await pilot.press("enter")
        await pilot.pause()
        assert "interval" in str(app.query_one("#status", Static).content)
        assert controller.schedule().report_hours == 2
        field.value = "0.5"
        await pilot.press("enter")
        await pilot.pause()
        assert app.query_one("#home").display
        assert controller.schedule().report_hours == 0.5
    assert len(api.calls) == calls
    assert controller.connection()["chat_id"] == "42"


@pytest.mark.parametrize("failure", [OSError, SQLAlchemyError])
async def test_interval_save_failure_rolls_back_preferences_and_keeps_ui_retryable(
    setup, monkeypatch, failure
):
    controller, _ = setup
    await controller.connect(TOKEN, lambda _: None)
    controller.save_schedule(2)
    state = controller.memory.setting("onboarding")
    original = controller.store._ensure

    def fail_state(conn, table, row):
        if row.get("name") == "onboarding":
            raise failure("Controlled storage failure")
        return original(conn, table, row)

    app = SetupTerminal(controller)
    async with app.run_test() as pilot:
        await pilot.click("#schedule")
        app.query_one("#report-hours", Input).value = "4"
        monkeypatch.setattr(controller.store, "_ensure", fail_state)
        await pilot.press("enter")
        await pilot.pause()
        assert "Could not save" in str(app.query_one("#status", Static).content)
        assert controller.schedule().report_hours == 2
        assert controller.memory.setting("onboarding") == state
        monkeypatch.setattr(controller.store, "_ensure", original)
        await pilot.press("enter")
        await pilot.pause()
        assert app.query_one("#home").display
        assert controller.schedule().report_hours == 4


async def test_supervisor_doctor_reads_onboarding_and_requires_matching_telegram(
    setup, monkeypatch, capsys
):
    controller, api = setup
    await controller.connect(TOKEN, lambda _: None)
    controller.save_schedule(0.5)
    await asyncio.to_thread(Path("config.local.json").write_text, demo_policy().model_dump_json())
    monkeypatch.setenv("TRADEBOT_NVIDIA_API_KEY", "fixture_only_nvidia")
    calls = len(api.calls)
    assert main(["--supervisor", "--doctor"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["report_interval_hours"] == 0.5 and doctor["telegram_ready"]
    assert not doctor["network_access_verified"] and not controller.memory.rows(tasks)
    assert len(api.calls) == calls
    monkeypatch.setenv(TOKEN_NAME, "999:different_bot")
    assert main(["--supervisor", "--doctor"]) == 1
    assert not json.loads(capsys.readouterr().out)["telegram_ready"]
    assert main(["--supervisor", "--headless"]) == 1
    assert "paired Telegram chat" in capsys.readouterr().out
