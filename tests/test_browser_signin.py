import asyncio
import hashlib
import os
import signal
import stat
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from playwright.async_api import Error
from textual.widgets import Button, Input, Static

from tradebot import browser_signin
from tradebot.browser_signin import XCookies, extract_cookies, install_browser, sign_in
from tradebot.onboarding import SetupController, SetupError, save_token
from tradebot.settings import Credentials
from tradebot.setup_terminal import SetupTerminal


def cookie(name, value=None, **updates):
    return {
        "name": name,
        "value": value or "private-" + name,
        "domain": ".x.com",
        "path": "/",
        "secure": True,
        "expires": -1,
        **updates,
    }


PAIR = [cookie("auth_token"), cookie("ct0")]


def test_capture_only_required_cookies_without_repr_leak():
    captured = extract_cookies([*PAIR, cookie("guest_id"), cookie("other", domain="example.com")])
    assert captured.header() == "auth_token=private-auth_token; ct0=private-ct0"
    assert "private-" not in repr(captured)
    assert extract_cookies([*PAIR, cookie("ct0")]) == captured
    assert extract_cookies([cookie("auth_token", expires=101), cookie("ct0")], now=100)


@pytest.mark.parametrize(
    "change",
    [
        {"domain": "evilx.com"},
        {"domain": "x.com.evil.test"},
        {"domain": "twitter.com"},
        {"domain": "sub.x.com"},
        {"path": "/i"},
        {"secure": False},
        {"expires": 100},
        {"expires": float("nan")},
        {"expires": float("inf")},
        {"expires": "never"},
        {"value": "bad\nsecret"},
        {"value": "x"},
        {"value": "a" * 1025},
        {"partitionKey": "https://other.test"},
    ],
)
def test_invalid_domain_expiry_security_or_value_never_completes_pair(change):
    assert extract_cookies([cookie("auth_token", **change), cookie("ct0")], now=100) is None
    assert extract_cookies([cookie("auth_token")]) is None
    assert extract_cookies([*PAIR, cookie("ct0", "private-conflicting")]) is None


@pytest.fixture
def browser(tmp_path, monkeypatch):
    executable = tmp_path / "chromium"
    executable.touch()
    page = SimpleNamespace(goto=AsyncMock())
    context = SimpleNamespace(
        new_page=AsyncMock(return_value=page),
        cookies=AsyncMock(side_effect=[[], PAIR]),
        pages=[page],
    )
    instance = SimpleNamespace(
        new_context=AsyncMock(return_value=context),
        close=AsyncMock(),
        is_connected=Mock(return_value=True),
    )
    chromium = SimpleNamespace(
        executable_path=str(executable), launch=AsyncMock(return_value=instance)
    )
    manager = AsyncMock()
    manager.__aenter__.return_value = SimpleNamespace(chromium=chromium)
    monkeypatch.setattr(browser_signin, "async_playwright", lambda: manager)
    return SimpleNamespace(
        executable=executable,
        page=page,
        context=context,
        instance=instance,
        chromium=chromium,
        manager=manager,
    )


async def test_isolated_headed_login_polls_then_closes_without_persisting_profile(
    browser, tmp_path
):
    pair = await sign_in(poll_interval=0)
    assert pair.auth_token == "private-auth_token"
    browser.chromium.launch.assert_awaited_once_with(headless=False)
    browser.instance.new_context.assert_awaited_once_with(no_viewport=True)
    browser.page.goto.assert_awaited_once_with(
        "https://x.com/i/flow/login", wait_until="domcontentloaded"
    )
    assert browser.context.cookies.await_args.args == ("https://x.com/",)
    browser.instance.close.assert_awaited_once()
    browser.manager.__aexit__.assert_awaited_once()
    assert list(tmp_path.iterdir()) == [browser.executable]


async def test_missing_binary_is_actionable_and_never_launches(browser):
    browser.executable.unlink()
    with pytest.raises(SetupError, match="Install browser"):
        await sign_in()
    browser.chromium.launch.assert_not_awaited()


@pytest.mark.parametrize("stage", ["launch", "context", "goto", "cookies"])
async def test_browser_errors_are_redacted_and_close_open_browser(browser, stage):
    target = {
        "launch": browser.chromium.launch,
        "context": browser.instance.new_context,
        "goto": browser.page.goto,
        "cookies": browser.context.cookies,
    }[stage]
    target.side_effect = Error("private-auth_token private-ct0 provider body")
    with pytest.raises(SetupError, match="local desktop") as error:
        await sign_in()
    assert "private-" not in str(error.value)
    if stage != "launch":
        browser.instance.close.assert_awaited_once()


async def test_closed_window_stops_login_without_cookies(browser):
    browser.context.pages = []
    with pytest.raises(SetupError, match="Browser closed"):
        await sign_in()
    browser.instance.close.assert_awaited_once()


