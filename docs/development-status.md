# Development status

[Wiki home](README.md) · [Continuous runtime](continuous-runtime.md) · [Codebase map](codebase-map.md)

Reviewed **2026-10-10**. **v0.2 implements the continuous research team.** Trading
orders remain disabled. Real NVIDIA/Telegram/source access has not been tested
without owner credentials.

## Implemented in this release

- Default NVIDIA NIM / `deepseek-ai/deepseek-v4.1-flash` adapter for research and
  chat, with local structured-output validation, bounded repair, model identity
  checks and conservative token/billing accounting.
- Four specialist LangGraph agents with distinct instructions/scoped context,
  bounded typed research tools and original findings followed by peer review.
- Durable supervisor with singleton lease and independent collection, worker,
  report and delivery loops; fixed X-hour cycles and immediate next-cycle work.
- yfinance stock-news discovery and macro search, optional existing X/SEC/IR
  sources, registered page reads and truthful missing/failed coverage.
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
A complete HTTP-fixture test crosses NVIDIA transport, all four agents, synthesis,
report persistence and Telegram delivery. Tests isolate real owner secrets.

Release verification locally: **126 passed, two PostgreSQL tests skipped without
a test server; 96.39% statement coverage**. CI runs the PostgreSQL cases with its
database service; see the commit-specific Actions result for that outcome.

CI runs Python 3.12/3.13, isolated PostgreSQL, lint/format, a 90% minimum coverage
gate, map freshness and launcher checks. PostgreSQL tests exercise both the existing
ledger and concurrent research-task/outbox claims with cycle budget accounting.
See [Actions](https://github.com/JKGiova/agentic-trading-workflow/actions) for the
commit-specific outcome. Local PostgreSQL tests require an isolated test URL.
Offline fixture success is not a real provider-access or predictive-quality claim.

## Next steps

1. Configure the selected watchlist, private NVIDIA/Telegram credentials and owner
   chat pairing; measure actual latency, output quality, quota and source coverage.
2. Provision AgentReach-backed approved X/transcript access and fuller official
   company facts. The current Social role reports a gap without source access.
3. Consume every closed-cycle obligation in the bounded debate/Orchestrator
   pipeline, then produce one volatility-aware portfolio-wide Manager plan.
4. Complete durable reservations, order intents, reconciliation and protections
   before any Alpaca paper submission; run prospective forecast calibration.

The supervisor checkpoints are application task/turn records, not a LangGraph
checkpointer backend. Memory currently retrieves by stock/time; semantic/full-text
retrieval remains a measured later enhancement. Reports without broker access
have no executable reference quote. Graphify remains uninstalled; the published
map is a deterministic AST export.
