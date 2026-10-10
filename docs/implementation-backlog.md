# Concrete implementation backlog

[Wiki home](README.md) · [Project overview](../README.md)

The design is retained. This backlog translates it into code-sized deliverables; none is marked implemented by the documentation update.

## Continuous-cycle priority

The [owner update](continuous-analysis.md) supersedes single-pass research and entry-only debates. Add W3a durable news-task workers and bounded analyst exchanges, W4a fixed cycle boundaries/report manifests with next-cycle overlap, and W5a every-stock debate obligations plus a volatility-aware Portfolio Manager. The original W0-W5 evidence/retrieval/recovery prerequisites remain. Acceptance uses a simulated clock: all report obligations are present, late results cannot alter a closed manifest, research continues during debate, and budget exhaustion remains visible.

## First vertical slice

Build one restartable `research_only` cycle for a configured stock using a simulated clock: process queued news across the window, store real request coverage and role assessments, cross-review findings, close the report manifest, debate the stock, define revised confidence, and produce a nonexecutable Portfolio Manager plan. Keep the next research cycle running while decision work completes.

Use actual source access where available and marked fixtures for offline verification. Do not claim social/news completeness from mock data. Initial confidence/expected return cannot skip debate. Add deterministic budget and paper submission only after this read/research path works.

## Ordered work packages

| ID | Depends on | Code deliverable | Acceptance result |
| --- | --- | --- | --- |
| T0. Access and upstream spike | Owner configuration | Source-capability report; evaluate pinned TradingAgents versus a minimal custom graph; dependency lock | One authorized news, X, SEC/IR, publisher, and quote/calendar sample; gaps/costs recorded; no orders |
| T1. Bootstrap/contracts | T0 | `config/`, `storage/`, Pydantic contracts, migrations, CLI entry point | Invalid settings fail clearly; secrets excluded; mode is research-only; dependency lock reproducible |
| T2. Collectors/evidence | T1 | News, X, SEC/IR and search adapters; versions, cursors, cutoff queries | Empty/failure distinct; deduplication, pagination and restart recovery verified |
| T3. Sessions/coverage | T2 | Jobs, portfolio lease, scheduler, holding lookup matrix | Same-slot enqueue deduplicates; stale workers fenced; every holding has actual category attempts |
| T4. Analyst team | T3 | Continuous role/task loops, bounded cross-review and deadline report manifests | Original findings/revisions/dissent preserved; late work excluded; report per stock; no numerical prefilter |
| T5. Direct debate/judgment | T4 | Every-stock obligations, fair queue, bounded rounds/verification and Orchestrator verdict | Holdings/HOLD/NO_ACTION included; no initial confidence filtering; incomplete obligations visible; final gaps defer |
| T6. Manager/preview | T5 | Separate volatility-aware portfolio-plan agent and deterministic sizing previews | One action/stock; approved additions only; confidence/downside, liquidity, correlation and pending buys considered |
| T7. Paper lifecycle | T6 | Reservations, durable intents, Alpaca paper adapter, independent monitor | Simultaneous budgets cannot overspend; timeout/duplicates/partial fills/cancellations/restart reconciled |
| T8. Prospective evaluation | T5; trading metrics after T7 | Forecast settlement, benchmark/corporate-action handling, calibration and comparisons | Initial/final forecasts settled independently of exits; no future data; losses/costs/coverage reported |
| T9. Terminal/operations | T3-T8 as available | Textual four-pane CLI, source/queue/ledger/cost views, supervision/backups | Research-only versus paper visible; dissent/gaps/unknown orders visible; restore/recovery exercised |

T0-T6 can run without order submission. T7 requires a verified paper account and tested limits; live mode is outside this prototype. Internal services remain separate from the owner's single-window terminal. [v0.1 status](development-status.md) records implemented subsets rather than marking these whole milestones complete.

## Minimum verification by milestone

