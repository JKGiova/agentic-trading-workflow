# Connector implementation and source access

[Wiki home](README.md) · [Project overview](../README.md)

Reviewed **2026-10-09**. Propose US equities for the first paper spike; this is a technical scope choice requiring an owner-configured watchlist. Every connector must prove access and timestamp behavior before agents rely on it.

## Concrete provider mapping

| Need | First connector | Access and limitation |
| --- | --- | --- |
| Stock-linked financial news | Alpaca News, supplied by Benzinga | REST history and news streaming; authenticate with entitled API credentials and verify accessible content |
| Approved financial publications | Authorized RSS/licensed publisher feeds; Tavily for domain-restricted discovery | Alpaca does not supply Reuters/FT/WSJ access; search results do not grant full-article access |
| Company disclosures | SEC EDGAR submissions/facts plus per-company IR feeds/pages | EDGAR covers relevant US filers; IR endpoints and permitted content vary by company |
| Market/macro news | Approved official central-bank/economic-release feeds and financial-news sources | Build a source registry; FRED/ALFRED can add structured macro context and vintages |
| Approved X authors | Official X Recent Search | Whitelist author IDs, account-to-query mapping, pagination, and spending cap |
| Prices, account, calendar, orders | Alpaca Trading/Market Data through `alpaca-py` | Paper broker first; record feed entitlement and timestamps |

No provider automatically satisfies all four analyst categories. Successful authentication does not prove sufficient coverage.

## Alpaca news and market data

Implement `AlpacaNewsConnector` over `GET https://data.alpaca.markets/v1beta1/news`, using symbol/time filters, pagination, and available article content. Persist provider ID, source, URL, symbol mapping, creation/update times, and acquisition time. Treat absent article content as a limited evidence item, not a successfully read full article.

Start with REST polling/backfill; optionally add `wss://stream.data.alpaca.markets/v1beta1/news`. After reconnecting, recover from the last durable cursor with an overlap and deduplicate. The news docs describe historical Benzinga coverage from 2015; test the needed symbols/dates and account entitlement rather than assuming complete history.

Use the broker clock/calendar for trading-session checks and the forecast's five-trading-day settlement date. Store quote source, exchange/feed, event time, and observed time. Alpaca Basic equity data is IEX coverage, not the consolidated market; its individual Algo Trader Plus plan lists $99/month with broader coverage. A Paper Only account's documented entitlement is IEX. Verify which feed is actually accessible; delayed or partial coverage cannot be labeled consolidated live pricing.

## X whitelist and three-hour research

Use `GET https://api.x.com/2/tweets/search/recent` with an app bearer credential. An example query template, populated only from configuration:

```text
(from:APPROVED_HANDLE_A OR from:APPROVED_HANDLE_B)
($TICKER OR "Company Name" OR "Approved Alias")
-is:retweet
```

Reply/repost/quote inclusion follows the configured whitelist policy. Request author and creation-time fields. Check each returned `author_id` against approved stable IDs even when the query uses usernames; username changes require refreshing the mapping.

Set an explicit recent window ending at the evidence cutoff, follow `next_token`, and retain the final cursor only after durable writes. Recover unprocessed backlog; Recent Search's seven-day range is insufficient for older gaps without authorized archive access. Split oversized queries within current operator/query limits and log pagination completeness.

Continuous collection may batch source queries. The session coverage service still executes and logs required stock-specific lookups for held stocks; a generic batch or an old cached summary cannot fabricate that requirement. Short-lived cache reuse must retain the original request/cutoff and satisfy the coverage policy.

Budget on returned billable resources, not merely HTTP calls. The published post-read rate is $0.005/resource; user reads are separately priced. X documents within-UTC-day billing deduplication as a soft guarantee. Keep internal deduplication and conservative spending headroom regardless.

## SEC, IR, and historical financial context

Map symbols to padded ten-digit CIKs. Use:

- `https://data.sec.gov/submissions/CIK##########.json` for filing metadata.
- `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` for disclosed facts.
- Authorized filing documents/IR releases for the actual announcement and relevant narrative.

SEC's public data APIs require no API key. Use an identifying user agent, caching, backoff, and a shared limiter below its published 10-requests/second maximum. Record acceptance/filing metadata and amendments; select only versions available at the decision cutoff. Facts for the same financial period can have later revisions.

Maintain company-specific IR URL/feed configuration rather than guessing endpoints. If an IR page has no reliable publication timestamp, record acquisition time and uncertainty. FRED/ALFRED is optional structured context; economic revisions require vintage-aware retrieval for replay.

## Publisher discovery and permitted retrieval

Implement `PublicationSearchConnector` with Tavily Search restricted to approved domains. Request results and source URLs rather than relying on an API-generated answer. Resolve original publication dates where available, fetch only authorized accessible content, and record redirects/source identity.

Search date filters help discovery but do not implement an exact three-hour or point-in-time guarantee. Enforce timestamps locally. Paywalled or inaccessible items remain headline/reference evidence with explicit limitations; approved publications must have a tested access path if full-text processing is required.

## Connector result contract and proof

Each call produces request ID, provider, category/stock, query, requested window, observed time, evidence IDs, cursor/pages, completeness, status, retry count, and cost/usage. Use the existing complete-with-results, complete-no-new-results, degraded, and failed coverage states.

The first access spike proves: one authorized news fetch, one stock-specific X lookup, one filing/IR lookup, one publisher lookup, and one quote/calendar retrieval. Save sanitized samples and negative cases. Missing paid access remains an explicit blocker for that source; do not substitute another platform while claiming X coverage.

## Primary references

- [Alpaca news endpoint](https://docs.alpaca.markets/us/reference/news-3), [history](https://docs.alpaca.markets/us/docs/historical-news-data), [stream](https://docs.alpaca.markets/us/docs/streaming-real-time-news)
- [Alpaca feed plans](https://docs.alpaca.markets/us/docs/about-market-data-api), [paper environment](https://docs.alpaca.markets/us/docs/paper-trading)
- [X Recent Search](https://docs.x.com/x-api/posts/search/quickstart/recent-search), [query operators](https://docs.x.com/x-api/posts/search/integrate/build-a-query), [pricing](https://docs.x.com/x-api/getting-started/pricing)
- [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [fair access](https://www.sec.gov/about/developer-resources)
- [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [FRED API and vintage data](https://fred.stlouisfed.org/docs/api/fred/)

## Related pages

- [Data and sources](data-and-sources.md)
- [Agent runtime](agent-runtime.md)
- [Persistence and contracts](persistence-and-contracts.md)
- [Implementation backlog](implementation-backlog.md)
