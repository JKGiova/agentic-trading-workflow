"""Nonsecret JSON policy plus environment-only credentials."""

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tradebot.contracts import Contract, Money, Probability


class Instrument(Contract):
    symbol: str
    name: str
    sector: str
    cik: str | None = None
    aliases: list[str] = Field(default_factory=list)
    ir_feeds: list[str] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def valid_symbol(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", value):
            raise ValueError("invalid equity symbol")
        return value


class RiskPolicy(Contract):
    max_position_weight: Probability = 0.10
    max_gross_weight: Probability = 0.70
    max_sector_weight: Probability = 0.30
    cash_reserve_weight: Probability = 0.20
    per_position_loss_budget: Money = Decimal("60")
    portfolio_stress_budget: Money = Decimal("300")
    max_daily_loss: Probability = 0.03
    max_positions: Annotated[int, Field(gt=0)] = 10
    cost_buffer: Probability = 0.005
    max_snapshot_age_seconds: Annotated[int, Field(gt=0)] = 60


class Policy(Contract):
    instruments: list[Instrument] = Field(default_factory=list)
    approved_x_authors: dict[str, str] = Field(default_factory=dict)
    market_domains: list[str] = Field(default_factory=list)
    market_query: str = "US equity market macro interest rates geopolitical news"
    session_hours: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 3
    news_hours: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 3
    history_days: Annotated[int, Field(ge=1, le=30)] = 7
    horizon_trading_days: Annotated[int, Field(gt=0)] = 5
    max_debates: Annotated[int, Field(gt=0)] = 3
    session_timeout_seconds: Annotated[int, Field(gt=0)] = 1800
    model: str = "google/gemini-2.5-flash"
    model_max_tokens: Annotated[int, Field(gt=0)] = 1800
    model_concurrency: Annotated[int, Field(gt=0)] = 4
    # User-configured conservative rates; update for the selected endpoint.
    input_dollars_per_million: Money = Decimal("0.30")
    output_dollars_per_million: Money = Decimal("2.50")
    monthly_model_budget: Money = Decimal("30")
    max_call_input_tokens: Annotated[int, Field(gt=0)] = 40000
    risk: RiskPolicy = Field(default_factory=RiskPolicy)

    @field_validator("instruments")
    @classmethod
    def unique(cls, values):
        if len({x.symbol for x in values}) != len(values):
            raise ValueError("duplicate watchlist symbol")
        return values

    @field_validator("approved_x_authors")
    @classmethod
    def approved(cls, values):
        for author_id, handle in values.items():
            if not author_id.isdigit() or not re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle):
                raise ValueError("X authors require numeric IDs and verified handles")
        return values

    @classmethod
    def read(cls, path: Path) -> "Policy":
        return cls.model_validate(json.loads(path.read_text()))


class Credentials(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRADEBOT_", env_file=".env", extra="ignore")
    openrouter_api_key: SecretStr = SecretStr("")
    alpaca_api_key: SecretStr = SecretStr("")
    alpaca_secret_key: SecretStr = SecretStr("")
    x_bearer_token: SecretStr = SecretStr("")
    tavily_api_key: SecretStr = SecretStr("")
    sec_user_agent: str = ""

    def missing(self, policy: Policy) -> list[str]:
        missing = [
            name
            for name in [
                "openrouter_api_key",
                "alpaca_api_key",
                "alpaca_secret_key",
                "x_bearer_token",
                "tavily_api_key",
            ]
            if not getattr(self, name).get_secret_value()
        ]
        if not policy.instruments:
            missing.append("configured watchlist")
        if not policy.approved_x_authors:
            missing.append("approved X author IDs/handles")
        if not policy.market_domains:
            missing.append("authorized market search domains")
        if not self.sec_user_agent:
            missing.append("SEC identifying user agent")
        return missing