- **Data:** provider timestamps, missing dates, pagination caps, author/domain enforcement, corrections, stale headlines, and three-hour/backlog behavior.
- **Agents:** fabricated citations/retrieval claims, malformed probabilities/scenarios, prompt-injection content, model/provider changes, and bounded repair.
- **Debate:** independent openings, exact round caps, verification cutoff, no initial score filtering, fair queue, and reasoned dissent.
- **Allocator:** separate role/tools, final confidence lineage, unchanged/reduce/close handling, total-position reinforcement sizing and risk caps.
- **Execution:** reserved intent atomicity, concurrency, ambiguous HTTP response, stable client IDs, duplicate broker events, partial protection quantities and reconnect gaps.

Run routine CI against deterministic fixtures and a real test PostgreSQL instance where concurrency matters. Provider integrations are separately enabled and charge-aware; never contact broker submission or funded providers merely by importing a test. Publish measured checks only after implementation exists.

## Workflow-first packages: current priority

The owner selected Alpaca, yfinance and AgentReach and prioritized understanding/developing memory and search. The following packages refine T0-T6/C0-C4; they do not bypass T7 execution prerequisites or declare older packages complete.

| Package | Deliverable | Acceptance |
| --- | --- | --- |
| W0. Provider contracts | Pin selected backends; typed yfinance leads, AgentReach capabilities and Alpaca timestamps | Fixture parsing, tab/cache isolation, author/domain policy, failures versus sampled empty results; opt-in access checks separate |
| W1. Research memory | Alembic evidence/event/claim/question versions and cutoff-aware SQL queries | Corrections immutable, event duplicates linked, future observations/summaries excluded; PostgreSQL transaction tests |
| W2. Retrieval | Instrument/event/full-text context assembly and retrieval manifests | Relevant original disclosure and contradictions retained within budget; stale cache cannot satisfy fresh holding research |
| W3. Analyst tools | Scoped search/read/transcript/social loops, durable requests and bounded budgets | CES-like lead deepened to available primary evidence; unavailable transcript/identity remains a gap; no arbitrary shell |
| W4. Recoverable graph | Persistent checkpoint/thread ID, stage references, verification revisions | Crash before/after durable tool result resumes correctly; persisted result reused; cutoff advance reruns affected reasoning |
| W5. Decisions and lessons | Position-thesis retrieval, portfolio-wide preview, outcome settlement and reflective hypotheses | Every holding reviewed; reinforcement debated; future lessons excluded; both confidence stages retained |

Implement W0 then W1/W2, then W3/W4 as one restartable stock slice, then W5 and broader coverage. Optional embeddings follow measured lexical-retrieval evaluation. [Research workflow](research-workflow.md) gives the graph and example; [memory and retrieval](memory-and-retrieval.md) gives write/read paths and failure cases.

## Next concrete task

The custom research graph and terminal now exist. Start the refined **C0+C1**
packages in [connector implementation](connector-implementation.md): typed source
capabilities, timestamped quotes and content/version contracts, a source registry,
and a bounded opt-in read-only probe. T0 real access still needs the authorized
watchlist, X IDs/handles, publisher access and private provider credentials. Fixture
tests can be implemented before those accounts are available.

Then implement C2/C3 collection and C4 evidence/verification before improving agent
research autonomy. C5 broker reconciliation precedes C6 paper intents/protection;
use the [trading acceptance matrix](trading-connectors.md). The current shared-model,
fixed-evidence agent implementation and remaining work are detailed in
[agent runtime](agent-runtime.md). Upstream/model comparison remains an optional
measured experiment, not a reason to discard the implemented custom graph.

Use the model candidates and cost assumptions as experiments. Do not choose a framework or stronger model based only on a polished report or claimed profitability.

## Definition of prototype completion

One recoverable scheduled paper workflow covers all holdings, creates fair bounded debate obligations for every analyzed-stock report, preserves both forecasts, produces a separate Allocator decision, independently validates/reserves/submits permitted paper orders, monitors them continuously, and reports prospective outcomes and operating costs. No live-readiness or calibrated-forecast claim follows automatically.

## Related pages

- [Implementation plan](PLAN.md)
- [Implementation stack](implementation-stack.md)
- [Connector implementation](connector-implementation.md)
- [Agent runtime](agent-runtime.md)
- [Persistence and contracts](persistence-and-contracts.md)
- [Deployment and costs](deployment-and-costs.md)

