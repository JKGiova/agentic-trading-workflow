# Trading connectors: read first, paper execution later

[Wiki home](README.md) · [News connectors](connector-implementation.md) · [Risk policy](risk-and-execution.md)

Reviewed **2026-10-10**. `AlpacaReadOnly` is implemented; the interfaces, financial
ledger and execution lifecycle below are planned. No order-submission method or
live-trading mode is introduced by this document.

## First broker scope and boundaries

Use Alpaca paper for the first US-equity integration. The first execution slice is
long-only, without leverage, regular-session trading and whole-share quantities.
Fractional shares, extended sessions, shorting and other brokers require separate
capability/test work. A low nominal share price is not an admission filter; asset
tradability, usable data, liquidity and configured risk limits are independent checks.
Research/holding reviews still include positions outside the opening watchlist.
Existing fractional or otherwise unsupported holdings remain visible and researched;
defer unsupported execution rather than rounding a close and claiming it completed.

Keep four independent interfaces. Provider-specific HTTP/stream parsing belongs
behind them; agents see stored evidence and proposals, never trading credentials.

| Interface | Planned operations/result | Current subset |
| --- | --- | --- |
| `MarketDataReader` | Quote with bid/ask/sizes, venue/feed, provider event time and observed time; bars for liquidity/stress; clock/calendar | IEX midpoint returned as a Decimal; quote metadata is currently discarded |
| `BrokerReader` | Account constraints, assets, holdings, paginated open/closed orders and fills; lookup by broker/client order ID | Account, long positions and up to 500 open orders |
| `PaperExecutionGateway` | Submit/cancel/query typed durable intents; explicit paper endpoint/account binding | Not implemented |
| `OrderMonitor` | Durable trade-update events, REST reconciliation, protection quantities and reservation settlement | Not implemented |

Broker clock/calendar and asset capabilities must be read from the broker, not
inferred from local weekdays or the LLM. Preserve exchange timezone, holidays,
early closes and feed entitlement. A recent account fetch is not a recent quote;
the current `Snapshot.as_of` only dates account acquisition. Use ask-side/capped
costs to bound buy commitments, rather than a midpoint that cannot bound execution.

The first provider transport remains the existing `httpx` stack, with explicit
bounded read retries. A stream library or `alpaca-py` can be adopted after measuring
reconnect behavior; SDK convenience does not replace intent/reconciliation logic.

## C5: reconcile before enabling submission

Capture a snapshot generation from account, positions, orders and recent fills.
Those reads are not an atomic broker transaction: check for intervening events,
retry/reconcile within a bounded interval, and mark unresolved generations unusable
for added risk. Record restrictions, cash and buying-power semantics separately.
Internal cash controls remain more restrictive than a margin-enabled paper account.

Known pending orders use remaining quantity and a conservative price/cost bound.
Unknown order quantities, market-order commitments or truncated order lists block
new risk until reconciled. Pending sell orders and protective legs reserve sell
capacity so reductions cannot oversell. Expected sale proceeds are not spendable
until confirmed under the account's availability rules.

Track external/manual orders, resets/account changes and corporate actions. An
account ID change invalidates previous intents and baseline assumptions; it must
not silently reuse another paper account's ledger. Detect symbol/quantity changes
and preserve thesis/research lineage without inventing missing entry information.

## C6: durable intent lifecycle

The Allocator produces a portfolio plan, including final-confidence lineage and
requested amounts. Code independently rechecks evidence/price expiry, account
generation, instrument permissions, all cash/stress/exposure limits and protection
requirements. A database transaction creates both the reservation and immutable
intent with a unique stable `client_order_id`. Network submission occurs after commit.

Start with bounded regular-session GTC limit entries and an application-controlled
entry expiry/cancel policy; record
quantity, price cap, time-in-force, cost reserve and compatible protection strategy.
There is no implicit market-order fallback or price chase. Round supported quantities
down and recheck every limit. Policy values are owner-configured, not agent overrides.
Verify broker support for the chosen GTC entry/protection combination. Protection
for holdings retained overnight must persist across sessions; canceling an expired
entry remainder must not silently remove protection from an already filled portion.

The dispatcher binds to the intended paper account and endpoint. It claims intents
using a fenced lease and persists submission state. Agents cannot call it. A timeout
or disconnected response produces **UNKNOWN**, retaining commitments; query the
same client ID before deciding whether a retry is possible. A negative lookup alone
does not prove a timed-out submission was never accepted: reconcile with bounded
waiting and broker history. Never mint a new ID to bypass uncertainty.

