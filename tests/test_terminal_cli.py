import asyncio
import json

import pytest
from textual.widgets import DataTable, Input, RichLog, Static

from tradebot.cli import main
from tradebot.service import TradeService
from tradebot.settings import Credentials
from tradebot.terminal import TradingTerminal


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
    assert "Startup/session failed" in capsys.readouterr().out
