# Research cycles, decision phases and scheduling

[Wiki home](README.md) · [Continuous analysis](continuous-analysis.md)

Research, decision/allocation and broker monitoring run independently. The full
[continuous-cycle specification](continuous-analysis.md) supersedes the earlier
single-pass session target; v0.1 has not yet implemented this scheduler.

| Process | Proposed cadence | Responsibility |
| --- | --- | --- |
| Source collection | Every 5 minutes | Discover, version and enqueue authorized news; maintain cursors |
| Analyst workers | Throughout each X-hour cycle, waking on durable tasks | Read, analyze, cross-review, research gaps and save findings |
| Cycle closure | Every X hours, initially 3 | Freeze the manifest and publish a report per analyzed stock |
| Debate and Manager | After closure, without stopping the next research cycle | Debate every report; produce one portfolio plan from completed outcomes |
| Broker/risk monitoring | Continuous while applicable | Reconcile fills, protections, commitments, freshness and failures |

Use UTC timestamps and explicit exchange calendars. Research cycles have separate
leases from the one active decision/allocation lease per portfolio. X measures
research duration; decision latency follows. Process all unhandled backlog with
publication-age labels, not only the latest three-hour publications.

## Research-cycle lifecycle

1. Create cycle ID, fixed start/end, source/prompt/policy versions and the union of
   configured stocks and broker-held stocks. Record identity and eligibility gaps.
2. Run mandatory stock-specific holding lookups and refresh shared market context.
3. Claim new/corrected events or follow-up tasks continuously, bounded by source,
   tool, operating-cost and time budgets. Save original specialist assessments.
4. Exchange typed findings/questions, retrieve missing original sources, and persist
   cited revisions and dissent. Complete/checkpoint each task before taking the next.
5. At the deadline, freeze the evidence/assessment/task manifest atomically. Late
   work belongs to the next cycle. Publish a complete or explicitly incomplete
   report per analyzed stock, including initial confidence and coverage.
6. Start the next cycle immediately. Preserve unfinished questions and task lineage;
   never lose a holding or silently label unfinished research successful.

Research states: `OPEN`, `RESEARCHING`, `FREEZING`, `REPORTING`, then `CLOSED` or
`PARTIAL`. Individual tasks also have pending/running/completed/failed/deferred states.

## Closed-cycle decision workflow

1. Claim the decision lease and reconcile Alpaca snapshot/quotes. Validate report
   age, policy version, coverage and the defined forecast reference basis.
2. Create a durable debate obligation for every analyzed stock, including holdings,
   HOLD and NO_ACTION cases. Process holding cases first, then fair last-debated/
   stock-ID ordering without confidence/payoff ranking. Unfinished debates remain visible.
3. Run bounded Bull/Bear research and verification on the frozen case. Material
   post-cutoff evidence requires an explicit revised case and refreshed affected reasoning.
4. The Orchestrator records revised confidence/scenarios, disagreement, thesis validity,
   holding implications and APPROVE/DEFER/REJECT for added exposure.
5. The Portfolio Manager receives approved addition candidates and all holding outcomes,
   plus fresh portfolio/volatility inputs. Choose OPEN/REINFORCE/HOLD/REDUCE/CLOSE/
   NO_ACTION and desired investment in one coherent plan. Deferred cases add no risk.
6. Deterministic services recompute confidence/downside, cash, pending commitments,
   concentration, liquidity, freshness and protection limits; reserve permitted capital.
7. The future paper execution service reconciles/submits/monitors durable intents.
   v0.1 remains read-only and produces nonexecutable previews.
8. Persist reports, debates, both confidence records, Manager rationale, validation,
   costs and incomplete obligations; release the decision lease.

Decision states: `QUEUED`, `DEBATING`, `JUDGING`, `MANAGING_PORTFOLIO`, `VALIDATING`,
`EXECUTING`, then `COMPLETED`, `PARTIAL` or `FAILED`. Do not count queued debates as
completed. Rejecting added exposure does not force an exit or skip holding management.
Independent protective monitoring and policy-triggered risk reduction do not wait
for the cycle. Unconfirmed exit proceeds cannot fund another order.

### Proposal contract

| Field | Purpose |
| --- | --- |
| Cycle, report-manifest, decision-session, proposal, and stock IDs | Traceability, immutable report membership and duplicate prevention |
| Path and action | Existing-position change or new-entry decision |
| Thesis and changes | Forward-looking justification and comparison with the entry thesis |
| Forecast and confidence lineage | Outcome ID, horizon, reference-price basis, `p_initial` and `p_final` record IDs/values, calibration statuses, and revision reasons |
| Research coverage | Required tasks, actual retrieval records, and unresolved gaps |
| Evidence IDs and URLs | Supporting and contradictory sources |
| Information cutoff | Latest time included in the analysis |
| Debate record | Every-stock obligation, pending/completed/deferred status, Bull/Bear cases, unresolved objections, holding implications and exposure verdict |
| Debate and budget policy | Queue order, research budget, uncertainty policy, stressed-loss limits, final confidence target, and loss-risk ceiling |
| Allocation and reservations | Current/pending exposure, applied caps, final quantity/notional, costs, reservation IDs, and limiting constraint |
| Desired exposure and protections | Inputs to deterministic sizing and risk checks |
| Allocator assessment and decision | Confidence/payoff support, final opportunity score, portfolio fit, action, investment rationale, and `ACCEPT`/`REJECT`/`DEFER` |
| Validator authorization | Deterministic `ACCEPT`/`REJECT`/`DEFER`, reservation and reasons, separate from agent/research verdicts |
| Invalidation, review, and expiry | Conditions and deadlines for reassessment |
| Execution status | Proposed, rejected by risk, submitted, partially filled, filled, canceled, or failed |

Trade actions: `OPEN`, `REINFORCE`, `HOLD`, `REDUCE`, `CLOSE`, and `NO_ACTION`. Research/debate states such as `DEFER` are not trade actions.

A proposal is not a confirmed fill. A successful debate does not authorize changing risk policy.

## Related pages

- [Architecture](architecture.md)
- [Analysis team](analysis-team.md)
- [Portfolio Manager](portfolio-allocator.md)
- [Opportunity analysis](opportunity-analysis.md)
- [Budget management](budget-management.md)
- [Agent runtime](agent-runtime.md)
- [Deployment and costs](deployment-and-costs.md)
- [Risk and execution](risk-and-execution.md)

