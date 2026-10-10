# Continuous analysis runtime

[Wiki home](README.md) · [CLI](cli.md) · [Model provider](model-provider.md)

**Implemented in v0.3.0 on Python 3.14, reviewed 2026-10-10.** Four specialist agents run throughout
configurable research cycles. A deterministic supervisor owns scheduling, source
assignment, memory, bounded peer review, report closure and Telegram delivery.
This is a research service; it submits no orders. The existing bounded debate and
allocation graphs remain separate. Closed-cycle reports create every-stock debate
obligations; automatically consuming them in the debate/portfolio pipeline is next.

## What runs

| Component | Implemented behavior |
| --- | --- |
| Supervisor | Singleton database lease, independent collection/worker/report/delivery loops, immediate next-cycle research |
| Market | Macro/sector transmission prompt; sampled Yahoo search and scoped historical context |
| Financial | Earnings/guidance/cash-flow prompt; Yahoo stock leads, financial evidence and original-source follow-up |
| Company | Announcements/filings/products prompt; shared stock leads, optional SEC metadata/IR feeds and authorized page reads |
| Social | Approved-author narrative/corroboration prompt; optional authenticated X adapter, with missing access explicitly reported |
| Analyst tools | Typed READ_EVIDENCE / SEARCH_NEWS / READ_PAGE actions validated and executed by Python; finite LangGraph loop |
| Collaboration | Original findings before peer review; one peer task per original, bounded follow-up tools, preserved claims/questions/dissent |
| Memory | SQLite locally or PostgreSQL; event versions/correction lineage, task checkpoints, actual tool results, leases and fixed report manifests |
| Reports | Financial lead produces initial confidence/scenarios per stock; unavailable synthesis becomes an incomplete report, never an invented HOLD |
| Telegram | Private pairing code, multipart plain-text summaries, durable outbox, quota retry and unknown-delivery tracking |
| CLI | Existing four-pane Textual terminal, continuous status/findings, stored-report chat, optional headless operation |

The supervisor is code, so model output cannot change clocks, source permissions,
budgets or task ownership. The Financial lead is the existing synthesis role;
adding the supervisor does not add another investment manager.

## Run and configure

