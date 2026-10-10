import asyncio
import json
import shutil
import subprocess

import pytest
from textual.widgets import DataTable, Input, RichLog, Static

from tradebot.cli import main
from tradebot.service import TradeService
from tradebot.settings import Credentials
from tradebot.terminal import TradingTerminal


@pytest.mark.parametrize("args", [("--help",), ("--demo", "--doctor"), ()])
def test_installed_tradingworkflow_command(tmp_path, args):
    command = shutil.which("tradingworkflow")
    assert command is not None, "Install the project into the active environment first"
    result = subprocess.run(
        [command, *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == (0 if args else 1), result.stderr
    if args == ("--help",):
        assert "usage: tradingworkflow" in result.stdout
        assert "--onboard" in result.stdout and "--telegram-test" in result.stdout
    elif args:
        doctor = json.loads(result.stdout)
        assert doctor["configuration_ok"] and doctor["mode"] == "demo"
        assert not doctor["orders_enabled"] and not doctor["network_access_verified"]
    else:
        assert "Open onboarding in an interactive terminal" in result.stdout
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("size", [(80, 24), (120, 36), (160, 48)])
async def test_four_panes_visible_selection_and_focus(store, policy, size):
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True)
    app = TradingTerminal(service)
    async with app.run_test(size=size) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panes = [
            app.query_one("#" + x)
            for x in ("positions-pane", "detail-pane", "chat-pane", "portfolio-pane")
        ]
        for pane in panes:
            assert pane.region.width > 20 and pane.region.height > 5
            assert pane.region.x >= 0 and pane.region.right <= size[0]
            assert pane.region.bottom <= size[1]
        assert panes[0].region.y == panes[1].region.y
        assert panes[2].region.y == panes[3].region.y
        assert panes[2].region.y >= panes[0].region.bottom
        assert app.selected == "AAPL"
        await pilot.press("down")
        await pilot.pause()
        assert app.selected == "NVDA"
        assert "NVDA" in str(app.query_one("#detail-text", Static).content)
        await pilot.press("f3")
        assert app.focused.id == "question"
        await pilot.press("f4")
        assert app.focused.id == "portfolio-pane"
        await pilot.press("f2")
        assert app.focused.id == "detail-pane"
        await pilot.press("f1")
        assert app.focused.id == "positions"


async def test_chat_and_research_keyboard_interactions(store, policy):
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True)
    app = TradingTerminal(service)
    async with app.run_test(size=(120, 36)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("f3")
        field = app.query_one("#question", Input)
        field.value = "Explain this position"
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        assert field.value == "" and not field.disabled
        assert len(store.chat_history()) == 2
        log = app.query_one("#chat-log", RichLog)
        assert log.virtual_size.width <= log.content_size.width
        await pilot.press("ctrl+r")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert "Final confidence" in str(app.query_one("#detail-text", Static).content)
        assert "60.0%" in str(app.query_one("#detail-text", Static).content)
        assert log.virtual_size.width <= log.content_size.width
        assert "COMPLETE" in app.last_status
        assert store.snapshot().cash == 9000


async def test_slow_chat_does_not_freeze_selection_or_terminal(store, policy):
    started, release = asyncio.Event(), asyncio.Event()
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True)
    original = service.model.answer

    async def delayed(*args):
        started.set()
        await release.wait()
        return await original(*args)

    service.model.answer = delayed
    app = TradingTerminal(service)
    async with app.run_test(size=(100, 32)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("f3")
        app.query_one("#question", Input).value = "Question"
        await pilot.press("enter")
        await asyncio.wait_for(started.wait(), timeout=2)
        await pilot.press("f1", "down")
        await pilot.pause()
        assert app.selected == "NVDA"
        release.set()
        await app.workers.wait_for_complete()
        assert not app.query_one("#question", Input).disabled


async def test_empty_portfolio_and_refresh_error_are_visible(store, policy):
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True)
    snapshot = store.snapshot().model_copy(update={"positions": []})
    store.save_snapshot(snapshot)

    async def failed_refresh():
        raise RuntimeError("Provider read unavailable")

    service.refresh = failed_refresh
    app = TradingTerminal(service)
    async with app.run_test(size=(80, 24)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.query_one("#positions", DataTable).row_count == 0
        assert "No open position" in str(app.query_one("#detail-text", Static).content)
        assert "unavailable" in app.last_status


def test_cli_init_doctor_and_one_session(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["--init"]) == 0
    assert main(["--init"]) == 1
    assert main(["--doctor"]) == 1
    assert "missing" in capsys.readouterr().out
    assert main(["--demo", "--doctor"]) == 0
    assert main(["--demo", "--once"]) == 0
    output = capsys.readouterr().out
    assert '"status": "COMPLETE"' in output
    assert json.loads((tmp_path / "config.local.json").read_text())["instruments"] == []


def test_cli_missing_config_is_handled(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main([]) == 1
    assert "interactive terminal" in capsys.readouterr().out


def test_continuous_cli_demo_and_doctor(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["--init"]) == 0
    assert main(["--demo", "--supervisor", "--once"]) == 0
    result = json.loads(capsys.readouterr().out.split("credentials.\n")[-1])
    assert result["status"] == "CLOSED"
    assert set(result["payload"]["reports"]) == {"AAPL", "NVDA", "MSFT"}
    assert main(["--demo", "--supervisor", "--doctor"]) == 0
    assert main(["--headless", "--demo"]) == 1
    assert main(["--telegram-pair", "--demo"]) == 1


async def test_continuous_terminal_runs_and_stops_four_panes(store, policy):
    service = TradeService(store, policy, Credentials(_env_file=None), demo=True, continuous=True)
    app = TradingTerminal(service)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.3)
        assert service.supervisor_task is not None
        assert "Continuous research" in str(app.query_one("#performance-text", Static).content)
        await pilot.press("ctrl+r")
        await pilot.pause(0.2)
        assert app.query_one("#positions", DataTable).row_count == 2
        # Render an already tested closed report while the continuous workers remain active.

        cycle = service.supervisor.current()
        service.supervisor.memory.save_report(
            cycle["id"],
            "AAPL",
            {
                "cutoff": cycle["end"],
                "forecast": {"probability": 0.5},
                "roles": {"company": [{"summary": "Saved finding"}]},
                "evidence": [],
            },
        )
        app.render_portfolio()
        assert "Saved finding" in str(app.query_one("#detail-text", Static).content)
        await pilot.press("f3")
        app.query_one("#question", Input).value = "What does AAPL research show?"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert service.store.chat_history()[-1]["role"] == "assistant"
    assert service.closed
    assert service.supervisor_task.done()


def test_cli_headless_and_pair_paths_are_executable(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["--init"]) == 0

    config = json.loads((tmp_path / "config.local.json").read_text())
    config["instruments"] = [{"symbol": "NVDA", "name": "NVIDIA", "sector": "technology"}]
    (tmp_path / "config.local.json").write_text(json.dumps(config))
    monkeypatch.setenv("TRADEBOT_NVIDIA_API_KEY", "fixture")
    monkeypatch.setenv("TRADEBOT_TELEGRAM_BOT_TOKEN", "fixture")

    async def supervise(self, notify):
        assert self.continuous
        notify("Supervisor stopped")

    monkeypatch.setattr(TradeService, "run_supervisor", supervise)
    assert main(["--supervisor", "--headless"]) == 0
    from tradebot.telegram import TelegramNotifier

    async def pair(self):
        self.memory.set_setting(
            "telegram_owner", {"chat_id": "42", "bot_fingerprint": self.identity}
        )

    monkeypatch.setattr(TelegramNotifier, "pair", pair)
    assert main(["--telegram-pair"]) == 0
    assert main(["--supervisor", "--doctor"]) == 0
    monkeypatch.delenv("TRADEBOT_TELEGRAM_BOT_TOKEN")
    assert main(["--telegram-pair"]) == 1
    assert "fixture" not in capsys.readouterr().out
