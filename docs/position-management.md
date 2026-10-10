# Existing-position management

[Wiki home](README.md) · [Project overview](../README.md)

The continuously working analysis team supplies a mandatory researched holding case at cycle closure; every such report enters the scheduled stock debate. The Portfolio Manager agent compares it with current exposure, entry thesis, protective orders, and relevant historical evidence, then chooses the position action. Profit or loss alone is not sufficient justification.

| Action | Conditions to justify the proposal |
| --- | --- |
| `REINFORCE` | Fresh evidence strengthens the forward-looking thesis; the reinforcement debate is approved with supportable revised confidence/payoffs; confidence-based total-position target, cash, liquidity, concentration, and incremental risk permit additional exposure |
| `REDUCE` | The thesis weakens, uncertainty or concentration increases, or remaining upside no longer justifies current exposure; retain a justified smaller position |
| `CLOSE` | The thesis is invalidated, its time-bound catalyst expires, or an explicit exit condition is met; target quantity is zero |
| `HOLD` | The thesis remains valid and evidence does not justify a change; schedule the next review |

`HOLD` is an intentional additional action so the system is not forced to reinforce, reduce, or close a valid holding on every run.

Use [budget management](budget-management.md) to size reinforcements against the total holding and pending buys. Do not reset the allowance on each session. Falling confidence or exposure above the new target requires a reasoned `REDUCE`, `CLOSE`, or `HOLD` review; ordinary holding actions follow the scheduled stock debate, while independent protections and deterministic policy-triggered risk reduction do not wait for it.

For each holding, record: `p_initial`, available `p_final`, their calibration status and the research verdict, confidence target when final confidence is available, selected exposure and investment, original thesis, what changed, contrary evidence, research coverage, selected action, desired exposure change, invalidation conditions, next review, and risks.

Reinforcement requires a new forward-looking justification and must not be automatic averaging down. A new thesis cannot silently replace an invalidated entry thesis; record the invalidation and explain any separate proposal.

A recommendation does not bypass the deterministic risk gate. Mark an incomplete review as deferred rather than presenting it as a fully researched `HOLD`. Every admissible reinforcement proposal enters the same bounded Bull/Bear debate as an opening, without a confidence/payoff prefilter. Debate directly evaluates the reward/downside case; the Orchestrator records revised confidence and a verdict, then the Allocator chooses the action and amount. A rejected addition still leaves the holding subject to a hold/reduce/close decision. Every holding report enters debate; the Portfolio Manager receives its outcome and assesses it alongside approved candidates. Independent protection and deterministic emergency risk controls remain separate.

## Related pages

- [Mandatory holding research](analysis-team.md)
- [Session workflow](session-workflow.md)
- [Portfolio Manager](portfolio-allocator.md)
- [Opportunity analysis](opportunity-analysis.md)
- [Budget management](budget-management.md)
- [Risk and execution](risk-and-execution.md)