After [installation and environment activation](cli.md#install-and-connect-telegram),
use `tradingworkflow` for Telegram-only first-run setup. Its onboarding asks for the
bot token, pairs your private chat, sends a test and asks for the hours between
reports without running the analysis team. Later launches reuse saved setup; choose
**Report interval** to change the schedule. See [onboarding](onboarding.md).

First verify the full offline path without credentials:

```bash
tradingworkflow --demo --supervisor --once
tradingworkflow --demo --supervisor
```

The first command advances an injected clock and closes a synthetic cycle immediately;
it does not wait three hours. The second opens the four-pane terminal and keeps the
team running until Ctrl+Q. Ctrl+R requests collection in continuous mode. Demo and
provider state use separate default databases.

Create a private configuration, then edit its watchlist and limits:

```bash
tradingworkflow --init
```

`config.local.json` is ignored by git. Its `instruments` array must contain the
chosen stocks. For example, the instrument shape is
`{"symbol":"NVDA","name":"NVIDIA","sector":"technology"}`; this is a configuration
example, not an investment recommendation. Configure official `ir_feeds`, CIKs,
`article_domains` and approved X author IDs/handles when those sources are available.

Use onboarding for Telegram or supply its token manually in `.env`. Supply the
NVIDIA key in the private `.env` when enabling research:

```dotenv
TRADEBOT_NVIDIA_API_KEY=your_private_key
TRADEBOT_TELEGRAM_BOT_TOKEN=your_private_bot_token
```

No Alpaca/X/search credentials are required just to start continuous Yahoo-based
research. Missing optional sources are recorded as gaps. Alpaca credentials enable
read-only account refresh and mandatory research on actual holdings. With no broker
connection, reports have no executable quote/reference price and cannot authorize
orders. Source sampling is not a complete archive.

Pair Telegram with an explicit one-time command in your private chat:

```bash
tradingworkflow --telegram-pair
tradingworkflow --supervisor --doctor
tradingworkflow --supervisor
# Optional supervised/background process:
tradingworkflow --supervisor --headless
```

Pairing displays the bot link and `/start <one-time-code>`. Only an exact code from
a private chat whose sender matches the chat is accepted. The binding is stored
locally against a token fingerprint; changing the bot requires pairing again.
Alternatively supply an explicitly known numeric `TRADEBOT_TELEGRAM_CHAT_ID`.
Doctor validates local configuration, the effective report interval and a matching
Telegram destination, not live API access. Analysis startup requires a token and
paired chat. Provider `--supervisor --once` waits for one real cycle and attempts
delivery before exiting; it does not fast-forward time. Delivery not yet confirmed
remains durable with its normal retry/unknown-send behavior.

## Operational policy

Defaults: `session_hours=3`, `collection_seconds=300`, four model workers,
`agent_tool_rounds=3`, `agent_timeout_seconds=300`, `task_retries=2`,
`max_cycle_tasks=240`, `cycle_model_budget=8`, `report_language="Italian"`.
`news_hours` independently defaults to three hours. NIM uses
`deepseek-ai/deepseek-v4.1-flash`, 8,192 output tokens and the configured input bound.

Onboarding's saved report interval overrides `session_hours` for continuous research.
Manual setups without a saved interval use the configured `session_hours`. Schedule
changes are read during operation and apply to the next cycle without shortening or
discarding an open cycle. v0.2 cycles can resume across this upgrade when only the
interval changed; changes to source, model, budget or other policy fields still
require restoring the original configuration. Demo mode ignores saved owner settings.

Operating dollars are conservative reservations using the policy's rates, not
verified NVIDIA bills. Monthly limits apply across calls; each cycle reserves 70%
of its model allowance for research and 30% for report synthesis. Per-call
reservations enforce these limits atomically, including concurrent workers and
cycles spanning a month boundary. Idle workers make no model calls. Coverage tasks
run once per role/stock/cycle, not every empty poll. Source quotas remain provider
constraints; real throughput and model quality need a credentialed measurement.

Source collection is deduplicated within a cycle; one Yahoo article shared across
roles is one source, not multiple confirmations. Lookup results and page content
are bounded. Pages must reference known evidence IDs and registered HTTPS domains;
private-address destinations, unregistered redirects and oversized responses are
rejected. Full evidence stays in memory while model context receives limited excerpts.
AgentReach-backed X/transcript provisioning is not integrated yet; the current
optional X path is the existing authenticated adapter.

At a deadline, freeze assessment and evidence IDs, open the next fixed window,
carry unfinished/deferred events forward, and synthesize reports independently.
Late findings cannot change the closed manifest. Crashes resume stored turns/tool
results; a reclaimed task fences the old worker. A crash between closure and carry
is recovered idempotently. Downtime windows and task-cap gaps remain visible.
Busy cycles use bounded hierarchical role summaries before final synthesis;
original assessments remain in the immutable report. Intermediate summaries are
cached against their input digest so a restart can reuse completed work. Failed or
budget-limited synthesis is explicitly incomplete.
Unexpected background-worker failure stops the supervisor and releases its lease,
rather than leaving an apparently running service with a dead subsystem.

## Telegram behavior and review

Each closed cycle queues a plain-text recap for every analyzed watchlist stock and
holding: role findings, initial uncalibrated confidence, dissent, source links,
coverage gaps and unfinished tasks. Summaries are split within Telegram's UTF-16
length limit and sent in part order. Each X-hour window freezes independently while
the next research cycle starts; delivery follows report synthesis and may be delayed
by provider latency or quotas. Keep the process running for recurring reports.

Telegram does not provide our application an exactly-once send key. A timed-out or
interrupted send becomes UNKNOWN and is not automatically resent; later parts of
that summary wait. Successful parts record Telegram message IDs. Rate-limit
responses receive bounded retry, then FAILED. The terminal shows pending, sent,
unknown and failed deliveries. There is no incoming trading-command interface.

CI exercises HTTP fixtures and deterministic clocks, including a full NIM-client →
onboarding/pairing → saved interval → analysts → two consecutive frozen reports →
Telegram-outbox delivery path, including no early report and no duplicate send.
It also uses isolated PostgreSQL
for task-claim and spending concurrency. These prove behavior under controlled
responses, not real model accuracy, account quota or source completeness. A real
NVIDIA/Telegram test follows when owner credentials are supplied.
