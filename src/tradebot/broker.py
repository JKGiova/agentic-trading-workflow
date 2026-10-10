"""Hard-coded read-only Alpaca PAPER account adapter. No order submission method."""

from decimal import Decimal

import httpx

from tradebot.contracts import Position, Snapshot, utcnow
from tradebot.settings import Credentials, Policy


class BrokerError(RuntimeError):
    pass


class AlpacaReadOnly:
    BASE = "https://paper-api.alpaca.markets"

    def __init__(
        self, credentials: Credentials, policy: Policy, client: httpx.AsyncClient | None = None
    ):
        self.policy = policy
        self.headers = {
            "APCA-API-KEY-ID": credentials.alpaca_api_key.get_secret_value(),
            "APCA-API-SECRET-KEY": credentials.alpaca_secret_key.get_secret_value(),
        }
        self.client = client or httpx.AsyncClient(timeout=15, follow_redirects=False)
        self.owns_client = client is None

    async def close(self):
        if self.owns_client:
            await self.client.aclose()

    async def get(self, path: str, params=None):
        if not self.headers["APCA-API-KEY-ID"] or not self.headers["APCA-API-SECRET-KEY"]:
            raise BrokerError("Alpaca paper credentials missing")
        try:
            result = await self.client.get(self.BASE + path, headers=self.headers, params=params)
            result.raise_for_status()
            return result.json()
        except httpx.HTTPError, ValueError:
            raise BrokerError("Alpaca paper read failed; cached snapshot remains visible") from None

    async def snapshot(self, previous: Snapshot | None) -> Snapshot:
        import asyncio

        account, positions, orders = await asyncio.gather(
            self.get("/v2/account"),
            self.get("/v2/positions"),
            self.get("/v2/orders", {"status": "open", "limit": 500}),
        )
        sectors = {x.symbol: x.sector for x in self.policy.instruments}
        held = []
        reconciled = len(orders) < 500 and not account.get("trading_blocked", False)
        for raw in positions:
            if Decimal(raw["qty"]) <= 0 or raw.get("side") == "short":
                raise BrokerError("Short positions unsupported; no allocation preview available")
            old = previous.position(raw["symbol"]) if previous else None
            held.append(
                Position(
                    symbol=raw["symbol"],
                    quantity=raw["qty"],
                    average_price=raw["avg_entry_price"],
                    price=raw["current_price"],
                    sector=sectors.get(raw["symbol"], "unknown"),
                    thesis=old.thesis if old else "Entry thesis unavailable",
                )
            )
        buys, sells, pending_sectors = {}, {}, {}
        for order in orders:
            symbol = order["symbol"]
            bucket = buys if order["side"] == "buy" else sells
            qty = Decimal(order.get("qty") or "0") - Decimal(order.get("filled_qty") or "0")
            position = next((p for p in held if p.symbol == symbol), None)
            price = Decimal(order.get("limit_price") or (str(position.price) if position else "0"))
            notional = Decimal(order.get("notional") or "0")
            if qty <= 0 or price <= 0:
                reconciled = False  # Unknown pending commitments never create cash headroom.
            bucket[symbol] = bucket.get(symbol, Decimal(0)) + max(notional, qty * price)
            pending_sectors[symbol] = sectors.get(symbol, "unknown")
        equity = Decimal(account["equity"])
        return Snapshot(
            as_of=utcnow(),
            cash=account["cash"],
            positions=held,
            pending_buys=buys,
            pending_sells=sells,
            pending_sectors=pending_sectors,
            baseline_equity=previous.baseline_equity if previous else equity,
            daily_start_equity=Decimal(account.get("last_equity", account["equity"])),
            source="Alpaca PAPER read-only; marks may be from prior market session",
            reconciled=reconciled,
        )

    async def quote(self, symbol: str) -> Decimal:
        if not self.headers["APCA-API-KEY-ID"]:
            raise BrokerError("Alpaca data credential missing")
        try:
            response = await self.client.get(
                f"https://data.alpaca.markets/v2/stocks/{symbol}/quotes/latest",
                params={"feed": "iex"},
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()["quote"]
            ask, bid = Decimal(str(data["ap"])), Decimal(str(data["bp"]))
            if ask <= 0 or bid <= 0:
                raise BrokerError("No usable IEX quote")
            return (ask + bid) / 2
        except httpx.HTTPError, ValueError, KeyError:
            raise BrokerError("IEX quote unavailable") from None
