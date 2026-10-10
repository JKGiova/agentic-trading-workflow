# Selected providers: NVIDIA NIM, Alpaca, yfinance and AgentReach

[Wiki home](README.md) · [Research workflow](research-workflow.md) · [Memory](memory-and-retrieval.md)

**Selected target, 2026-10-10.** The owner chose Alpaca, yfinance and AgentReach.
This supersedes the earlier Alpaca-news/official-X/Tavily default proposal.
Existing adapters remain documented as implemented; provider migration is pending.

The selected model service is now **NVIDIA NIM / DeepSeek V4.1 Flash**, replacing
the OpenRouter baseline in the target. All initial roles and chat use
`deepseek-ai/deepseek-v4.1-flash`; see [model provider](model-provider.md). The
default model client is now NVIDIA NIM. The continuous team uses yfinance,
registered page reads and optional existing X/SEC/IR adapters; AgentReach-backed
provisioning remains pending. See [continuous runtime](continuous-runtime.md).

| Component | Selected responsibility | Explicit boundary |
| --- | --- | --- |
| NVIDIA NIM | DeepSeek V4.1 Flash inference for analysts, debate, Orchestrator, Manager and chat | Model endpoint only; tool capability, quota and billing must be checked; memory/scheduling remain ours |
| Alpaca | Account, holdings, pending orders, quotes/bars, clock/calendar; later paper execution | Broker-confirmed state and feed timestamps; agents cannot submit orders |
| yfinance | Primary financial/company news and press-release discovery; shared macro searches | Yahoo sampling is not a complete news archive or guaranteed three-hour coverage |
| AgentReach | Selected web-search, page-reading, approved-X and available video-transcript capabilities | Setup/routing ecosystem around underlying tools; not our graph, memory service or guaranteed data API |
| SEC/IR and official releases | Original financial disclosures, announcements and macro facts reached through registered adapters | Keep typed official adapters and configured identity/source rules |

Alpaca/Benzinga news and Tavily remain optional alternatives if enabled explicitly.
Official X remains an optional alternative. A fallback cannot silently change source,
author policy, billing or coverage status. Firecrawl is not required for the initial
selected path; it can remain an explicit article-extraction fallback.

## yfinance discovery

Use `Ticker.get_news(count=..., tab="all")` for mixed stock leads, or separately
configured `news` and `press releases` requests. Keep request identity/cache scope
explicit and deduplicate results across categories. Verify the pinned version's
cache behavior rather than reusing a Ticker object and assuming each tab refetches.
Use `Search(..., news_count=...)` for shared macro queries and an explicit sampled
fallback when ticker news is unavailable. Validate returned ticker/entity relevance.

Persist title, summary, publisher, original/canonical URL, provider ID, raw timestamp,
normalized publication time and observed time. `content` in a Yahoo response may be
a metadata object; it does not establish that we received a full article. Article
reading is a separate registered operation. Apply the exact UTC window locally.

Yahoo is unofficial access through yfinance. Lock a tested package version, rate-limit
and log schema changes, empty responses, caps, failures and missing dates. A requested
count does not guarantee history pagination; durable polling with overlap only archives
what was actually observed. Do not claim recovery of older missing coverage from
increasing count. Real access/retention suitability must be checked during the spike.

The inspected TradingAgents Yahoo adapter formats titles, summaries and links, with
Yahoo Search fallback and coverage-gap handling. Borrow those limitations explicitly;
our AgentReach-backed reading step is an additional capability.

## AgentReach integration

The reviewed upstream describes web reading through Jina Reader, search through Exa,
Twitter/X through selected CLI backends, and YouTube captions through yt-dlp. These
are examples from upstream, not verified capabilities in our environment. Pin both
AgentReach and every enabled backend; do not rely on an auto-changing runtime route.

Use AgentReach for provisioning/diagnostics and a capability report. Our Python
adapter dispatches narrow, typed operations to the selected underlying CLI/MCP/API.
No arbitrary agent-generated command execution. Spawn allowlisted argv without a
shell, with time/output limits, validated output and secrets kept out of logs/prompts.
Provisioning or backend changes happen outside a trading session.

For X, configure approved IDs/handles and inclusion rules. Verify the author and
original timestamp on every result. Backend authentication and supported searches
vary; upstream currently documents manual cookie configuration for its Twitter CLI
path. Credentials are supplied privately, never harvested or included in reports.
If stable author IDs or exact-time collection cannot be verified, mark the capability
degraded rather than claiming successful mandatory social coverage.

For conferences, register official/company/event channels and discover source URLs.
Captions can be missing, automatic, incomplete or mistranslated. Preserve language,
timecodes, origin and limitations; no transcript means no transcript-based claim.
Neither AgentReach nor search grants access to a publisher's paywalled full text.

## Alpaca

Keep the tested read-only REST adapter and improve timestamp/feed/account contracts.
Use Alpaca as the authoritative broker snapshot and proposed tradable market-data
source; yfinance prices cannot silently replace executable quotes. Verify actual
IEX/consolidated entitlements and freshness, clock/calendar, supported instruments
and pending commitments. SDK selection remains an implementation detail.

Paper execution follows the durable budget/intent/recovery/protection milestone in
[trading connectors](trading-connectors.md). Selecting Alpaca does not enable orders.

## Initial capability checks

An opt-in, bounded read-only spike records: one Yahoo news/press-release sample;
one registered page read; one approved-X lookup with verifiable identity/date;
one available or explicitly unavailable transcript; and one Alpaca quote/account read.
Record underlying backend/version, authentication requirement, cost basis, supported
window, latency and content level. Fixtures cannot prove provider access or completeness.

## Primary references

- [yfinance news tabs](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_news.html)
- [TradingAgents inspected Yahoo adapter](https://github.com/TauricResearch/TradingAgents/blob/1394a3f72aa4393e1a98f51b382434c4b4c2d972/tradingagents/dataflows/vendors/yahoo/news.py)
- [AgentReach upstream](https://github.com/Panniantong/Agent-Reach) and [installation guidance](https://github.com/Panniantong/Agent-Reach/blob/main/docs/install.md), reviewed 2026-10-10; pin a revision in the access spike
- [Alpaca market data](https://docs.alpaca.markets/us/docs/about-market-data-api) and [paper trading](https://docs.alpaca.markets/us/docs/paper-trading)