async def test_login_timeout_closes_browser_without_capture(browser):
    browser.context.cookies.side_effect = None
    browser.context.cookies.return_value = []
    with pytest.raises(SetupError, match="timed out"):
        await sign_in(max_wait_seconds=0.02)
    browser.instance.close.assert_awaited_once()


async def test_cancelling_login_closes_browser_and_driver(browser):
    entered = asyncio.Event()

    async def waiting(*args):
        entered.set()
        await asyncio.Event().wait()

    browser.context.cookies.side_effect = waiting
    task = asyncio.create_task(sign_in())
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    browser.instance.close.assert_awaited_once()
    browser.manager.__aexit__.assert_awaited_once()


@pytest.fixture
def installer(monkeypatch):
    process = SimpleNamespace(returncode=0, pid=99999, wait=AsyncMock(return_value=0), kill=Mock())
    spawn = AsyncMock(return_value=process)
    killpg = Mock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(os, "killpg", killpg)
    return SimpleNamespace(process=process, spawn=spawn, killpg=killpg)


async def test_explicit_installer_downloads_only_chromium_without_shell_or_raw_logs(installer):
    await install_browser()
    assert installer.spawn.await_args.args[1:] == (
        "-m",
        "playwright",
        "install",
        "--no-shell",
        "chromium",
    )
    kwargs = installer.spawn.await_args.kwargs
    assert kwargs["stdout"] == kwargs["stderr"] == asyncio.subprocess.DEVNULL
    assert kwargs["start_new_session"] == (os.name == "posix")
    installer.killpg.assert_not_called()


async def test_failed_install_is_actionable(installer):
    installer.process.wait.return_value = 1
    installer.process.returncode = 1
    with pytest.raises(SetupError, match="installation failed"):
        await install_browser()


@pytest.mark.parametrize("cancel", [False, True])
async def test_timeout_and_cancel_stop_installer_process_group(installer, cancel):
    entered = asyncio.Event()
    installer.process.returncode = None

    async def waiting():
        if entered.is_set():
            installer.process.returncode = -9
            return -9
        entered.set()
        await asyncio.Event().wait()

    installer.process.wait.side_effect = waiting
    task = asyncio.create_task(install_browser(max_wait_seconds=10 if cancel else 0.02))
    await asyncio.wait_for(entered.wait(), 1)
    if cancel:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        with pytest.raises(SetupError, match="timed out"):
            await task
    if os.name == "posix":
        installer.killpg.assert_called_once_with(99999, signal.SIGKILL)
    else:
        installer.process.kill.assert_called_once()
    assert installer.process.wait.await_count == 2


async def test_windows_installer_cancellation_kills_downloader_tree(installer, monkeypatch):
    monkeypatch.setattr(browser_signin, "_POSIX", False)
    entered = asyncio.Event()
    installer.process.returncode = None

    async def waiting():
        if entered.is_set():
            return -9
        entered.set()
        await asyncio.Event().wait()

    installer.process.wait.side_effect = waiting
    killer = SimpleNamespace(wait=AsyncMock(return_value=0))
    installer.spawn.side_effect = [installer.process, killer]
    task = asyncio.create_task(install_browser())
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert installer.spawn.await_args.args == ("taskkill", "/PID", "99999", "/T", "/F")
    killer.wait.assert_awaited_once()
    installer.process.kill.assert_called_once()
    installer.killpg.assert_not_called()


@pytest.fixture
def news_setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in ("TELEGRAM_BOT_TOKEN", "X_AUTH_TOKEN", "X_CT0"):
        monkeypatch.delenv("TRADEBOT_" + key)
    save_token("123:fixture")
    controller = SetupController()
    owner = {"chat_id": "42", "bot_fingerprint": hashlib.sha256(b"123:fixture").hexdigest()}
    controller.memory.set_setting("telegram_owner", owner)
    controller.memory.set_setting("onboarding", {"version": 3, "steps": {"telegram": owner}})
    controller.save_schedule(3)
    controller.complete_access("model_access", deferred=True)
    yield controller
    controller.close()


@pytest.mark.parametrize("size", [(80, 24), (120, 36)])
async def test_browser_onboarding_stages_masked_pair_until_explicit_save_and_authors(
    news_setup, monkeypatch, size
):
    capture = AsyncMock(return_value=XCookies("private-auth_token", "private-ct0"))
    monkeypatch.setattr("tradebot.setup_terminal.sign_in", capture)
    app = SetupTerminal(news_setup)
    async with app.run_test(size=size) as pilot:
        assert app.query_one("#news-form").display
        app.query_one("#x-signin").scroll_visible(immediate=True)
        await pilot.pause()
        await pilot.click("#x-signin")
        await pilot.pause()
        capture.assert_awaited_once()
        assert "not saved yet" in str(app.query_one("#browser-status", Static).content)
        assert "private-" not in app.export_screenshot()
        assert news_setup.credentials.x_auth_token.get_secret_value() == ""
        app.save_access("news_access")
        assert "approved" in str(app.query_one("#status", Static).content).lower()
        assert "news_access" in news_setup.pending_steps()
        app.query_one("#x-authors", Input).value = "42:approved"
        app.save_access("news_access")
        assert app.query_one("#home").display and news_setup.pending_steps() == []
        assert app.query_one("#x-cookies", Input).value == ""
    loaded = Credentials()
    assert loaded.x_auth_token.get_secret_value() == "private-auth_token"
    assert loaded.x_ct0.get_secret_value() == "private-ct0"
    saved_stat = await asyncio.to_thread(Path(".tradebot/credentials.env").stat)
    assert stat.S_IMODE(saved_stat.st_mode) == 0o600
    reopened = SetupController()
    try:
        assert reopened.pending_steps() == []
        assert reopened.policy().approved_x_authors == {"42": "approved"}
    finally:
        reopened.close()


