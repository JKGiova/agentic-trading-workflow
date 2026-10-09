# Existing-position management

[Wiki home](README.md) · [Project overview](../README.md)

The Decision Manager reviews every broker-held stock using mandatory fresh research, current exposure, entry thesis, protective orders, and relevant historical evidence. Profit or loss alone is not sufficient justification.

| Action | Conditions to justify the proposal |
| --- | --- |
| `REINFORCE` | Fresh evidence strengthens the forward-looking thesis; eligibility, liquidity, concentration, and incremental risk permit additional exposure |
| `REDUCE` | The thesis weakens, uncertainty or concentration increases, or remaining upside no longer justifies current exposure; retain a justified smaller position |
| `CLOSE` | The thesis is invalidated, its time-bound catalyst expires, or an explicit exit condition is met; target quantity is zero |
| `HOLD` | The thesis remains valid and evidence does not justify a change; schedule the next review |

`HOLD` is an intentional additional action so the system is not forced to reinforce, reduce, or close a valid holding on every run.

For each holding, record: original thesis, what changed, contrary evidence, research coverage, selected action, desired exposure change, invalidation conditions, next review, and risks.

Reinforcement requires a new forward-looking justification and must not be automatic averaging down. A new thesis cannot silently replace an invalidated entry thesis; record the invalidation and explain any separate proposal.

A recommendation does not bypass the deterministic risk gate. Mark an incomplete review as deferred rather than presenting it as a fully researched `HOLD`. Optional escalation to the same Bull/Bear debate is reserved for materially contradictory reinforcement proposals; ordinary position review happens before new-entry debates.

## Related pages

- [Mandatory holding research](analysis-team.md)
- [Session workflow](session-workflow.md)
- [Risk and execution](risk-and-execution.md)
