# Implementation plan

[Wiki home](README.md) · [Project overview](../README.md)

| Milestone | Deliverable | Acceptance criteria |
| --- | --- | --- |
| 0. Scope and upstream spike | Select watchlist, primary forecast horizon, benchmark/cost hurdle, trade-success target, initial/final confidence thresholds, Analyst Lead, investment/risk budgets, sources, model budgets, and starting architecture | Run a paper-only spike; document source access and gaps; no live execution |
| 1. Research and coverage | Connectors, durable evidence, event deduplication, and enforced held-stock lookup matrix | Every holding has a recorded task per category; distinguish no results from failure; recover collection without gaps |
| 2. Analysis and first gate | Four independent reports, Analyst Lead synthesis, and `p_initial` screening | Initial confidence has a defined target and calibration label; low valid estimates reject additions before debate; missing estimates defer; every holding still gets research/review |
| 3. Holding cases and Allocator role | News/thesis comparison and separate Portfolio Allocator holding decisions | Every holding is reviewed or deferred; hold/reduce/close remain available despite failed addition gates; reinforcement requires both gates and debate; no automatic averaging down |
| 4. Debate and revised confidence | Bull/Bear cases, verification, Orchestrator `p_final`, research verdict, and second gate | Only first-gate survivors enter; both estimates are preserved on the same outcome basis; final confidence may decrease; low final values reject; missing evidence defers; budgets enforced |
| 5. Investment, budget, and paper execution | Allocator confidence assessment, position/investment proposals, `p_final` sizing tools, shared budget ledger, deterministic validation, and paper execution | Allocator cannot override gates or probabilities; only final confidence sizes additions; reinforcements use total exposure; reservations prevent overspending; pending commitments and unavailable proceeds count; partial fills/restarts handled |
| 6. Evaluation and confidence | Stage-specific prospective outcomes, calibration reports, and controlled comparisons | Compare confidence-based sizing with fixed sizing and no-trade baselines; compare full workflow versus no-debate and single-analysis baselines using identical data, costs, universe, and horizons |
| 7. Dashboard and operations | Stock recaps, holding review table, debate verdicts, coverage health, audit history, both confidence stages and revision reasons, Allocator rationale, budget reservations, allocation reasons, costs, and kill switch | Incomplete coverage, stale inputs, dissent, deferred proposals, and execution state are visible |
| 8. Live-readiness review | Separate decision about a limited live deployment | Review requirements, operating procedures, evaluation evidence, and broker support; live mode is explicitly disabled by default |

Paper profitability alone is insufficient evidence for deployment. Paper fills can omit liquidity constraints, market impact, and latency-related slippage.

## Open decisions

- Initial selected stocks, exchanges, broker, and stock-level eligibility rules.
- Decision interval X and sessions outside market hours.
- Primary forecast horizon, benchmark, cost hurdle, and settlement-price definition.
- Financial-news providers, primary sources, approved X accounts, and retention rights.
- LLM provider/model per role and total session cost/latency budget.
- Candidate shortlist size and bounded research/rebuttal budgets.
- Investable capital, minimum cash reserve, initial/final confidence thresholds, maximum position weight, session deployment cap, and allocation tie-break policy.
- Exact exposure, daily-loss, liquidity, freshness, and protection limits.
- Minimum evaluation evidence required before enabling any calibrated probability.
- Preferred upstream starting point after the technical spike.

Initial design choices already proposed: four analyst roles with an internal lead, a Bull/Bear pair, one Orchestrator, and a separate Portfolio Allocator, mandatory research of all holdings, `HOLD` as an unchanged-exposure option, five-trading-day primary forecasts, and paper-only execution.

## Related pages

- [Development status](development-status.md)
- [Architecture](architecture.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Budget management](budget-management.md)
- [Source research](research.md)
