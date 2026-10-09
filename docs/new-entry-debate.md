# Entry and reinforcement proposals: Bull/Bear debate

[Wiki home](README.md) · [Project overview](../README.md)

Only additions passing the initial [opportunity screen](opportunity-screening.md) can enter debate. The screen combines `p_initial`, payoff magnitude, uncertainty, stressed downside, and feasibility; it does not reject solely because confidence is below a fixed percentage. Valid inadequate edge/score or hard-risk failure rejects the addition before Bull/Bear calls; missing inputs defer it. Preserve the initial record.

After mandatory holding reviews, the Orchestrator nominates a bounded shortlist from passed opening and reinforcement proposals. Propose at most three debates per session initially; reserve holding-research capacity first. A passed candidate omitted for lack of debate budget is deferred, not approved.

## Participants

- **Bull Researcher:** strongest evidence-backed case for opening or adding now, catalyst, remaining opportunity, and invalidators.
- **Bear Researcher:** strongest case against adding now, contradictory evidence, prior pricing-in, weak sources, downside, and reasons to wait.

Both receive the same frozen bundle, `p_initial`, scenario probabilities and average payoffs, uncertainty haircut, opportunity score, outcome definition, price snapshot, and portfolio constraints. Neither must invent arguments; either may recommend no trade.

The Orchestrator coordinates and judges the debate, then defines `p_final` and revised payoff/downside assumptions. The separate Portfolio Allocator owns the subsequent action and amount.

## Bounded protocol

| Stage | Process | Required result |
| --- | --- | --- |
| 0. First-gate verification | Runtime validates coverage, confidence/payoffs, robust edge, opportunity score, and risk eligibility | Reject/defer immediately on failure; no debate |
| 1. Independent opening | Bull and Bear do not see each other's opening | Cited thesis, opposing facts, assumptions, and invalidators |
| 2. Cross-examination | Each challenges at most three material claims | Evidence-linked questions |
| 3. Verification and rebuttal | Orchestrator routes bounded analyst lookups and freezes an updated shared bundle | Verified answers and one rebuttal per side; unresolved claims remain explicit |
| 4. Independent final cases | Each sees both rebuttals and recommends enter/wait/reject | Final case, residual risks, and proposed forecast revisions with reasons |
| 5. Orchestrator review | Assess both cases and verified facts | `p_final`, calibration status, revised scenarios, robust edge/score, revision rationale, and `APPROVE`/`DEFER`/`REJECT` |
| 6. Second gate and handoff | Runtime checks final opportunity record and verdict | Reject inadequate final edge/score or hard-risk failure; defer invalid inputs; only supported passes reach the Allocator |

One opening, one challenge/rebuttal round, and one final case per side. No retries until consensus or a favorable probability appears.

A material lookup requires forecast validation. Keep the information cutoff, outcome definition, and price basis comparable with the first estimate; material basis changes require a new analysis version and first gate. If verification cannot finish within budget, defer. News after cutoff queues a later review.

## Orchestrator judgment

Evaluate traceability, causal validity, novelty, timing, opportunity after costs, downside, and unresolved factual conflicts.

- `APPROVE`: supported thesis, current conditions, sufficient robust expected net payoff and opportunity score, with supported final confidence; proceed to Allocator review.
- `DEFER`: missing/invalid confidence, unverified evidence, timing, or unresolved material conflict; identify what permits reconsideration.
- `REJECT`: thesis undermined or eligibility fails, including inadequate robust edge/score or unacceptable stressed loss.

Record `p_initial` and `p_final` separately and explain resolved challenges, dissent, and confidence changes. The revised value may go down, remain unchanged, or go up; it cannot be chosen by averaging votes or favoring persuasive writing.

A Bear victory rejects/defers a long addition; it does not create a short. An `APPROVE` does not choose the position size or guarantee a trade. The Allocator may still reject, defer, or choose a smaller investment within the [shared portfolio budget](budget-management.md).

## Related pages

- [Stock forecasts](forecasts-and-confidence.md)
- [Opportunity screening](opportunity-screening.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Position management](position-management.md)
- [Budget management](budget-management.md)
- [Validation](validation.md)
