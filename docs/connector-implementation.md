# Connector implementation and source access

[Wiki home](README.md) · [Project overview](../README.md)

Reviewed **2026-10-10** against the current source and official provider documentation.
Keep US equities and Alpaca paper as the first integration scope, with an
owner-configured watchlist. This is an implementation plan, not verified account
access. No paid subscriptions, credentials or order permissions were added.

## What the code actually does

| Connector | Current implementation | Gap before trusted research/execution |
| --- | --- | --- |
| Alpaca news | Authenticated HTTP REST, symbol/time filters, bounded pagination | Requests full content but stores only `summary`; ignores provider update time and symbol list; financial/company queries duplicate the same feed |
| Tavily | Domain-checked macro query, dated result snippets | Same generic market query per stock; no publisher body retrieval, usage ledger or proof of exhaustive coverage |
| X | Recent search, configured aliases/handles, stable author-ID validation, pagination | No query batching, durable cursor, source-cost reservation or explicit reply/quote policy |
| SEC | Submissions metadata for configured CIKs and acceptance timestamps | No actual filing text, company facts, old submission-file backfill or cross-process rate limiter |
| Company IR | Explicitly configured HTTPS RSS, bounded response and feed parsing | Feed summary only; body retrieval, identity/redirect policy and content-version handling missing |
| Alpaca account/data | Paper account, long holdings, open orders, IEX quote midpoint | Quotes lose exchange/event timestamps; clock/calendar/assets and robust commitment reconciliation missing |

These are direct `httpx` adapters in `research.py` and `broker.py`; `alpaca-py` is
not an installed dependency. Reuse the tested REST transport behind separate
interfaces first. Add a pinned WebSocket transport only when implementing durable
stream/reconnect handling; an SDK must not conceal submission retries or feed identity.

Collection currently runs inside each session, not as an independent service.
History comes from previously stored evidence, not a historical-provider backfill.
Existing HTTP fixtures verify parsing/permissions; real entitlements are unverified.

## Concrete provider mapping

| Need | First connector | Access and limitation |
| --- | --- | --- |
| Stock-linked financial news | Alpaca News, supplied by Benzinga | REST history and news streaming; authenticate with entitled API credentials and verify accessible content |
| Approved financial publications | Authorized RSS/licensed publisher feeds; Tavily for domain-restricted discovery | Alpaca does not supply Reuters/FT/WSJ access; search results do not grant full-article access |
| Company disclosures | SEC EDGAR submissions/facts plus per-company IR feeds/pages | EDGAR covers relevant US filers; IR endpoints and permitted content vary by company |
| Market/macro news | Approved official central-bank/economic-release feeds and financial-news sources | Build a source registry; FRED/ALFRED can add structured macro context and vintages |
| Approved X authors | Official X Recent Search | Whitelist author IDs, account-to-query mapping, pagination, and spending cap |
| Prices, account, calendar, orders | Alpaca Trading/Market Data behind typed transport interfaces | Existing HTTP reads first; future paper execution stays separate from agents |

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

## Concrete implementation sequence

The following packages refine T0-T3 and T7; they do not mark those milestones complete.

| Package | Deliverable | Acceptance check |
| --- | --- | --- |
| C0. Capabilities and identity | Versioned source registry, instrument/CIK aliases, publisher domains, X IDs/handles and account/feed capabilities; separate opt-in network probe | One small bounded read per enabled capability; 401/403/429, empty data and missing entitlement distinguished; sanitized local report; no orders |
| C1. Evidence contracts | Provider item/version identity, many-to-many stock/category links, publication/update/observation timestamps, content level, scope and rights/retention metadata | One Benzinga item used by two analysts is one event/version; corrections remain immutable; full text, summary, search snippet and filing metadata never conflated |
| C2. News and social adapters | Consume accessible Alpaca content; fetch once and route to financial/company views; X query batches; authorized publisher/IR retrieval; SEC documents/facts | Pagination exhaustion versus cap, future/date-only items, renamed authors, redirects, corrections, missing content, delayed publication and query limits covered by fixtures |
| C3. Durable collection | Alembic migrations, cursor and job transactions, per-source rate/cost reservations; independent collector workers | Crash after page write/before cursor advance resumes without losing items; overlap deduplicates; source outage does not stop other collectors or broker monitoring |
| C4. Session evidence and verification | Holding-specific request matrix, bounded history/backlog, immutable bundle and analyst views; typed verification dispatch | Every holding has actual stock-relevant attempt IDs; empty is distinct from failed; fresh/unknown dates do not fabricate three-hour coverage; unresolved requests remain visible |
| C5. Broker read/reconciliation | Typed quotes, asset eligibility, clock/calendar, account constraints, paginated orders/fills and snapshot generations | Feed identity/freshness retained; unknown commitments block additions; closed sessions, halts, manual broker changes and reconnect gaps reconciled |
| C6. Paper lifecycle | Shared capital ledger, intents, dispatcher, order updates and protection manager | Separate [trading connector acceptance matrix](trading-connectors.md) passes before enabling paper submission |

