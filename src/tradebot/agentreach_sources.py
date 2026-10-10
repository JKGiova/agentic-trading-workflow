"""Pinned Agent Reach Jina page reads and explicit-cookie twitter-cli searches."""

import asyncio
import json
import re
import sys
from contextlib import suppress
from datetime import timedelta

from tradebot.contracts import Category
from tradebot.research import make_evidence


class AgentReachSources:
    def __init__(self, credentials, policy, runner=None, timeout=30):
        self.credentials, self.policy = credentials, policy
        self.runner = runner or self.run
        self.timeout = timeout
        self.lock = asyncio.Lock()

    async def run(self, payload):
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "tradebot.agentreach_worker",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            async with asyncio.timeout(self.timeout):
                output, _ = await process.communicate(json.dumps(payload).encode())
            if process.returncode or len(output) > 2_000_000:
                raise ValueError(
                    "Agent Reach source lookup failed; check access or renew X cookies"
                )
            result = json.loads(output)
            if not isinstance(result, dict):
                raise ValueError("Invalid Agent Reach response")
            return result
        finally:
            if process.returncode is None:
                with suppress(ProcessLookupError):
                    process.kill()
                await process.wait()

    async def social(self, instrument, start, cutoff):
        auth = self.credentials.x_auth_token.get_secret_value()
        ct0 = self.credentials.x_ct0.get_secret_value()
        if not auth or not ct0 or not self.policy.approved_x_authors:
            raise ValueError("Agent Reach X cookies or approved author IDs/handles missing")
        handles = list(self.policy.approved_x_authors.values())
        authors = " OR ".join(f"from:{handle}" for handle in handles)
        aliases = [instrument.symbol, instrument.name, *instrument.aliases]
        terms = " OR ".join('"' + re.sub(r'["\\\r\n]', "", name) + '"' for name in aliases)
        # The backend uses day operators; exact UTC bounds are enforced on results below.
        query = (
            f"({authors}) ({terms}) -filter:retweets "
            f"since:{start.date()} until:{(cutoff + timedelta(days=1)).date()}"
        )
        if len(query) > 512:
            raise ValueError("X query exceeds the bounded author/alias limit")
        async with self.lock:
            raw = await self.runner(
                {"operation": "x", "auth_token": auth, "ct0": ct0, "query": query}
            )
        rows = raw.get("tweets")
        if not isinstance(rows, list) or len(rows) > 50:
            raise ValueError("Invalid X search response")
        items, gaps = [], bool(raw.get("capped")) or len(rows) >= 50
        for row in rows:
            try:
                author = row["author"]
                author_id, handle = str(author["id"]), author["screenName"]
                approved = self.policy.approved_x_authors.get(author_id)
                if not approved or approved.casefold() != handle.casefold():
                    gaps = True
                    continue
                if row.get("isRetweet") or row.get("isPromoted"):
                    continue
                if not any(
                    re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", row["text"], re.I)
                    for alias in aliases
                    if alias
                ):
                    gaps = True
                    continue
                post_id = str(row["id"])
                if not post_id.isdigit() or not row["text"].strip():
                    gaps = True
                    continue
                item = make_evidence(
                    "agentreach_x",
                    post_id,
                    instrument.symbol,
                    Category.SOCIAL,
                    row["text"],
                    row["text"],
                    f"https://x.com/{approved}/status/{post_id}",
                    row.get("createdAtISO") or row["createdAt"],
                    author_id,
                )
                if start <= item.published_at <= cutoff:
                    items.append(item)
            except KeyError, TypeError, ValueError, AttributeError:
                gaps = True
        return list({x.id: x for x in items}.values()), not gaps

    async def read(self, url):
        raw = await self.runner({"operation": "web", "url": url})
        text = raw.get("text")
        if not isinstance(text, str) or len(text.encode()) > 2_000_000:
            raise ValueError("Invalid or oversized Agent Reach page")
        source = re.search(r"^URL Source:\s*(\S+)", text, re.MULTILINE)
        if not source or source[1].rstrip("/") != url.rstrip("/"):
            raise ValueError("Reader source changed; redirects require separate registration")
        _, separator, content = text.partition("Markdown Content:")
        if not separator or not content.strip():
            raise ValueError("No accessible source text")
        lower = text.casefold()
        if any(
            marker in lower
            for marker in (
                "requiring captcha",
                "title: just a moment",
                "attention required! | cloudflare",
                "401 unauthorized",
                "403 forbidden",
                "sign in to continue",
                "subscribe to continue",
            )
        ):
            raise ValueError("Reader returned a login, paywall or challenge page")
        return content.strip()

    def capabilities(self):
        return {
            "web": "Agent Reach / Jina Reader"
            if self.policy.article_backend == "agentreach"
            else "direct HTTP",
            "x": "Agent Reach / twitter-cli"
            if self.policy.x_backend == "agentreach"
            else "official X API",
            "x_cookies_configured": bool(
                self.credentials.x_auth_token.get_secret_value()
                and self.credentials.x_ct0.get_secret_value()
            ),
            "approved_x_authors": len(self.policy.approved_x_authors),
            "registered_article_domains": len(self.policy.article_domains),
            "network_verified": False,
        }