@pytest.mark.parametrize("exit_app", [False, True])
async def test_ui_can_cancel_or_exit_during_login_and_preserves_existing_access(
    news_setup, monkeypatch, exit_app
):
    news_setup.save_news_access("auth_token=old-auth_token; ct0=old-ct0-cookie", "42:approved", {})
    private = await asyncio.to_thread(Path(".tradebot/credentials.env").read_bytes)
    entered, cleaned = asyncio.Event(), asyncio.Event()

    async def waiting():
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    monkeypatch.setattr("tradebot.setup_terminal.sign_in", waiting)
    app = SetupTerminal(news_setup)
    async with app.run_test(size=(80, 24)) as pilot:
        app.show_access("news_access")
        app.query_one("#x-signin").scroll_visible(immediate=True)
        await pilot.pause()
        await pilot.click("#x-signin")
        await asyncio.wait_for(entered.wait(), 1)
        assert not app.query_one("#cancel-browser", Button).disabled
        assert app.query_one("#save-news", Button).disabled
        assert "private-" not in repr(app.browser_worker)
        if exit_app:
            app.exit()
        else:
            await pilot.click("#cancel-browser")
            await pilot.pause()
            assert not app.busy and app.query_one("#cancel-browser", Button).disabled
            assert "cancelled" in str(app.query_one("#browser-status", Static).content)
    assert cleaned.is_set()
    assert await asyncio.to_thread(Path(".tradebot/credentials.env").read_bytes) == private


@pytest.mark.parametrize(
    "failure", [None, SetupError("Choose Install browser first."), OSError("private-auth_token")]
)
async def test_ui_install_and_failure_are_retryable_without_secret_output(
    news_setup, monkeypatch, failure
):
    installer = AsyncMock(side_effect=failure)
    monkeypatch.setattr("tradebot.setup_terminal.install_browser", installer)
    app = SetupTerminal(news_setup)
    async with app.run_test(size=(80, 24)) as pilot:
        app.query_one("#install-browser").scroll_visible(immediate=True)
        await pilot.pause()
        await pilot.click("#install-browser")
        await pilot.pause()
        installer.assert_awaited_once()
        assert not app.busy
        assert app.query_one("#cancel-browser", Button).disabled
        message = str(app.query_one("#browser-status", Static).content)
        assert "private-" not in message
        assert "installed" in message if failure is None else "browser" in message.lower()
        assert news_setup.credentials.x_auth_token.get_secret_value() == ""


@pytest.mark.browser
@pytest.mark.skipif(
    os.environ.get("TRADEBOT_TEST_BROWSER") != "1",
    reason="Opt-in real Chromium fixture test; requires installed browser and desktop/Xvfb",
)
async def test_real_chromium_capture_uses_offline_login_fixture_and_closes(monkeypatch):
    """Exercise real headed Chromium APIs; no request reaches X or a real account."""
    from playwright.async_api import async_playwright

    manager = async_playwright()
    opened = []

    class FixtureBrowser:
        async def __aenter__(self):
            playwright = await manager.__aenter__()
            original_launch = playwright.chromium.launch

            async def launch(**kwargs):
                instance = await original_launch(**kwargs)
                opened.append(instance)
                original_context = instance.new_context

                async def new_context(**options):
                    context = await original_context(**options)

                    async def offline_login(route):
                        assert route.request.url.startswith("https://x.com/")
                        await context.add_cookies(PAIR)
                        await route.fulfill(status=200, body="<html>Offline login fixture</html>")

                    await context.route("**/*", offline_login)
                    return context

                instance.new_context = new_context
                return instance

            return SimpleNamespace(
                chromium=SimpleNamespace(
                    executable_path=playwright.chromium.executable_path, launch=launch
                )
            )

        async def __aexit__(self, *args):
            await manager.__aexit__(*args)

    monkeypatch.setattr(browser_signin, "async_playwright", FixtureBrowser)
    captured = await sign_in(max_wait_seconds=30, poll_interval=0)
    assert captured == XCookies("private-auth_token", "private-ct0")
    assert len(opened) == 1 and not opened[0].is_connected()
