"""First-run Telegram onboarding and connection home in one terminal window."""

from contextlib import suppress

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Footer, Input, Label, Static
from textual.worker import WorkerCancelled, WorkerFailed

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
    #intro, #status { height: auto; margin-bottom: 1; }
    #token-form { height: auto; }
    Label { margin-bottom: 0; }
    Input { margin-bottom: 1; }
    Horizontal { height: auto; }
    Button { margin-right: 1; }
    #home { height: auto; }
    #connection { height: auto; margin-bottom: 1; }
    """

    def __init__(self, controller, force=False):
        super().__init__()
        self.controller, self.force = controller, force
        self.busy = False

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
        token = self.controller.credentials.telegram_bot_token.get_secret_value()
        self.query_one("#token", Input).value = token
        self.query_one("#token", Input).focus()
        self.status("Your token is hidden and saved privately on this computer.")

    def show_home(self):
        self.query_one("#heading", Static).update("Telegram")
        self.query_one("#intro").display = False
        self.query_one("#token-form").display = False
        self.query_one("#home").display = True
        self.query_one("#token", Input).value = ""
        username = (self.controller.memory.setting("telegram_bot") or {}).get("username", "")
        self.query_one("#connection", Static).update(
            f"@{username} · private chat paired" if username else "Your private chat is paired."
        )
        if not self.controller.pending_steps():
            self.status("Setup complete. Your saved connection will be used on future launches.")
        else:
            result = self.controller.last_test()
            self.status(
                test_status(result) if result else "Send a test message to finish Telegram setup."
            )
        self.query_one("#test", Button).focus()

    def set_busy(self, busy):
        self.busy = busy
        if not self.is_running:
            return
        for widget_id in ("connect", "test", "change", "token"):
            self.query_one("#" + widget_id).disabled = busy

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
            self.status(test_status(result))
        except TimeoutError:
            self.status("Pairing timed out. Connect again and send the displayed /start code.")
        except SetupError as exc:
            self.status(str(exc))
        except (ValueError, RuntimeError, OSError, KeyError, TypeError):
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
            self.status(test_status(result))
        except (ValueError, RuntimeError, OSError, KeyError, TypeError):
            self.status("Test failed. Check your connection or reconnect your bot.")
        finally:
            self.set_busy(False)

    @on(Button.Pressed, "#change")
    def change(self):
        if not self.busy:
            self.show_form()

    @on(Button.Pressed, "#exit")
    def leave(self):
        self.exit()

    async def on_unmount(self):
        self.workers.cancel_all()
        # Await client cleanup before the CLI closes storage.
        with suppress(WorkerCancelled, WorkerFailed):
            await self.workers.wait_for_complete()
