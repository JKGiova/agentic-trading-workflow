# Budget management and confidence-based investment

[Wiki home](README.md) · [Project overview](../README.md)

The analysis team's initial confidence screens additions before debate. The Orchestrator's revised confidence determines final eligibility and the investment ceiling. A separate [Portfolio Allocator agent](portfolio-allocator.md) evaluates that confidence, chooses the action and amount, and uses deterministic budget/risk tools. A debate approval is a research verdict, not permission to spend.

## Which confidence controls investment?

Use `p_initial` before debate and `p_final` after debate, both estimating the probability that a long position entered at the current executable reference price achieves a positive total return after estimated round-trip fees and slippage over the declared forecast horizon. For reinforcement, evaluate the forward return from today's price, not the original purchase price.

Keep the benchmark-outperformance forecast separate. Outperforming a falling benchmark can still lose money and cannot substitute for `p_final`. Record the outcome definition, price, costs, horizon, probability, calibration status, evidence, and expiry. The analysis team owns `p_initial`; following debate, the Orchestrator records `p_final` and explains any change without averaging Bull/Bear votes. The Allocator consumes the final record without rewriting it. Both estimates must share the same outcome and reference-price basis.

Initially, model estimates are uncalibrated and may be used only for explicitly labeled paper experiments. Live eligibility requires an approved calibration and evaluation policy for the applicable model, prompt, horizon, and data regime. The model cannot modify policy or increase its probability simply to secure a larger allocation.

## Accept, reject, or defer

Apply two gates to `OPEN` and `REINFORCE`. Each consumes the policy-eligible probability for that stage; raw/calibrated values and their status remain separately recorded:

| Condition | Budget decision |
| --- | --- |
| Valid `p_initial <= p_initial_min` | Immediate `REJECT` with `INITIAL_CONFIDENCE_TOO_LOW`; skip debate and investment selection for this addition |
| Valid `p_final <= p_final_min` after debate | `REJECT` with `FINAL_CONFIDENCE_TOO_LOW`; no added investment |
| Missing, expired, unsupported, or policy-ineligible confidence | `DEFER`; obtain a valid forecast |
| Both gates passed, `p_final > p_final_min`, supported thesis, positive expected net payoff, and Orchestrator `APPROVE` | Portfolio Allocator assesses confidence, selects action and investment, then requests deterministic validation |
| A hard eligibility or risk rule fails | `REJECT`, regardless of confidence |
| No available capital, unresolved reconciliation, or quantity below the broker minimum | `DEFER`; record the limiting constraint |
| An executable quantity passes every check and cash is reserved | `ACCEPT` for submission; acceptance is not a confirmed fill |

Confidence is necessary for adding exposure but does not establish positive expected payoff: a likely small gain can be outweighed by an unlikely large loss. Record scenario payoffs and their assumptions separately.

`REDUCE` and `CLOSE` do not need to pass the entry-confidence threshold. Risk-reducing actions remain available when confidence falls. Missing news alone does not require liquidation.

## Confidence-based sizing

Only `p_final` sizes an addition after debate. `p_initial` is a screening value and must not be substituted, averaged with the final estimate, or chosen because it gives a larger amount. The Allocator may propose less than the calculated ceiling, with a recorded reason.

Proposed initial paper policy:

```text
confidence_weight = clamp((p_final - p_final_min) / (1 - p_final_min), 0, 1)
confidence_target_value = NAV * max_position_weight * confidence_weight
incremental_ceiling = max(0, confidence_target_value
                            - current_position_value
                            - pending_buy_value)
```

Require `0 <= p_initial_min < 1`, `0 <= p_final_min < 1`, `0 <= p_initial <= 1`, `0 <= p_final <= 1`, and validated finite inputs. NAV is reconciled, marked portfolio equity. The target is the maximum total exposure allowed by this confidence rule, not a new allowance on every session. Reserve conservative pending-buy notional once, including estimated costs.

For illustration only, assume the initial gate and debate approval already passed, with NAV **$10,000**, `max_position_weight = 10%`, and `p_final_min = 60%`:

| Revised confidence `p_final` | Confidence weight | Target position ceiling | Result if all other checks pass |
| --- | --- | --- | --- |
| 60% or less | 0 | $0 | Reject an opening or reinforcement |
| 70% | 0.25 | $250 | Accept up to $250 for a new position |
| 80% | 0.50 | $500 | Accept up to $500 for a new position |
| 90% | 0.75 | $750 | Accept up to $750 for a new position |

With both thresholds set to 60% for a paper experiment:

- Initial 55%: reject immediately, skip debate, and invest $0 in the proposed addition.
- Initial 80%, revised 55%: reject after debate and invest $0 in the proposed addition.
- Initial 80%, revised 70%: the Allocator may accept up to the $250 final-confidence ceiling, subject to all other checks. The $500 ceiling implied by 80% must not be used.

At 80% revised confidence, an existing $300 holding with no pending buys may receive at most **$200 more**, before other limits and costs. If free cash is only $120, the additional investment is at most $120 including its cost allowance.

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

Pool eligible openings and reinforcements in one allocation pass. Rank by descending final `p_final`; break ties by expected net payoff per estimated downside, then stock ID. This is a proposed deterministic paper heuristic to evaluate, not a claim of optimal portfolio construction.

For each proposal, the deterministic sizing tool computes the largest executable quantity satisfying **all** confidence, cash-reserve, gross-exposure, position, sector, loss-risk, session, liquidity, and broker constraints, including pending commitments and costs. The Allocator chooses an amount at or below that ceiling with a sizing rationale. Round down to supported quantities and recheck independently. Reserve the validated amount atomically before considering the next proposal. Unused capital stays in cash; rejection of one candidate does not enlarge another candidate's confidence ceiling.

Loss-risk estimates must include downside scenarios and gap/slippage assumptions. A stop price does not guarantee a maximum realized loss.

## Budget ledger and order lifecycle

Store the policy version, NAV, both confidence record IDs and values, both gate results and calibration statuses, revision rationale, Allocator assessment/action, confidence target, current/pending exposure, every applied cap, final quantity/notional, cost reserve, decision reason, and reservation/order IDs.

- Reserve cash and risk headroom atomically before submission. Only one deterministic allocation transaction may modify a portfolio budget at a time.
- A submission timeout retains the reservation until order status is reconciled; retrying must not reserve or submit twice.
- Partial fills convert the filled portion into holdings while the remaining quantity keeps its reservation.
- Release an unfilled reservation only after broker-confirmed cancellation, rejection, or expiry.
- Broker buying power may already account for open orders. Reconcile it with the internal ledger without subtracting the same reservation twice; use the more restrictive verified availability on comparable bases.
- Recompute headroom after fills, price changes, deposits, withdrawals, and confirmed order changes. Reject or defer stale proposals before submission.
- Keep trading capital separate from news, X API, LLM, market-data, and hosting budgets. Reserve research capacity for required holding reviews before optional debates; operating-budget exhaustion blocks new exposure without disabling reconciliation and risk monitoring.

## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Existing-position management](position-management.md)
- [New-entry debate](new-entry-debate.md)
- [Risk and execution](risk-and-execution.md)
- [Validation](validation.md)
