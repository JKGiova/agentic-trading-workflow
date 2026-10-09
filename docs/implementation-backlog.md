# Concrete implementation backlog

[Wiki home](README.md) · [Project overview](../README.md)

The design is retained. This backlog translates it into code-sized deliverables; none is marked implemented by the documentation update.

## First vertical slice

Build one manually triggered, restartable `research_only` session for a configured stock: retrieve permitted news/X/disclosures, store real request coverage, run four analyst roles and lead synthesis, debate directly, produce the Orchestrator's revised forecast, and let the separate Allocator produce a non-executable proposal.

Use actual source access where available and marked fixtures for offline verification. Do not claim social/news completeness from mock data. Initial confidence/expected return cannot skip debate. Add deterministic budget and paper submission only after this read/research path works.

## Ordered work packages

| ID | Depends on | Code deliverable | Acceptance result |
| --- | --- | --- | --- |
| T0. Access and upstream spike | Owner configuration | Source-capability report; evaluate pinned TradingAgents versus a minimal custom graph; dependency lock | One authorized news, X, SEC/IR, publisher, and quote/calendar sample; gaps/costs recorded; no orders |
| T1. Bootstrap/contracts | T0 | `config/`, `storage/`, Pydantic contracts, migrations, CLI entry point | Invalid settings fail clearly; secrets excluded; mode is research-only; dependency lock reproducible |
| T2. Collectors/evidence | T1 | News, X, SEC/IR and search adapters; versions, cursors, cutoff queries | Empty/failure distinct; deduplication, pagination and restart recovery verified |
| T3. Sessions/coverage | T2 | Jobs, portfolio lease, scheduler, holding lookup matrix | Same-slot enqueue deduplicates; stale workers fenced; every holding has actual category attempts |
| T4. Analyst team | T3 | Four role definitions and Financial Analyst lead stage | Reports cite valid evidence; initial probability may be missing; scenarios/cutoff consistent; no numerical prefilter |
| T5. Direct debate/judgment | T4 | Fair queue, bounded rounds/verification, Orchestrator forecast/verdict | Low initial confidence/edge still debated; immutable cases/revisions; queued work visible; final gaps defer |
| T6. Allocator/preview | T5 | Holding review and separate portfolio-plan agent; deterministic sizing previews | One action/stock; no reinforcement without debate; confidence/downside cap includes holdings/pending buys |
| T7. Paper lifecycle | T6 | Reservations, durable intents, Alpaca paper adapter, independent monitor | Simultaneous budgets cannot overspend; timeout/duplicates/partial fills/cancellations/restart reconciled |
| T8. Prospective evaluation | T5; trading metrics after T7 | Forecast settlement, benchmark/corporate-action handling, calibration and comparisons | Initial/final forecasts settled independently of exits; no future data; losses/costs/coverage reported |
| T9. Dashboard/operations | T3-T8 as available | FastAPI, Streamlit, source/queue/ledger/cost views, supervision/backups | Research-only versus paper visible; dissent/gaps/unknown orders visible; restore/recovery exercised |

T0-T6 can run without order submission. T7 requires a verified paper account and tested limits; live mode is outside this prototype. Backend/API and dashboard remain separable.

## Minimum verification by milestone

- **Data:** provider timestamps, missing dates, pagination caps, author/domain enforcement, corrections, stale headlines, and three-hour/backlog behavior.
- **Agents:** fabricated citations/retrieval claims, malformed probabilities/scenarios, prompt-injection content, model/provider changes, and bounded repair.
- **Debate:** independent openings, exact round caps, verification cutoff, no initial score filtering, fair queue, and reasoned dissent.
- **Allocator:** separate role/tools, final confidence lineage, unchanged/reduce/close handling, total-position reinforcement sizing and risk caps.
- **Execution:** reserved intent atomicity, concurrency, ambiguous HTTP response, stable client IDs, duplicate broker events, partial protection quantities and reconnect gaps.

Run routine CI against deterministic fixtures and a real test PostgreSQL instance where concurrency matters. Provider integrations are separately enabled and charge-aware; never contact broker submission or funded providers merely by importing a test. Publish measured checks only after implementation exists.

## Next concrete task

Start **T0**: choose the prototype's authorized watchlist and X authors, validate the five access paths, and compare a pinned upstream analysis with the minimal custom role graph on the same sanitized evidence. Record dependency/runtime compatibility, source limitations, latency, token usage, and the exact adaptations needed.

Use the model candidates and cost assumptions as experiments. Do not choose a framework or stronger model based only on a polished report or claimed profitability.

## Definition of prototype completion

One recoverable scheduled paper workflow covers all holdings, sends all admissible additions to fair bounded debate, preserves both forecasts, produces a separate Allocator decision, independently validates/reserves/submits permitted paper orders, monitors them continuously, and reports prospective outcomes and operating costs. No live-readiness or calibrated-forecast claim follows automatically.

## Related pages

- [Implementation plan](PLAN.md)
- [Implementation stack](implementation-stack.md)
- [Connector implementation](connector-implementation.md)
- [Agent runtime](agent-runtime.md)
- [Persistence and contracts](persistence-and-contracts.md)
- [Deployment and costs](deployment-and-costs.md)
