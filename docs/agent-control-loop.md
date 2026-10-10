# Building the analysts as continuous agents

[Wiki home](README.md) · [Cycle semantics](continuous-analysis.md) · [Agent runtime](agent-runtime.md)

**Target design, not implemented in v0.1.** The current graph calls four analysts
once over a precollected bundle, synthesizes the reports and runs debate. The goal
is four specialists with their own bounded research tools and persistent work
history, invoked repeatedly as new work arrives throughout an X-hour cycle.

## What to borrow from TradingAgents

TradingAgents constructs analyst roles with distinct prompts and tool sets, and
embeds each analyst in a private `agent -> tools -> agent` graph. A finite tool-round
budget forces a report; only that report crosses back to the parent graph. Its
parent graph joins analyst reports, then runs investment debate, a research manager,
a trader, risk debate and a portfolio manager. This is a **bounded run per case**,
not an X-hour autonomous research service. Some roles have no interactive tools;
tool capability depends on the role. See [upstream graph construction](https://github.com/TauricResearch/TradingAgents/blob/main/tradingagents/graph/setup.py)
and [analyst execution plans](https://github.com/TauricResearch/TradingAgents/blob/main/tradingagents/graph/analyst_execution.py).

Keep that small, bounded agent/tool pattern, but add an outer durable scheduler,
event queue and explicit cycle closure. Reusing one unbounded LangGraph invocation
for three hours would make retries, budgets, new arrivals and cycle cutoff harder
to control.

## Agent contract

Give each specialist a versioned role definition: instructions, allowed tools,
input schema, output schema, model choice and per-task/cycle budgets. The same
model can serve several roles initially; different role definitions and source
permissions make the specialization real. The Market Analyst sees sector/market
context; Financial sees earnings, guidance and comparable facts; Company sees
original company disclosures and event details; Social sees authorized X authors
with provenance. A shared event ID connects their separate interpretations.

One invocation has an immutable task envelope: `cycle_id`, `stock_id`,
`event_version_id`, `role`, `as_of`, `prompt_version` and `budget`. Its private
scratch messages are disposable; durable evidence IDs, assessments, questions,
revisions and source-attempt results are the memory. Structured outputs contain
material claims, cited evidence IDs, directional impact, uncertainty, affected
stocks, explicit open questions and a proposed follow-up. A model cannot write
directly to the shared notebook or broker: code validates and commits its output.

## Two nested loops

1. **Short agent loop, per task.** Claim a durable queue item; load the original
   evidence, relevant event/position history and cutoff-aware memories. The agent
   either requests an allowed research tool or submits a typed assessment. The
   controller checks source policy, deadline and remaining budget, runs the tool,
   stores its actual result/attempt ID, then resumes the agent. After a bounded
   number of tool calls, persist a partial assessment and an explicit gap.
2. **Long control loop, across the cycle.** Collectors discover yfinance leads and
   permitted X/source updates at their own cadence. The scheduler deduplicates and
   enqueues event versions, mandatory holding lookups, questions and corrections.
   Workers invoke short agent loops on demand. Original assessments are committed
   before cross-review; peers receive cited findings, may challenge or ask one
   bounded follow-up, and record revisions without erasing dissent. On completion
   they claim another task; while idle they consume no model tokens.

Example: a yfinance headline mentions an NVIDIA CES announcement. A Company task
looks for the original announcement; Financial tests any revenue/guidance claim;
Market compares sector conditions; Social checks only approved accounts. A peer's
question can enqueue another Company lookup. If the primary source cannot be read,
the result remains an unresolved coverage gap. An amended announcement becomes a
new event version; its original assessment stays in the audit trail.

## Durable controller and memory

Start with a PostgreSQL task table leased by `(cycle, event version, stock, role,
stage, prompt version)`, a unique idempotency key and a bounded retry count. Save
news/evidence, assessments and peer messages in application tables. Use LangGraph
checkpoints with a per-task thread ID for resumable reasoning, carrying compact
IDs rather than entire article bodies. A checkpoint does not replace the task
lease, source attempt log or transactional business result. After a crash, reclaim
expired leases, reuse recorded tool results and avoid repeating a completed stage.

Retrieval is scoped: event and stock first, then held-position thesis, relevant
prior questions and settled historical lessons available **as of** the task
cutoff. Retrieve original evidence and contradictory claims, not a growing chat
transcript; keep publication and observation times separate. Newer evidence
cannot silently modify a closed cycle or an earlier forecast.

The controller enforces max in-flight model calls, per-source requests, token/cost
ceilings and fairness. Reserve capacity for all holdings and closing reports;
cycle exhaustion records pending work and gaps. An agent may propose a search,
never override allowlists, budgets, freshness rules, or position limits.

## Closure and downstream handoff

At `cycle_end`, atomically freeze the eligible evidence/assessment manifest and
start the next research cycle. Late results belong to the next cycle. The Financial
lead synthesizes a report for every analyzed watchlist stock and holding, with
the four-category coverage, initial confidence, payoff scenarios and unresolved
questions. Every report creates a debate obligation, regardless of initial score.
Bull and Bear assess confidence against potential and downside; the Orchestrator
records its revised confidence and verdict. The Portfolio Manager then reviews
all completed cases together against measured volatility, cash, pending orders and
portfolio exposure. Code validates/reserves any eventual order independently.

Research in the new cycle continues while debate and portfolio planning consume
the frozen old one. Protective monitoring and broker reconciliation run as
independent deterministic processes. X hours is the report cadence, not a promise
to execute a trade at each boundary.

## Build and verify in slices

| Slice | Implementation | Offline acceptance |
| --- | --- | --- |
| 1 | Role-specific prompts and typed assessment schema on the existing graph | Four distinguishable reports; invalid citations and fabricated tool completions rejected |
| 2 | Event/version tables, queue leases and one Company agent with bounded source tools | A CES-like item deepens to original evidence; duplicate work and crash/retry do not duplicate assessments |
| 3 | Other three specialists, scoped retrieval and cross-review mailbox | Originals precede peer reading; bounded questions produce cited revisions and preserved dissent |
| 4 | Simulated-clock cycle coordinator and immutable manifests | Boundary/late-work/restart cases; all watched and held stocks produce reports; next cycle overlaps debate |
| 5 | Every-stock debate and one portfolio-wide Manager plan | No confidence prefilter; all obligations visible; volatility, cash and pending exposure constrain investment |

Use deterministic fixture data and a simulated clock for timing tests. Real
provider and model behavior needs separate opt-in checks with measured spend;
the initial vertical slice stays research-only. See the
[implementation backlog](implementation-backlog.md) for connector and execution
dependencies.
