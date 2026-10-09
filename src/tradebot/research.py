"""Permission-scoped retrieval and truthful search coverage, including held stocks."""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from tradebot.contracts import Category, Coverage, Evidence, SearchAttempt, utcnow
from tradebot.settings import Credentials, Instrument, Policy


def make_evidence(
    provider, provider_id, stock, category, title, text, url, published, author_id=None
):
    if isinstance(published, str):
        try:
            published = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            published = parsedate_to_datetime(published)
    if published.tzinfo is None:
        raise ValueError("Provider publication date lacks timezone")
    text = text[:5000]
    digest = hashlib.sha256(f"{title}\n{text}\n{url}\n{published}".encode()).hexdigest()[:16]
    return Evidence(
        id=f"{provider}:{provider_id}:{digest}",
        stock=stock,
        category=category,
        source=provider,
        title=title[:500],
        text=text,
        url=url,
        published_at=published,
        retrieved_at=utcnow(),
        author_id=author_id,
    )


class Research:
    def __init__(
        self, credentials: Credentials, policy: Policy, client: httpx.AsyncClient | None = None
    ):
        self.credentials, self.policy = credentials, policy
        self.client = client or httpx.AsyncClient(timeout=15, follow_redirects=False)
        self.owns_client = client is None
        self.sec_lock = asyncio.Lock()
        self.last_sec = 0.0

    async def close(self):
        if self.owns_client:
            await self.client.aclose()

    async def _news(self, stock, category, start, cutoff):
        key = self.credentials.alpaca_api_key.get_secret_value()
        secret = self.credentials.alpaca_secret_key.get_secret_value()
        if not key or not secret:
            raise ValueError("Alpaca credentials missing")
        items, token = [], None
        for _ in range(10):
            params = {
                "symbols": stock,
                "start": start.isoformat(),
                "end": cutoff.isoformat(),
                "limit": 50,
                "include_content": "true",
                "sort": "asc",
            }
            if token:
                params["page_token"] = token
            result = await self.client.get(
                "https://data.alpaca.markets/v1beta1/news",
                params=params,
                headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
            )
            result.raise_for_status()
            data = result.json()
            for item in data["news"]:
                items.append(
                    make_evidence(
                        "alpaca_news",
                        item["id"],
                        stock,
                        category,
                        item["headline"],
                        item.get("summary", ""),
                        item["url"],
                        item["created_at"],
                    )
                )
            token = data.get("next_page_token")
            if not token:
                break
        return items, not bool(token)

    async def _social(self, instrument, start, cutoff):
        credential = self.credentials.x_bearer_token.get_secret_value()
        if not credential or not self.policy.approved_x_authors:
            raise ValueError("X access/author whitelist missing")
        if cutoff - start > timedelta(days=7):
            raise ValueError("Recent X search cannot cover more than seven days")
        handles = list(self.policy.approved_x_authors.values())
        author_part = " OR ".join("from:" + handle for handle in handles)
        aliases = [instrument.symbol, instrument.name, *instrument.aliases]
        # Configured company strings are escaped data, never raw query operators.
        terms = ['"' + name.replace('"', "").replace("\\", "") + '"' for name in aliases]
        query = f"({author_part}) ({' OR '.join(terms)}) -is:retweet"
        if len(query) > 512:
            raise ValueError("X query too long; reduce aliases/whitelist or implement batching")
        items, token = [], None
        for _ in range(10):
            params = {
                "query": query,
                "start_time": start.isoformat(),
                "end_time": cutoff.isoformat(),
                "max_results": 100,
                "tweet.fields": "author_id,created_at,referenced_tweets",
            }
            if token:
                params["next_token"] = token
            response = await self.client.get(
                "https://api.x.com/2/tweets/search/recent",
                params=params,
                headers={"Authorization": f"Bearer {credential}"},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("errors"):
                raise ValueError("X returned partial query errors")
            for post in data.get("data", []):
                if post["author_id"] not in self.policy.approved_x_authors:
                    raise ValueError("X returned an unapproved author; whitelist mismatch")
                items.append(
                    make_evidence(
                        "x",
                        post["id"],
                        instrument.symbol,
                        Category.SOCIAL,
                        post["text"][:200],
                        post["text"],
                        f"https://x.com/i/status/{post['id']}",
                        post["created_at"],
                        post["author_id"],
                    )
                )
            token = data.get("meta", {}).get("next_token")
            if not token:
                break
        return items, not bool(token), query

    async def _market(self, stock, start, cutoff):
        key = self.credentials.tavily_api_key.get_secret_value()
        if not key or not self.policy.market_domains:
            raise ValueError("Tavily key/authorized market domains missing")
        response = await self.client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key,
                "query": self.policy.market_query,
                "topic": "news",
                "search_depth": "basic",
                "max_results": 10,
                "include_domains": self.policy.market_domains,
                "start_date": start.date().isoformat(),
                "end_date": cutoff.date().isoformat(),
            },
        )
        response.raise_for_status()
        items, complete = [], True
        from urllib.parse import urlparse

        for raw in response.json().get("results", []):
            domain = urlparse(raw["url"]).hostname or ""
            if not any(domain == d or domain.endswith("." + d) for d in self.policy.market_domains):
                complete = False
                continue
            if not raw.get("published_date"):
                complete = False
                continue
            items.append(
                make_evidence(
                    "tavily",
                    raw["url"],
                    stock,
                    Category.MARKET,
                    raw["title"],
                    raw.get("content", ""),
                    raw["url"],
                    raw["published_date"],
                )
            )
        # Search results are bounded discovery, never an exhaustive publisher archive.
        return items, complete

    async def _sec(self, instrument, start, cutoff):
        if not instrument.cik or not self.credentials.sec_user_agent:
            raise ValueError("CIK/SEC identifying user agent missing")
        async with self.sec_lock:
            delay = 0.2 - (time.monotonic() - self.last_sec)
            if delay > 0:
                await asyncio.sleep(delay)
            self.last_sec = time.monotonic()
            response = await self.client.get(
                f"https://data.sec.gov/submissions/CIK{instrument.cik.zfill(10)}.json",
                headers={"User-Agent": self.credentials.sec_user_agent},
            )
        response.raise_for_status()
        recent = response.json()["filings"]["recent"]
        items, complete = [], True
        count = len(recent["accessionNumber"])
        for index in range(count):
            date = recent.get("acceptanceDateTime", recent["filingDate"])[index]
            if "T" not in date:
                # Date-only filings cannot be assumed visible at a specific intraday cutoff.
                if start.date().isoformat() <= date <= cutoff.date().isoformat():
                    complete = False
                continue
            accession = recent["accessionNumber"][index]
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(instrument.cik)}/"
                f"{accession.replace('-', '')}/{recent['primaryDocument'][index]}"
            )
            form = recent["form"][index]
            items.append(
                make_evidence(
                    "sec",
                    accession,
                    instrument.symbol,
                    Category.COMPANY,
                    f"{instrument.name} filed {form}",
                    "Filing metadata only. Full filing content has not been retrieved.",
                    url,
                    date,
                )
            )
        return items, complete

    async def _rss(self, instrument, url, start, cutoff):
        if not url.startswith("https://"):
            raise ValueError("Only explicitly configured HTTPS feeds are permitted")
        response = await self.client.get(url)
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise ValueError("Feed exceeds retrieval bound")
        feed = feedparser.parse(response.content)
        items, complete = [], not bool(feed.bozo)
        for entry in feed.entries[:100]:
            date = entry.get("published") or entry.get("updated")
            if not date:
                complete = False
                continue
            items.append(
                make_evidence(
                    "ir_rss",
                    entry.get("id", entry.link),
                    instrument.symbol,
                    Category.COMPANY,
                    entry.title,
                    entry.get("summary", ""),
                    entry.link,
                    date,
                )
            )
        return items, complete and len(feed.entries) <= 100

    async def collect(self, instrument: Instrument, cutoff):
        start = cutoff - timedelta(hours=self.policy.news_hours)
        stock = instrument.symbol
        items, attempts = [], []

        async def record(category, provider, query, operation):
            try:
                result = await operation()
                found, complete = result[:2]
                found = [item for item in found if start <= item.published_at <= cutoff]
                if len(result) == 3:
                    query = result[2]
                status = (
                    (Coverage.RESULTS if found else Coverage.EMPTY)
                    if complete
                    else Coverage.DEGRADED
                )
                reason = (
                    "Executed bounded provider query"
                    if complete
                    else "Incomplete pagination/dated coverage"
                )
            except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as exc:
                found, status = [], Coverage.FAILED
                reason = f"{provider} failed ({type(exc).__name__}); no completed search claimed"
            items.extend(found)
            attempts.append(
                SearchAttempt(
                    stock=stock,
                    category=category,
                    source=provider,
                    query=query,
                    start=start,
                    cutoff=cutoff,
                    completed_at=utcnow(),
                    coverage=status,
                    evidence_ids=[x.id for x in found],
                    reason=reason,
                )
            )

        # Execute and record stock-scoped tasks, including every held instrument.
        await asyncio.gather(
            record(
                Category.MARKET,
                "tavily",
                self.policy.market_query,
                lambda: self._market(stock, start, cutoff),
            ),
            record(
                Category.FINANCIAL,
                "alpaca_news",
                f"symbols={stock}; category=financial",
                lambda: self._news(stock, Category.FINANCIAL, start, cutoff),
            ),
            record(
                Category.COMPANY,
                "alpaca_news",
                f"symbols={stock}; category=company",
                lambda: self._news(stock, Category.COMPANY, start, cutoff),
            ),
            record(
                Category.SOCIAL,
                "x",
                f"approved_authors; stock={stock}",
                lambda: self._social(instrument, start, cutoff),
            ),
        )
        if instrument.cik:
            await record(
                Category.COMPANY,
                "sec",
                f"CIK={instrument.cik}",
                lambda: self._sec(instrument, start, cutoff),
            )
        for url in instrument.ir_feeds:
            await record(
                Category.COMPANY,
                "ir_rss",
                url,
                lambda url=url: self._rss(instrument, url, start, cutoff),
            )
        # Metadata-only SEC results aren't financial facts; no invented company-facts analysis.
        return list({item.id: item for item in items}.values()), attempts


class DemoResearch:
    async def close(self):
        pass

    async def collect(self, instrument, cutoff):
        start = cutoff - timedelta(hours=3)
        items, attempts = [], []
        for category in Category:
            item = make_evidence(
                "demo",
                f"{instrument.symbol}-{category}",
                instrument.symbol,
                category,
                f"SYNTHETIC {category} event",
                "Explicit demo fixture, no real market fact.",
                "https://example.invalid/demo",
                cutoff - timedelta(minutes=30),
            )
            items.append(item)
            attempts.append(
                SearchAttempt(
                    stock=instrument.symbol,
                    category=category,
                    source="demo",
                    query=f"fixture lookup: {instrument.symbol}/{category}",
                    start=start,
                    cutoff=cutoff,
                    completed_at=utcnow(),
                    coverage=Coverage.RESULTS,
                    evidence_ids=[item.id],
                    reason="Executed synthetic fixture lookup, not an external search",
                )
            )
        return items, attempts
