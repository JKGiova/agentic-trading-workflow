# Development status

[Wiki home](README.md) · [Continuous runtime](continuous-runtime.md) · [Codebase map](codebase-map.md)

Reviewed **2026-10-10**. **v0.4.0 targets Python 3.14 and adds credential onboarding and Agent Reach web/X research.** Trading
orders remain disabled. Real NVIDIA/Telegram/X account access has not been tested
without owner credentials.

## Implemented in this release

- Install with `uv sync --locked --no-dev --python 3.14`, activate `.venv`, and
  launch with the packaged `tradingworkflow` command. The Bash launcher starts the
  same entry point; `tradebot` remains a compatibility alias.
- Default launcher opens a single-window Telegram onboarding/home screen without
  model or broker credentials. Token entry is masked, pairing uses a private
  one-time code, and successful setup sends an isolated test message.
- Onboarding asks for X hours between reports, supports decimal intervals and
  persists validated preferences atomically with setup completion. Existing paired
  users add this step without reentering tokens. Schedule changes preserve current
  cycle deadlines and take effect on the next cycle, including across restarts.
- Continuous startup checks a matching Telegram destination; the four-pane CLI shows
  the report cutoff and interval. One-cycle runs attempt delivery before shutdown.
- Atomic private token storage, saved/versioned setup steps, reconnect and explicit
  standalone test commands. Setup state can retain completed steps when future
  wallet/configuration capabilities are added. Model keys, X cookies and optional
  SEC/Alpaca read-only credentials are collected by this release.
- Default NVIDIA NIM / `deepseek-ai/deepseek-v4.1-flash` adapter for research and
  chat, with local structured-output validation, bounded repair, model identity
  checks and conservative token/billing accounting.
- Four specialist LangGraph agents with distinct instructions/scoped context,
  bounded typed research tools and original findings followed by peer review.
- Durable supervisor with singleton lease and independent collection, worker,
  report and delivery loops; fixed X-hour cycles and immediate next-cycle work.
- yfinance stock-news discovery and macro search, pinned Agent Reach/Jina web
  reads and twitter-cli approved-X retrieval, optional SEC/IR and explicit legacy
  sources, and truthful missing/failed coverage.
- New masked model/news setup screens, deferred Telegram-only setup, exact
  author/domain registration, private atomic key storage and metadata fingerprints.
- SQLite/PostgreSQL event versions and correction lineage, task leases,
  input/turn/tool checkpoints, retries/backoff, preserved questions/dissent and
  restart recovery with old-worker fencing.
- Atomic report manifests, late-result exclusion, unfinished/deferred-event carry,
  per-stock initial forecasts and every-stock debate obligations without a filter.
- Monthly and cycle research/report model budgets enforced before each call.
- Telegram private pairing, durable multipart summaries, ordered delivery,
  quota retry and unknown-send recovery; no incoming trading commands.
- Four-pane Textual CLI, continuous status/findings and stored-report chatbot,
  headless mode and a simulated-clock full-cycle demo.
- Source policy edits staged across cycle boundaries and interrupted updates;
  v0.2/v0.3 cycles retain their original backends until closure during upgrades.
- Updated locked dependencies, codebase map and meaningful offline/integration tests.

## Retained earlier capabilities

The earlier eight-role bounded decision graphs, read-only Alpaca account/quotes,
mandatory holding research, fair debate queue and deterministic allocation previews
remain available in normal session mode. They do not automatically consume the
new supervisor's closed-cycle cases. There is no broker-submission method.

## Verification

The offline suite covers timing boundaries, news corrections, duplicate work,
original-before-peer ordering, tool/citation validation, crash/lease recovery,
spend limits, frozen manifests, source failures, next-cycle overlap, Telegram
pairing/rate limits/unknown sends, CLI startup/shutdown and the four-pane terminal.
A complete HTTP-fixture test crosses onboarding, saved scheduling, NVIDIA transport,
all four agents, synthesis, two consecutive reports and Telegram delivery. Tests
isolate real owner secrets.

Release verification locally on **Python 3.14.8**: **222 passed, two PostgreSQL tests
skipped without a test server; 96.30% statement coverage**. CI runs the PostgreSQL cases with its
database service; see the commit-specific Actions result for that outcome.

CI runs Python 3.14, isolated PostgreSQL, lint/format, a 90% minimum coverage
gate, map freshness, installed-command checks and launcher checks. Offline tests
exercise the installed `tradingworkflow` executable for help, configuration checks
and safe noninteractive first launch; CI also launches it after activating `.venv`.
PostgreSQL tests exercise both the existing
ledger and concurrent research-task/outbox claims with cycle budget accounting.
See [Actions](https://github.com/JKGiova/agentic-trading-workflow/actions) for the
commit-specific outcome. Local PostgreSQL tests require an isolated test URL.
Offline fixture success is not a real provider-access or predictive-quality claim.

## Next steps

1. Configure the selected watchlist, private NVIDIA/Telegram credentials and owner
   chat pairing; measure actual latency, output quality, quota and source coverage.
2. Verify credentialed Agent Reach X access and add transcript/search capabilities
   and fuller official company facts. The Social role reports missing access as a gap.
3. Consume every closed-cycle obligation in the bounded debate/Orchestrator
   pipeline, then produce one volatility-aware portfolio-wide Manager plan.
4. Complete durable reservations, order intents, reconciliation and protections
   before any Alpaca paper submission; run prospective forecast calibration.

The supervisor checkpoints are application task/turn records, not a LangGraph
checkpointer backend. Memory currently retrieves by stock/time; semantic/full-text
retrieval remains a measured later enhancement. Reports without broker access
have no executable reference quote. Graphify remains uninstalled; the published
map is a deterministic AST export.