| Observed state | Ledger/worker behavior |
| --- | --- |
| Reserved, not dispatched | Keep cash/risk committed; expired intent may release only when submission was never started |
| Submission unknown | Retain reservation; reconcile; block conflicting intents |
| Accepted/pending | Monitor; do not call it a fill |
| Partially filled | Record immutable fills; convert filled commitment into holdings; retain residual reservation; verify protection |
| Filled | Settle actual cash/fees; reconcile holdings and protection; no residual buy reservation |
| Cancel requested | Keep residual commitment until cancellation is confirmed; a fill may race with cancellation |
| Canceled/rejected/expired | Release only confirmed unfilled commitment; retain any acquired holding |
| Duplicate/out-of-order event | Idempotent fill/event processing plus broker-authoritative reconciliation; do not regress cumulative fills |

The monitor uses Alpaca's `trade_updates` stream plus independent periodic REST
reconciliation. Streams improve responsiveness but are not the sole financial
record. Deduplicate execution/event IDs, reconcile after disconnects and restart,
and keep monitoring active when research, models or the CLI fail. Proposed starting
REST cadence is 30 seconds, adjusted after measured limits/latency; it is not an
execution/protection guarantee.

## Protection is its own acceptance milestone

Alpaca's bracket documentation says exit legs activate only after the entry is
completely filled. Therefore a partial fill cannot be assumed protected just
because a bracket request succeeded. Choose and prove the supported entry/protection
sequence in paper before enabling C6. Track required versus broker-confirmed active
protected quantity from the first partial fill onward, including reductions and closes.

Test protective-leg creation/replacement/cancellation, fill races and inventory
locks before general execution. If protection cannot be confirmed, pause added risk,
reconcile the entry/remainder and invoke only the explicitly configured recovery
procedure. A kill switch cancels/blocks additions according to policy; it does not
automatically liquidate holdings. Stops can gap or fail to fill at a trigger price;
they never replace stressed-loss sizing. Fractional/protection combinations remain
outside the first slice until their actual capabilities are proven.

## Acceptance matrix

| Test group | Required evidence before paper enablement |
| --- | --- |
| Reads and prices | Credentials/errors redacted; stale/missing/crossed quotes; feed identity; clock holidays/early closes; halted/nontradable assets; full order pagination |
| Capital concurrency | PostgreSQL transactions cannot overspend shared cash/stress/exposure; no double-counted broker/internal reservations; pending sells cannot oversell |
| Submission recovery | Crash before/after request, accepted response lost, delayed client-ID visibility, duplicate dispatch and fenced stale workers |
| Fills/cancel races | Multiple partial fills, duplicate/reordered events, cancel acknowledgment with late fill, rejection/expiry and external broker changes |
| Protection | Partial and full entries, missing/rejected legs, quantity changes on reduction, competing exits and monitor reconnect |
| Restart and operations | Database restore/replay, stream gap filled by REST, CLI/model outage, kill switch, account reset and unreconciled snapshot |
| Opt-in paper smoke | Isolated paper account, explicit allowed instrument/quantity/notional, one bounded lifecycle and recorded residual holdings/protection; no live endpoint |

Routine CI uses a deterministic broker simulator and an isolated PostgreSQL database.
Only an explicitly enabled paper smoke test may submit simulated orders; ordinary
tests and the source capability probe never do. Current 76-test CI verifies the
research terminal and read fixtures, not this unimplemented execution acceptance matrix.
Paper outcomes also need separate prospective evaluation; simulator fills do not
establish live liquidity, slippage or strategy performance.

## Primary references

- [Alpaca paper environment and simulation assumptions](https://docs.alpaca.markets/us/docs/paper-trading)
- [Order types, limits and bracket behavior](https://docs.alpaca.markets/us/docs/orders-at-alpaca)
- [Trade-update stream](https://docs.alpaca.markets/us/docs/websocket-streaming)
- [Official TradingClient source: account, asset, client-ID, clock/calendar and order operations](https://github.com/alpacahq/alpaca-py/blob/master/alpaca/trading/client.py)
- [Market data entitlements](https://docs.alpaca.markets/us/docs/about-market-data-api)

See [budget management](budget-management.md) and [storage contracts](persistence-and-contracts.md)
for the retained confidence-sizing and transaction design.