### Source registry and access probe

Planned source entries include source ID, adapter, allowed hosts/endpoints, categories,
required/optional role, query scope, supported windows, retention permission,
per-request page/result limits, timeout/rate policy and operating-budget bucket.
Credentials stay in `.env` or secret storage, never in the registry or model context.
Stock configuration carries stable identity, exchange, sector, CIK, aliases and
approved IR URLs; an unknown holding is still researched, with identity gaps disclosed.

The existing `--doctor` only checks local configuration. A future capability probe
must be explicit, show its planned sources and maximum operating spend, and issue
no submission requests. It records checks individually rather than calling all
providers mandatory by accident. A deliberately disabled source is not a successful
empty lookup. The agreed four-category policy still requires social coverage for
additions; disabling X cannot silently make that requirement pass. An optional
publisher failure is disclosed; a required source failure blocks affected additions.

Test configured journal access independently: the Alpaca feed is Benzinga, not an
entitlement to every approved newspaper. Tavily discovers URLs/snippets; only a
permitted publisher API/feed or accessible article supplies article evidence.
Store the original publisher separately from a discovery provider and validate
redirect destinations before retrieval. Do not fetch arbitrary URLs invented by a model.

### Time windows, duplicates and backlog

Store raw source timestamps and normalized UTC values: `published_at`,
`provider_updated_at`, `observed_at` and the timestamp's precision. Unknown/date-only
publication times stay explicitly uncertain; they cannot prove intraday coverage.
Keep content hashes/versions and an event identity so syndication, reposts and
financial/company routing do not count as independent confirmations.

First collect the latest three hours plus configured historical context, then maintain
durable cursors with a proposed five-minute polling interval and overlap. Polling
cadence is independent of X-hour AI sessions and measured against source budgets.
Process both new publications and newly observed corrections to old items. Provider
pagination tokens are recovery hints, not permanent cursors; expired tokens restart
from a durable timestamp/ID watermark with overlap. Recent X search only covers
seven days; older gaps stay recorded unless authorized archive access exists.

Session inputs contain the latest window, relevant history and unprocessed backlog
without relabeling old news as newly published. A reused shared market briefing must
have real source attempt IDs and an explicit stock relevance assessment. Generic
macro search cannot stand in for missing company/financial/social holding lookups.
Coverage describes the bounded configured scope, not every article or post online.

For SEC facts, preserve concept, unit, period, form, accession and revision lineage;
resolve the associated filing's availability before using a revision at a cutoff.
Do not compare incompatible units/fiscal periods or treat a later revision as an
earlier-known financial fact. Share the SEC limiter across every process/host using
the same identity, with a conservative configured rate below its published ceiling.

### Operating spend and transport failures

Reserve the maximum permitted returned-resource cost before each X page and the
configured search credits before each Tavily request. Record actual usage where
available; an ambiguous charge retains its conservative reservation. X's documented
within-UTC-day billing deduplication is not the application's correctness mechanism.
Use bounded queries, avoid unnecessary user expansions and version reference rates.
Tavily requests should fix search depth, disable automatic parameter changes and
request usage metadata; validate returned domains even with provider restrictions.

Retries honor provider rate-reset/Retry-After information with bounded jitter and
the remaining page/time/spend budget. 401/403 needs configuration/entitlement repair;
it is not a retry loop. A 429 or transport failure never becomes an empty-success
report. Preserve completed pages and the precise incomplete window on interruption.
Prioritize mandatory holding coverage when operating budget is scarce; optional
debates remain pending without confidence/EV queue ranking.

## First deliverable to implement

Implement **C0+C1 first**: typed capability/quote/evidence contracts, registry checks,
content-level labels and a charge-aware, read-only probe. Its initial result should
show, per configured stock, which authorized sources can supply fresh evidence and
which account/feed capabilities work. Then improve C2 and durable collection before
exposing bounded verification to the agents. Trading implementation follows C5/C6,
not a direct `submit_order` call added to the existing read-only class.

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

