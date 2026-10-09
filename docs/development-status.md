# Development status

[Wiki home](README.md) · [Project overview](../README.md)

Reviewed: **2026-10-09**.

## Completed documentation

- English project overview and linked wiki index.
- Four specialist analyst roles and a mandatory holding-research coverage matrix.
- Analyst-team initial confidence/payoff scenarios and known gaps, passed directly to debate without a numerical prefilter.
- Orchestrator revised confidence/payoffs, reasoned research verdicts, and immutable forecast lineage.
- Separate Portfolio Allocator agent analyzing confidence and choosing actions/investments.
- Stock forecast contracts with separate benchmark and positive-net-return outcomes.
- Debate/Allocator acceptance, confidence/downside investment sizing, shared budget, cash reserves, and order reservations.
- Bounded fair debate queue, visible pending proposals, and verification of initial estimate gaps.
- Existing-position review actions, including hold and incomplete-review handling.
- Bounded Bull/Bear debate for openings and reinforcements, with Orchestrator verdicts.
- Persistent evidence, source permissions, scheduling, risk, and paper-execution design.
- Reference-project comparison, validation strategy, and implementation milestones.

## Implementation status

The repository currently contains documentation and a license. No collectors, LLM agents, broker adapters, dashboard, runtime configuration, trading tests, or measured performance are implemented by this documentation change.

## Next milestone

Start Milestone 0 in the implementation plan: define the stock watchlist, forecast horizon, sources, model budget, debate budget/queue policy and stressed-loss assumptions, Analyst Lead, portfolio budget policy, and broker candidate, then evaluate one upstream in a reproducible paper-only technical spike.

## Checks for this update

- Required design sections distributed across topic pages.
- Internal Markdown file links checked against the proposed repository tree.
- Root README kept as a short navigation page.
- Confidence/payoff comparison, direct debate handoff, final confidence/downside sizing, reinforcement, and compounding arithmetic checked.
- Eight-role ownership, direct debate handoff, fair queue behavior, final confidence/downside sizing, and holding-risk exceptions checked across pages.
- Forecast, opportunity, debate, Allocator, budget, execution, validation, and milestone pages aligned.
- Published content checked after the commit.

These are documentation checks. They do not qualify a trading implementation.

## Related pages

- [Implementation plan](PLAN.md)
- [Source research](research.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Validation](validation.md)
