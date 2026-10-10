# Persistence, contracts, and concurrency

[Wiki home](README.md) · [Project overview](../README.md)

This is the proposed application data model. Implement it through versioned Alembic migrations after the source-access spike. PostgreSQL holds business truth; LangGraph checkpoint tables are separate workflow state.

## Logical tables

The [memory design](memory-and-retrieval.md) extends these contracts with event versions, evidence chunks, claims, unresolved questions, retrieval manifests and settled lessons. Each derived record has its own recorded-time cutoff; LangGraph checkpoints store references and resume state rather than replacing this ledger.

| Tables | Key records and constraints |
| --- | --- |
| `instruments`, `source_configs` | Instrument identity, watchlist eligibility, CIK/aliases, author/publisher whitelist and policy version |
| `source_cursors`, `evidence_items`, `evidence_versions` | Provider/source IDs, durable pagination/backfill state, accessible text/reference, publication/acquisition/revision times, hash and rights metadata |
| `evidence_instruments` | Many-to-many evidence/stock link with explicit mapping confidence or reason |
| `sessions`, `session_stocks` | Portfolio, slot, cutoff, snapshot/policy versions, state, coverage, and stage results |
| `search_tasks`, `search_attempts` | Required stock/category tasks and actual requests, pages, statuses, matched evidence, retries and usage |
| `analyst_reports`, `report_evidence` | Immutable role/stock reports and evidence foreign-key links |
| `forecasts` | Initial/final stage, outcome ID, horizon, reference price, probabilities/scenarios, model/prompt/calibration versions, expiry and settlement |
| `debate_queue`, `debates`, `debate_turns` | Queue age, round/role content, verification links, bundle versions, dissent and research verdict |
| `portfolio_snapshots`, `position_theses` | Broker-confirmed positions/cash/pending orders and entry thesis/review/invalidation history |
| `allocation_plans`, `allocation_proposals` | Allocator judgment, target amount, tool-derived caps, rationale and validator result |
| `reservations`, `order_intents`, `orders`, `broker_events` | Cash/risk commitments, stable client order ID, broker state, quantities, fills, and deduplication |
| `jobs`, `portfolio_leases`, `usage_events` | Durable work claims, one-session ownership, fencing token, cost reservations and actual usage |

Start with evidence, coverage, sessions, jobs, and usage tables; add debate and execution tables in their corresponding milestones. Keep relational identifiers/indexed timestamps outside JSONB; validated narrative/scenario payloads can use JSONB.

Use UTC `timestamptz` for event times, explicit exchange-calendar dates for settlement, and decimal/numeric arithmetic for currency, prices, and quantities. Avoid floating-point money. Forecast probabilities and scenario fractions need finite bounds and explicit decimal conventions.

## Immutable contracts

| Object | Required fields |
| --- | --- |
| `EvidenceRef` | ID/version, source, URL, stock links, publication/acquisition times, usable content status and hash |
| `CoverageResult` | Stock/category, task and executed-attempt IDs, request window, pagination completeness, coverage state and gaps |
| `AnalystReport` | Role, stock/context, cutoff, summary, citations, direction, assumptions, disagreement and coverage |
| `Forecast` | Outcome ID, stock/stage, price/horizon/cost definition, probability or missing status, scenarios, uncertainty, citations, model metadata and expiry |
| `DebateVerdict` | Initial/final references, both cases, verified challenges, unresolved gaps, revised estimates, verdict and explanation |
| `AllocationProposal` | Stock/action, final forecast/verdict, current/pending exposure, target/increment, caps, rationale, safeguards and expiry |
| `OrderIntent` | Proposal/policy IDs, paper account, stable client ID, executable quantity, reservation, protection requirements and lifecycle state |

Forbid unknown output fields where appropriate and validate references against the stored bundle. Scenarios must have nonnegative probabilities summing to one within a documented tolerance and agree with the positive-net-return probability. Missing initial estimates remain legitimate debate inputs; missing final sizing/coverage inputs cannot authorize added risk.

A new forecast revision links to its predecessor. Do not overwrite an original probability after its outcome becomes known. Reference content that cannot be retained is explicitly unavailable, subject to source policy.

## Uniqueness and useful indexes

Propose unique provider/item IDs; provider/item/version hashes; portfolio/scheduled-slot session IDs; session/stock/category/task keys; stage/stock/input-version report keys; and client-order IDs. Deduplicate broker events using a provider event key or a documented deterministic event fingerprint.

Index evidence/stock links and acquisition/publication time, search session/stock/category, forecast outcome/settlement/state, pending queue order, job status/available time, and open order/reservation portfolio/state. Add foreign-key-side indexes used in joins and verify plans with realistic fixtures. Do not create a vector index before simple stock/event/time retrieval is measured.

## Concurrency and transactions

- A singleton scheduler inserts jobs with unique slot keys; trigger retries cannot create duplicate sessions.
- Workers claim jobs atomically with `FOR UPDATE SKIP LOCKED`, record ownership/lease expiry, and commit before network/model work. Recover expired claims with a bounded retry policy.
- A short transaction claims a portfolio lease and increments its fencing token. Heartbeats renew it; stale workers must fail the token check before mutating decisions or intents.
- Do not hold a database transaction during news/model calls. Scheduler `max_instances` alone does not lock other processes or replicas.
- Budget validation locks the relevant portfolio budget row, checks fresh broker/snapshot/policy versions, accounts for pending commitments, reserves capital, and writes the order intent atomically.
- Submission and broker-event processing are idempotent business operations. External HTTP success is not inferred from a timeout.
- An unknown broker order or unrecognized external account activity blocks new exposure pending reconciliation. Prefer one strategy per paper account.

Keep the financial ledger's transactional connection handling separate from graph-checkpointer connection settings. An advisory lock can support a single-process prototype only when its owning connection is held explicitly; connection-pool reuse must not accidentally release or transfer ownership.

## First persistence verification

Prove: evidence deduplication/versioning, cutoff-safe retrieval, empty versus failed search, same-slot job deduplication, lease recovery after process death, stale-worker fencing, simultaneous capital requests, intent/reservation atomicity, duplicate events, partial fills, and timeout-after-submission recovery. These are future implementation checks, not tests already run.

## Primary references

- [PostgreSQL locks](https://www.postgresql.org/docs/current/explicit-locking.html)
- [SQLAlchemy](https://docs.sqlalchemy.org/) and [Alembic migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [LangGraph state persistence](https://docs.langchain.com/oss/python/langgraph/persistence)

## Related pages

- [Agent runtime](agent-runtime.md)
- [Budget management](budget-management.md)
- [Validation](validation.md)
- [Implementation backlog](implementation-backlog.md)

