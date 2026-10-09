# Validation and confidence evaluation

[Wiki home](README.md) · [Project overview](../README.md)

Use chronological train/development and held-out evaluation periods where applicable. Freeze strategy rules, prompts, and configuration before evaluating a held-out period. Compare against a relevant passive benchmark and a simple strategy without LLM analysis.

Measure net returns, maximum drawdown, risk-adjusted performance, exposure, concentration, turnover, trading costs, data/model costs, and operational failures. Report results by period and market regime.

Historical news must be available as of each simulated decision, including filing delays and revisions. Modern LLMs may already know outcomes of historical events; historical replay therefore requires leakage analysis and prospective paper testing.

Compare the full workflow against the same analyst inputs without debate, and against a simpler single-analysis baseline. Report whether debate improves outcomes after its extra model cost and latency. More fluent arguments or agreement do not establish better trades.

Settle all recorded forecasts, including untraded and rejected stocks, where data permits. Measure Brier score, reliability by confidence band with sample counts, abstention/coverage, direction accuracy, cost-adjusted outcomes, and drawdown. Overlapping forecasts and repeated evidence are dependent observations; use suitable chronological validation and do not report them as independent trials.

Operational tests must cover missing feeds, empty results versus failed searches, forged coverage claims, watchlist removals with remaining holdings, duplicate events, unsupported confidence, debate convergence without new evidence, unresolved objections, exceeded budgets, malformed proposals, unauthorized instruments, stale quotes, simultaneous sessions, rejected orders, partial fills, timeout-after-submit, unavailable exit proceeds, and restart recovery.

## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [New-entry debate](new-entry-debate.md)
- [Implementation plan](PLAN.md)
