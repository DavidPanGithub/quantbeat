"""Tests for the pricing / P&L math in app.trading."""
import math

from app import trading
from app.config import (
    DIRECTION_DOWN,
    DIRECTION_UP,
    INSTRUMENT_CALL,
    INSTRUMENT_LONG,
    INSTRUMENT_PUT,
    INSTRUMENT_SHORT,
    MIN_PREMIUM_FRACTION,
)


def test_direction_of():
    assert trading.direction_of(INSTRUMENT_LONG) == DIRECTION_UP
    assert trading.direction_of(INSTRUMENT_CALL) == DIRECTION_UP
    assert trading.direction_of(INSTRUMENT_SHORT) == DIRECTION_DOWN
    assert trading.direction_of(INSTRUMENT_PUT) == DIRECTION_DOWN


def test_historical_vol_flat_series_is_zero():
    assert trading.historical_vol([100.0] * 10) == 0.0


def test_historical_vol_positive_for_moving_series():
    assert trading.historical_vol([100, 102, 99, 105, 101]) > 0


def test_premium_is_floored_when_vol_is_zero():
    price = 200.0
    prem = trading.option_premium(price, sigma=0.0, horizon=10)
    assert math.isclose(prem, price * MIN_PREMIUM_FRACTION)


def test_long_and_short_are_linear_and_symmetric():
    long = trading.evaluate_trade(INSTRUMENT_LONG, 1000, 100, 110, premium=5)
    short = trading.evaluate_trade(INSTRUMENT_SHORT, 1000, 100, 110, premium=5)
    assert math.isclose(long.pnl, 100.0)   # +10% on $1000
    assert math.isclose(short.pnl, -100.0)  # mirror image


def test_call_in_the_money_is_leveraged():
    # $1000 staked, $5 premium -> 200 contracts; +$10 payoff each = $2000 gross.
    out = trading.evaluate_trade(INSTRUMENT_CALL, 1000, 100, 110, premium=5)
    assert out.strike == 100
    assert math.isclose(out.contracts, 200.0)
    assert math.isclose(out.payoff, 10.0)
    assert math.isclose(out.pnl, 1000.0)  # 200 * 10 - 1000 stake = +100%


def test_option_downside_is_capped_at_the_stake():
    # Wrong-way put on a rising market expires worthless: lose exactly the stake.
    out = trading.evaluate_trade(INSTRUMENT_PUT, 1000, 100, 110, premium=10)
    assert out.payoff == 0.0
    assert math.isclose(out.pnl, -1000.0)


def test_option_breaks_even_when_payoff_equals_premium():
    out = trading.evaluate_trade(INSTRUMENT_CALL, 1000, 100, 110, premium=10)
    assert math.isclose(out.payoff, 10.0)
    assert math.isclose(out.pnl, 0.0)  # 100 contracts * 10 - 1000 stake


def test_put_in_the_money_profits():
    out = trading.evaluate_trade(INSTRUMENT_PUT, 1000, 100, 90, premium=5)
    assert math.isclose(out.payoff, 10.0)
    assert math.isclose(out.pnl, 1000.0)
