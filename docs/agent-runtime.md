# Agent runtime and tool boundaries

[Wiki home](README.md) · [Project overview](../README.md)

## Current implementation: reviewed 2026-10-10

The eight roles run as bounded model calls, not independent services. The current
code has two compiled LangGraph graphs: analyst/synthesis and debate/judgment.
`Workflow.run` sequences collection, holding reviews, the fair debate queue and
allocation previews around those graphs. They are runnable, but real-model quality
and source-account access have not been measured.

| Role | Implemented now | Next improvement |
| --- | --- | --- |
| Market Analyst | Independent report per stock from the supplied bundle | Shared session briefing plus explicit stock relevance and official macro evidence |
| Financial Analyst | Independent report; separate lead call synthesizes all four reports into initial scenarios/confidence | Cutoff-aware financial facts, earnings comparisons and distinct financial instructions |
| Company Analyst | Independent report, with SEC metadata/IR summaries when collected | Read authorized disclosures and distinguish announcement, amendment and analyst interpretation |
| Social Analyst | Report over supplied approved-author X evidence | Distinguish original claims, quotes, reposts and corroborated facts; track coverage gaps |
| Bull and Bear | Independent opening, challenge, rebuttal and final calls: eight turns per stock | Typed material-claim challenges and bounded verification requests |
| Orchestrator | Revised forecast, dissent and approve/defer/reject verdict; runtime checks references and unsupported approvals | Evidence-backed verification verdicts and explicit revision rationale |
| Portfolio Manager | Holding review before debates; separate per-stock post-debate action/notional proposal | One portfolio-wide plan with shared-capital and stress accounting |

Reports are independent of other analysts' conclusions, but **all four currently
receive the same mixed-category snippets**. Role identity and task text differ;
specialist prompt templates, role-scoped inputs and per-role model selection are
not implemented. All calls use one configured OpenRouter model. The Financial
Analyst's lead stage is an additional call, not a ninth specialist role.

The runtime currently gives models at most three evidence snippets per category,
with text truncated to 700 characters each. The next input builder should select
material events, preserve source/content limitations and supply bounded evidence
excerpts with stable IDs. It must not hide an opposing item simply because newer
duplicates consumed the snippet limit.

Models do not invoke research tools today: deterministic code collects evidence
first and passes JSON context. Unexpected model tool calls are rejected. Debate
verification only rereads selected frozen records; it cannot retrieve a missing
filing or substantiate a new external claim. Citation membership and schema checks
do not establish factual correctness, analyst diversity or calibrated confidence.

Stage outputs and input hashes are persisted, but graphs are compiled without a
durable checkpointer. There is no automatic session crash-resume. Confidence/EV
does not filter or rank the debate queue, and no role has a broker submission tool.

### Next agent work, after connector contracts

1. Version specialist prompts and construct role-specific views of one immutable
   evidence bundle. Preserve shared definitions for cutoff, outcome, horizon and
   price so initial/final confidence remains comparable.
2. Introduce a typed `VerificationRequest`: claim/evidence IDs, missing fact,
   permitted source, stock and cutoff. The runtime dispatches it through connector
   permissions, page/cost limits and the required holding-research budget. Each
   side may challenge at most three material claims; requests can return verified,
   contradicted, unresolved or unavailable, with actual attempt IDs.
3. Evidence first observed after a historical cutoff is not retroactively known.
   If fresh retrieval expands the decision's information basis, create a new
   bundle/forecast version and record the change instead of quietly modifying the
   old case. Reprice and re-debate material changes before allocation.
4. Produce one portfolio allocation plan after all completed judgments; apply
   confidence/downside sizing and cash/exposure limits atomically in code. Model
   proposals never reserve cash or submit orders directly.
5. Add checkpointer/job recovery, then evaluate the same frozen cases with actual
   configured models: unsupported claims, conflicting evidence, injection text,
   unresolved verification, repair rate, latency and operating spend. Forecast
   settlement/calibration remains a separate prospective milestone.

The measured demo executes **47 model-stage calls** for three researched/debated
stocks and two holding reviews. Those are deterministic fixtures, not 47 paid API
calls. [Operating costs](deployment-and-costs.md) distinguishes the current call
count from the proposed shared-briefing optimization.

## Target runtime

The [agent control-loop blueprint](agent-control-loop.md) specifies how to turn
the bounded specialist calls into on-demand, tool-using, recoverable agents and
how that differs from TradingAgents' per-case graph.

The [continuous-cycle refinement](continuous-analysis.md) now supersedes the single-pass target: analysts process/cross-review items throughout X hours, freeze report manifests, and create every-stock debate obligations. Research task leases and the portfolio decision lease are separate. The target Portfolio Manager is the current Allocator role, with volatility/portfolio tools. None of this renames or changes the current runtime in this plan update.

Follow the [research workflow](research-workflow.md): analysts can request scoped news/search/page/transcript/social tools and retrieve [persistent event/position context](memory-and-retrieval.md). yfinance supplies leads, AgentReach-selected backends supply research capabilities, and Alpaca supplies broker/market data. Requests are validated and executed by code, with stored attempt IDs and bounded spend.

Implement recoverable research-task/cycle graphs and a separate closed-cycle decision graph. The eight roles are reusable definitions; durable workers invoke them as news or follow-up work arrives. Each specialist records an original item assessment before bounded cross-review; preserve revisions and dissent. At the deadline, freeze the report manifest before lead synthesis. Neither initial probability nor opportunity diagnostics select or order stock-debate admission.

## Proposed graph stages

