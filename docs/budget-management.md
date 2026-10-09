# Budget management and confidence-based investment

[Wiki home](README.md) · [Project overview](../README.md)

The analysis team's confidence/payoff estimates go directly to debate as inputs, without screening proposals. Bull/Bear analyze them, and the Orchestrator's revised estimates and research verdict inform investment review. A separate [Portfolio Allocator](portfolio-allocator.md) chooses the action and amount; deterministic tools enforce confidence-based sizing, downside budgets, cash reservations, and risk limits.

## Acceptance depends on opportunity, not probability alone

Both stages estimate the probability of positive net total return over the same frozen horizon and reference-price basis: `p_initial` before debate, `p_final` afterward. The team/Orchestrator also publish net payoff scenarios, stressed downside, uncertainty, and opportunity scores. Keep benchmark-outperformance probability separate.

[Opportunity analysis inside the debate](opportunity-analysis.md) combines probability with payoff magnitude:

```text
expected_net_return = p * U - (1 - p) * D
robust_edge = expected_net_return - uncertainty_penalty
opportunity_score = robust_edge / stressed_loss_fraction
```

`U` and `D` are conditional average gain/loss magnitudes already net of trading costs. Prefer a full scenario distribution in implementation. Unsupported payoffs, invalid probabilities, or missing risk estimates defer exposure. Uncalibrated estimates remain limited to explicit paper experiments; live eligibility requires approved validation.

These metrics support debate and investment reasoning; they have no minimum-score or minimum-confidence pass/fail thresholds.

| Condition | Decision |
| --- | --- |
| Admissible opening or reinforcement proposal | Queue for debate regardless of initial confidence/edge/score |
| Session debate budget exhausted | Keep pending with a visible reason; refresh inputs when resumed |
| Initial estimates missing or uncertain | Debate may request bounded verification; disclose gaps |
| Orchestrator research `REJECT` or `DEFER` | No addition proceeds to investment selection |
| Orchestrator `APPROVE` with supported/current final inputs | Allocator assesses portfolio fit and chooses action/amount |
| Final sizing/evidence inputs unsupported | Defer added investment |
| Hard eligibility or risk constraints fail at validation | Reject execution regardless of agent approval |
| No capital, unresolved reconciliation, or subminimum quantity | Defer and record the constraint |
| Executable proposal passes independent validation and cash is reserved | Accept for submission; acceptance is not a fill |

There is no automatic rejection at 60% or any other universal probability threshold. Lower confidence can be justified by better supported gains relative to losses. High volatility, nominally cheap shares, and optimistic maximum targets do not establish favorable opportunity.

`REDUCE` and `CLOSE` remain available independently of entry debate; missing news alone does not require liquidation.

## Confidence-based sizing with a downside budget

Only the final probability and revised downside record size an addition after debate. Never substitute the initial probability or whichever estimate gives a larger allocation.

Proposed simple paper policy:

```text
confidence_weight = p_final
confidence_target_value = NAV * max_position_weight * confidence_weight
loss_risk_target_value = per_position_loss_budget / L_stress_final
total_position_ceiling = min(confidence_target_value, loss_risk_target_value,
                             other_position_and_portfolio_caps)
incremental_ceiling = max(0, total_position_ceiling
                            - current_position_value
                            - pending_buy_value)
```

Require finite valid inputs, `0 <= p_final <= 1`, and `L_stress_final > 0`. NAV is reconciled marked equity; the loss budget is a configured currency amount. Stressed loss includes gaps and liquidity assumptions and is not a guaranteed maximum loss.

Confidence still influences investment: with the same downside and constraints, higher final confidence raises the confidence ceiling. A volatile opportunity may deserve debate but receive a smaller amount because its stressed-loss ceiling is tighter. The Allocator may choose less than the permitted ceiling, with reasons.

For illustration, NAV **$10,000** and maximum position weight **10%**, assuming debate approval, Allocator acceptance, and all independent checks pass:

| Final confidence | Confidence-based total-position ceiling before other caps |
| --- | --- |
| 60% | $600 |
| 70% | $700 |
| 80% | $800 |
| 90% | $900 |

With final confidence 60%, stressed loss 15%, and a $60 loss budget, the downside ceiling is `$60 / 0.15 = $400`; the total holding may be at most **$400**, before other constraints. If already holding $250 and reserving $50 for pending buys, reinforcement is at most **$100** more. Cost allowances may further reduce executable notional.

These are proposed test parameters, not optimized settings or evidence of profitability. Count total holdings and pending exposure rather than resetting an investment allowance every session. A lower target prompts a documented holding review rather than an automatic sale solely on a changed estimate.

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

Pool eligible openings and reinforcements in one allocation pass. The Allocator assesses final confidence, payoffs, downside, diversification, and portfolio fit together and records why it funds each chosen position. No score alone compels acceptance or investment. Deterministic constraints limit every proposed amount. This is a proposed deterministic paper heuristic to evaluate, not a claim of optimal portfolio construction.

For each proposal, the deterministic sizing tool computes the largest executable quantity satisfying **all** confidence-based sizing, stressed-loss, cash-reserve, gross-exposure, position, sector, loss-risk, session, liquidity, and broker constraints, including pending commitments and costs. The Allocator chooses an amount at or below that ceiling with a sizing rationale. Round down to supported quantities and recheck independently. Reserve the validated amount atomically before considering the next proposal. Unused capital stays in cash; rejection of one candidate does not enlarge another candidate's confidence ceiling.

Loss-risk estimates must include downside scenarios and gap/slippage assumptions. A stop price does not guarantee a maximum realized loss.

## Budget ledger and order lifecycle

Store the policy version, NAV, both confidence record IDs and values, debate/research verdicts and calibration statuses, initial/revised scenario payoffs, robust edges/scores, stressed-loss assumptions, uncertainty penalties, revision rationale, Allocator assessment/action, confidence and loss-risk targets, current/pending exposure, every applied cap, final quantity/notional, cost reserve, decision reason, and reservation/order IDs.

- Reserve cash and risk headroom atomically before submission. Only one deterministic allocation transaction may modify a portfolio budget at a time.
- A submission timeout retains the reservation until order status is reconciled; retrying must not reserve or submit twice.
- Partial fills convert the filled portion into holdings while the remaining quantity keeps its reservation.
- Release an unfilled reservation only after broker-confirmed cancellation, rejection, or expiry.
- Broker buying power may already account for open orders. Reconcile it with the internal ledger without subtracting the same reservation twice; use the more restrictive verified availability on comparable bases.
- Recompute headroom after fills, price changes, deposits, withdrawals, and confirmed order changes. Reject or defer stale proposals before submission.
- Keep trading capital separate from news, X API, LLM, market-data, and hosting budgets. Reserve research capacity for required holding reviews before optional debates; operating-budget exhaustion blocks new exposure without disabling reconciliation and risk monitoring.

Portfolio capital and operating spend have different ledgers. See [deployment and costs](deployment-and-costs.md) for model/source pricing, workload assumptions, and cost reservations; see [storage contracts](persistence-and-contracts.md) for atomic cash/risk reservations.

## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Existing-position management](position-management.md)
- [New-entry debate](new-entry-debate.md)
- [Risk and execution](risk-and-execution.md)
- [Validation](validation.md)
