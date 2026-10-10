# Agent runtime and tool boundaries

[Wiki home](README.md) · [Project overview](../README.md)

## Current implementation: v0.2, reviewed 2026-10-10

The [continuous research team](continuous-runtime.md) runs four specialist
LangGraph agent/tool loops under a durable supervisor. The default model client
is NVIDIA NIM / DeepSeek V4.1 Flash for the team, synthesis, chat and the separate
legacy decision workflow. Source access and real-model quality still need the
credentialed owner pilot.

| Role | Implemented now | Remaining work |
| --- | --- | --- |
| Market Analyst | Macro/sector prompt, scoped evidence/history, Yahoo search and bounded tools | Measure source coverage and market relevance on real cases |
| Financial Analyst | Financial prompt, earnings/guidance claims, original/peer findings and lead synthesis | Cutoff-aware numerical company facts and model evaluation |
| Company Analyst | Announcements/filings prompt, Yahoo leads, optional SEC/IR and registered page reads | Full typed SEC facts and AgentReach transcript capabilities |
| Social Analyst | Approved-author prompt, optional authenticated X, explicit coverage gaps | AgentReach-backed author/date capability and real account setup |
| Bull and Bear | Existing bounded opening/challenge/rebuttal/final graph | Consume each closed-cycle obligation and verify external claims |
| Orchestrator | Existing structured revised forecast/verdict and citation validation | Integrate closed-cycle evidence revisions |
| Portfolio Manager | Existing per-stock action/notional previews | One portfolio-wide volatility/capital plan |

Original specialist findings are saved before peer review. Role instructions,
scoped context, known evidence IDs and tool policy differ. Each agent can request
READ_EVIDENCE, SEARCH_NEWS or READ_PAGE through a validated typed action, then
resume from the result. Tool loops and retries are bounded. Native function calls
and hosted JSON Schema enforcement are not assumed; unexpected native calls are
rejected. Local schema/citation checks do not prove factual correctness or
calibrated confidence.

The supervisor persists task inputs, model turns, pending tool requests/results,
completed findings, corrections, peer revisions and frozen report manifests.
Database leases fence stale workers. These application checkpoints recover a
restarted agent without repeating a committed turn; graphs are still compiled
without a LangGraph checkpointer backend. Full filing text, transcript provisioning,
semantic retrieval and automatic decision recovery remain separate milestones.

Cycle closure creates a report and durable debate obligation for every analyzed
watchlist stock and holding, without a confidence/EV prefilter. New research runs
while report synthesis and Telegram delivery finish. Automatic execution of the
closed-cycle debate/portfolio pipeline is pending. The older bounded eight-role
session remains available separately; its allocation proposals cannot submit orders.

Operating budgets enforce monthly and per-cycle call reservations atomically.
Cycle research uses 70% of its allowance and report closure uses 30%. A missing
source, exhausted budget or failed model creates an explicit gap; a task is not
rerun just because the model's conclusion is unwelcome. Unknown NVIDIA billing
retains conservative reservations. The historical 47-call demo measurement applies
to the old three-stock decision workflow, not to the continuous team.

## Target runtime

Use [NVIDIA NIM / DeepSeek V4.1 Flash](model-provider.md) for all initial model
roles and chat. The adapter is implemented; real endpoint access and quality still require the
credentialed capability tests.

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
- [NVIDIA NIM model endpoint](https://build.nvidia.com/deepseek-ai/deepseek-v4.1-flash)
- [Pydantic validation](https://docs.pydantic.dev/latest/concepts/models/)
- [Alpaca order behavior](https://docs.alpaca.markets/us/docs/orders-at-alpaca)

## Related pages

- [Analysis team](analysis-team.md)
- [Direct debate](new-entry-debate.md)
- [Portfolio Manager](portfolio-allocator.md)
- [Persistence and contracts](persistence-and-contracts.md)
- [Implementation backlog](implementation-backlog.md)

