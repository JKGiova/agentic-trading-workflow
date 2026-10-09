# Implementation stack and build options

[Wiki home](README.md) · [Project overview](../README.md)

Reviewed **2026-10-09**. These are concrete implementation proposals, not installed services. Preserve the eight AI roles, direct debate without a numerical prefilter, independent Allocator, mandatory holding research, and paper-first execution.

## Recommended first implementation

Build a small Python application with an explicit LangGraph workflow and PostgreSQL business ledger. Study TradingAgents at a pinned revision; adapt selected components only after a technical spike. Keep source collection, decision sessions, and order monitoring as separate workers.

| Responsibility | Proposed tool/package | How we use it |
| --- | --- | --- |
| Runtime | Python 3.13, virtual environment | One language for agents, data, risk, and evaluation; verify the dependency lock on the target OS |
| Agent workflow | `langgraph`, `langgraph-checkpoint-postgres` | Explicit nodes/branches, shared frozen evidence, and persistent session checkpoints |
| Model gateway | OpenRouter through a thin `httpx` client | Provider-independent paid model calls, bounded tool loops, JSON Schema output, usage logging |
| Contracts | `pydantic`, `pydantic-settings` | Validate reports, scenarios, forecasts, allocation proposals, and configuration |
| Business storage | PostgreSQL, `sqlalchemy` 2.x, `psycopg`, `alembic` | Evidence, jobs, queue, forecasts, reservations, orders, and versioned migrations |
| Periodic triggers | APScheduler 3.x | One scheduler enqueues collection/session/settlement jobs; database deduplication controls execution |
| APIs and feeds | `httpx`, `feedparser`, `beautifulsoup4` | Bounded API/RSS retrieval and parsing of authorized accessible content |
| Broker/data | `alpaca-py`; direct news REST adapter | Paper account, holdings, calendar, quotes, orders, and order updates |
| Service API | `fastapi`, `uvicorn` | Typed status, evidence, session, portfolio, and policy endpoints |
| First dashboard | `streamlit` | Read the API and show research, confidence, verdicts, allocations, coverage, and costs |
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

Start with one paid model across all roles to make the first comparison reproducible:

- Baseline candidate: `google/gemini-2.5-flash` through OpenRouter.
- Comparison candidate: `anthropic/claude-sonnet-4.6`, evaluated on the same evidence and contract tasks.
- Later experiment: cheaper analyst/lead calls and a stronger debate/Orchestrator/Allocator model, recording each role's model.

These are available research candidates, not a claim that either predicts stocks reliably. Verify endpoint tool-calling and structured-output support before enabling a model. Use `response_format: json_schema` where supported and require the needed parameters in provider routing; still validate locally. Record provider, model ID, prompt/schema versions, reasoning settings, retries, and billed usage. Do not silently switch models mid-experiment or convert fluent output into calibrated confidence.

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
| `src/tradebot/api/`, `dashboard/` | API and initial UI |
| `tests/` | Offline fixtures and separately enabled provider/paper integration checks |

These paths are planned and do not yet contain implementation.

## Primary references

- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) and [checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)
- [OpenRouter structured output](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
- [SQLAlchemy](https://docs.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [Psycopg](https://www.psycopg.org/psycopg3/docs/)
- [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [feedparser](https://feedparser.readthedocs.io/en/latest/), [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [APScheduler 3.x](https://apscheduler.readthedocs.io/en/3.x/userguide.html)
- [Mastra workflows](https://mastra.ai/docs/workflows/overview), [Temporal activities](https://docs.temporal.io/activities)
- [Alpaca Python SDK](https://alpaca.markets/sdks/python/api_reference/trading/trading-client.html)
- [FastAPI](https://fastapi.tiangolo.com/) and [Streamlit](https://docs.streamlit.io/)

## Related pages

- [Connector implementation](connector-implementation.md)
- [Agent runtime](agent-runtime.md)
- [Persistence and contracts](persistence-and-contracts.md)
- [Deployment and costs](deployment-and-costs.md)
- [Implementation backlog](implementation-backlog.md)
