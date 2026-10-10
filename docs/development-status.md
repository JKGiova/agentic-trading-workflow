# Development status

[Wiki home](README.md) · [CLI guide](cli.md) · [Codebase map](codebase-map.md)

Reviewed **2026-10-10**. The full plan is retained; **v0.1 is the first runnable research-only release**, not a complete autonomous paper-trading deployment.

## Implemented

- Python package, dependency lock, private environment credentials, typed policy and CLI doctor.
- Executable `start.sh`: uv/Python bootstrap, locked runtime installation and default demo launch.
- Single-window Textual interface: open positions, selected position, chatbot and portfolio/performance.
- Selection/focus shortcuts, scrolling, persistent chat and asynchronous research/chat.
- Explicit synthetic offline demo, separate from provider-backed data.
- LangGraph analyst/synthesis and debate/judgment graphs with the agreed eight-role ownership.
- Mandatory stock-specific research for every holding, including those outside the watchlist.
- Alpaca news, approved-author X, restricted-domain Tavily, configured SEC metadata and IR RSS adapters.
- Read-only Alpaca paper account, holdings, pending orders and IEX quotes; no order-submission method.
- Independent analyst reports, initial confidence/scenarios, holding reviews and separate Allocator.
- Direct fair debate queue without confidence/EV/score thresholds, bounded rounds and frozen-evidence verification.
- Orchestrator final confidence/verdict, citation checks and refusal of unsupported final approvals.
- Deterministic confidence/downside sizing, cash, exposure, sector, pending-order and freshness previews.
- Durable evidence/search logs, immutable completed stages, queue, conversations and model-budget reservations.
- SQLite local mode and an initial PostgreSQL-compatible schema with lease/budget concurrency tests.
- Account refresh and opt-in X-hour sessions while the terminal is open.
- Offline workflow/provider/terminal tests, CI and a deterministic AST codebase map.

## Verification

At source commit `590d40d75264d7cfac2d028c8163791379828b8f`, **75 local tests passed,
one PostgreSQL test skipped, 94.80% line coverage**. No local test database URL was
available. Ruff, launcher syntax and generated-map checks passed; the launcher was
also exercised in an actual terminal, with clean exit, and completed a demo session.

Tests cover scenario consistency, weak/missing initial confidence reaching debate, removed-watchlist holdings, source failure, forged citations, fair queue rotation, holding priority, concurrency, immutable stages, timeouts, safe chat and layouts at 80×24, 120×36 and 160×48.

[The latest verified implementation CI](https://github.com/JKGiova/agentic-trading-workflow/actions/runs/38030865729)
passed on both Python 3.12 and 3.13 with isolated PostgreSQL 16: **76 tests passed,
none skipped, approximately 95% coverage**. Jobs also passed lint/format, map
freshness, launcher syntax, launcher doctor and launcher demo-session checks.
CI uses the official PostgreSQL ECR Public mirror after a Docker Hub pull-limit
failure. [Subsequent runs](https://github.com/JKGiova/agentic-trading-workflow/actions)
enforce the same 90% coverage minimum.

## Agent and connector maturity

All eight roles and the intended confidence/debate/Allocator sequence exist.
Current analyst calls use one model and the same mixed evidence snippets; independent
calls do not yet have specialist prompts or scoped research tools. Debate verification
only rereads frozen evidence. The Allocator proposes each stock independently, not
one capital-reserving portfolio plan. Graph checkpoints and automatic resume are
pending. See [agent runtime](agent-runtime.md) for the role-by-role review.

News adapters exist but full Alpaca article content is discarded in favor of
summaries, financial/company requests duplicate the feed, and collection has no
independent durable worker. SEC is metadata-only, Tavily is discovery, and quote
timestamps/feed metadata are discarded. These are explicit work packages in
[connector implementation](connector-implementation.md), with the separate
[trading connector specification](trading-connectors.md) defining future execution.

No actual paid-provider access, entitlements, measured predictive performance or broker submissions were verified in this implementation session. HTTP fixtures validate expected adapter behavior; real-account access still requires T0.

Graphify is connected, but listing workspaces/repositories and querying graph statistics return `no_workspace`. The actual workspace handle is still needed. The published AST map is explicitly separate; no Graphify export or indexed commit is claimed.

## Remaining full-plan milestones

| Area | Pending work |
| --- | --- |
| T0 access | Owner-account source/model/quote capabilities, real latency/usage/coverage |
| T1 storage | Alembic upgrades, normalized relational contracts and full financial ledger |
| T2 collection | Full SEC facts/filings, deeper publisher coverage, macro vintages, independent collectors and source spend reservations |
| T3 recovery | Durable job workers, cursors, shared rate limiting, persistent graph checkpoints and automatic crash-resume |
| T4–T5 evidence | External bounded verification, deeper event deduplication and shared portfolio briefings |
| T6 portfolio | Portfolio-wide stress estimates and atomic shared-capital reservations; current previews are independent and nonexecutable |
| T7 execution | Durable intents, paper submission, ambiguous-response reconciliation, fills, protections and independent monitoring |
| T8 validation | Prospective outcome settlement, corporate actions, benchmarks, calibration and measured returns |
| T9 operations | Supervision, backups/restores, alerts and long-running recovery exercises |

The initial runtime uses flat modules, startup schema creation and conservative stress assumptions. It does not represent every proposed package, worker or table as completed.

## Plan refinement: 2026-10-10

Documentation refinement checks: all local Markdown links passed, the regenerated AST map is unchanged and current, Ruff passed, and the existing offline suite passed **75 tests with 1 PostgreSQL test skipped, 94.80% coverage**. The local database URL remains unavailable; new provider access and new workflow behavior were not exercised because this change is a plan only.

The selected target now uses Alpaca for broker/market data, yfinance for primary news discovery and AgentReach-backed bounded research. [Research workflow](research-workflow.md) specifies specialist tool loops and conference follow-up; [memory design](memory-and-retrieval.md) specifies event/evidence/thesis storage, retrieval and checkpoints. These are documentation changes: yfinance and AgentReach are not installed, and current provider adapters/tool restrictions are unchanged.

## Next milestone

Start W0/W1 in the [workflow-first backlog](implementation-backlog.md): selected-provider contracts plus evidence/event memory. Implement C0/C1 capability and evidence contracts with offline fixtures, then run
opt-in T0 source/model/account reads when owner configuration is available. Continue
with durable collection and typed bounded verification; C5/C6 broker reconciliation,
shared-capital reservations, intents and protection remain prerequisites for paper
submission. Graphify still requires the actual workspace handle. See the
[retained backlog](implementation-backlog.md).

