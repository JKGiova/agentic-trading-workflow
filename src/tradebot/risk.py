"""Deterministic previews. Proposals are never network orders in v0.1."""

from datetime import timedelta
from decimal import ROUND_DOWN, Decimal

from tradebot.contracts import Action, Allocation, Contract, Forecast, Money, Snapshot, utcnow
from tradebot.settings import RiskPolicy


class Preview(Contract):
    accepted: bool
    action: Action
    notional: Money
    quantity: Money
    ceiling: Money
    reasons: list[str]


def decimal(value) -> Decimal:
    return Decimal(str(value))


def preview(
    symbol: str,
    sector: str,
    allocation: Allocation,
    snapshot: Snapshot,
    forecast: Forecast | None,
    policy: RiskPolicy,
    price: Decimal,
    eligible: bool,
    coverage_complete: bool,
    approved: bool,
    stressed_existing: Decimal = Decimal(0),
) -> Preview:
    action = allocation.action
    reasons = []
    position = snapshot.position(symbol)
    if action in {Action.HOLD, Action.NO_ACTION}:
        return Preview(
            accepted=True,
            action=action,
            notional=0,
            quantity=0,
            ceiling=0,
            reasons=["No exposure change"],
        )
    if price <= 0 or not price.is_finite():
        reasons.append("Missing valid quote")
    if (
        not snapshot.reconciled
        or snapshot.as_of < utcnow() - timedelta(seconds=policy.max_snapshot_age_seconds)
        or snapshot.as_of > utcnow() + timedelta(seconds=5)
    ):
        reasons.append("Portfolio snapshot stale, future-dated or unreconciled")
    if snapshot.pending_buys.get(symbol, 0) or snapshot.pending_sells.get(symbol, 0):
        reasons.append("Existing pending order for this instrument")
    if action in {Action.REDUCE, Action.CLOSE}:
        if not position:
            reasons.append("No holding to reduce")
        ceiling = position.value if position else Decimal(0)
        value = ceiling if action == Action.CLOSE else min(allocation.requested_notional, ceiling)
    else:
        if not eligible:
            reasons.append("Stock is outside eligible watchlist")
        if not coverage_complete or not approved:
            reasons.append("Complete mandatory coverage and approved debate required")
        if not forecast or forecast.probability is None or forecast.stressed_loss is None:
            reasons.append("Supported final confidence and stressed downside required")
        if action == Action.OPEN and position:
            reasons.append("OPEN cannot modify an existing position")
        if action == Action.REINFORCE and not position:
            reasons.append("REINFORCE requires an existing position")
        if position and position.price < position.average_price:
            reasons.append("Averaging down is disabled")
        occupied = {p.symbol for p in snapshot.positions} | set(snapshot.pending_buys)
        if symbol not in occupied and len(occupied) >= policy.max_positions:
            reasons.append("Maximum simultaneous positions reached")
        daily_loss = snapshot.daily_start_equity - snapshot.equity
        if daily_loss >= snapshot.daily_start_equity * decimal(policy.max_daily_loss):
            reasons.append("Daily loss stop reached")
        gross = sum((p.value for p in snapshot.positions), Decimal(0)) + snapshot.reserved
        sector_value = sum((p.value for p in snapshot.positions if p.sector == sector), Decimal(0))
        sector_value += sum(
            (
                value
                for sym, value in snapshot.pending_buys.items()
                if snapshot.pending_sectors.get(sym, "unknown") == sector
            ),
            Decimal(0),
        )
        current = position.value if position else Decimal(0)
        pending = snapshot.pending_buys.get(symbol, Decimal(0))
        probability = (
            decimal(forecast.probability) if forecast and forecast.probability else Decimal(0)
        )
        loss = (
            decimal(forecast.stressed_loss) if forecast and forecast.stressed_loss else Decimal(1)
        )
        confidence_cap = snapshot.equity * decimal(policy.max_position_weight) * probability
        downside_cap = policy.per_position_loss_budget / loss
        ceiling = max(
            Decimal(0),
            min(
                confidence_cap - current - pending,
                downside_cap - current - pending,
                (
                    snapshot.cash
                    - snapshot.reserved
                    - snapshot.equity * decimal(policy.cash_reserve_weight)
                )
                / (1 + decimal(policy.cost_buffer)),
                snapshot.equity * decimal(policy.max_gross_weight) - gross,
                snapshot.equity * decimal(policy.max_sector_weight) - sector_value,
                (policy.portfolio_stress_budget - stressed_existing) / loss - current - pending,
            ),
        )
        value = min(allocation.requested_notional, ceiling)
    quantity = (
        (value / price).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        if price > 0
        else Decimal(0)
    )
    notional = quantity * price
    if quantity <= 0:
        reasons.append("No executable positive quantity within limits")
    return Preview(
        accepted=not reasons,
        action=action,
        notional=notional if not reasons else 0,
        quantity=quantity if not reasons else 0,
        ceiling=ceiling,
        reasons=reasons or ["Research preview only: no broker submission enabled"],
    )
