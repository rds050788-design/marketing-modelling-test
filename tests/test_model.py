"""Tests for the growth-rate marketing response model (CLAUDE.md section 3)."""

import numpy as np
import pytest

from src.model import backtest_mape, fit_model, forecast, load_history

RANDOM_WALK_MAPE_CEILING = 3.0  # spec's random-walk baseline is 4.72%


@pytest.fixture(scope="module")
def history():
    return load_history()


@pytest.fixture(scope="module")
def fitted(history):
    return fit_model(history)


def test_spend_and_mom_ranges_match_known_data(fitted):
    lo, hi = fitted.spend_range
    assert lo == pytest.approx(2_230_000)
    assert hi == pytest.approx(4_381_000)

    mom_lo, mom_hi = fitted.mom_change_range
    assert mom_lo == pytest.approx(-0.0481, abs=1e-3)
    assert mom_hi == pytest.approx(0.1849, abs=1e-3)


def test_same_month_and_carryover_coefficients_are_significant_and_small(fitted):
    # Section 3: b1 ~ 0.30, b2 ~ 0.21, both significant, both far below the
    # naive confounded revenue~spend coefficient of 5.07.
    assert 0.2 < fitted.same_month_coef < 0.4
    assert 0.1 < fitted.carryover_coef < 0.3
    assert fitted.pvalues["d_log_spend"] < 0.05
    assert fitted.pvalues["d_log_spend_lag1"] < 0.05


def test_adjusted_r_squared_matches_expected_fit_quality(fitted):
    assert fitted.adj_rsquared == pytest.approx(0.47, abs=0.05)


def test_baseline_growth_is_the_dominant_small_positive_intercept(fitted):
    # Section 3 baseline growth ~4-5%/month; user-editable per section 6.
    assert 0.0 < fitted.intercept < 0.08


def test_backtest_beats_random_walk_by_a_wide_margin(history):
    mape = backtest_mape(history, min_train=11)
    assert mape < RANDOM_WALK_MAPE_CEILING
    assert mape < 1.5  # well within the accurate specifications in section 3's table


def test_forecast_shape_and_ordering(fitted, history):
    budget = [history["mkt_investment"].iloc[-1]] * 12
    result = forecast(fitted, budget)

    assert result["revenue"].shape == (12,)
    assert result["lower"].shape == (12,)
    assert result["upper"].shape == (12,)
    assert np.all(result["lower"] <= result["revenue"])
    assert np.all(result["revenue"] <= result["upper"])
    # Revenue should keep growing off flat spend, since baseline growth > 0.
    assert np.all(np.diff(result["revenue"]) > 0)


def test_forecast_responds_monotonically_to_budget(fitted, history):
    last_spend = history["mkt_investment"].iloc[-1]
    low_budget = [last_spend * 0.8] * 12
    high_budget = [last_spend * 1.2] * 12

    low = forecast(fitted, low_budget, seed=1)
    high = forecast(fitted, high_budget, seed=1)

    assert np.all(high["revenue"] > low["revenue"])


def test_baseline_growth_override_shifts_the_forecast(fitted, history):
    budget = [history["mkt_investment"].iloc[-1]] * 12
    default = forecast(fitted, budget, seed=2)
    higher_baseline = forecast(fitted, budget, baseline_growth=fitted.intercept + 0.02, seed=2)

    assert np.all(higher_baseline["revenue"] > default["revenue"])
