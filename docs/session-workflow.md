# Session workflow and scheduling

[Wiki home](README.md) · [Project overview](../README.md)

News collection, decision sessions, and execution monitoring run independently. Implement the triggers with one APScheduler 3.x process feeding unique PostgreSQL jobs; the session worker runs the explicit LangGraph workflow. See [runtime](agent-runtime.md), [concurrency contracts](persistence-and-contracts.md), and [deployment](deployment-and-costs.md).

| Process | Proposed starting frequency | Responsibility |
| --- | --- | --- |
| Source collection | Every 5 minutes | Fetch new authorized content, record acquisition times, and recover missed items |
| AI decision session | Every 3 hours; configurable to X hours | Review existing holdings, evaluate opportunities, and propose actions |
| Order and risk monitoring | Continuous while applicable markets are active | Track fills, protections, exposure, data freshness, and operational failures |
| Session reporting | After every session | Save evidence, proposals, risk outcomes, execution status, and costs |

Market calendars and time zones must be explicit. Store timestamps in UTC and use the selected exchange calendar for market-open checks. Only one decision session per portfolio may run at a time.

If sessions are more than three hours apart, process the unhandled backlog since the last successful session as well as the latest three-hour window. If they are closer together, identify evidence already considered. A restart must not silently lose news or repeat trades.

## Decision-session workflow

1. Acquire a portfolio lock, create a session ID, and establish an evidence cutoff.
2. Reconcile broker holdings, cash, fills, and pending orders; build the union of watchlist and held stocks.
3. Collect new evidence and relevant history, including unprocessed backlog.
4. Run the four analysts independently, prioritizing mandatory holding-specific searches.
5. Validate coverage; retry bounded missing tasks and mark unresolved gaps.
6. Have the Analyst Lead synthesize the team's stock recaps, forecasts, labeled `p_initial`, scenario payoffs, stressed downside, robust edge, and opportunity score; retain the independent reports.
7. Send every mandatory holding case to the Portfolio Allocator for hold/reduce/close review and identification of possible reinforcements. Preserve incomplete-review status.
8. Queue all admissible openings and reinforcements for debate without a confidence, edge, or score filter.
9. Run the bounded Bull/Bear protocol in least-recently-debated order, then stock ID. Proposals beyond the session budget remain queued; initial estimate gaps are investigated within the verification budget.
10. Have the Orchestrator publish revised `p_final` when supported, payoff/downside assumptions, diagnostics, revision reasons, and `APPROVE`/`DEFER`/`REJECT`. Retain the initial records and both final cases.
11. Send approved, current, supportable research cases to the Allocator. Record rejected/deferred cases and unresolved gaps; no numerical opportunity gate is applied.
12. Have the Portfolio Allocator independently assess final confidence and portfolio fit, choose position actions and investments using sizing tools, and produce one coherent plan. Net by stock and prohibit contradictory orders.
13. Recompute deterministic confidence and stressed-loss ceilings, cash-reserve, pending-order, risk, liquidity, and protection constraints; reserve validated capital atomically. Record the agent's decision separately from the validator's final authorization.
14. Reconcile and refresh quotes before submission; expire materially changed proposals. Submit permitted paper orders, monitor fills, and record broker-confirmed state.
15. Persist analyst reports, both confidence/payoff records, debate queue and research verdicts, revisions, coverage, holding reviews, debates, allocation assessments, validator outcomes, order states, costs, and checkpoints; release the lock.

Session states: `COLLECTING`, `ANALYZING`, `REVIEWING_POSITIONS`, `QUEUED_FOR_DEBATE`, `DEBATING`, `JUDGING`, `ALLOCATING`, `VALIDATING`, `EXECUTING`, then `COMPLETED`, `PARTIAL`, or `FAILED`.

Complete required holding reviews before optional entry debates. Rejection of added exposure never skips an existing holding's research or blocks a justified reduction/close. Research and execution have distinct checkpoints; recovery must not repeat submissions. Proposed exit proceeds remain unavailable until broker confirmation and applicable account rules permit their use.

### Proposal contract

| Field | Purpose |
| --- | --- |
| Session, proposal, and stock IDs | Traceability and duplicate prevention |
| Path and action | Existing-position change or new-entry decision |
| Thesis and changes | Forward-looking justification and comparison with the entry thesis |
| Forecast and confidence lineage | Outcome ID, horizon, reference-price basis, `p_initial` and `p_final` record IDs/values, calibration statuses, and revision reasons |
| Research coverage | Required tasks, actual retrieval records, and unresolved gaps |
| Evidence IDs and URLs | Supporting and contradictory sources |
| Information cutoff | Latest time included in the analysis |
| Debate record | Completed or skipped, Bull/Bear final cases, unresolved objections, and Orchestrator verdict for any addition |
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
- [Portfolio Allocator](portfolio-allocator.md)
- [Opportunity analysis](opportunity-analysis.md)
- [Budget management](budget-management.md)
- [Agent runtime](agent-runtime.md)
- [Deployment and costs](deployment-and-costs.md)
- [Risk and execution](risk-and-execution.md)
