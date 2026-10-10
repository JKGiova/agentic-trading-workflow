# Persistent memory and data retrieval

[Wiki home](README.md) · [Research workflow](research-workflow.md)

**Target design, 2026-10-10.** Current evidence/stage/chat persistence is a foundation;
event memory, this retrieval pipeline and persistent graph resume are still pending.

Memory means storing facts and retrieving the right subset for a new question.
It does not require keeping an ever-growing conversation in every agent prompt.

## Separate stores and responsibilities

| Memory | Records | How it is used |
| --- | --- | --- |
| Workflow checkpoint | Session/thread ID, current node, pending requests, completed stage IDs, bundle version | Resume an interrupted session; persistent LangGraph checkpointer |
| Evidence archive | Original source, permitted text/reference, versions, dates, hashes, chunks | Reconstruct and cite what was actually retrieved |
| Event knowledge | Event identity, company links, cited claims, corrections, contradictions, unanswered questions | Follow a conference, earnings release or regulatory case across sessions |
| Position memory | Entry thesis, invalidation conditions, reviews, decisions, broker-confirmed outcomes | Compare new evidence with the reason for holding the stock |
| Decision and lesson memory | Immutable forecasts/decisions, settled outcomes, reflective hypotheses | Inspect past reasoning and test lessons without future leakage |

PostgreSQL is the business source of truth. Use separate LangGraph checkpoint tables
for graph state. A graph Store can expose application memory, but must not create a
second unsynchronized copy of the evidence/financial ledger. SQLite remains suitable
for local tests/demo with a persistent SQLite checkpointer if needed; PostgreSQL is
the first deployment target. In-memory savers do not survive process restarts.

## Proposed records

Extend [persistence contracts](persistence-and-contracts.md) with:

| Record | Required information |
| --- | --- |
| `research_events`, `event_versions` | Stable event ID, type, instrument links, event date, recorded time, cited summary, lifecycle and predecessor |
| `evidence_chunks` | Evidence-version ID, ordinal, section/timecode, exact text or allowed reference, text hash and optional embedding metadata |
| `claims`, `claim_evidence` | Statement, stock/event, supporting or opposing evidence, verification status, validity and recorded times |
| `research_questions` | Question, requester, event/stock, source scope, attempts, pending/resolved/unavailable status and next review |
| `retrieval_manifests` | Session/role/query, filters, selected evidence versions, ranking rationale, budget and omitted/gapped content |
| `decision_outcomes`, `lessons` | Decision/forecast ID, horizon/benchmark/costs, outcome-known time, reflection, evidence and validation status |

Summaries, claims and lessons are model-derived interpretations, not new primary
sources. Preserve their evidence lineage and prompt/model version. Updates append
a version and supersession link; corrections do not erase what an earlier session saw.

## Write path

1. Persist each search attempt, including failures and empty results.
2. Normalize provider identity, timestamps and content level. Atomically write
   evidence versions and cursor progress; restart with overlap after an uncertain write.
3. Link instruments deterministically where possible, then record uncertain mappings.
   Group repeated coverage by original announcement/event, retaining attribution.
4. Split readable text into bounded sections, initially around 500-800 tokens with
   small overlap. Preserve transcript timecodes and tables/units when applicable.
5. Extract candidate claims and event summaries with evidence IDs. Validate references
   and distinguish supported, contradicted and unresolved claims. A citation check
   establishes lineage, not factual correctness; material claims need verification.
6. Save role reports, forecasts, debate results, thesis revisions and decisions.
7. A separate settlement job computes outcomes at the defined horizon and records
   when those outcomes became known. Reflective lessons begin as unvalidated hypotheses.

Do not store private credentials in any memory. Enforce source-specific retention;
deleting prohibited content also removes derived chunks/embeddings and records the
availability change, while retaining permitted audit metadata. Raw research and
portfolio history stay in private storage and never in the GitHub wiki.

## Read path: start with SQL and full-text search

Begin with PostgreSQL indexed instrument/event/time filters and full-text search.
Add `pgvector` only if measured retrieval misses justify semantic search. Embeddings
are a search index over evidence, not the memory source of truth.

