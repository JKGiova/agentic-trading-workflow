# Entry and reinforcement proposals: Bull/Bear debate

[Wiki home](README.md) · [Project overview](../README.md)

Only eligible additions with a valid `p_initial > p_initial_min` can enter debate. A valid low initial estimate directly rejects the addition before any Bull/Bear calls. Missing or invalid confidence defers it. The initial record cannot be bypassed or overwritten.

After mandatory holding reviews, the Orchestrator nominates a bounded shortlist from passed opening and reinforcement proposals. Propose at most three debates per session initially; reserve holding-research capacity first. A passed candidate omitted for lack of debate budget is deferred, not approved.

## Participants

- **Bull Researcher:** strongest evidence-backed case for opening or adding now, catalyst, remaining opportunity, and invalidators.
- **Bear Researcher:** strongest case against adding now, contradictory evidence, prior pricing-in, weak sources, downside, and reasons to wait.

Both receive the same frozen bundle, `p_initial`, outcome definition, price snapshot, and portfolio constraints. Neither must invent arguments; either may recommend no trade.

The Orchestrator coordinates and judges the debate, then defines `p_final`. The separate Portfolio Allocator owns the subsequent action and amount.

## Bounded protocol

| Stage | Process | Required result |
| --- | --- | --- |
| 0. First-gate verification | Runtime validates coverage, estimate, eligibility, and `p_initial > p_initial_min` | Reject/defer immediately on failure; no debate |
| 1. Independent opening | Bull and Bear do not see each other's opening | Cited thesis, opposing facts, assumptions, and invalidators |
| 2. Cross-examination | Each challenges at most three material claims | Evidence-linked questions |
| 3. Verification and rebuttal | Orchestrator routes bounded analyst lookups and freezes an updated shared bundle | Verified answers and one rebuttal per side; unresolved claims remain explicit |
| 4. Independent final cases | Each sees both rebuttals and recommends enter/wait/reject | Final case, residual risks, and proposed forecast revisions with reasons |
| 5. Orchestrator review | Assess both cases and verified facts | `p_final`, calibration status, scenario payoffs, revision rationale, and `APPROVE`/`DEFER`/`REJECT` |
| 6. Second gate and handoff | Runtime checks final confidence and verdict | Reject valid `p_final <= p_final_min`; defer invalid confidence; only supported passes reach the Allocator |

One opening, one challenge/rebuttal round, and one final case per side. No retries until consensus or a favorable probability appears.

A material lookup requires forecast validation. Keep the information cutoff, outcome definition, and price basis comparable with the first estimate; material basis changes require a new analysis version and first gate. If verification cannot finish within budget, defer. News after cutoff queues a later review.

## Orchestrator judgment

Evaluate traceability, causal validity, novelty, timing, opportunity after costs, downside, and unresolved factual conflicts.

- `APPROVE`: supported thesis, current conditions, positive expected net payoff, and eligible final confidence; proceed to Allocator review.
- `DEFER`: missing/invalid confidence, unverified evidence, timing, or unresolved material conflict; identify what permits reconsideration.
- `REJECT`: thesis undermined or eligibility fails, including a valid final confidence at/below threshold.

Record `p_initial` and `p_final` separately and explain resolved challenges, dissent, and confidence changes. The revised value may go down, remain unchanged, or go up; it cannot be chosen by averaging votes or favoring persuasive writing.

A Bear victory rejects/defers a long addition; it does not create a short. An `APPROVE` does not choose the position size or guarantee a trade. The Allocator may still reject, defer, or choose a smaller investment within the [shared portfolio budget](budget-management.md).

## Related pages

- [Stock forecasts](forecasts-and-confidence.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Position management](position-management.md)
- [Budget management](budget-management.md)
- [Validation](validation.md)