| Stage | Concrete behavior | Durable output |
| --- | --- | --- |
| Reconcile | Read broker account, positions, pending orders, clock, and policy | Timestamped portfolio snapshot and session cutoff |
| Research | Execute required holding-specific lookup matrix and selected-stock collection | Search attempts, evidence versions, and coverage |
| Analyze/cross-review | Continuous role-scoped item loops; original findings then bounded exchanges | Cited original assessments, revisions, questions and dissent |
| Close/synthesize | Freeze cycle manifest; Financial Analyst assembles report per stock | Cutoff/bundle version, coverage, initial confidence/scenarios and gaps |
| Holding case | Compare news and thesis during research; include every holding at closure | Cited thesis changes and mandatory debate obligation |
| Queue debate | Admit every analyzed-stock report without numerical screening | Holding priority, then fair last-debated/stock-ID queue with visible obligations |
| Debate | Two openings, two challenge sets, bounded verification, two rebuttals, two final cases | Individual turn records and frozen evidence-bundle revisions |
| Judge | Orchestrator assesses cases and defines revised confidence/payoffs | Explained approve/defer/reject research verdict |
| Manage portfolio | Manager assesses debate/holding outcomes, measured volatility and fresh state | One portfolio plan, actions, amount, risk rationale and constraints |
| Validate | Code recomputes caps, checks freshness/coverage, and reserves capital | Independent authorization or rejection/defer, plus order intent |
| Monitor/report | Execution worker and independent monitor reconcile broker states | Fills, protections, costs, and session report |

For added exposure, a completed debate and supported final estimates are mandatory. Ordinary holding management follows every-stock debate; independent deterministic protection and policy-triggered risk reduction remain active without waiting for cycle closure.

## Typed tools

All tools accept schema-validated arguments, attach a request/session/stock ID, enforce source permissions in code, and return evidence or state IDs. The model cannot invent retrieval completion.

| Proposed tool | Who may use it | Implementation boundary |
| --- | --- | --- |
| `lookup_market_context` | Market Analyst | Authorized macro/news adapters, shared briefing with per-stock relevance |
| `lookup_stock_news` | Financial/Company Analysts | Approved provider/domain registry; category and stock scope enforced |
| `get_company_filings`, `get_financial_facts` | Financial/Company Analysts | CIK/IR adapters and cutoff-aware facts |
| `search_approved_x_posts` | Social Analyst | Selected AgentReach-backed X adapter, stable author-ID validation and cost/page cap; official X is optional |
| `get_evidence`, `retrieve_history` | Analysts, debate, Orchestrator, Allocator | Permitted evidence IDs and stock/event/cutoff queries |
| `request_verification` | Bull/Bear via Orchestrator | At most three challenges per side; runtime dispatches bounded analyst lookups |
| `get_portfolio_snapshot`, `preview_allocation_limits` | Allocator | Read broker-confirmed state and call deterministic sizing |
| `submit_allocation_proposal` | Allocator | Store a proposal; it does not submit an order |

No role receives broker submission, source-whitelist editing, unrestricted browsing/shell, or policy-changing tools. Ordinary typed functions suffice; MCP can expose the same read/research contracts later if interoperability is needed. It is not required for the first workflow.

## Structured model execution

Use a thin model-client interface with paid-model configuration and a strict output schema per stage. A stock report cites database evidence IDs; a debate challenge references a material claim, not an arbitrary prompt. Validate probability ranges, finite numbers, scenario probabilities, action enums, stock eligibility, references, cutoff, and outcome consistency locally.

Proposed starting operational settings: four concurrent model calls, 120-second model-call timeout, 15-second connector timeout, one schema-repair attempt, and a 30-minute session deadline. Provider transient-error retries use bounded backoff within the same operating budget. These settings must be measured in the spike, not assumed to meet a production SLA.

Invalid output is recorded and deferred after bounded repair. Do not retry until the verdict changes, average agent votes, or use malformed initial confidence to skip debate. Initial gaps can be investigated; unresolved final gaps prevent added investment. A schema-valid answer is not automatically factually correct or calibrated.

Store graph checkpoints with a session-specific thread ID and PostgreSQL checkpointer. Keep evidence/ledger records in application tables; the graph carries IDs and compact validated state instead of full articles and credentials. A restarted node must reuse a completed business-stage result where its immutable inputs match.

## Research cutoff and quote refresh

Freeze outcome, horizon, reference price, cost assumptions, evidence IDs, and cutoff for initial/final comparisons. Verification may add evidence available by that cutoff. Later news or a material price-basis change creates a new proposal version and refreshed debate; stale approval cannot be silently repriced.

All eligible proposals enter a queue. A session cost/time cap may leave some pending, but never financially rejects them based on initial probability/score. Refresh queued evidence before resumption. A zero-result successful source request differs from a failed or incomplete search.

## Side-effect recovery

Checkpointing does not make external orders exactly-once. The validator writes a cash reservation and stable-client-ID order intent in one database transaction. A separate execution worker submits the intent and queries the broker by that client ID after ambiguous responses before any retry.

Unknown submission retains the reservation. Partial fills convert the filled share into holdings while the rest remains reserved. Only broker-confirmed cancellation/rejection/expiry releases the remaining commitment. The monitor reconciles reconnect gaps and updates protection quantities independently of AI sessions.

## Primary references

- [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)
- [OpenRouter structured outputs and endpoint support](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Pydantic validation](https://docs.pydantic.dev/latest/concepts/models/)
- [Alpaca order behavior](https://docs.alpaca.markets/us/docs/orders-at-alpaca)

## Related pages

- [Analysis team](analysis-team.md)
- [Direct debate](new-entry-debate.md)
- [Portfolio Manager](portfolio-allocator.md)
- [Persistence and contracts](persistence-and-contracts.md)
- [Implementation backlog](implementation-backlog.md)

