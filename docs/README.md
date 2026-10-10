# Agentic Trading Workflow Wiki

[Project overview](../README.md)

This is the versioned project wiki. Each page covers one part of the design; implementation milestones and current progress are tracked separately. All content is in English.

**Status: v0.1 research-only terminal.** Start with the [CLI guide](cli.md),
[development status](development-status.md) and [codebase map](codebase-map.md).
The topic pages retain the full target; execution and prospective validation remain pending.

## Implementation specifications

The proposed build is Python/LangGraph with PostgreSQL, NVIDIA NIM / DeepSeek V4.1 Flash model calls, explicit source adapters, and an Alpaca paper pilot. Model-provider migration from the current OpenRouter client is pending. Alternatives and unverified access requirements are documented rather than silently selected.

| Page | Purpose |
| --- | --- |
| [Continuous analyst cycles](continuous-analysis.md) | X-hour news loops, analyst collaboration, report boundaries, every-stock debates and Portfolio Manager |
| [Agent control loop](agent-control-loop.md) | TradingAgents comparison, actual agent contracts, durable task loops and implementation slices |
| [Model provider](model-provider.md) | NVIDIA NIM / DeepSeek V4.1 Flash selection, connection contract, capability checks and pending migration |
| [Research workflow](research-workflow.md) | TradingAgents-style analyst tool loops, event follow-up, cutoff revisions and a CES example |
| [Memory and retrieval](memory-and-retrieval.md) | Persistent checkpoints, evidence/event/thesis memory, SQL retrieval and outcome lessons |
| [Selected provider plan](provider-plan.md) | Alpaca, yfinance and AgentReach responsibilities, boundaries and access checks |
| [Implementation stack](implementation-stack.md) | Concrete packages, framework alternatives, model candidates, and planned modules |
| [Connector implementation](connector-implementation.md) | News, approved X authors, SEC/IR, publisher search, quotes, and capability proofs |
| [Trading connectors](trading-connectors.md) | Current read-only subset, planned broker interfaces, intent lifecycle, protection and acceptance tests |
| [Agent runtime](agent-runtime.md) | Graph stages, typed tools, structured output, budgets, and side-effect recovery |
| [Persistence and contracts](persistence-and-contracts.md) | Logical tables, contracts, indexes, leases, transactions, and idempotency |
| [Deployment and costs](deployment-and-costs.md) | Worker topology, configuration, reference pricing, and workload-derived costs |
| [Implementation backlog](implementation-backlog.md) | Ordered T0-T9 deliverables and acceptance results |

## Start here

Read the architecture, analyst team, forecasts, opportunity analysis, position management, debate, Portfolio Manager, and budget management pages in that order. Use the implementation plan to choose the first development milestone.

## Pages

| Page | Purpose |
| --- | --- |
| [Architecture and scope](architecture.md) | Stock universe, eight agent roles, component ownership, and proposed stack |
| [Analyst team and mandatory research](analysis-team.md) | Market, financial, company, and social analysts; held-stock coverage requirements |
| [Forecasts and confidence](forecasts-and-confidence.md) | Initial/revised confidence, outcome definitions, research decisions, and calibration |
| [Opportunity analysis](opportunity-analysis.md) | Confidence, payoff, costs, uncertainty, and downside examined inside debate |
| [Existing-position management](position-management.md) | Reinforce, reduce, close, hold, and thesis comparison |
| [Stock report debate](new-entry-debate.md) | Bull/Bear roles, bounded rounds, verification, and revised confidence |
| [Portfolio Manager](portfolio-allocator.md) | Agent assessment of confidence, position choice, investment, and tool boundaries |
| [Budget management](budget-management.md) | Agent decisions, confidence/downside investment sizing, shared capital limits, and reservations |
| [Session workflow](session-workflow.md) | Scheduling, portfolio reconciliation, action sequencing, and proposal contracts |
| [Data and sources](data-and-sources.md) | Approved publications and X accounts, timestamps, deduplication, and memory |
| [Risk and execution](risk-and-execution.md) | Deterministic limits, protective orders, idempotency, and paper execution |
| [Validation](validation.md) | Prospective evaluation, debate comparisons, and operational checks |
| [Implementation plan](PLAN.md) | Milestones, acceptance criteria, and open decisions |
| [Development status](development-status.md) | What is documented, what is implemented, and the next milestone |
| [Source research](research.md) | Recommended repositories, their gaps, and primary documentation |

## Current design decisions

- Selected target: Alpaca broker/market data, yfinance primary news discovery, and AgentReach-backed bounded research; existing adapters remain unchanged until migration.
- Next development focuses on evidence/event memory, retrieval, analyst tool loops and recoverable sessions; see the workflow and memory pages.

- Four specialist analysts continuously process market, financial, company and authorized social news within X-hour cycles, preserving original findings, collaboration and dissent.
- At each deadline, freeze one report per analyzed stock and create a debate obligation for every report. Research continues in the next cycle while decision work completes.
- Every open position requires fresh, recorded searches and an explicit coverage status.
- Stock forecasts have an explicit horizon and outcome; model confidence is labeled uncalibrated until validated.
- Existing positions can be reinforced, reduced, closed, or held unchanged.
- The analyst team supplies initial confidence, payoff scenarios, and gaps directly to debate; no numerical prefilter selects proposals.
- Bull/Bear directly assess the probability/payoff trade-off; the Orchestrator records revised confidence, scenarios, and a research verdict.
- A separate Portfolio Manager (the target name for the existing Allocator role) analyzes revised confidence, measured volatility, cash, pending commitments and portfolio risk, then chooses actions and investment.
- Debate and Allocator judgments decide whether exposure is justified; final confidence scales investment within a stressed-loss budget; a shared budget ledger enforces cash reserves, pending commitments, and risk caps.
- Risk limits and execution are deterministic services, with paper trading as the first target.

## Documentation layout

The root README is the entry point. Design pages live under `docs/`, with `PLAN.md` for milestones and `development-status.md` for actual progress, following the structure of the Moonlight tvOS PyroWave workspace.

