# Agent runtime and tool boundaries

[Wiki home](README.md) · [Project overview](../README.md)

Implement one explicit LangGraph session graph. The eight roles are reusable agent definitions, not eight permanently running servers. Four independent analyst reports complete before the Financial Analyst's separate lead/synthesis stage. Construct each analyst's input from the frozen evidence and its assigned scope only; do not expose other analysts' conclusions until synthesis. Neither initial probability nor opportunity diagnostics select or order debate candidates.

## Proposed graph stages

| Stage | Concrete behavior | Durable output |
| --- | --- | --- |
| Reconcile | Read broker account, positions, pending orders, clock, and policy | Timestamped portfolio snapshot and session cutoff |
| Research | Execute required holding-specific lookup matrix and selected-stock collection | Search attempts, evidence versions, and coverage |
| Analyze | One shared Market briefing and stock-specific Financial/Company/Social reports | Structured reports with independent conclusions |
| Synthesize | Financial Analyst acts as lead only after all reports finish | Stock recap, initial confidence/scenarios, or explicit missing estimates |
| Review holdings | Allocator reviews each mandatory holding case | Hold/reduce/close decision or deferred review; reinforcement candidate |
| Queue debate | Admit eligible openings/reinforcements without numerical screening | Fair queue ordered by last debate time, then stock ID |
| Debate | Two openings, two challenge sets, bounded verification, two rebuttals, two final cases | Individual turn records and frozen evidence-bundle revisions |
| Judge | Orchestrator assesses cases and defines revised confidence/payoffs | Explained approve/defer/reject research verdict |
| Allocate | Allocator independently assesses approved cases and proposes one portfolio plan | Action, target exposure, incremental amount, and sizing rationale |
| Validate | Code recomputes caps, checks freshness/coverage, and reserves capital | Independent authorization or rejection/defer, plus order intent |
| Monitor/report | Execution worker and independent monitor reconcile broker states | Fills, protections, costs, and session report |

For added exposure, a completed debate and supported final estimates are mandatory. For risk reduction, researched holding decisions and independent deterministic protection remain available without an entry debate.

## Typed tools

All tools accept schema-validated arguments, attach a request/session/stock ID, enforce source permissions in code, and return evidence or state IDs. The model cannot invent retrieval completion.

| Proposed tool | Who may use it | Implementation boundary |
| --- | --- | --- |
| `lookup_market_context` | Market Analyst | Authorized macro/news adapters, shared briefing with per-stock relevance |
| `lookup_stock_news` | Financial/Company Analysts | Approved provider/domain registry; category and stock scope enforced |
| `get_company_filings`, `get_financial_facts` | Financial/Company Analysts | CIK/IR adapters and cutoff-aware facts |
| `search_approved_x_posts` | Social Analyst | Official X connector, stable author-ID whitelist and cost/page cap |
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
- [Portfolio Allocator](portfolio-allocator.md)
- [Persistence and contracts](persistence-and-contracts.md)
- [Implementation backlog](implementation-backlog.md)
