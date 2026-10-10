"""Versioned Telegram and provider setup; no research runs during onboarding."""

import hashlib
import os
import re
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from pydantic import SecretStr, ValidationError

from tradebot.analysis_memory import AnalysisMemory, cycles, outbox
from tradebot.contracts import utcnow
from tradebot.settings import Credentials, Policy, ReportSchedule
from tradebot.storage import Store
from tradebot.telegram import TelegramNotifier

SETUP_VERSION = 3
# Add only ready product capabilities here; completed steps survive future additions.
REQUIRED_STEPS = ("telegram", "report_schedule", "model_access", "news_access")
TOKEN_NAME = "TRADEBOT_TELEGRAM_BOT_TOKEN"


class SetupError(ValueError):
    """Owner-facing setup guidance that never contains credentials or provider bodies."""


def save_token(token, path=Path(".tradebot/credentials.env")):
    """Atomically replace the app-owned secret file without overwriting the owner's .env."""
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token) or len(token) > 512:
        raise SetupError("Enter the bot token provided by BotFather")
    save_credentials({TOKEN_NAME: token}, path)


def save_credentials(updates, path=Path(".tradebot/credentials.env")):
    """Keep unrelated secrets and owner .env; replace only explicitly supplied entries."""
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Private setup files cannot be symbolic links")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    values = dotenv_values(path, interpolate=False) if path.exists() else {}
    values.update(updates)
    lines = []
    for key, value in values.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError("Invalid saved credential name")
        if any(c in (value or "") for c in "\r\n\x00"):
            raise SetupError("Credentials must contain a single line")
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
    def __init__(
        self, database=None, notifier_factory=TelegramNotifier, config=Path("config.local.json")
    ):
        directory = Path(".tradebot")
        if directory.is_symlink():
            raise ValueError("Private setup directory cannot be a symbolic link")
        directory.mkdir(exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        self.store = Store(database or f"sqlite:///{directory / 'research.db'}")
        self.memory = AnalysisMemory(self.store)
        self.credentials = Credentials()
        self.notifier_factory = notifier_factory
        self.config = Path(config)

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
        for step in ("model_access", "news_access"):
            saved = completed.get(step)
            if saved and not saved.get("deferred"):
                try:
                    current = self.access_status(step)
                except ValueError, OSError:
                    current = None
                if saved != current:
                    completed.pop(step, None)
        return [step for step in REQUIRED_STEPS if step not in completed]

    def access_status(self, step):
        names = (
            ("nvidia_api_key", "openrouter_api_key")
            if step == "model_access"
            else (
                "x_auth_token",
                "x_ct0",
                "sec_user_agent",
                "alpaca_api_key",
                "alpaca_secret_key",
                "x_bearer_token",
                "tavily_api_key",
            )
        )
        values = {}
        for name in names:
            value = getattr(self.credentials, name)
            value = value.get_secret_value() if hasattr(value, "get_secret_value") else value
            values[name] = hashlib.sha256(value.encode()).hexdigest() if value else ""
        payload = {"fingerprints": values, "network_verified": False}
        if step == "news_access":
            payload["authors"] = self.policy().approved_x_authors
            payload["article_domains"] = self.policy().article_domains
        return payload

    def complete_access(self, step, deferred=False):
        state = self.memory.setting("onboarding") or {"steps": {}}
        payload = {"deferred": True} if deferred else self.access_status(step)
        self.memory.set_setting(
            "onboarding",
            {
                **state,
                "version": SETUP_VERSION,
                "steps": {**state.get("steps", {}), step: payload},
                "updated_at": utcnow().isoformat(),
            },
        )

    def save_access(self, step, values, complete=True):
        allowed = (
            {"nvidia_api_key", "openrouter_api_key"}
            if step == "model_access"
            else {
                "x_auth_token",
                "x_ct0",
                "sec_user_agent",
                "alpaca_api_key",
                "alpaca_secret_key",
                "x_bearer_token",
                "tavily_api_key",
            }
        )
        if step not in {"model_access", "news_access"} or not set(values) <= allowed:
            raise SetupError("Unknown credential field")
        updates = {}
        for name, value in values.items():
            value = value.strip()
            if not value:  # Blank inputs retain saved/environment values.
                continue
            if name == "sec_user_agent":
                valid = len(value) <= 200 and re.fullmatch(r"[^\r\n\x00$]+@[^\s@]+\.[^\s@]+", value)
            else:
                valid = re.fullmatch(r"[A-Za-z0-9_./+=:-]{8,1024}", value)
            if not valid:
                raise SetupError(
                    "Enter valid single-line credentials; SEC identity needs a contact email"
                )
            env_name = "TRADEBOT_" + name.upper()
            exported = os.environ.get(env_name, "")
            if env_name in os.environ and exported != value:
                raise SetupError(
                    "Update the conflicting exported environment variable before saving"
                )
            updates[env_name] = value
        merged = {
            name: getattr(self.credentials, name).get_secret_value()
            for name in allowed
            if name != "sec_user_agent"
        }
        merged.update(
            {name.removeprefix("TRADEBOT_").lower(): value for name, value in updates.items()}
        )
        if step == "model_access" and not merged[f"{self.policy().model_provider}_api_key"]:
            raise SetupError(
                "Enter the API key for the configured model provider, or choose Configure later"
            )
        if step == "news_access":
            for pair in (("x_auth_token", "x_ct0"), ("alpaca_api_key", "alpaca_secret_key")):
                if bool(merged[pair[0]]) != bool(merged[pair[1]]):
                    raise SetupError(
                        "Provide both X cookies and both Alpaca keys, or leave each pair empty"
                    )
        save_credentials(updates)
        self.credentials = Credentials()
        if complete:
            self.complete_access(step)

    def policy(self):
        return Policy.read(self.config) if self.config.exists() else Policy()

    def parse_authors(self, value, domains=None):
        authors = {}
        for entry in filter(None, re.split(r"[,\n]+", value.strip())):
            pieces = entry.strip().split(":")
            if len(pieces) != 2 or pieces[0].strip() in authors:
                raise SetupError("Use unique numeric_id:handle entries separated by commas")
            authors[pieces[0].strip()] = pieces[1].strip().lstrip("@")
        policy = self.policy()
        updates = {"approved_x_authors": authors}
        if domains is not None:
            registered = [entry.strip().lower() for entry in domains.split(",") if entry.strip()]
            if any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", entry)
                for entry in registered
            ):
                raise SetupError(
                    "Enter exact public hostnames separated by commas, without URLs or paths"
                )
            updates["article_domains"] = list(dict.fromkeys(registered))
        try:
            changed = Policy.model_validate({**policy.model_dump(), **updates})
        except ValidationError:
            raise SetupError(
                "X authors need numeric IDs and handles, for example 123456:company"
            ) from None
        return changed

    def save_authors(self, value, domains=None):
        policy = self.parse_authors(value, domains)
        if self.config.is_symlink() or self.config.parent.is_symlink():
            raise SetupError("Configuration cannot be a symbolic link")
        previous = self.policy()
        open_rows = self.memory.rows(cycles, cycles.c.status == "OPEN")
        transition = None
        if open_rows and (
            policy.approved_x_authors != previous.approved_x_authors
            or policy.article_domains != previous.article_domains
        ):
            saved = self.memory.setting("news_policy_transition") or {}
            original = saved.get("previous") if saved.get("cycle") == open_rows[0]["id"] else None
            transition = {
                "cycle": open_rows[0]["id"],
                "ready": False,
                "previous": original
                or {
                    "approved_x_authors": previous.approved_x_authors,
                    "article_domains": previous.article_domains,
                },
                "next": {
                    "approved_x_authors": policy.approved_x_authors,
                    "article_domains": policy.article_domains,
                },
            }
            # Write-ahead metadata preserves the active cycle's policy if the file
            # replacement succeeds but the following database update is interrupted.
            self.memory.set_setting("news_policy_transition", transition)
        self.config.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="policy-", dir=self.config.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(policy.model_dump_json(indent=2) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.config)
        finally:
            Path(temporary).unlink(missing_ok=True)
        if transition:
            self.memory.set_setting("news_policy_transition", {**transition, "ready": True})
        return policy

    def save_news_access(self, cookies, authors, values, domains=None):
        # Validate the entire form before storing any credentials.
        policy = self.parse_authors(authors, domains)
        if cookies.strip():
            pairs = {}
            for pair in cookies.split(";"):
                key, separator, value = pair.strip().partition("=")
                if key in {"auth_token", "ct0"}:
                    if not separator or key in pairs or not value:
                        raise SetupError(
                            "Paste a Cookie-Editor Header String containing auth_token and ct0"
                        )
                    pairs[key] = value
            if set(pairs) != {"auth_token", "ct0"}:
                raise SetupError(
                    "Paste a Cookie-Editor Header String containing auth_token and ct0"
                )
            values = {**values, "x_auth_token": pairs["auth_token"], "x_ct0": pairs["ct0"]}
        has_x = values.get("x_auth_token") or self.credentials.x_auth_token.get_secret_value()
        if has_x and not policy.approved_x_authors:
            raise SetupError("Add approved X author IDs and handles before enabling cookie access")
        # Save credentials first; completion is recorded again after the author file succeeds.
        self.save_access("news_access", values, complete=False)
        self.save_authors(authors, domains)
        self.complete_access("news_access")

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
