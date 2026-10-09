# Risk controls and paper execution

[Wiki home](README.md) · [Project overview](../README.md)

The runtime enforces the analysis team's first confidence gate before debate and the Orchestrator's revised confidence gate afterward. The [Portfolio Allocator agent](portfolio-allocator.md) chooses actions and investments only for eligible additions. Deterministic [budget tools](budget-management.md) size the ceiling from `p_final` and intersect it with independent risk and broker limits. Passing confidence alone cannot authorize an order.

Configure risk rules independently of the model:

- Approved instruments and permitted actions.
- Maximum position size, gross exposure, sector concentration, and portfolio risk.
- Minimum cash reserve, session deployment cap, pending-order reservations, and cost allowances.
- Maximum daily loss using realized and unrealized P&L, including applicable costs.
- Minimum liquidity, maximum spread, and quote-freshness requirements.
- Maximum concurrent positions and outstanding orders.
- Protective-order requirements and maximum holding or review periods.
- A manual kill switch and defined recovery procedures.

For the first prototype, propose long-only paper trading without leverage. Numeric thresholds are configuration decisions to settle before implementing execution. Neither analyst confidence nor a debate approval can bypass these limits. Source-coverage failures prohibit opening or reinforcing affected stocks.

If a critical feed is missing or stale, stop new risk-taking and continue reconciliation and protection monitoring. Define failure responses before development; a kill switch must not implicitly mean liquidating every holding.

Use broker-managed protective orders where supported. Confirm their activation after fills and keep protection quantities aligned with partial fills. Stops do not guarantee execution at the trigger price, and protection support varies by broker, instrument, and trading session.

Assign stable client order IDs. After a timeout, query order status before retrying. Test interrupted submissions, duplicate callbacks, partial fills, cancellations, reconnection, and recovery after restart.

Treat all retrieved articles and posts as untrusted data. Embedded instructions must never alter the whitelist, risk limits, permissions, or execution tools.

## Related pages

- [Position management](position-management.md)
- [New-entry debate](new-entry-debate.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Budget management](budget-management.md)
- [Validation](validation.md)
