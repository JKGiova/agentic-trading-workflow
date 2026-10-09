# Stock forecasts and two-stage confidence

[Wiki home](README.md) · [Project overview](../README.md)

The analysis team produces the first stock forecast and confidence. The Orchestrator produces a separate revised confidence after Bull/Bear debate. Both records are immutable, evidence-backed estimates; the revised estimate may be lower, unchanged, or higher.

## Confidence ownership and gates

| Stage | Owner | Output | Consequence |
| --- | --- | --- | --- |
| Initial analysis | Analyst Lead synthesizing four independent reports | `p_initial`, evidence, scenarios, uncertainty, and calibration status | Valid `p_initial <= p_initial_min` directly rejects added exposure; no debate |
| Debate review | Orchestrator reviewing Bull/Bear cases and verified rebuttals | `p_final`, research verdict, revision reasons, unresolved objections, and calibration status | Valid `p_final <= p_final_min` rejects added exposure |
| Investment decision | Separate Portfolio Allocator agent | Confidence assessment, position action, desired exposure, and investment proposal | Use `p_final` for eligible additions, within deterministic budget/risk limits |

Missing, expired, malformed, or unsupported confidence defers new exposure. A research `REJECT` or `DEFER` cannot be overridden by a high number. Passing the first gate guarantees neither debate approval nor investment.

## Measurable outcome

Both `p_initial` and `p_final` estimate the same event: a long position entered at the recorded executable reference price achieves a positive total return after estimated round-trip fees and slippage over the declared horizon. Reinforcement evaluates forward return from today's price, not the original entry price.

Freeze stock, price snapshot, start/settlement times, exchange calendar, cost assumptions, evidence cutoff, and outcome ID for the comparison. If verified research changes the outcome definition or materially changes the reference-price basis, invalidate the proposal and start a new versioned analysis and gate; do not present incomparable estimates as a confidence revision. Later news queues a new review.

Maintain a separate benchmark-outperformance forecast: total return exceeds the configured benchmark return by a predeclared cost hurdle. Outperforming a falling benchmark can still lose money; this probability cannot replace trade confidence.

## Forecast contract

| Field | Meaning |
| --- | --- |
| Stock, as-of time, and outcome ID | Instrument, evidence cutoff, price, horizon, costs, and settlement rule |
| News summary | Recap of market, financial, company, and authorized social evidence |
| Direction | Bullish, neutral, bearish, or insufficient evidence |
| Initial confidence | `p_initial`, analyst-team record, evidence, and calibration label |
| Revised confidence | Optional `p_final`, Orchestrator record, and calibration label; absent when debate was skipped |
| Revision explanation | Specific challenges and verified facts that changed or preserved confidence |
| Evidence quality | Strong, mixed, weak, or incomplete, with source coverage |
| Scenarios and expected net payoff | Upside/central/downside mechanisms, payoffs, assumptions, and invalidators |
| Supporting/opposing sources | Evidence IDs, URLs, publication and acquisition times |
| Disagreement and missing data | Analyst conflicts, unresolved debate objections, and failed searches |
| Expiry and gate results | Refresh deadline, policy version, both thresholds, and routing reason |

Agreement and debate persuasiveness do not establish probability. Neither the lead nor Orchestrator may average agent votes, count repeated headlines, or increase confidence to unlock funding. The Allocator evaluates support and consistency but cannot invent a third probability or rewrite either estimate.

## Calibration and evaluation

Initially label each estimate **model estimate — uncalibrated**, permit `INSUFFICIENT_EVIDENCE`, and use estimates only in explicit paper experiments. Predictive confidence and evidence quality remain separate.

Evaluate `p_initial` and `p_final` separately with prospective outcomes, held-out chronological calibration, Brier scores, reliability curves, sample counts, and baselines. The final estimate exists only for first-gate survivors; compare confidence revisions on that same subset and report screening coverage to avoid selection bias.

If calibration is enabled, retain raw and calibrated values separately. The policy fixes which policy-eligible value each gate and sizing tool consumes; agents cannot choose the more favorable one. Live eligibility requires approved validation for each stage's model, prompt, horizon, and data regime. Revalidate after material changes.

Settle all available forecasts, including rejected/untraded proposals, independently of actual exits. Closing a trade does not erase or redefine the original forecast.

## Dashboard summary

Show news recap, horizon, initial confidence and first-gate result, debate status, revised confidence and revision explanation, second-gate result, Allocator action, target/final investment, calibration labels, disagreement, and expiry. Show skipped debate and missing final confidence explicitly.

## Related pages

- [Analysis team](analysis-team.md)
- [Bull/Bear debate](new-entry-debate.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Budget management](budget-management.md)
- [Validation](validation.md)
