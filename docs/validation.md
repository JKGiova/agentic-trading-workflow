# Validation and confidence evaluation

[Wiki home](README.md) · [Project overview](../README.md)

Use chronological train/development and held-out evaluation periods where applicable. Freeze strategy rules, prompts, and configuration before evaluating a held-out period. Compare against a relevant passive benchmark and a simple strategy without LLM analysis.

Measure net returns, maximum drawdown, risk-adjusted performance, exposure, concentration, turnover, trading costs, data/model costs, and operational failures. Report results by period and market regime.

Historical news must be available as of each simulated decision, including filing delays and revisions. Modern LLMs may already know outcomes of historical events; historical replay therefore requires leakage analysis and prospective paper testing.

Compare the full workflow against the same analyst inputs without debate, and against a simpler single-analysis baseline. Report whether debate improves outcomes after its extra model cost and latency. More fluent arguments or agreement do not establish better trades.

Compare confidence/downside allocations with fixed-size allocations under identical cash and risk limits. Freeze debate queue/cost policy, uncertainty diagnostics, payoff/stress methods, and sizing parameters before held-out evaluation; report sensitivity across predeclared values without tuning on evaluation results. Assess net performance and losses by both probability band and invested capital, not just the frequency of winning trades.

Evaluate `p_initial` and `p_final` calibration separately. Compare pre/post-debate accuracy on identical completed debates with available initial/final estimates, report all initially analyzed candidates and rejection rates, and measure whether large confidence increases have evidence support and predictive value. Do not assume debate improves calibration. Evaluate predicted payoff magnitudes, scenario frequencies, net-return forecast error, stressed-loss exceedances, compounding, drawdown, and dependence across trades; winning frequency alone does not validate expected revenue.

Settle both benchmark-outperformance and positive-net-return forecasts separately. Settle all recorded forecasts, including untraded and rejected stocks, where data permits. Measure Brier score, reliability by confidence band with sample counts, abstention/coverage, direction accuracy, cost-adjusted outcomes, and drawdown. Overlapping forecasts and repeated evidence are dependent observations; use suitable chronological validation and do not report them as independent trials.

Routing checks must cover low initial confidence, negative initial expected return, and low initial score still entering debate; unsupported initial estimates triggering bounded verification rather than automatic screening; no confidence/score queue priority; fair queue carryover and refreshing stale proposals; missing final estimates deferring investment; explicit research rejection; preserved records; inconsistent scenario probabilities, missing tail cases, duplicate cost subtraction, invalid/zero diagnostic denominators, and attempts to override research verdicts or risk limits. Holdings remain reviewed and risk-reducing actions remain available.

Budget checks must cover final confidence/downside sizing rather than initial or maximum confidence, missing/expired confidence, monotonic sizing with other inputs fixed, reinforcement against existing and pending exposure, simultaneous reservations, cash-reserve preservation, capital/sector/risk/session caps, rounding and broker minimums, cost allowances, partial-fill reservation conversion, confirmed cancellation release, and prevention of double-counting broker reservations. Lower confidence must not block a justified risk-reducing exit.

Operational tests must cover missing feeds, empty results versus failed searches, forged coverage claims, watchlist removals with remaining holdings, duplicate events, unsupported confidence, debate convergence without new evidence, unresolved objections, exceeded budgets, malformed proposals, unauthorized instruments, stale quotes, simultaneous sessions, rejected orders, partial fills, timeout-after-submit, unavailable exit proceeds, and restart recovery.

Implementation checks are assigned to T0-T9 in the [concrete backlog](implementation-backlog.md). Use fixtures for routine CI and a test PostgreSQL instance for concurrency; separately enabled source/paper integrations record actual access and cost. No implementation tests or paper sessions have run as part of this documentation research.

## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [Opportunity analysis](opportunity-analysis.md)
- [New-entry debate](new-entry-debate.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Budget management](budget-management.md)
- [Implementation backlog](implementation-backlog.md)
- [Implementation plan](PLAN.md)
