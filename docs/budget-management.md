# Budget management and confidence-based investment

[Wiki home](README.md) · [Project overview](../README.md)

Confidence determines whether new exposure is eligible and how much capital it may receive. The Decision Manager supplies an evidence-backed probability; a deterministic allocator applies the configured threshold, sizing formula, and portfolio constraints. A debate approval is a research verdict, not permission to spend.

## Which confidence controls investment?

Use `p_trade`: the probability that a long position entered at the current executable reference price achieves a positive total return after estimated round-trip fees and slippage over the declared forecast horizon. For reinforcement, evaluate the forward return from today's price, not the original purchase price.

Keep the benchmark-outperformance forecast separate. Outperforming a falling benchmark can still lose money and cannot substitute for `p_trade`. Record the outcome definition, price, costs, horizon, probability, calibration status, evidence, and expiry. Following a debate, the Decision Manager records the final estimate and explains any change; it must not average Bull/Bear votes.

Initially, model estimates are uncalibrated and may be used only for explicitly labeled paper experiments. Live eligibility requires an approved calibration and evaluation policy for the applicable model, prompt, horizon, and data regime. The model cannot modify policy or increase its probability simply to secure a larger allocation.

## Accept, reject, or defer

Apply the following rules to `OPEN` and `REINFORCE`:

| Condition | Budget decision |
| --- | --- |
| Valid, current `p_trade <= p_min` | `REJECT` new exposure with reason `CONFIDENCE_BELOW_OR_AT_THRESHOLD` |
| Missing, expired, unsupported, or policy-ineligible confidence | `DEFER`; obtain a valid forecast |
| `p_trade > p_min`, supported thesis, positive expected net payoff, and required research/debate approval | Eligible for allocation; continue to cash and risk checks |
| A hard eligibility or risk rule fails | `REJECT`, regardless of confidence |
| No available capital, unresolved reconciliation, or quantity below the broker minimum | `DEFER`; record the limiting constraint |
| An executable quantity passes every check and cash is reserved | `ACCEPT` for submission; acceptance is not a confirmed fill |

Confidence is necessary for adding exposure but does not establish positive expected payoff: a likely small gain can be outweighed by an unlikely large loss. Record scenario payoffs and their assumptions separately.

`REDUCE` and `CLOSE` do not need to pass the entry-confidence threshold. Risk-reducing actions remain available when confidence falls. Missing news alone does not require liquidation.

## Confidence-based sizing

Proposed initial paper policy:

```text
confidence_weight = clamp((p_trade - p_min) / (1 - p_min), 0, 1)
confidence_target_value = NAV * max_position_weight * confidence_weight
incremental_ceiling = max(0, confidence_target_value
                            - current_position_value
                            - pending_buy_value)
```

Require `0 <= p_min < 1`, `0 <= p_trade <= 1`, and validated finite inputs. NAV is reconciled, marked portfolio equity. The target is the maximum total exposure allowed by this confidence rule, not a new allowance on every session. Reserve conservative pending-buy notional once, including estimated costs.

For illustration only, with NAV **$10,000**, `max_position_weight = 10%`, and `p_min = 60%`:

| Trade confidence | Confidence weight | Target position ceiling | Result if all other checks pass |
| --- | --- | --- | --- |
| 60% or less | 0 | $0 | Reject an opening or reinforcement |
| 70% | 0.25 | $250 | Accept up to $250 for a new position |
| 80% | 0.50 | $500 | Accept up to $500 for a new position |
| 90% | 0.75 | $750 | Accept up to $750 for a new position |

At 80% confidence, an existing $300 holding with no pending buys may receive at most **$200 more**, before other limits and costs. If free cash is only $120, the additional investment is at most $120 including its cost allowance.

These figures are test configuration examples, not optimized thresholds or evidence of profitability. Higher confidence increases the ceiling under identical conditions; it does not force spending or override a tighter cap. A lower confidence target triggers a documented position review rather than an automatic sale based only on a changed number.

## Portfolio budget and allocation order

Configure and version:

| Budget | Purpose |
| --- | --- |
| Investable portfolio capital and cash reserve | Define which cash may be deployed; preserve a minimum cash balance |
| Maximum gross exposure and position weight | Limit portfolio deployment and each total holding |
| Sector and correlated-exposure limits | Prevent several apparently independent proposals from consuming the same risk budget |
| Portfolio loss-risk and daily-loss limits | Bound estimated downside and stop adding risk after a configured loss limit |
| Session new-capital limit | Cap combined openings and reinforcements in one session |
| Position/order count and liquidity limits | Bound operational load and executable size |
| Cost and slippage allowance | Reserve more than quoted notional where required |

Reconcile holdings and pending orders before computing headroom. Prioritize approved reductions and closes, but do not finance buys with expected sale proceeds. Refresh available cash only after broker confirmation, subject to settlement and account restrictions.

Pool eligible openings and reinforcements in one allocation pass. Rank by descending final `p_trade`; break ties by expected net payoff per estimated downside, then stock ID. This is a proposed deterministic paper heuristic to evaluate, not a claim of optimal portfolio construction.

For each proposal, compute the largest executable quantity satisfying **all** confidence, cash-reserve, gross-exposure, position, sector, loss-risk, session, liquidity, and broker constraints, including pending commitments and costs. Round down to supported quantities and recheck. Reserve the approved amount atomically before considering the next proposal. Unused capital stays in cash; rejection of one candidate does not enlarge another candidate's confidence ceiling.

Loss-risk estimates must include downside scenarios and gap/slippage assumptions. A stop price does not guarantee a maximum realized loss.

## Budget ledger and order lifecycle

Store the policy version, NAV, confidence and calibration status, confidence target, current/pending exposure, every applied cap, final quantity/notional, cost reserve, decision reason, and reservation/order IDs.

- Reserve cash and risk headroom atomically before submission. Only one allocator may modify a portfolio budget at a time.
- A submission timeout retains the reservation until order status is reconciled; retrying must not reserve or submit twice.
- Partial fills convert the filled portion into holdings while the remaining quantity keeps its reservation.
- Release an unfilled reservation only after broker-confirmed cancellation, rejection, or expiry.
- Broker buying power may already account for open orders. Reconcile it with the internal ledger without subtracting the same reservation twice; use the more restrictive verified availability on comparable bases.
- Recompute headroom after fills, price changes, deposits, withdrawals, and confirmed order changes. Reject or defer stale proposals before submission.
- Keep trading capital separate from news, X API, LLM, market-data, and hosting budgets. Reserve research capacity for required holding reviews before optional debates; operating-budget exhaustion blocks new exposure without disabling reconciliation and risk monitoring.

## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [Existing-position management](position-management.md)
- [New-entry debate](new-entry-debate.md)
- [Risk and execution](risk-and-execution.md)
- [Validation](validation.md)
