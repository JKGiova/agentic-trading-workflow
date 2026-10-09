# New-entry proposals and Bull/Bear debate

[Wiki home](README.md) · [Project overview](../README.md)

After existing-position reviews, the Decision Manager nominates a bounded shortlist of new-entry candidates from eligible watchlist stocks. Propose a maximum of three debates per session as an initial cost budget, configurable before testing.

Candidates need sufficient evidence coverage, a fresh stock forecast, a causal thesis, a horizon, invalidators, and an initial feasibility check. The shortlist is research output, not an order.

### Participants

- **Bull Researcher:** builds the strongest evidence-backed case for entering now, identifies the catalyst and remaining opportunity, and specifies what would invalidate the case.
- **Bear Researcher:** builds the strongest case against entering now, including contradictory facts, prior pricing-in, weak sources, timing, downside scenarios, and better reasons to wait.

Both receive the same frozen evidence bundle, price snapshot, forecast definition, and portfolio constraints. The roles create competing hypotheses, not a requirement to invent arguments. Either may acknowledge that the evidence supports no trade.

The Decision Manager is the judge, not a third debate participant. The risk gate remains independent of its judgment.

### Bounded protocol

| Stage | Process | Required result |
| --- | --- | --- |
| 1. Independent opening | Bull and Bear write their initial assessments without seeing each other's responses | Thesis, cited claims, opposing facts, uncertainty, and explicit invalidators |
| 2. Cross-examination | Each reads the opposing assessment and challenges at most three specific material claims | Evidence-linked questions identifying assumptions or missing support |
| 3. Verification and rebuttal | The orchestrator routes focused research requests to the appropriate analyst, freezes an updated shared bundle, and gives each side one rebuttal | Answers tied to verified evidence; remaining unresolved claims are marked |
| 4. Final independent recommendation | Each submits its recommendation after seeing both rebuttals | Enter/wait/reject recommendation, residual risks, and any forecast revisions with reasons |
| 5. Judgment | Decision Manager reviews both cases and verified evidence | `APPROVE`, `DEFER`, or `REJECT`, with rationale, conditions, expiry, and dissent preserved |

This is one opening round, one challenge/rebuttal round, and one final recommendation per side. No unlimited discussion or retries until the agents agree.

A lookup that materially changes the proposal requires renewed analyst/forecast validation. Respect the session's evidence cutoff; information arriving after it queues a new review. If the required verification cannot finish within the session budget, defer the candidate.

### Judgment rules

Assess source traceability, causal validity, novelty, timing, remaining opportunity after costs, downside scenarios, unresolved factual conflicts, and portfolio fit.

- `APPROVE`: the proposal is sufficiently supported, its conditions remain valid, and it can proceed to deterministic risk checks.
- `DEFER`: specific missing evidence, timing, or unresolved material conflict prevents a decision. Record what would permit reconsideration.
- `REJECT`: verified evidence undermines the thesis or the setup fails explicit eligibility criteria.

The judge must state which challenges were resolved, which remain, and why the evidence supports its verdict. Do not pick the more persuasive writing style, automatically split the two probability estimates, or require consensus.

A Bear victory means rejecting or deferring the proposed long entry; it does not automatically create a short trade.

Rank approved proposals against the same portfolio budget. Count pending orders and do not assume that cash from proposed exits is available before fills. Approval expires if price, liquidity, evidence, or portfolio state changes materially.

## Related pages

- [Stock forecasts](forecasts-and-confidence.md)
- [Position management](position-management.md)
- [Validation](validation.md)
