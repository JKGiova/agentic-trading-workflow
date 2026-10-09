# Opportunity screening: confidence, potential, and downside

[Wiki home](README.md) · [Project overview](../README.md)

Deciding whether to spend research/debate time on a stock must combine the probability of success with the size of potential gains and losses. Confidence alone is neither an opportunity score nor an expected return. All selected stocks receive initial research and all holdings receive mandatory review; this screen routes proposed additions to debate.

## Required estimates

The analysis team publishes an initial scenario distribution and `p_initial`. After debate, the Orchestrator publishes a revised distribution and `p_final`. For each stage record:

| Input | Definition |
| --- | --- |
| Probability | Probability of positive net total return over the frozen horizon |
| Positive payoff `U` | Conditional average positive net return, not the most optimistic price target |
| Negative payoff `D` | Magnitude of the conditional average nonpositive net return |
| Full scenarios | Mutually exclusive cases with probabilities, net returns, mechanisms, and evidence; include adverse/tail cases |
| Stressed loss fraction `L_stress` | Conservative downside estimate including gaps and liquidity effects; positive, finite, and at least the modeled average loss |
| Uncertainty penalty `h` | Predeclared nonnegative return haircut for estimate uncertainty, with policy and rationale |
| Horizon and costs | Same holding period, reference-price basis, fees, spread/slippage, and outcome definition |
| Quality and feasibility | Source coverage, calibration status, liquidity, eligibility, and price freshness |

Use percentage returns per unit of invested capital, not raw share price or euros per share. A €3 share is not inherently more attractive than a €300 share. Estimate volatility, downside, and liquidity independently rather than inferring them from price.

## Expected value and risk-adjusted score

For a simplified two-bucket distribution:

```text
expected_net_return = p * U - (1 - p) * D
robust_edge = expected_net_return - h
opportunity_score = robust_edge / L_stress
```

`U` and `D` already include estimated trading costs; do not subtract those costs again. The probability must refer to the same net-return event. In the implementation, prefer `expected_net_return = sum(q_i * net_return_i)` over an explicit scenario distribution, with nonnegative probabilities summing to one. The sum of probabilities of positive-return cases must agree with the confidence record.

Require `L_stress > 0`; missing/zero denominators or unsupported payoffs defer the proposal rather than creating an infinite score. The uncertainty haircut is a policy assumption, not a statistical confidence interval. Stressed loss is not a guaranteed maximum loss.

At both stages, pass only if:

- Evidence, confidence, payoff estimates, and costs are complete and policy-eligible.
- `robust_edge > min_edge_stage`, with a nonnegative configured minimum.
- `opportunity_score > min_score_stage`, with a nonnegative configured minimum.
- Stressed downside, liquidity, and other hard eligibility/risk constraints pass.

There is no universal 60% or similar probability-only rejection rule. Lower confidence can pass with sufficiently favorable supported payoffs; higher confidence can fail when losses outweigh gains. Invalid probabilities still defer exposure. Passing is permission for the next review stage, not a prediction of profit or an order.

## Illustrative comparison

These are invented net-of-cost assumptions over the same horizon, with `h = 0` for arithmetic illustration only:

| Candidate | Confidence | Average gain `U` | Average loss `D` | Expected net return | Assumed stressed loss | Opportunity score |
| --- | --- | --- | --- | --- | --- | --- |
| A: lower confidence, larger potential | 60% | 20% | 10% | 8.0% | 15% | 0.533 |
| B: higher confidence, smaller potential | 80% | 3% | 7% | 1.0% | 10% | 0.100 |
| C: high confidence, unfavorable downside | 90% | 1% | 20% | -1.1% | 30% | -0.037 |

Candidate A can rank above B despite lower confidence. C fails a positive-edge requirement despite high confidence. Real routing also applies uncertainty haircuts, threshold policy, source quality, liquidity, and tail-risk limits; these examples are not estimates for NVIDIA or any named stock.

## Debate routing and revised review

1. The analyst team computes the initial distribution, confidence, edge, and score.
2. The deterministic initial opportunity gate rejects additions with valid but inadequate edge/score or hard-risk failure. Missing inputs defer them.
3. Rank passing candidates by descending initial opportunity score, then robust edge, evidence-quality tier, and stock ID. Respect the bounded debate budget; excess candidates defer.
4. Bull/Bear challenge probability, average payoffs, assumed downside, novelty, costs, and uncertainty. Inflated upside targets do not count as evidence.
5. The Orchestrator records revised probabilities and scenario payoffs, explains changes, and recomputes final edge/score. A final opportunity gate prevents a probability-only decision from contradicting the initial screen.
6. The Portfolio Allocator analyzes the revised record and chooses the position and investment within [budget constraints](budget-management.md). Initial and final records remain immutable.

Do not automatically debate every volatile stock, expand the watchlist, or treat repeated sessions as independent opportunities. Forecasts of different horizons cannot be ranked by raw expected return; the prototype uses one horizon and defers incompatible comparisons.

## Expected return is not guaranteed long-run revenue

The law of large numbers concerns averages under specified probabilistic assumptions, not guaranteed earnings from a finite trading account. Model estimates can be wrong, market regimes change, trades can be correlated, and large losses can exhaust capital before an average stabilizes.

Equal arithmetic expected returns do not imply equal compound growth or drawdown. For example, +50% followed by -50% leaves 75% of the starting capital. Evaluate net compounding, tail losses, portfolio dependence, and risk of ruin prospectively; do not justify unlimited size or repeated bets by the law of large numbers.

## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [Bull/Bear debate](new-entry-debate.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Budget management](budget-management.md)
- [Validation](validation.md)
- [Primary references](research.md)
