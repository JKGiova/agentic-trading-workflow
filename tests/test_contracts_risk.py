from datetime import timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tradebot.contracts import Allocation, Forecast, Position, Scenario, utcnow
from tradebot.risk import preview
from tradebot.service import demo_snapshot
from tradebot.settings import Credentials, Policy, RiskPolicy


def forecast(probability=0.6, stressed_loss=0.15):
    return Forecast(
        probability=probability,
        scenarios=[
            Scenario(label="gain", probability=probability, net_return=0.08),
            Scenario(label="loss", probability=1 - probability, net_return=-0.03),
        ],
        stressed_loss=stressed_loss,
        evidence_ids=["news"],
        rationale="test",
        gaps=[],
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_probability(value):
    with pytest.raises(ValidationError):
        forecast(value)


def test_forecast_mass_must_match_confidence():
    data = forecast().model_dump()
    data["probability"] = 0.7
    with pytest.raises(ValidationError):
        Forecast.model_validate(data)
    data = forecast().model_dump()
    data["scenarios"] = []
    with pytest.raises(ValidationError):
        Forecast.model_validate(data)


def test_missing_initial_confidence_is_valid_for_debate():
    Forecast(
        probability=None,
        scenarios=[],
        stressed_loss=None,
        evidence_ids=[],
        rationale="Unknown",
        gaps=["Missing initial estimate"],
    )


def test_extra_fields_secrets_and_config_validation():
    with pytest.raises(ValidationError):
        Allocation(action="OPEN", requested_notional=1, rationale="test", broker_tool="buy")
    assert "secret-example" not in repr(Credentials(openrouter_api_key="secret-example"))
    with pytest.raises(ValidationError):
        Policy(approved_x_authors={"bad": "unverified"})
    with pytest.raises(ValidationError):
        Policy(session_hours=0)


def check(action="OPEN", symbol="MSFT", requested=1000, **overrides):
    params = dict(
        symbol=symbol,
        sector="technology",
        allocation=Allocation(action=action, requested_notional=requested, rationale="test"),
        snapshot=demo_snapshot(),
        forecast=forecast(),
        policy=RiskPolicy(portfolio_stress_budget=2000),
        price=Decimal("100"),
        eligible=True,
        coverage_complete=True,
        approved=True,
    )
    params.update(overrides)
    return preview(**params)


def test_confidence_downside_sizing_and_quantity_rounding():
    result = check()
    assert result.accepted
    assert result.ceiling == Decimal("400")  # min(10,000*.1*.6, 60/.15)
    assert result.quantity == Decimal("4")
    result = check(price=Decimal("333"))
    assert result.notional <= result.ceiling
    assert result.quantity == Decimal("1.201201")


def test_reinforcement_subtracts_existing_holding():
    snap = demo_snapshot().model_copy(
        update={
            "positions": [
                Position(
                    symbol="AAPL", quantity=1, average_price=230, price=250, sector="technology"
                )
            ]
        }
    )
    result = check(action="REINFORCE", symbol="AAPL", snapshot=snap)
    assert result.ceiling == Decimal("150")


@pytest.mark.parametrize(
    "override",
    [
        {"eligible": False},
        {"coverage_complete": False},
        {"approved": False},
        {"forecast": None},
        {"price": Decimal("0")},
        {"snapshot": demo_snapshot().model_copy(update={"reconciled": False})},
        {"snapshot": demo_snapshot().model_copy(update={"as_of": utcnow() - timedelta(minutes=2)})},
        {"snapshot": demo_snapshot().model_copy(update={"pending_buys": {"MSFT": Decimal("100")}})},
    ],
)
def test_added_exposure_refused_independent_of_model(override):
    result = check(**override)
    assert not result.accepted
    assert result.notional == 0


def test_no_numeric_confidence_filter():
    result = check(forecast=forecast(0.1))
    assert result.accepted
    assert result.ceiling == Decimal("100")


def test_reduce_close_bypass_entry_research_requirements():
    result = check(
        action="CLOSE",
        symbol="AAPL",
        forecast=None,
        eligible=False,
        coverage_complete=False,
        approved=False,
        price=Decimal("250"),
    )
    assert result.accepted
    assert result.notional == 500
    assert result.quantity == 2
    result = check(
        action="REDUCE",
        symbol="AAPL",
        requested=10000,
        forecast=None,
        approved=False,
        price=Decimal("250"),
    )
    assert result.notional == 500


def test_hold_on_source_failure_and_no_averaging_down():
    assert check(action="HOLD", symbol="AAPL", coverage_complete=False).accepted
    snap = demo_snapshot()
    positions = [snap.positions[0].model_copy(update={"average_price": Decimal("300")})]
    result = check(
        action="REINFORCE", symbol="AAPL", snapshot=snap.model_copy(update={"positions": positions})
    )
    assert not result.accepted
    assert "Averaging down is disabled" in result.reasons


def test_cash_sector_gross_position_and_daily_loss_limits():
    snap = demo_snapshot()
    assert not check(snapshot=snap.model_copy(update={"cash": Decimal("0")})).accepted
    assert not check(policy=RiskPolicy(max_sector_weight=0.05)).accepted
    assert not check(policy=RiskPolicy(max_gross_weight=0.05)).accepted
    assert not check(policy=RiskPolicy(max_positions=2)).accepted
    assert not check(
        snapshot=snap.model_copy(update={"daily_start_equity": Decimal("12000")})
    ).accepted
    assert not check(stressed_existing=Decimal("2000")).accepted
