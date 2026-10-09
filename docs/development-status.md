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

- Concrete package/framework comparison and proposed Python/LangGraph build.
- Connector/API/access specifications for news, approved X accounts, SEC/IR, search, quotes, and calendar.
- Graph/tool boundaries, logical data model, contracts, concurrency and recovery specifications.
- Worker deployment, configuration requirements, model/source cost scenarios, and ordered T0-T9 backlog.
- Four upstream revisions and license files inspected; no upstream code imported.

## Implementation status

The repository currently contains documentation and a license. No collectors, LLM agents, broker adapters, dashboard, runtime configuration, trading tests, or measured performance are implemented by this documentation change.

## Next milestone

Start [T0](implementation-backlog.md): prove authorized source/quote access and compare pinned TradingAgents with a minimal custom graph on the same evidence. Owner-supplied watchlist, X authors, provider credentials/entitlements, and financial limits are still needed for an operational spike.

## Checks for this update

- Required design sections distributed across topic pages.
- Internal Markdown file links checked against the proposed repository tree.
- Root README kept as a short navigation page.
- Confidence/payoff comparison, direct debate handoff, final confidence/downside sizing, reinforcement, and compounding arithmetic checked.
- Eight-role ownership, direct debate handoff, fair queue behavior, final confidence/downside sizing, and holding-risk exceptions checked across pages.
- Forecast, opportunity, debate, Allocator, budget, execution, validation, and milestone pages aligned.
- Official tool/provider documentation and upstream license/source files reviewed.
- Token/call/credit arithmetic and documentation links checked.
- Published content checked after the commit.

These are documentation checks. They do not qualify a trading implementation.

## Related pages

- [Implementation backlog](implementation-backlog.md)
- [Implementation stack](implementation-stack.md)
- [Implementation plan](PLAN.md)
- [Source research](research.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Validation](validation.md)
