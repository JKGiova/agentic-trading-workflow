# Implementation stack and build options

[Wiki home](README.md) · [Project overview](../README.md)

Reviewed **2026-10-09**. The [v0.1 CLI](cli.md) implements a first subset with a dependency lock. This page retains the full implementation target; see [status](development-status.md) for differences. Preserve the eight AI roles, direct debate without a numerical prefilter, independent Allocator and mandatory holding research.

## Continuous-cycle refinement

The selected target is now [continuous analyst cycles](continuous-analysis.md): durable per-news tasks, bounded cross-review, fixed report manifests, every-stock debates and a volatility-aware Portfolio Manager. Use separate research-task and decision graphs/leases; current v0.1 still uses one-pass model stages.

## Recommended first implementation

Build a small Python application with an explicit LangGraph workflow and PostgreSQL business ledger. Study TradingAgents at a pinned revision; adapt selected components only after a technical spike. Keep source collection, decision sessions, and order monitoring as separate workers.

| Responsibility | Proposed tool/package | How we use it |
| --- | --- | --- |
| Runtime | Python 3.12/3.13, virtual environment | One language for agents, data, risk, and evaluation; locked dependencies and CI |
| Agent workflow | `langgraph`, `langgraph-checkpoint-postgres` | Explicit nodes/branches, shared frozen evidence, and persistent session checkpoints |
| Model provider | NVIDIA NIM / `deepseek-ai/deepseek-v4.1-flash` through a thin `httpx` client | Bounded model/tool loops, validated typed outputs and usage logging; migrate the current OpenRouter adapter |
| Contracts | `pydantic`, `pydantic-settings` | Validate reports, scenarios, forecasts, allocation proposals, and configuration |
| Business storage | PostgreSQL, `sqlalchemy` 2.x, `psycopg`, `alembic` | Evidence, jobs, queue, forecasts, reservations, orders, and versioned migrations |
| Periodic triggers | APScheduler 3.x | One scheduler enqueues collection/session/settlement jobs; database deduplication controls execution |
| APIs and feeds | `httpx`, `feedparser`, `beautifulsoup4` | Bounded API/RSS retrieval and parsing of authorized accessible content |
| Broker/data | Existing Alpaca REST adapter; optional pinned `alpaca-py` transport | Paper account, holdings, timestamped quotes/bars, calendar and future order lifecycle |
| News discovery | Pinned `yfinance` | Stock news/press-release leads and shared macro search, with local date/relevance checks |
| Deeper research | Pinned AgentReach and selected underlying backends | Typed search/page/approved-X/transcript adapters; no arbitrary model-generated shell |
| Persistent research memory | PostgreSQL full-text search, event/evidence tables; optional later `pgvector` | Instrument/event/time retrieval first; graph checkpoints remain separate |
| Owner interface | `textual` | One four-pane terminal for positions, selection focus, research chat and portfolio/performance |
| Evaluation | `pandas`, `numpy`, `scikit-learn` | Prospective forecast settlement, return/drawdown summaries, and calibration |
| Verification | `pytest`, `pytest-asyncio`, `ruff` | Contract, temporal, recovery, reservation, and execution checks |

Create and commit a resolved dependency lock during implementation. Do not copy an upstream's unconstrained dependency list or mix APScheduler 3.x examples with its different development API. Keep graph checkpoint storage distinct from the financial ledger.

## Other viable routes

| Route | Fit | Trade-off | Decision |
| --- | --- | --- | --- |
| Custom Python/LangGraph | Best fit with the current Python plan, explicit debate rounds, and Python evaluation | We implement connector contracts and durable broker lifecycle | Recommended prototype |
| Adapt TradingAgents/TradingCrew | Useful existing analyst/debate or broker/UI components | Existing roles, debate order, source selection, memory, and execution must be audited and adapted | Run a pinned spike before importing code |
| TypeScript/Mastra + PostgreSQL | Coherent alternative for a TypeScript-first team; agents/tools and explicit workflows | Translate Python contracts/evaluation and implement the same broker/reservation guarantees | Alternative, not a second parallel runtime |
| Python + Temporal for durable jobs | Useful when distributed worker recovery and scheduling exceed the simple queue | Adds another service and replay/activity discipline; broker idempotency still required | Later operational upgrade |

Select one orchestration route. Framework memory does not replace the evidence/position ledger, and no framework by itself supplies broker safety or calibrated probabilities.

## Initial model experiment

The owner selected **NVIDIA NIM with DeepSeek V4.1 Flash** on 2026-10-10. Start
with `deepseek-ai/deepseek-v4.1-flash` across every role and the chatbot, preserving
distinct specialist instructions and source permissions. This supersedes the
OpenRouter/Gemini baseline; the current runnable client still needs migration.

See [model provider](model-provider.md) for the endpoint, private credential and
acceptance checks. Verify native tool calls and structured-output support on the
exact endpoint; use JSON Schema constraints only where supported and validate
locally. Record provider, requested/returned model, prompt/schema versions,
reasoning settings, retries, token usage and the separate billing basis. Later
model comparisons require an explicit experiment; confidence is not calibrated
merely because the output is fluent.

## Proposed repository modules

| Planned path | Ownership |
| --- | --- |
| `src/tradebot/config/` | Watchlist, source whitelist, model settings, risk and operating budgets |
| `src/tradebot/connectors/` | Alpaca news/quotes, X, SEC, IR/RSS, web search, and optional macro APIs |
| `src/tradebot/evidence/` | Normalization, versions, event grouping, cutoff retrieval, and coverage |
| `src/tradebot/agents/` | Four analysts, internal lead stage, Bull/Bear, Orchestrator, and Allocator |
| `src/tradebot/workflows/` | Graph nodes, fair debate queue, stage checkpoints, and session recovery |
| `src/tradebot/portfolio/` | Position cases, deterministic sizing, cash/risk ledger, and policy enforcement |
| `src/tradebot/execution/` | Paper adapter, durable order intents, submission reconciliation, and protections |
| `src/tradebot/storage/` and `migrations/` | Database repositories and migrations |
| `src/tradebot/terminal.py`, `service.py`, `cli.py` | Single-window terminal and internal application services |
| `tests/` | Offline fixtures and separately enabled provider/paper integration checks |

The initial implementation currently uses flat modules; planned package splits, Alembic, distributed jobs and execution/checkpointer services remain later work.

## Primary references

- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) and [checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)
- [NVIDIA NIM DeepSeek V4.1 Flash](https://build.nvidia.com/deepseek-ai/deepseek-v4.1-flash)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
- [SQLAlchemy](https://docs.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [Psycopg](https://www.psycopg.org/psycopg3/docs/)
- [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [feedparser](https://feedparser.readthedocs.io/en/latest/), [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [APScheduler 3.x](https://apscheduler.readthedocs.io/en/3.x/userguide.html)
- [Mastra workflows](https://mastra.ai/docs/workflows/overview), [Temporal activities](https://docs.temporal.io/activities)
- [Alpaca Python SDK](https://alpaca.markets/sdks/python/api_reference/trading/trading-client.html)
- [Textual](https://textual.textualize.io/) and [terminal interaction testing](https://textual.textualize.io/guide/testing/)

## Related pages

- [Connector implementation](connector-implementation.md)
- [Agent runtime](agent-runtime.md)
- [Persistence and contracts](persistence-and-contracts.md)
- [Deployment and costs](deployment-and-costs.md)
- [Implementation backlog](implementation-backlog.md)

