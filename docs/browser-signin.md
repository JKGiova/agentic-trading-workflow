# Browser sign-in for X

[Wiki home](README.md) · [Onboarding](onboarding.md) · [Agent Reach connectors](agentreach-connectors.md)

**Implemented in v0.5.0 on Python 3.14.** News onboarding can open a dedicated local
Chromium window and capture the two cookies needed by the Agent Reach-selected X
backend. You enter credentials and complete any two-factor authentication directly
on X. The app does not collect your password.

## Connect your account

1. Run `tradingworkflow`, finish Telegram/model setup or defer the model, then open
   **News credentials**.
2. On first use, choose **Install browser**. This downloads Playwright's Chromium
   build for your operating system; subsequent launches reuse the binary.
3. Choose **Sign in to X**. Complete login and verification in the separate browser.
   The terminal stays responsive and offers **Cancel** and Exit.
4. Once `auth_token` and `ct0` are available, the browser closes and the masked
   **X cookies** field is populated. Nothing has been saved yet.
5. Enter approved sources as `numeric_id:handle`, separated by commas, then choose
   **Save news access**. Existing approved sources are retained for editing.

Closing the browser, cancelling, timeout or failed login does not change saved
credentials. Login allows ten minutes; the initial page load has Playwright's
normal navigation timeout. A failed save keeps captured cookies masked so you can
correct source configuration and retry. Configure later or leaving the app discards
unsaved cookies. To reconnect after expiry, repeat sign-in/save and restart research.

## Installation and platform requirements

`uv sync --locked` installs the Python dependency, not browser binaries. The
**Install browser** button downloads Chromium without a shell or administrator
commands. You can also install it from the activated environment:

```bash
python -m playwright install --no-shell chromium
```

Browser login requires a local graphical desktop. For Linux hosts missing browser
system libraries, consult Playwright's [browser installation guide](https://playwright.dev/python/docs/browsers).
Its separate `python -m playwright install-deps chromium` command installs OS
dependencies and can require administrator access; onboarding never runs it.
On a headless server, connect on a desktop or use the existing masked cookie-export
option. Cookie-Editor **Header String** exports remain supported.

## Credential boundaries

Sign-in uses a fresh, nonpersistent context with no existing Chrome, Edge, Firefox
or owner profile access. Normal completion/cancellation closes the browser and
driver. Only secure, unexpired, root-path `auth_token` and `ct0` cookies for
`x.com`/`.x.com` are accepted. Conflicting values, other domains, partitioned cookies
and incomplete pairs cannot complete capture. No screenshots, HTML, storage-state
dump, password or unrelated cookies are saved.

The explicit Save action uses existing atomic storage and source validation.
Cookies go to the ignored `.tradebot/credentials.env` file with POSIX 0600 permissions
in a 0700 directory. This is restricted plaintext storage. Cookies are never shown
in status messages or worker descriptions. Environment precedence/conflict checks
still apply.

Capturing a session does not verify X search or account restrictions. Runtime still
records failed/degraded coverage. Agents cannot start browser login; they only
receive approved evidence from the explicit-cookie X adapter. Agent Reach/Jina
reads public articles without these cookies.

## Verification

Offline tests cover scope/expiry/ambiguity, installed Playwright interfaces through
mocked browser fixtures, masked onboarding at 80×24 and 120×36, explicit save and
approved-author requirements, relaunch, errors, cancellation, timeout, private
storage and installer cleanup. GitHub CI additionally installs Chromium and runs
a real headed-browser test under Xvfb using an intercepted offline login page.
That fixture sends no requests to X and uses no real account.

Run the real browser fixture on a desktop after installing Chromium:

```bash
TRADEBOT_TEST_BROWSER=1 uv run pytest tests/test_browser_signin.py -m browser
# Linux CI without a desktop:
TRADEBOT_TEST_BROWSER=1 xvfb-run -a uv run pytest tests/test_browser_signin.py -m browser
```

Real X sign-in/search still requires your account interaction. Implementation uses
Playwright's [isolated contexts and cookies API](https://playwright.dev/python/docs/api/class-browsercontext).
