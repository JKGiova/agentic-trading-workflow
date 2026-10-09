# Implementation plan

[Wiki home](README.md) · [Project overview](../README.md)

| Milestone | Deliverable | Acceptance criteria |
| --- | --- | --- |
| 0. Scope and upstream spike | Select watchlist, primary forecast horizon, benchmark/cost hurdle, sources, model budgets, and starting architecture | Run a paper-only spike; document source access and gaps; no live execution |
| 1. Research and coverage | Connectors, durable evidence, event deduplication, and enforced held-stock lookup matrix | Every holding has a recorded task per category; distinguish no results from failure; recover collection without gaps |
| 2. Analyst team and forecasts | Four specialist reports and Decision Manager synthesis | Selected stocks have forecasts or explicit incomplete status; sources are valid; contradictory evidence is retained; confidence has a defined target and calibration label |
| 3. Existing-position review | Thesis comparison and reinforce/reduce/close/hold proposals | Every holding is reviewed or deferred; fresh coverage is enforced; no automatic averaging down or fabricated search completion |
| 4. Two-agent entry debate | Independent openings, bounded challenges, verified rebuttals, and judge verdicts | Both cases are retained; unresolved material claims defer approval; lookup and round budgets are enforced |
| 5. Portfolio risk and paper execution | Net action plan, deterministic gates, broker reconciliation, protective orders, and monitoring | No contradictory or duplicate orders; pending exposure and unavailable exit proceeds count; partial fills and restarts are handled |
| 6. Evaluation and confidence | Prospective outcomes, calibration reports, and controlled comparisons | Measure full workflow versus no-debate and single-analysis baselines using identical data, costs, universe, and horizons |
| 7. Dashboard and operations | Stock recaps, holding review table, debate verdicts, coverage health, audit history, costs, and kill switch | Incomplete coverage, stale inputs, dissent, deferred proposals, and execution state are visible |
| 8. Live-readiness review | Separate decision about a limited live deployment | Review requirements, operating procedures, evaluation evidence, and broker support; live mode is explicitly disabled by default |

Paper profitability alone is insufficient evidence for deployment. Paper fills can omit liquidity constraints, market impact, and latency-related slippage.

## Open decisions

- Initial selected stocks, exchanges, broker, and stock-level eligibility rules.
- Decision interval X and sessions outside market hours.
- Primary forecast horizon, benchmark, cost hurdle, and settlement-price definition.
- Financial-news providers, primary sources, approved X accounts, and retention rights.
- LLM provider/model per role and total session cost/latency budget.
- Candidate shortlist size and bounded research/rebuttal budgets.
- Exact exposure, daily-loss, liquidity, freshness, and protection limits.
- Minimum evaluation evidence required before enabling any calibrated probability.
- Preferred upstream starting point after the technical spike.

Initial design choices already proposed: four analyst roles, a Bull/Bear pair, one Decision Manager role, mandatory research of all holdings, `HOLD` as an unchanged-exposure option, five-trading-day primary forecasts, and paper-only execution.

## Related pages

- [Development status](development-status.md)
- [Architecture](architecture.md)
- [Source research](research.md)
