# Opportunity analysis inside the debate

[Wiki home](README.md) · [Project overview](../README.md)

Bull and Bear directly analyze confidence, potential gains, possible losses, costs, uncertainty, and liquidity. Initial confidence, expected return, and opportunity score do not filter or rank proposals before debate. All selected stocks receive initial research; every holding receives mandatory review.

## Estimates to investigate

The analysis team supplies initial scenarios and `p_initial` when supportable; mark missing inputs explicitly. After debate, the Orchestrator publishes a revised distribution and `p_final`. For each stage record:

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

A computed score requires `L_stress > 0`; missing/zero denominators or unsupported payoffs are flagged as unavailable, not converted into an infinite score. These gaps may be investigated during debate, but unresolved gaps prevent investment approval. The uncertainty haircut is a policy assumption, not a statistical confidence interval. Stressed loss is not a guaranteed maximum loss.


These calculations are supporting diagnostics for the debate and Allocator, not automatic pass/fail thresholds. There are no configured minimum confidence, edge, or score gates. The Orchestrator must explain the research verdict using the whole case; the Allocator makes the investment decision, subject to hard budget and risk limits.

## Illustrative comparison

These are invented net-of-cost assumptions over the same horizon, with `h = 0` for arithmetic illustration only:

| Candidate | Confidence | Average gain `U` | Average loss `D` | Expected net return | Assumed stressed loss | Opportunity score |
| --- | --- | --- | --- | --- | --- | --- |
| A: lower confidence, larger potential | 60% | 20% | 10% | 8.0% | 15% | 0.533 |
| B: higher confidence, smaller potential | 80% | 3% | 7% | 1.0% | 10% | 0.100 |
| C: high confidence, unfavorable downside | 90% | 1% | 20% | -1.1% | 30% | -0.037 |


These examples show why probability alone is insufficient. Bull/Bear should challenge average payoffs, costs, adverse scenarios, and uncertainty rather than accept optimistic targets. The figures are invented, not estimates for NVIDIA or any named stock, and do not automatically decide the verdict.

## Debate routing and ownership

1. The analyst team supplies its initial forecast, confidence when supportable, scenarios, and known gaps.
2. Every admissible opening or reinforcement proposal enters the debate queue without a numerical opportunity filter. Stock eligibility and watchlist rules still apply.
3. Schedule within the configured session research budget using least-recently-debated priority, then stock ID. Confidence and opportunity score do not determine queue order. Pending proposals are visibly queued, not financially rejected.
4. Bull/Bear examine the probability/payoff trade-off, costs, downside, timing, uncertainty, and portfolio relevance. Bounded verification can fill initial gaps.
5. The Orchestrator records revised confidence, scenarios, calculations when supported, dissent, and an explained `APPROVE`, `DEFER`, or `REJECT` research verdict.
6. The Portfolio Manager assesses an approved case and chooses the action and amount. It may still reject, defer, or choose a smaller investment; deterministic tools validate risk, reserve cash, and authorize execution.

A missing initial probability does not by itself skip debate; report it honestly. If final confidence, payoff evidence, coverage, or required sizing inputs remain unsupported, defer added investment. Debate completion is not permission to trade.

Do not expand the authorized stock universe or treat repeated sessions as independent opportunities. Compare forecasts on the same horizon and reference-price basis; refresh materially changed proposals.

## Expected return is not guaranteed long-run revenue

The law of large numbers concerns averages under specified probabilistic assumptions, not guaranteed earnings from a finite trading account. Model estimates can be wrong, market regimes change, trades can be correlated, and large losses can exhaust capital before an average stabilizes.

Equal arithmetic expected returns do not imply equal compound growth or drawdown. For example, +50% followed by -50% leaves 75% of the starting capital. Evaluate net compounding, tail losses, portfolio dependence, and risk of ruin prospectively; do not justify unlimited size or repeated bets by the law of large numbers.


## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [Bull/Bear debate](new-entry-debate.md)
- [Portfolio Manager](portfolio-allocator.md)
- [Budget management](budget-management.md)
- [Validation](validation.md)
- [Primary references](research.md)

