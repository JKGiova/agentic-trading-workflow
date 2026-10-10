"""yfinance discovery, optional authenticated social/filing sources, scoped page reads."""

import asyncio
import ipaddress
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from tradebot.contracts import Category, Coverage, SearchAttempt, utcnow
from tradebot.research import Research, make_evidence


class NewsSources:
    def __init__(
        self, credentials, policy, memory, client=None, ticker_factory=None, search_factory=None
    ):
        self.credentials, self.policy, self.memory = credentials, policy, memory
        self.client = client or httpx.AsyncClient(timeout=15, follow_redirects=False)
        self.owns_client = client is None
        self.legacy = Research(credentials, policy, self.client)
        self.ticker_factory = ticker_factory
        self.search_factory = search_factory

    async def close(self):
        if self.owns_client:
            await self.client.aclose()

    def yahoo(self, instrument):
        import yfinance as yf

        factory = self.ticker_factory or yf.Ticker
        return factory(instrument.symbol).get_news(count=30, tab="all")

    def normalize(self, instrument, rows, cutoff):
        items, gaps = [], False
        start = cutoff - timedelta(hours=self.policy.news_hours)
        for row in rows[:30]:
            try:
                content = row.get("content", row)
                date = content.get("pubDate") or content.get("displayTime")
                if not date and content.get("providerPublishTime"):
                    date = datetime.fromtimestamp(content["providerPublishTime"], UTC)
                link = content.get("canonicalUrl", {}).get("url") or content.get("link")
                if not date or not link:
                    gaps = True
                    continue
                item = make_evidence(
                    "yfinance",
                    row.get("id", link),
                    instrument.symbol,
                    Category.FINANCIAL,
                    content["title"],
                    content.get("summary", ""),
                    link,
                    date,
                )
                if start <= item.published_at <= cutoff:
                    items.append(item)
            except (ValueError, KeyError, TypeError, AttributeError):
                gaps = True
        return items, gaps or len(rows) >= 30

    async def collect(self, instrument, cutoff):
        start = cutoff - timedelta(hours=self.policy.news_hours)
        items, attempts = [], []

        async def run(category, source, operation):
            try:
                async with asyncio.timeout(30):
                    found, complete = await operation()
                found = [x for x in found if start <= x.published_at <= cutoff]
                status = (
                    (Coverage.RESULTS if found else Coverage.EMPTY)
                    if complete
                    else Coverage.DEGRADED
                )
                reason = "Executed source lookup; sampled news coverage is not exhaustive"
            except Exception as exc:
                # Third-party connector failures (including yfinance/curl exceptions)
                # are coverage failures. Cancellation is a BaseException and propagates.
                found, status = [], Coverage.FAILED
                reason = f"Source unavailable ({type(exc).__name__})"
            items.extend(found)
            attempts.append(
                SearchAttempt(
                    stock=instrument.symbol,
                    category=category,
                    source=source,
                    query=f"{instrument.symbol}/{category}",
                    start=start,
                    cutoff=cutoff,
                    completed_at=utcnow(),
                    coverage=status,
                    evidence_ids=[x.id for x in found],
                    reason=reason,
                )
            )

        async def news():
            raw = await asyncio.to_thread(self.yahoo, instrument)
            found, gaps = self.normalize(instrument, raw, cutoff)
            return found, not gaps

        await run(Category.FINANCIAL, "yfinance", news)
        financial = attempts[-1]
        attempts.append(
            financial.model_copy(
                update={
                    "category": Category.COMPANY,
                    "reason": "Shared Yahoo discovery leads, not independent company confirmation",
                }
            )
        )
        # Optional existing adapters remain explicit. Missing credentials remain recorded gaps.
        await run(Category.SOCIAL, "x", lambda: self.legacy._social(instrument, start, cutoff))

        async def market():
            import yfinance as yf

            factory = self.search_factory or yf.Search
            raw = await asyncio.to_thread(
                lambda: factory(self.policy.market_query, news_count=10).news
            )
            found, gaps = self.normalize(instrument, raw, cutoff)
            return [x.model_copy(update={"category": Category.MARKET}) for x in found], not gaps

        await run(Category.MARKET, "yfinance_search", market)
        if instrument.cik:
            await run(Category.COMPANY, "sec", lambda: self.legacy._sec(instrument, start, cutoff))
        for url in instrument.ir_feeds:
            await run(
                Category.COMPANY,
                "ir_rss",
                lambda url=url: self.legacy._rss(instrument, url, start, cutoff),
            )
        return list({(x.id, x.category): x for x in items}.values()), attempts

    async def execute(self, request, task, context, now):
        instrument = next((x for x in self.policy.instruments if x.symbol == task["stock"]), None)
        if instrument is None:
            from tradebot.settings import Instrument

            instrument = Instrument(symbol=task["stock"], name=task["stock"], sector="unknown")
        if request.action == "SEARCH_NEWS":
            # Stock/role are fixed by the task; a model query cannot expand scope or author policy.
            items, attempts = await self.collect(instrument, now)
            if request.query:
                import yfinance as yf

                factory = self.search_factory or yf.Search
                query = f"{instrument.symbol} {request.query}"
                async with asyncio.timeout(30):
                    raw = await asyncio.to_thread(lambda: factory(query, news_count=10).news)
                found, gaps = self.normalize(instrument, raw, now)
                items = [*found, *items]
                attempts.append(
                    SearchAttempt(
                        stock=instrument.symbol,
                        category=Category(task["role"]),
                        source="yfinance_search",
                        query=query,
                        start=now - timedelta(hours=self.policy.news_hours),
                        cutoff=now,
                        completed_at=now,
                        coverage=Coverage.DEGRADED
                        if gaps
                        else Coverage.RESULTS
                        if found
                        else Coverage.EMPTY,
                        evidence_ids=[x.id for x in found],
                        reason="Executed targeted sampled search",
                    )
                )
            self.memory.remember(items, now)
            return {
                "status": "EXECUTED",
                "query": request.query,
                "scope": instrument.symbol,
                "evidence": [x.model_dump(mode="json") for x in items],
                "attempts": [x.model_dump(mode="json") for x in attempts],
            }
        known = {item["id"]: item for item in context["evidence"]}
        for result in task["payload"]["checkpoint"].get("tools", []):
            known.update({x["id"]: x for x in result.get("evidence", [])})
        if request.evidence_id not in known:
            raise ValueError("Read references an unknown evidence ID")
        item = known[request.evidence_id]
        if request.action == "READ_EVIDENCE":
            return {"status": "EXECUTED", "evidence": [item]}
        url = urlparse(item["url"])
        allowed = {d.lower() for d in self.policy.article_domains}
        allowed.update(urlparse(feed).hostname for feed in instrument.ir_feeds)
        if instrument.cik:
            allowed.add("www.sec.gov")
        if (
            url.scheme != "https"
            or url.username
            or url.password
            or url.port not in {None, 443}
            or url.hostname not in allowed
        ):
            raise ValueError("Article URL is outside the registered HTTPS source policy")
        # Refuse private destinations and redirects before fetching source content.
        addresses = await asyncio.get_running_loop().getaddrinfo(url.hostname, 443)
        if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise ValueError("Source does not resolve to public addresses")
        headers = (
            {"User-Agent": self.credentials.sec_user_agent} if url.hostname == "www.sec.gov" else {}
        )
        async with self.client.stream("GET", item["url"], headers=headers) as response:
            response.raise_for_status()
            if response.is_redirect:
                raise ValueError("Source redirect requires separate registration")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 2_000_000:
                    raise ValueError("Article exceeds retrieval bound")
        soup = BeautifulSoup(bytes(body), "html.parser")
        for node in soup(["script", "style", "nav", "footer"]):
            node.decompose()
        text = soup.get_text(" ", strip=True)
        if not text:
            raise ValueError("No accessible source text")
        evidence = make_evidence(
            "page",
            item["id"],
            task["stock"],
            Category(task["role"]),
            item["title"],
            text,
            item["url"],
            item["published_at"],
        )
        evidence = evidence.model_copy(update={"retrieved_at": now})
        self.memory.remember([evidence], now)
        return {
            "status": "EXECUTED",
            "content_level": "bounded page text",
            "evidence": [evidence.model_dump(mode="json")],
        }
