# Development status

[Wiki home](README.md) · [CLI guide](cli.md) · [Codebase map](codebase-map.md)

Reviewed **2026-10-09**. The full plan is retained; **v0.1 is the first runnable research-only release**, not a complete autonomous paper-trading deployment.

## Implemented

- Python package, dependency lock, private environment credentials, typed policy and CLI doctor.
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

**68 local tests passed, 94.78% line coverage.** One PostgreSQL integration test was skipped locally because no test URL was available; attempts to start local PostgreSQL were blocked by OS-user restrictions. Ruff and generated-map checks passed.

Tests cover scenario consistency, weak/missing initial confidence reaching debate, removed-watchlist holdings, source failure, forged citations, fair queue rotation, holding priority, concurrency, immutable stages, timeouts, safe chat and layouts at 80×24, 120×36 and 160×48.

[GitHub CI](https://github.com/JKGiova/agentic-trading-workflow/actions) is configured for Python 3.12/3.13 with isolated PostgreSQL 16 and a 90% coverage minimum. Its result must be read from the workflow run; configuration is not proof that it passed.

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

## Next milestone

Configure Graphify and provider-backed research with selected stocks, approved X authors and keys; verify T0 without orders. Then implement durable collection/jobs and the reservation/intent/recovery pipeline before network trading. See the [retained backlog](implementation-backlog.md).

