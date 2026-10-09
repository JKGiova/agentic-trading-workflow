# Implementation plan

[Wiki home](README.md) · [Project overview](../README.md)

| Milestone | Deliverable | Acceptance criteria |
| --- | --- | --- |
| 0. Scope and upstream spike | Select watchlist, primary forecast horizon, benchmark/cost hurdle, trade-success target, debate budget and fair queue policy, Analyst Lead, investment/risk budgets, sources, model budgets, and starting architecture | Run a paper-only spike; document source access and gaps; no live execution |
| 1. Research and coverage | Connectors, durable evidence, event deduplication, and enforced held-stock lookup matrix | Every holding has a recorded task per category; distinguish no results from failure; recover collection without gaps |
| 2. Analysis and direct handoff | Four independent reports and Analyst Lead confidence/payoff synthesis | Probability/payoffs share a horizon and cost definition; missing estimates are explicit; no numerical filter skips debate; all holdings remain researched |
| 3. Holding cases and Allocator role | News/thesis comparison and separate Portfolio Allocator holding decisions | Every holding is reviewed or deferred; hold/reduce/close remain available independently of entry debate; reinforcement requires debate and investment/risk review; no automatic averaging down |
| 4. Direct debate and revised confidence | Fair queue, Bull/Bear probability/payoff analysis, verification, Orchestrator `p_final`, and research verdict | Initial confidence/score does not select or order proposals; missing initial estimates may be investigated; verdicts are reasoned; pending/deferred cases and both records are preserved |
| 5. Investment, budget, and paper execution | Allocator confidence assessment, position/investment proposals, `p_final` sizing tools, shared budget ledger, deterministic validation, and paper execution | Allocator cannot override research verdicts or probabilities; only revised confidence/downside size additions; reinforcements use total exposure; reservations prevent overspending; pending commitments and unavailable proceeds count; partial fills/restarts handled |
| 6. Evaluation and confidence | Stage-specific probability/payoff outcomes, calibration reports, and controlled comparisons | Compare confidence/downside sizing with fixed sizing and no-trade baselines; compare full workflow versus no-debate and single-analysis baselines using identical data, costs, universe, and horizons |
| 7. Dashboard and operations | Stock recaps, holding review table, debate verdicts, coverage health, audit history, both confidence/payoff stages, opportunity scores, and revision reasons, Allocator rationale, budget reservations, allocation reasons, costs, and kill switch | Incomplete coverage, stale inputs, dissent, deferred proposals, and execution state are visible |
| 8. Live-readiness review | Separate decision about a limited live deployment | Review requirements, operating procedures, evaluation evidence, and broker support; live mode is explicitly disabled by default |

Paper profitability alone is insufficient evidence for deployment. Paper fills can omit liquidity constraints, market impact, and latency-related slippage.

## Concrete work packages

The [ordered backlog](implementation-backlog.md) maps this roadmap into implementable deliverables:

| Roadmap milestone | Work packages |
| --- | --- |
| 0. Scope/upstream spike | T0 source-access proof, pinned upstream comparison, and dependency lock |
| 1. Research/coverage | T1 contracts/storage, T2 connectors, T3 jobs and mandatory coverage |
| 2. Analyst team | T4 independent reports and internal lead synthesis |
| 3. Existing holdings | T6 Allocator holding review and position cases |
| 4. Direct debate | T5 fair queue, bounded rounds, Orchestrator judgment |
| 5. Paper execution | T6 sizing preview, T7 reservations/intents/monitor |
| 6. Evaluation | T8 forecast settlement and prospective comparisons |
| 7. Dashboard/operations | T9 API/UI, supervision, and recovery |
| 8. Live readiness | Separate later decision; prototype live mode remains unsupported |

The proposed route is [Python/LangGraph and PostgreSQL](implementation-stack.md), with [explicit connectors](connector-implementation.md), [typed tool boundaries](agent-runtime.md), and [a transactional business ledger](persistence-and-contracts.md). Compare actual usage with [cost assumptions](deployment-and-costs.md); public prices are not measured project costs.

## Open decisions

- Initial selected stocks, exchanges, broker, and stock-level eligibility rules.
- Decision interval X and sessions outside market hours.
- Primary forecast horizon, benchmark, cost hurdle, and settlement-price definition.
- Financial-news providers, primary sources, approved X accounts, and retention rights.
- LLM provider/model per role and total session cost/latency budget.
- Maximum debates per session, fair queue policy, and bounded research/rebuttal budgets.
- Investable capital, minimum cash reserve, debate queue/cost budget, maximum position weight, session deployment cap, and allocation tie-break policy.
- Conditional-payoff and tail-scenario methods, uncertainty diagnostics, and stressed-loss budget.
- Exact exposure, daily-loss, liquidity, freshness, and protection limits.
- Minimum evaluation evidence required before enabling any calibrated probability.
- Confirm a minimal custom LangGraph build versus selective adaptation of pinned TradingAgents after T0.

Initial design choices already proposed: four analyst roles with an internal lead, a Bull/Bear pair, one Orchestrator, and a separate Portfolio Allocator, mandatory research of all holdings, `HOLD` as an unchanged-exposure option, five-trading-day primary forecasts, and paper-only execution.

## Related pages

- [Implementation backlog](implementation-backlog.md)
- [Development status](development-status.md)
- [Architecture](architecture.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Budget management](budget-management.md)
- [Source research](research.md)