For each stock and question:

1. Apply access, instrument/event scope, retention and cutoff filters first. Evidence
   requires `observed_at <= cutoff`; each derived record also requires its own
   `recorded_at <= cutoff`. A lesson additionally requires `outcome_known_at <= cutoff`.
2. Retrieve the position thesis, unresolved questions and required fresh coverage.
3. Retrieve recent news, relevant older event versions and primary documents. Search
   names/aliases and lexical terms; optionally combine a later semantic index.
4. Diversify by underlying event/original source, preserve contradictions and choose
   passages relevant to the role. Similarity and freshness alone must not remove dissent.
5. Build a bounded context package containing source IDs, dates, excerpts, limitations
   and a retrieval manifest. Start around 6,000 evidence tokens per analyst and measure
   whether it preserves material facts. Budgets are configurable and role-specific.
6. If the answer remains unsupported or the evidence is stale, open a targeted
   external research request rather than letting memory pretend to supply the fact.

Query and selected-version logs make the report reproducible. Cache keys include
stock/event, question, cutoff, source-policy version, bundle version and role. A cache
hit retains original acquisition time and does not count as a new holding lookup.
Semantic neighbors from other companies are labelled analogies, not stock evidence.

Example: asking "Has the new product become available?" retrieves the original CES
announcement, its promised release window, later corrections, any launch evidence,
and the holding thesis. It should not retrieve only the most recent bullish headline.

## Decisions, lessons and confidence

Retrieve a small number of prior same-stock decisions and relevant settled lessons,
with pending outcomes clearly labelled. A winning trade does not prove its rationale
was correct; a losing trade does not establish that the forecast was badly calibrated.
Assess forecasts over many settled cases with fixed definitions and costs.

Do not adjust risk limits, confidence calibration or investment policy automatically
from an LLM reflection. Keep reflections separate from prospective calibration data.
Counterfactual forecasts are settled independently of whether a trade was executed.

## Recovery

Use a stable session UUID as LangGraph `thread_id`. Checkpoints store references to
immutable business records, not all source documents. A repeated read task checks its
durable request/result key before issuing a second billable call. Distinguish persisted
results from unknown remote outcomes; checkpointing alone cannot guarantee exactly-once
external calls or broker effects. Reconciliation is required for those effects.

Resume restores bundle/policy versions and pending work. Material post-cutoff evidence
creates a new research revision. A completed decision and a resumed stage must not
append a second forecast/lesson or duplicate a capital reservation.

## Development and verification order

1. Evidence/event migrations, versioning and exact cutoff queries.
2. Instrument/event/full-text retrieval and auditable context assembly.
3. Typed analyst search/read loops and durable request IDs.
4. Graph checkpoint/resume and failure injection.
5. Position-thesis retrieval and decision/outcome memory.
6. Retrieval evaluation, then optional embeddings and lesson experiments.

Use small labelled fixtures with known answers: the relevant original disclosure is
retrieved; a contradiction survives duplicate-heavy news; later corrections and
future outcomes are excluded from replay; inaccessible text remains inaccessible;
restart restores pending work without silently paying twice for a persisted result.
Run PostgreSQL integration tests for transactions/checkpoints; model-backed retrieval
quality is a separate opt-in evaluation, not established by deterministic fixtures.

## What we borrow from TradingAgents

At inspected commit `1394a3f72aa4393e1a98f51b382434c4b4c2d972`, its memory log saves
decisions and later settlement/reflection information, retrieves recent same-stock
and cross-stock lessons, and applies an outcome-resolution cutoff when requested.
We retain this separation but add structured event/evidence memory and intraday
timestamps. This is an adaptation plan, not a claim that we installed its code.

- [TradingAgents memory implementation](https://github.com/TauricResearch/TradingAgents/blob/1394a3f72aa4393e1a98f51b382434c4b4c2d972/tradingagents/memory/log.py)
- [LangGraph persistence, checkpointers and cross-thread stores](https://docs.langchain.com/oss/python/langgraph/persistence)
