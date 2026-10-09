# Entry and reinforcement proposals: Bull/Bear debate

[Wiki home](README.md) · [Project overview](../README.md)

Admissible opening and reinforcement proposals enter debate directly. There is no confidence, expected-return, or opportunity-score filter before debate. Watchlist/instrument eligibility and source permissions remain enforced.

After mandatory holding reviews, the Orchestrator places proposals in a durable debate queue. Propose at most three debates per session initially, with required holding research funded first. Use least-recently-debated priority, then stock ID; do not rank or reject proposals by initial confidence or payoff score. Proposals beyond the session budget remain queued with a visible reason and require fresh inputs when resumed.

## Participants

- **Bull Researcher:** strongest supported case for opening or adding now, probability of success, average upside, catalyst, costs, and invalidators.
- **Bear Researcher:** strongest supported case against adding, average/adverse losses, liquidity and gaps, prior pricing-in, uncertainty, contrary evidence, and reasons to wait.

Both receive the same frozen analyst reports, initial confidence when available, scenarios, diagnostic calculations, known gaps, price snapshot, outcome definition, and portfolio constraints. Either may recommend no trade. Unsupported initial estimates are marked missing, not fabricated or used to block debate automatically.

The Orchestrator coordinates and judges the debate, then records revised `p_final` and payoff/downside assumptions. The separate Portfolio Allocator owns the action and investment.

## Bounded protocol

| Stage | Process | Required result |
| --- | --- | --- |
| 1. Independent opening | Bull and Bear do not see each other's opening | Cited thesis, probability/payoff trade-off, opposing facts, assumptions, gaps, and invalidators |
| 2. Cross-examination | Each challenges at most three material claims | Evidence-linked questions, including overstated upside or understated losses/costs |
| 3. Verification and rebuttal | Orchestrator routes bounded analyst lookups and freezes the updated shared bundle | Verified answers and one rebuttal per side; unresolved gaps remain explicit |
| 4. Independent final cases | Each sees both rebuttals and recommends enter/wait/reject | Final case, residual risks, and forecast/scenario revisions with reasons |
| 5. Orchestrator review | Assess both cases and verified facts directly | `p_final` when supported, revised scenarios and diagnostics, calibration status, dissent, rationale, and `APPROVE`/`DEFER`/`REJECT` |
| 6. Allocator handoff | Approved, current, supportable research cases go to the separate investment agent | Position/investment assessment; no automatic numerical confidence or score gate |

One opening, one challenge/rebuttal round, and one final case per side. No retries until consensus or a favorable probability appears.

Keep information cutoff, outcome definition, and price basis comparable with the initial forecast. Material changes require a refreshed versioned proposal and debate. If verification cannot finish within budget, defer; news after cutoff queues a later review.

## Orchestrator judgment

The debate directly evaluates confidence, potential payoff, costs, stressed downside, liquidity, timing, novelty, causal validity, and unresolved conflicts. Use [expected-return and opportunity calculations](opportunity-analysis.md) as evidence for reasoning, not threshold tests.

- `APPROVE`: a sufficiently supported case with a justified probability/payoff trade-off; proceed to Allocator review.
- `DEFER`: missing/unsupported final estimates, research gaps, unresolved material conflict, expiry, or timing; identify what permits reconsideration.
- `REJECT`: verified evidence undermines the thesis or the reward does not justify the costs/downside, with an explicit rationale.

A high score does not compel approval; a low initial confidence does not prevent debate. Preserve initial/final records and explain which challenges changed or preserved the assessment. Neither averaging agent votes nor persuasive writing determines confidence.

A Bear victory rejects/defers a long addition; it does not create a short. Approval does not choose size or guarantee a trade. The Allocator may reject, defer, or choose a smaller amount, and independent budget/risk validators may refuse execution.

## Related pages

- [Stock forecasts](forecasts-and-confidence.md)
- [Opportunity analysis](opportunity-analysis.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Position management](position-management.md)
- [Budget management](budget-management.md)
- [Validation](validation.md)
