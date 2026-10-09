# Session workflow and scheduling

[Wiki home](README.md) · [Project overview](../README.md)

News collection, decision sessions, and execution monitoring run independently.

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
4. Run the four analysts independently, prioritizing all mandatory holding-specific searches.
5. Validate research coverage; retry bounded missing tasks and mark unresolved gaps.
6. Have the Decision Manager publish a per-stock news recap, forecast, and labeled confidence.
7. Review every existing holding and propose `REINFORCE`, `REDUCE`, `CLOSE`, or `HOLD`; distinguish incomplete reviews.
8. Nominate eligible new-entry candidates and perform the bounded Bull/Bear debate.
9. Judge candidates as `APPROVE`, `DEFER`, or `REJECT`; retain both final cases.
10. Build one coherent portfolio proposal from existing-position changes and approved entries. Net by stock and prohibit contradictory same-session orders.
11. Apply the confidence threshold, compute confidence-based total-position ceilings, and allocate one shared budget across openings and reinforcements. Apply cash-reserve, pending-order, risk, liquidity, and protective-order checks; record final `ACCEPT`, `REJECT`, or `DEFER` and reserve permitted capital atomically.
12. Reconcile and refresh quotes before submission; expire proposals that no longer satisfy their conditions.
13. Submit permitted paper orders, monitor fills, and record broker-confirmed state.
14. Persist analyst reports, forecasts, search coverage, decisions, debates, order states, costs, and checkpoints; release the lock.

Session states: `COLLECTING`, `ANALYZING`, `REVIEWING_POSITIONS`, `DEBATING`, `VALIDATING`, `EXECUTING`, then `COMPLETED`, `PARTIAL`, or `FAILED`.

Complete required position reviews before optional debates. Research and execution use distinct checkpoints, so recovery cannot repeat submissions. Proposed exit proceeds remain unavailable until broker state confirms otherwise.

### Proposal contract

| Field | Purpose |
| --- | --- |
| Session, proposal, and stock IDs | Traceability and duplicate prevention |
| Path and action | Existing-position change or new-entry decision |
| Thesis and changes | Forward-looking justification and comparison with the entry thesis |
| Forecast and confidence status | Horizon, exact outcome, estimate, calibration status, and uncertainty |
| Research coverage | Required tasks, actual retrieval records, and unresolved gaps |
| Evidence IDs and URLs | Supporting and contradictory sources |
| Information cutoff | Latest time included in the analysis |
| Debate record | Bull/Bear final cases, unresolved objections, and judge verdict for new entries |
| Budget and confidence policy | Policy version, final `p_trade`, calibration status, entry threshold, and confidence-based target |
| Allocation and reservations | Current/pending exposure, applied caps, final quantity/notional, costs, reservation IDs, and limiting constraint |
| Desired exposure and protections | Inputs to deterministic sizing and risk checks |
| Budget verdict | `ACCEPT`, `REJECT`, or `DEFER`, with reasons distinct from the research verdict |
| Invalidation, review, and expiry | Conditions and deadlines for reassessment |
| Execution status | Proposed, rejected by risk, submitted, partially filled, filled, canceled, or failed |

Trade actions: `OPEN`, `REINFORCE`, `HOLD`, `REDUCE`, `CLOSE`, and `NO_ACTION`. Research/debate states such as `DEFER` are not trade actions.

A proposal is not a confirmed fill. A successful debate does not authorize changing risk policy.

## Related pages

- [Architecture](architecture.md)
- [Analysis team](analysis-team.md)
- [Budget management](budget-management.md)
- [Risk and execution](risk-and-execution.md)
