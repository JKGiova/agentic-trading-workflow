# Portfolio Allocator agent

[Wiki home](README.md) · [Project overview](../README.md)

The Portfolio Allocator is a separate AI agent that makes the position and investment decision after analysis and, for additions, debate. It receives structured evidence and portfolio state rather than relying on the Orchestrator's confidence alone.

## Inputs and confidence assessment

For each eligible addition, provide both confidence records, gate results, research coverage, Bull/Bear cases, Orchestrator verdict and revision reasons, scenario payoffs, invalidators, expiry, holdings, pending orders, free cash, and versioned policy.

The Allocator checks:

- Both estimates refer to the same measurable outcome and reference-price basis.
- The initial and final gates passed, required debate completed, and the Orchestrator verdict is `APPROVE`.
- Final confidence is supported by traceable evidence, with uncertainty and calibration status disclosed.
- Confidence revisions address actual challenges or verified facts; a large unexplained increase is deferred for clarification.
- Expected net payoff, downside, concentration, timing, and cash availability support the proposed position.

It may reject a confident proposal that lacks portfolio fit, select a smaller investment, or defer unresolved evidence. It cannot overrule a failed opportunity gate, modify policy, rewrite probabilities, or repeatedly request revisions until a proposal passes. Clarification is bounded and must preserve prior records.

## Position choices

| Portfolio state | Available choices |
| --- | --- |
| Eligible stock without a holding | `OPEN` or `NO_ACTION`; `OPEN` requires both gates and debate approval |
| Existing holding | `REINFORCE`, `HOLD`, `REDUCE`, or `CLOSE` |
| Reinforcement proposal | Both gates and the same bounded debate are mandatory before adding capital |
| Valid holding whose addition was rejected | Choose `HOLD`, `REDUCE`, or `CLOSE` from its researched thesis; rejection alone does not force an exit |
| Incomplete ordinary holding review | Mark review deferred; no added exposure; independent protection and deterministic risk reduction remain active |

The prototype is long-only. The agent chooses the eligible stock, action, and target exposure; Bear victory does not authorize a short.

## Investment selection and tools

Use the Orchestrator's policy-eligible `p_final` and revised opportunity/downside record in [budget management](budget-management.md). Final confidence scales the position ceiling; a separate stressed-loss budget caps volatile exposure. Never substitute `p_initial` after debate. A favorable expected payoff can support a lower-confidence trade without implying a larger safe investment.

The deterministic sizing tool returns confidence ceiling, stressed-loss ceiling, current/pending exposure, cash/risk headroom, and maximum executable quantity. The agent proposes a positive amount at or below this limit, explaining any smaller amount using scenario downside, uncertainty, or portfolio fit. Under identical constraints, higher final confidence raises the ceiling; it does not guarantee a larger chosen investment.

Rank supported additions under the configured policy and build one coherent portfolio plan with existing-position changes. A structured plan contains:

| Field | Required value |
| --- | --- |
| Confidence lineage | Initial/final record IDs, values, calibration status, outcome ID, and gate results |
| Confidence and opportunity assessment | Why final probability/payoffs are usable, robust edge/score, stressed loss, revision reasons, and residual uncertainty |
| Decision | Action plus `ACCEPT`, `REJECT`, or `DEFER` for the proposal |
| Investment | Desired total position, incremental notional/quantity, maximum permitted amount, and reason for sizing |
| Portfolio effects | Cash remaining, concentration, estimated downside, pending commitments, and applied constraints |
| Thesis and safeguards | Evidence, invalidators, protective requirements, review time, and expiry |

An agent's `ACCEPT` is a recommendation. Deterministic validators recompute quantities and constraints, reserve cash atomically, and authorize submission. They may reject or defer an otherwise accepted proposal. Only the execution service holds broker credentials.

## Existing-position priority

Review all holdings before optional entry debates. The Allocator may decide a researched hold, reduction, or close directly using the holding case and available initial forecast; those actions do not require a successful opportunity gate or debate. Candidate reinforcements remain unapproved until they complete both gates and debate.

After debate, run a final allocation pass across eligible additions and existing-position decisions. Preserve one action per stock and do not spend hypothetical exit proceeds. If an earlier holding action was already submitted, reconcile it and exclude incompatible later actions.

## Related pages

- [Architecture](architecture.md)
- [Forecasts and confidence](forecasts-and-confidence.md)
- [Existing-position management](position-management.md)
- [Opportunity screening](opportunity-screening.md)
- [Budget management](budget-management.md)
- [Session workflow](session-workflow.md)
