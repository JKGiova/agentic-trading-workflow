"""Explicit owner pairing and durable Telegram delivery without unsafe resend."""

import asyncio
import hashlib
import secrets
from datetime import timedelta

import httpx

from tradebot.analysis_memory import outbox


def split_message(text, limit=3500):
    """Telegram's length bound is in UTF-16 units; leave room for part labels."""
    parts, current, units = [], [], 0
    for char in text:
        size = len(char.encode("utf-16-le")) // 2
        if units + size > limit:
            parts.append("".join(current))
            current, units = [], 0
        current.append(char)
        units += size
    if current:
        parts.append("".join(current))
    return [f"[{index + 1}/{len(parts)}] {part}" for index, part in enumerate(parts)]


class TelegramNotifier:
    def __init__(self, credentials, memory, client=None):
        self.token = credentials.telegram_bot_token.get_secret_value()
        self.identity = hashlib.sha256(self.token.encode()).hexdigest()
        self.memory = memory
        self.chat_id = credentials.telegram_chat_id
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=False)
        self.owns_client = client is None
        if self.chat_id and not self.chat_id.lstrip("-").isdigit():
            raise ValueError("Telegram chat ID must be numeric")
        stored = memory.setting("telegram_owner")
        if not self.chat_id and stored and stored.get("bot_fingerprint") == self.identity:
            self.chat_id = stored["chat_id"]

    async def close(self):
        if self.owns_client:
            await self.client.aclose()

    async def call(self, method, payload):
        if not self.token:
            raise ValueError("Telegram token missing")
        try:
            response = await self.client.post(
                f"https://api.telegram.org/bot{self.token}/{method}", json=payload
            )
            if response.status_code == 429:
                data = response.json()
                return {
                    "retry_after": min(
                        3600, max(1, int(data.get("parameters", {}).get("retry_after", 60)))
                    )
                }
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise RuntimeError("Telegram rejected the request")
            return data["result"]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            # HTTP exception URLs contain the bot token; never propagate them.
            raise RuntimeError(f"Telegram request failed ({type(exc).__name__})") from None

    async def pair(self, notify=print, pair_seconds=180, nonce=None):
        nonce = nonce or secrets.token_hex(8)
        bot = await self.call("getMe", {})
        notify(f"Open https://t.me/{bot['username']} and send: /start {nonce}")
        offset = 0
        async with asyncio.timeout(pair_seconds):
            while True:
                updates = await self.call(
                    "getUpdates", {"offset": offset, "timeout": 10, "allowed_updates": ["message"]}
                )
                if isinstance(updates, dict):
                    await asyncio.sleep(updates["retry_after"])
                    continue
                for update in updates:
                    offset = max(offset, update["update_id"] + 1)
                    message = update.get("message", {})
                    chat = message.get("chat", {})
                    sender = message.get("from", {})
                    if (
                        message.get("text") == f"/start {nonce}"
                        and chat.get("type") == "private"
                        and sender.get("id") == chat.get("id")
                    ):
                        self.chat_id = str(chat["id"])
                        self.memory.set_setting(
                            "telegram_owner",
                            {"chat_id": self.chat_id, "bot_fingerprint": self.identity},
                        )
                        notify("Telegram owner paired. Cycle summaries are now authorized.")
                        return self.chat_id
                await asyncio.sleep(0.5)

    async def deliver(self, now):
        if not self.token or not self.chat_id:
            return
        pending = sorted(
            self.memory.rows(
                outbox, outbox.c.status == "PENDING", outbox.c.retry_at <= now.isoformat()
            ),
            key=lambda row: row["id"],
        )
        for row in pending:
            # Persist intent before send. A crash/timeout is UNKNOWN; never blindly resend.
            blocked = self.memory.rows(
                outbox, outbox.c.cycle == row["cycle"], outbox.c.status.in_(["UNKNOWN", "FAILED"])
            )
            earlier = self.memory.rows(
                outbox,
                outbox.c.cycle == row["cycle"],
                outbox.c.id < row["id"],
                outbox.c.status != "SENT",
            )
            if blocked or earlier or not self.memory.claim_delivery(row, now):
                continue
            try:
                result = await self.call(
                    "sendMessage",
                    {
                        "chat_id": self.chat_id,
                        "text": row["payload"]["text"],
                        "link_preview_options": {"is_disabled": True},
                    },
                )
                if "retry_after" in result:
                    attempts = row["payload"].get("attempts", 0) + 1
                    self.memory.delivery_result(
                        row,
                        "PENDING" if attempts < 4 else "FAILED",
                        now + timedelta(seconds=result["retry_after"]),
                        attempts=attempts,
                    )
                    break
                self.memory.delivery_result(row, "SENT", now, message_id=result["message_id"])
            except (RuntimeError, KeyError, TypeError):
                self.memory.delivery_result(
                    row, "UNKNOWN", now, error="Delivery outcome unknown; no automatic resend"
                )
                break


class DemoNotifier:
    async def close(self):
        pass

    async def deliver(self, now):
        pass
