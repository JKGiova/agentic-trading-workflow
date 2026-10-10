"""First-run Telegram onboarding and connection home in one terminal window."""

import asyncio
from contextlib import suppress

from sqlalchemy.exc import SQLAlchemyError
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Collapsible, Footer, Input, Label, Static
from textual.worker import WorkerCancelled, WorkerFailed

from tradebot.browser_signin import install_browser, sign_in
from tradebot.onboarding import SetupError, test_status


class SecretInput(Input):
    def post_message(self, message: Message) -> bool:
        # Password rendering alone does not hide Input values in message/debug representations.
        if isinstance(message, (Input.Changed, Input.Submitted)):
            message.value = "<hidden>"
        return super().post_message(message)


class SetupTerminal(App):
    TITLE = "Agentic Trading Workflow"
    BINDINGS = [("ctrl+q", "quit", "Exit")]
    CSS = """
    Screen { align: center middle; }
    #setup { width: 76; max-width: 100%; height: auto; max-height: 100%;
             border: round $primary; padding: 1 2; }
    #heading { text-style: bold; color: $accent; margin-bottom: 1; }
    #intro, #status, #browser-status { height: auto; margin-bottom: 1; }
    #token-form { height: auto; }
    Label { margin-bottom: 0; }
    Input { margin-bottom: 1; }
    Horizontal { height: auto; }
    Button { margin-right: 1; }
    #home { height: auto; }
    #schedule-form { height: auto; }
    #model-form, #news-form { height: auto; }
    #schedule-intro, #schedule-summary { height: auto; margin-bottom: 1; }
    #connection { height: auto; margin-bottom: 1; }
    """

    def __init__(self, controller, force=False):
        super().__init__()
        self.controller, self.force = controller, force
        self.busy = False
        self.browser_worker = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="setup"):
            yield Static("Welcome to Agentic Trading Workflow", id="heading", markup=False)
            yield Static(
                "Connect your Telegram bot to receive updates. Create a bot with @BotFather, "
                "then paste its token below. We will pair your private chat and send one test.",
                id="intro",
                markup=False,
            )
            with Vertical(id="token-form"):
                yield Label("Telegram bot token")
                yield SecretInput(
                    placeholder="Paste your BotFather token", password=True, id="token"
                )
                yield Button("Connect and send test", variant="primary", id="connect")
            with Vertical(id="home"):
                yield Static("", id="connection", markup=False)
                with Horizontal():
                    yield Button("Send test message", variant="primary", id="test")
                    yield Button("Change bot", id="change")
                    yield Button("Report interval", id="schedule")
                with Horizontal():
                    yield Button("Model credentials", id="model")
                    yield Button("News credentials", id="news")
                yield Static("", id="schedule-summary", markup=False)
            with Vertical(id="schedule-form"):
                yield Static(
                    "Choose how many hours the analysts work before sending a Telegram report. "
                    "Decimals work too: 0.5 means every 30 minutes. "
                    "Changes apply after any current cycle finishes.",
                    id="schedule-intro",
                    markup=False,
                )
                yield Label("Hours between reports")
                yield Input(value="3", type="number", id="report-hours")
                yield Button("Save report interval", variant="primary", id="save-schedule")
            with Vertical(id="model-form"):
                yield Static(
                    "Configure your model provider. NVIDIA NIM is the default. "
                    "Keys are stored locally; saving does not call or charge the model.",
                    markup=False,
                )
                for name, label in (
                    ("nvidia_api_key", "NVIDIA NIM API key"),
                    ("openrouter_api_key", "OpenRouter API key (alternative)"),
                ):
                    yield Label(label)
                    yield SecretInput(
                        password=True, id=name, placeholder="Blank keeps the saved key"
                    )
                with Horizontal():
                    yield Button("Save model keys", variant="primary", id="save-model")
                    yield Button("Configure later", id="skip-model")
            with Vertical(id="news-form"):
                yield Static(
                    "Agent Reach reads public web pages without login. For X, choose Sign in "
                    "to X and log in in the separate browser, or paste exported cookies. "
                    "X and the providers below are optional. "
                    "Saved credentials are not live-verified.",
                    markup=False,
                )
                with Horizontal():
                    yield Button("Save news access", variant="primary", id="save-news")
                    yield Button("Configure later", id="skip-news")
                with Horizontal():
                    yield Button("Sign in to X", variant="primary", id="x-signin")
                    yield Button("Install browser", id="install-browser")
                    yield Button("Cancel", id="cancel-browser", disabled=True)
                yield Static("", id="browser-status", markup=False)
                yield Label("X cookies · auth_token and ct0")
                yield SecretInput(password=True, id="x-cookies", placeholder="auth_token=…; ct0=…")
                yield Label("Approved X accounts · numeric_id:handle, numeric_id:handle")
                yield Input(id="x-authors", placeholder="123456:company")
                yield Label("Web reading · allowed article hostnames, separated by commas")
                yield Input(id="article-domains", placeholder="www.nvidia.com, www.sec.gov")
                yield Label("SEC identity · organization and contact email (optional)")
                yield Input(id="sec_user_agent", placeholder="YourCompany contact@example.com")
                with Collapsible(title="Optional Alpaca and legacy provider credentials"):
                    for name, label in (
                        ("alpaca_api_key", "Alpaca API key (read-only account access)"),
                        ("alpaca_secret_key", "Alpaca secret key"),
                        ("x_bearer_token", "Official X API token (explicit alternative)"),
                        ("tavily_api_key", "Tavily API key (older bounded sessions)"),
                    ):
                        yield Label(label)
                        yield SecretInput(
                            password=True, id=name, placeholder="Blank keeps the saved key"
                        )
            yield Static("", id="status", markup=False)
            yield Button("Exit", id="exit")
        yield Footer()

    def on_mount(self):
        if not self.force and self.controller.connection():
            self.show_home()
        else:
            self.show_form()

    def status(self, text):
        self.query_one("#status", Static).update(text)

    def show_form(self):
        self.query_one("#heading", Static).update("Welcome · Connect Telegram")
        self.query_one("#intro").display = True
        self.query_one("#token-form").display = True
        self.query_one("#home").display = False
        self.query_one("#schedule-form").display = False
        self.query_one("#model-form").display = False
        self.query_one("#news-form").display = False
        token = self.controller.credentials.telegram_bot_token.get_secret_value()
        self.query_one("#token", Input).value = token
        self.query_one("#token", Input).focus()
        self.status("Your token is hidden and saved privately on this computer.")

    def show_home(self):
        self.query_one("#browser-status", Static).update("")
        pending = self.controller.pending_steps()
        if "report_schedule" in pending and "telegram" not in pending:
            self.show_schedule()
            return
        for step in ("model_access", "news_access"):
            if step in pending and "telegram" not in pending:
                self.show_access(step)
                return
        self.query_one("#heading", Static).update("Connections")
        self.query_one("#intro").display = False
        self.query_one("#token-form").display = False
        self.query_one("#home").display = True
        self.query_one("#schedule-form").display = False
        self.query_one("#model-form").display = False
        self.query_one("#news-form").display = False
        for field in self.query(SecretInput):
            field.value = ""
        username = (self.controller.memory.setting("telegram_bot") or {}).get("username", "")
        self.query_one("#connection", Static).update(
            f"@{username} · private chat paired" if username else "Your private chat is paired."
        )
        schedule = self.controller.schedule()
        self.query_one("#schedule-summary", Static).update(
            f"Reports every {schedule.report_hours:g} hours while analysis is running."
            if schedule
            else "Choose a report interval after confirming your Telegram test."
        )
        if not pending:
            self.status(
                "Setup saved. Configure your watchlist, then check "
                "tradingworkflow --supervisor --doctor. "
                "Deferred credentials must be added before enabling their capabilities."
            )
        else:
            result = self.controller.last_test()
            self.status(
                test_status(result) if result else "Send a test message to finish Telegram setup."
            )
        self.query_one("#test", Button).focus()

    def show_schedule(self):
        self.query_one("#heading", Static).update("Reports · Choose interval")
        for widget_id in ("intro", "token-form", "home", "model-form", "news-form"):
            self.query_one("#" + widget_id).display = False
        self.query_one("#token", Input).value = ""
        self.query_one("#schedule-form").display = True
        schedule = self.controller.schedule()
        self.query_one("#report-hours", Input).value = (
            f"{schedule.report_hours:g}" if schedule else "3"
        )
        self.status("Save the interval to continue setup. Starting analysis is a separate command.")
        self.query_one("#report-hours", Input).focus()

    def set_busy(self, busy):
        self.busy = busy
        if not self.is_running:
            return
        for widget in self.query("Input, Button"):
            if widget.id != "exit":
                widget.disabled = busy
        self.query_one("#cancel-browser", Button).disabled = not (
            busy and self.browser_worker is not None
        )

    def show_access(self, step):
        self.query_one("#browser-status", Static).update("")
        form = "model-form" if step == "model_access" else "news-form"
        self.query_one("#heading", Static).update(
            "Model access" if step == "model_access" else "News access"
        )
        for widget_id in (
            "intro",
            "token-form",
            "home",
            "schedule-form",
            "model-form",
            "news-form",
        ):
            self.query_one("#" + widget_id).display = widget_id == form
        for field in self.query(SecretInput):
            field.value = ""
        if step == "news_access":
            try:
                policy = self.controller.policy()
            except ValueError, OSError:
                self.status(
                    "Cannot load the source policy. Repair your config file "
                    "or choose Configure later."
                )
                self.query_one("#x-cookies", Input).focus()
                return
            self.query_one("#x-authors", Input).value = ", ".join(
                f"{key}:{value}" for key, value in policy.approved_x_authors.items()
            )
            self.query_one(
                "#sec_user_agent", Input
            ).value = self.controller.credentials.sec_user_agent
            self.query_one("#article-domains", Input).value = ", ".join(policy.article_domains)
        self.status(
            "Blank fields retain saved access. Configure later skips this step without enabling it."
        )
        self.query_one("#nvidia_api_key" if step == "model_access" else "#x-cookies", Input).focus()

    @on(Button.Pressed, "#model")
    def change_model(self):
        if not self.busy:
            self.show_access("model_access")

    @on(Button.Pressed, "#news")
    def change_news(self):
        if not self.busy:
            self.show_access("news_access")

    @on(Button.Pressed, "#x-signin")
    @on(Button.Pressed, "#install-browser")
    def start_browser(self, event):
        if not self.busy:
            install = event.button.id == "install-browser"
            self.browser_worker = self.browser_login(install)
            self.set_busy(True)

    def browser_status(self, text):
        self.query_one("#browser-status", Static).update(text)
        self.status(text)

    @on(Button.Pressed, "#cancel-browser")
    def cancel_browser(self):
        if self.browser_worker is not None:
            self.browser_worker.cancel()

    @work(group="browser", exclusive=True, exit_on_error=False, description="X browser setup")
    async def browser_login(self, install=False):
        try:
            if install:
                self.browser_status("Downloading Chromium… You can cancel or exit while waiting.")
                await install_browser()
                self.browser_status(
                    "Browser installed. Choose Sign in to X to connect your account."
                )
            else:
                self.browser_status(
                    "Log in to X in the opened browser, including any verification. "
                    "Cookies will be captured automatically. You can cancel or close the browser."
                )
                cookies = await sign_in()
                self.query_one("#x-cookies", Input).value = cookies.header()
                self.browser_status(
                    "X cookies captured; not saved yet. Set approved accounts, then choose "
                    "Save news access. X search access has not been verified."
                )
        except asyncio.CancelledError:
            self.browser_status("Browser setup cancelled. No new cookies were saved.")
            raise
        except SetupError as exc:
            self.browser_status(str(exc))
        except OSError, RuntimeError:
            self.browser_status(
                "Browser setup failed. Check your local browser installation and retry."
            )
        finally:
            self.browser_worker = None
            self.set_busy(False)

    @on(Button.Pressed, "#save-model")
    @on(Input.Submitted, "#nvidia_api_key")
    @on(Input.Submitted, "#openrouter_api_key")
    def save_model(self):
        self.save_access("model_access")

    @on(Button.Pressed, "#save-news")
    @on(Input.Submitted, "#x-cookies")
    @on(Input.Submitted, "#x-authors")
    @on(Input.Submitted, "#article-domains")
    @on(Input.Submitted, "#sec_user_agent")
    @on(Input.Submitted, "#alpaca_api_key")
    @on(Input.Submitted, "#alpaca_secret_key")
    @on(Input.Submitted, "#x_bearer_token")
    @on(Input.Submitted, "#tavily_api_key")
    def save_news(self):
        self.save_access("news_access")

    def save_access(self, step):
        if self.busy:
            return
        try:
            if step == "model_access":
                self.controller.save_access(
                    step,
                    {
                        name: self.query_one("#" + name, Input).value
                        for name in ("nvidia_api_key", "openrouter_api_key")
                    },
                )
            else:
                self.controller.save_news_access(
                    self.query_one("#x-cookies", Input).value,
                    self.query_one("#x-authors", Input).value,
                    {
                        name: self.query_one("#" + name, Input).value
                        for name in (
                            "sec_user_agent",
                            "alpaca_api_key",
                            "alpaca_secret_key",
                            "x_bearer_token",
                            "tavily_api_key",
                        )
                    },
                    self.query_one("#article-domains", Input).value,
                )
            self.show_home()
        except SetupError as exc:
            self.status(str(exc))
        except ValueError, OSError, SQLAlchemyError:
            self.status(
                "Could not save access. Check your configuration and local storage, then retry."
            )

    @on(Button.Pressed, "#skip-model")
    @on(Button.Pressed, "#skip-news")
    def defer_access(self, event):
        if not self.busy:
            try:
                self.controller.complete_access(
                    "model_access" if event.button.id == "skip-model" else "news_access",
                    deferred=True,
                )
                self.show_home()
            except OSError, SQLAlchemyError:
                self.status("Could not save setup. Check local storage and retry.")

    @on(Button.Pressed, "#connect")
    @on(Input.Submitted, "#token")
    def connect(self):
        if not self.busy:
            self.set_busy(True)
            self.connect_bot()

    @work(group="setup", exclusive=True, exit_on_error=False, description="Connect Telegram")
    async def connect_bot(self):
        try:
            result = await self.controller.connect(
                self.query_one("#token", Input).value, self.status
            )
            self.show_home()
            self.status(
                test_status(result)
                + (
                    " Choose your report interval below."
                    if self.query_one("#schedule-form").display
                    else ""
                )
            )
        except TimeoutError:
            self.status("Pairing timed out. Connect again and send the displayed /start code.")
        except SetupError as exc:
            self.status(str(exc))
        except ValueError, RuntimeError, OSError, KeyError, TypeError:
            self.status("Connection failed. Check your token, network and private /start code.")
        finally:
            self.set_busy(False)
            if self.is_running and self.query_one("#token-form").display:
                self.query_one("#token", Input).focus()

    @on(Button.Pressed, "#test")
    def test(self):
        if not self.busy:
            self.set_busy(True)
            self.send_test()

    @work(group="setup", exclusive=True, exit_on_error=False)
    async def send_test(self):
        self.status("Sending your test message…")
        try:
            result = await self.controller.test()
            if result["status"] == "SENT":
                self.show_home()
            self.status(test_status(result))
        except ValueError, RuntimeError, OSError, KeyError, TypeError:
            self.status("Test failed. Check your connection or reconnect your bot.")
        finally:
            self.set_busy(False)

    @on(Button.Pressed, "#change")
    def change(self):
        if not self.busy:
            self.show_form()

    @on(Button.Pressed, "#schedule")
    def change_schedule(self):
        if not self.busy:
            self.show_schedule()

    @on(Button.Pressed, "#save-schedule")
    @on(Input.Submitted, "#report-hours")
    def save_schedule(self):
        if self.busy:
            return
        try:
            self.controller.save_schedule(self.query_one("#report-hours", Input).value)
            self.show_home()
        except SetupError as exc:
            self.status(str(exc))
        except OSError, SQLAlchemyError:
            self.status("Could not save the interval. Check local storage and try again.")

    @on(Button.Pressed, "#exit")
    def leave(self):
        self.exit()

    async def on_unmount(self):
        self.workers.cancel_all()
        # Await client cleanup before the CLI closes storage.
        with suppress(WorkerCancelled, WorkerFailed):
            await self.workers.wait_for_complete()
