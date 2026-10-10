"""Owner-initiated X login in an isolated, disposable local browser."""

import asyncio
import math
import os
import re
import signal
import sys
import time
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Error, async_playwright

from tradebot.onboarding import SetupError

_POSIX = os.name == "posix"


@dataclass(frozen=True)
class XCookies:
    auth_token: str = field(repr=False)
    ct0: str = field(repr=False)

    def header(self) -> str:
        return f"auth_token={self.auth_token}; ct0={self.ct0}"


def extract_cookies(cookies: list[dict], *, now: float | None = None) -> XCookies | None:
    """Accept only a current, unambiguous root-path pair for HTTPS x.com."""
    now = time.time() if now is None else now
    values: dict[str, set[str]] = {}
    for cookie in cookies:
        name = cookie.get("name")
        if (
            name not in {"auth_token", "ct0"}
            or cookie.get("domain") not in {"x.com", ".x.com"}
            or cookie.get("path") != "/"
            or cookie.get("secure") is not True
            or cookie.get("partitionKey")
        ):
            continue
        expires = cookie.get("expires", 0)
        value = cookie.get("value", "")
        if (
            not isinstance(expires, (float, int))
            or not math.isfinite(expires)
            or not (expires == -1 or expires > now)
            or not isinstance(value, str)
            or not re.fullmatch(r"[A-Za-z0-9_./+=:-]{8,1024}", value)
        ):
            continue
        values.setdefault(name, set()).add(value)
    if set(values) != {"auth_token", "ct0"} or any(len(v) != 1 for v in values.values()):
        return None
    return XCookies(next(iter(values["auth_token"])), next(iter(values["ct0"])))


async def install_browser(*, max_wait_seconds: float = 180) -> None:
    """Download Chromium only after the owner presses Install browser; never sudo."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "playwright",
        "install",
        "--no-shell",
        "chromium",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=_POSIX,
    )
    try:
        async with asyncio.timeout(max_wait_seconds):
            if await process.wait() != 0:
                raise SetupError(
                    "Browser installation failed. Check your network and retry, or run "
                    "python -m playwright install --no-shell chromium."
                )
    except TimeoutError:
        raise SetupError("Browser installation timed out. Check your network and retry.") from None
    finally:
        if process.returncode is None:
            if _POSIX:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
            else:
                # Kill the downloader's Node children too on Windows.
                with suppress(OSError):
                    killer = await asyncio.create_subprocess_exec(
                        "taskkill",
                        "/PID",
                        str(process.pid),
                        "/T",
                        "/F",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await killer.wait()
                with suppress(ProcessLookupError):
                    process.kill()
            await process.wait()


async def sign_in(*, max_wait_seconds: float = 600, poll_interval: float = 1) -> XCookies:
    """The owner types credentials/2FA; no page content or browser profile is retained."""
    browser = None
    try:
        async with asyncio.timeout(max_wait_seconds), async_playwright() as playwright:
            if not await asyncio.to_thread(Path(playwright.chromium.executable_path).is_file):
                raise SetupError("Choose Install browser first, then Sign in to X.")
            browser = await playwright.chromium.launch(headless=False)
            try:
                context = await browser.new_context(no_viewport=True)
                page = await context.new_page()
                await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
                while browser.is_connected() and context.pages:
                    pair = extract_cookies(await context.cookies("https://x.com/"))
                    if pair:
                        return pair
                    await asyncio.sleep(poll_interval)
                raise SetupError("Browser closed. No cookies were saved. Sign in again to retry.")
            finally:
                with suppress(Error):
                    await browser.close()
    except TimeoutError:
        raise SetupError("X sign-in timed out. No cookies were saved. Try again.") from None
    except Error:
        raise SetupError(
            "Could not complete browser sign-in. Use a local desktop, check Chromium's "
            "system dependencies and network, or paste exported cookies instead."
        ) from None
