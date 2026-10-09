"""Versioned contracts shared by agents, connectors, storage and terminal views."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Money = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Note = Annotated[str, Field(max_length=300)]


def utcnow() -> datetime:
    return datetime.now(UTC)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Category(StrEnum):
    MARKET = "market"
    FINANCIAL = "financial"
    COMPANY = "company"
    SOCIAL = "social"


class Coverage(StrEnum):
    RESULTS = "COMPLETE_WITH_RESULTS"
    EMPTY = "COMPLETE_NO_NEW_RESULTS"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class Action(StrEnum):
    OPEN = "OPEN"
    REINFORCE = "REINFORCE"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    NO_ACTION = "NO_ACTION"


class Evidence(Contract):
    id: str
    stock: str
    category: Category
    source: str
    title: str
    text: str
    url: str
    published_at: datetime
    retrieved_at: datetime
    author_id: str | None = None

    @field_validator("published_at", "retrieved_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("UTC-aware timestamps are required")
        return value.astimezone(UTC)


class SearchAttempt(Contract):
    stock: str
    category: Category
    source: str
    query: str
    start: datetime
    cutoff: datetime
    completed_at: datetime
    coverage: Coverage
    evidence_ids: list[str]
    reason: str


class Report(Contract):
    summary: Annotated[str, Field(max_length=1000)]
    direction: Literal["positive", "negative", "mixed", "unknown"]
    evidence_ids: list[str]
    opposing_evidence: Annotated[list[Note], Field(max_length=5)]
    gaps: Annotated[list[Note], Field(max_length=5)]


class Scenario(Contract):
    label: str
    probability: Probability
    net_return: Annotated[float, Field(ge=-1, allow_inf_nan=False)]


class Forecast(Contract):
    probability: Probability | None
    scenarios: list[Scenario]
    stressed_loss: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] | None
    evidence_ids: list[str]
    rationale: Annotated[str, Field(max_length=1000)]
    gaps: Annotated[list[Note], Field(max_length=5)]
    calibration: Literal["uncalibrated"] = "uncalibrated"

    @model_validator(mode="after")
    def coherent(self):
        if self.probability is None:
            return self
        if not self.scenarios or abs(sum(x.probability for x in self.scenarios) - 1) > 1e-6:
            raise ValueError("supported forecasts require probabilities summing to one")
        positive = sum(x.probability for x in self.scenarios if x.net_return > 0)
        if abs(positive - self.probability) > 1e-6:
            raise ValueError("confidence must equal positive net-return scenario mass")
        return self


class Case(Contract):
    argument: Annotated[str, Field(max_length=1000)]
    evidence_ids: list[str]
    challenges: Annotated[list[Note], Field(max_length=3)]
    verification_ids: Annotated[list[str], Field(max_length=3)]
    unresolved: Annotated[list[Note], Field(max_length=3)]


class Verdict(Contract):
    decision: Literal["APPROVE", "DEFER", "REJECT"]
    forecast: Forecast
    rationale: Annotated[str, Field(max_length=1000)]
    dissent: Annotated[str, Field(max_length=500)]


class Allocation(Contract):
    action: Action
    requested_notional: Money
    rationale: Annotated[str, Field(max_length=1000)]


class Position(Contract):
    symbol: str
    quantity: Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
    average_price: Money
    price: Money
    thesis: str = "Entry thesis unavailable; compare available research cautiously."
    sector: str = "unknown"

    @property
    def value(self) -> Decimal:
        return self.quantity * self.price

    @property
    def unrealized(self) -> Decimal:
        return self.quantity * (self.price - self.average_price)


class Snapshot(Contract):
    as_of: datetime
    cash: Money
    positions: list[Position]
    pending_buys: dict[str, Money] = Field(default_factory=dict)
    pending_sells: dict[str, Money] = Field(default_factory=dict)
    pending_sectors: dict[str, str] = Field(default_factory=dict)
    baseline_equity: Money
    daily_start_equity: Money
    source: str
    reconciled: bool

    @property
    def equity(self) -> Decimal:
        return self.cash + sum((p.value for p in self.positions), Decimal(0))

    @property
    def reserved(self) -> Decimal:
        return sum(self.pending_buys.values(), Decimal(0))

    def position(self, symbol: str) -> Position | None:
        return next((p for p in self.positions if p.symbol == symbol), None)
