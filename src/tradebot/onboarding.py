"""Versioned local setup, separate from research providers and trading credentials."""

import hashlib
import os
import re
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from pydantic import SecretStr, ValidationError

from tradebot.analysis_memory import AnalysisMemory, outbox
from tradebot.contracts import utcnow
from tradebot.settings import Credentials, ReportSchedule
from tradebot.storage import Store
from tradebot.telegram import TelegramNotifier

SETUP_VERSION = 2
# Add only ready product capabilities here; completed steps survive future additions.
REQUIRED_STEPS = ("telegram", "report_schedule")
TOKEN_NAME = "TRADEBOT_TELEGRAM_BOT_TOKEN"


class SetupError(ValueError):
    """Owner-facing setup guidance that never contains credentials or provider bodies."""


def save_token(token, path=Path(".tradebot/credentials.env")):
    """Atomically replace the app-owned secret file without overwriting the owner's .env."""
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token) or len(token) > 512:
        raise SetupError("Enter the bot token provided by BotFather")
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Private setup files cannot be symbolic links")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    values = dotenv_values(path) if path.exists() else {}
    values[TOKEN_NAME] = token
    lines = []
    for key, value in values.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError("Invalid saved credential name")
        escaped = (value or "").replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"{key}='{escaped}'\n")
    fd, temporary = tempfile.mkstemp(prefix="credentials-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write("".join(lines))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class SetupController:
    def __init__(self, database=None, notifier_factory=TelegramNotifier):
        directory = Path(".tradebot")
        if directory.is_symlink():
            raise ValueError("Private setup directory cannot be a symbolic link")
        directory.mkdir(exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        self.store = Store(database or f"sqlite:///{directory / 'research.db'}")
        self.memory = AnalysisMemory(self.store)
        self.credentials = Credentials()
        self.notifier_factory = notifier_factory

    def close(self):
        self.store.close()

    def connection(self):
        token = self.credentials.telegram_bot_token.get_secret_value()
        identity = hashlib.sha256(token.encode()).hexdigest()
        owner = self.memory.setting("telegram_owner") or {}
        return owner if token and owner.get("bot_fingerprint") == identity else {}

    def pending_steps(self):
        state = self.memory.setting("onboarding") or {"version": SETUP_VERSION, "steps": {}}
        connection = self.connection()
        completed = dict(state.get("steps", {}))
        if completed.get("telegram") != connection or not connection:
            completed.pop("telegram", None)
        schedule = self.schedule()
        if not schedule or completed.get("report_schedule") != schedule.model_dump(mode="json"):
            completed.pop("report_schedule", None)
        return [step for step in REQUIRED_STEPS if step not in completed]

    def schedule(self):
        return ReportSchedule.read(self.memory)

    def save_schedule(self, hours):
        try:
            schedule = ReportSchedule(report_hours=hours)
        except ValidationError:
            raise SetupError(
                "Enter an interval between 1 second and 8760 hours, for example 3 or 0.5 hours"
            ) from None
        payload = schedule.model_dump(mode="json")
        state = self.memory.setting("onboarding") or {"steps": {}}
        self.memory.set_settings(
            {
                "report_schedule": payload,
                "onboarding": {
                    **state,
                    "version": SETUP_VERSION,
                    "steps": {**state.get("steps", {}), "report_schedule": payload},
                    "updated_at": utcnow().isoformat(),
                },
            }
        )
        return schedule

    def last_test(self):
        last = self.memory.setting("telegram_test")
        rows = self.memory.rows(outbox, outbox.c.id == last["id"]) if last else []
        return rows[0] if rows else None

    async def connect(self, token, progress=print):
        token = token.strip() or self.credentials.telegram_bot_token.get_secret_value()
        if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token) or len(token) > 512:
            raise SetupError("Enter the bot token provided by BotFather")
        exported = os.environ.get(TOKEN_NAME, "")
        if exported and exported != token:
            raise SetupError(
                "Update the Telegram token in your environment before changing it here"
            )
        credentials = self.credentials.model_copy(
            update={"telegram_bot_token": SecretStr(token), "telegram_chat_id": ""}
        )
        notifier = self.notifier_factory(credentials, self.memory)
        try:
            bot = await notifier.call("getMe", {})
            username = bot.get("username", "")
            if not re.fullmatch(r"[A-Za-z0-9_]+", username) or not bot.get("is_bot"):
                raise RuntimeError("Telegram could not verify this bot. Check the token and retry")
            if not notifier.chat_id:
                await notifier.pair(progress)
            # Save only after the API accepts the token and the owner authorizes the chat.
            save_token(token)
            self.credentials = credentials
            self.memory.set_setting("telegram_bot", {"username": username})
            progress("Chat paired. Sending your test message…")
            return self._complete(await notifier.send_test())
        finally:
            await notifier.close()

    async def test(self):
        if not self.connection():
            raise ValueError("Connect your Telegram bot first")
        notifier = self.notifier_factory(self.credentials, self.memory)
        try:
            return self._complete(await notifier.send_test())
        finally:
            await notifier.close()

    def _complete(self, result):
        if result["status"] == "SENT":
            state = self.memory.setting("onboarding") or {"version": SETUP_VERSION, "steps": {}}
            state = {
                **state,
                "version": SETUP_VERSION,
                "steps": {**state.get("steps", {}), "telegram": self.connection()},
                "completed_at": utcnow().isoformat(),
            }
            self.memory.set_setting("onboarding", state)
        return result


def test_status(result):
    if result["status"] == "SENT":
        return "Test message delivered. Check your Telegram chat."
    if result["status"] == "PENDING":
        return "Telegram is rate limiting requests. Wait a moment, then press Send test message."
    return "Delivery could not be confirmed. Check Telegram before sending another test."
