"""Fits the growth-rate marketing response model (see CLAUDE.md section 3) and
produces revenue forecasts with residual-bootstrap likely ranges.

Specification:
    d_log_revenue_t = b0 + b1 * d_log_spend_t + b2 * d_log_spend_{t-1} + e_t

Spend and time are near-perfectly confounded in levels, so the model is fit on
month-over-month growth rates, which detrends both series. Uplifts from planned
game initiatives are NOT part of this model; they are applied on top by
scenarios.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm

DEFAULT_DATA_PATH = "data/dataset.csv"
FORECAST_HORIZON = 12
LIKELY_RANGE_TAIL = 0.05  # 5th/95th percentile -> 90% likely range


@dataclass
class FittedModel:
    intercept: float  # b0: baseline monthly growth with no extra marketing
    same_month_coef: float  # b1
    carryover_coef: float  # b2
    pvalues: dict
    adj_rsquared: float
    n_obs: int
    residuals: np.ndarray
    last_log_revenue: float
    last_spend: float
    last_d_log_spend: float  # most recent observed month-over-month spend change
    spend_range: tuple  # (min, max) observed spend, for guardrails
    mom_change_range: tuple  # (min, max) observed month-over-month spend change


def load_history(path: str = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Loads and sorts the monthly spend/revenue history."""
    df = pd.read_csv(path)
    df["year_month"] = pd.to_datetime(df["year_month"])
    return df.sort_values("year_month").reset_index(drop=True)


def _growth_frame(df: pd.DataFrame) -> pd.DataFrame:
    g = pd.DataFrame(
        {
            "d_log_revenue": np.log(df["total_revenue"]).diff(),
            "d_log_spend": np.log(df["mkt_investment"]).diff(),
        }
    )
    g["d_log_spend_lag1"] = g["d_log_spend"].shift(1)
    return g.dropna().reset_index(drop=True)


def fit_model(df: pd.DataFrame) -> FittedModel:
    """Fits the growth-rate-with-carryover specification via OLS."""
    g = _growth_frame(df)
    X = sm.add_constant(g[["d_log_spend", "d_log_spend_lag1"]])
    y = g["d_log_revenue"]
    result = sm.OLS(y, X).fit()

    mom_change = df["mkt_investment"].pct_change().dropna()

    return FittedModel(
        intercept=result.params["const"],
        same_month_coef=result.params["d_log_spend"],
        carryover_coef=result.params["d_log_spend_lag1"],
        pvalues=result.pvalues.to_dict(),
        adj_rsquared=result.rsquared_adj,
        n_obs=int(result.nobs),
        residuals=result.resid.to_numpy(),
        last_log_revenue=float(np.log(df["total_revenue"].iloc[-1])),
        last_spend=float(df["mkt_investment"].iloc[-1]),
        last_d_log_spend=float(g["d_log_spend"].iloc[-1]),
        spend_range=(float(df["mkt_investment"].min()), float(df["mkt_investment"].max())),
        mom_change_range=(float(mom_change.min()), float(mom_change.max())),
    )


def _growth_path(fitted: FittedModel, monthly_budget, baseline_growth: float | None) -> np.ndarray:
    """Deterministic monthly log-growth rate implied by a budget vector."""
    beta0 = fitted.intercept if baseline_growth is None else baseline_growth
    spend_history = np.concatenate([[fitted.last_spend], np.asarray(monthly_budget, dtype=float)])
    d_log_spend = np.diff(np.log(spend_history))
    d_log_spend_lag1 = np.concatenate([[fitted.last_d_log_spend], d_log_spend[:-1]])
    return beta0 + fitted.same_month_coef * d_log_spend + fitted.carryover_coef * d_log_spend_lag1


def forecast(
    fitted: FittedModel,
    monthly_budget,
    baseline_growth: float | None = None,
    n_boot: int = 2000,
    tail: float = LIKELY_RANGE_TAIL,
    seed: int = 0,
) -> dict:
    """Forecasts revenue for len(monthly_budget) months (no uplifts applied).

    Returns a dict with "revenue" (point forecast), "lower" and "upper"
    (residual-bootstrap likely range), one value per forecasted month.
    """
    monthly_budget = np.asarray(monthly_budget, dtype=float)
    mu = _growth_path(fitted, monthly_budget, baseline_growth)
    revenue = np.exp(fitted.last_log_revenue + np.cumsum(mu))

    rng = np.random.default_rng(seed)
    n_months = len(monthly_budget)
    draws = rng.choice(fitted.residuals, size=(n_boot, n_months), replace=True)
    boot_log_revenue = fitted.last_log_revenue + np.cumsum(mu + draws, axis=1)
    boot_revenue = np.exp(boot_log_revenue)

    lower = np.quantile(boot_revenue, tail, axis=0)
    upper = np.quantile(boot_revenue, 1 - tail, axis=0)

    return {"revenue": revenue, "lower": lower, "upper": upper}


def backtest_mape(df: pd.DataFrame, min_train: int = 10) -> float:
    """Rolling-origin, one-step-ahead, expanding-window backtest.

    Refits the model on data up to each point and scores the next month's
    growth-rate prediction, translated into a percentage revenue error.
    """
    g = _growth_frame(df)
    errors = []
    for t in range(min_train, len(g)):
        train = g.iloc[:t]
        X = sm.add_constant(train[["d_log_spend", "d_log_spend_lag1"]])
        result = sm.OLS(train["d_log_revenue"], X).fit()

        next_row = g.iloc[t]
        pred_d_log = (
            result.params["const"]
            + result.params["d_log_spend"] * next_row["d_log_spend"]
            + result.params["d_log_spend_lag1"] * next_row["d_log_spend_lag1"]
        )
        pred_ratio = np.exp(pred_d_log)
        actual_ratio = np.exp(next_row["d_log_revenue"])
        errors.append(abs(pred_ratio - actual_ratio) / actual_ratio)

    return float(np.mean(errors)) * 100
