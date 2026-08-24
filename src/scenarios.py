"""Scenario objects, uplift application, and comparison metrics (CLAUDE.md
sections 4 and 6).

Uplifts represent business knowledge the fitted model cannot have. They are
applied on top of the model's forecast, never mixed into it:

    forecast = model(budget) x (1 + uplift)

Two uplift modes are tracked as two separate series:
- "permanent": raises the compounding base, so later months build on the
  higher level.
- "one_month": affects only the flagged month; the underlying base is
  untouched, so it does not compound into subsequent months.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.model import FittedModel
from src.model import forecast as model_forecast

PERMANENT = "permanent"
ONE_MONTH = "one_month"


@dataclass
class Uplift:
    month: int  # 1-indexed position in the forecast horizon
    pct: float  # e.g. 0.15 for +15%
    mode: str = PERMANENT  # PERMANENT or ONE_MONTH
    note: str = ""


@dataclass
class Scenario:
    name: str
    monthly_budget: list
    baseline_growth: float | None = None  # None -> use the model's fitted value
    uplifts: list = field(default_factory=list)


@dataclass
class GuardrailBreach:
    month: int
    kind: str  # "spend_range" or "mom_change"
    value: float


@dataclass
class ScenarioResult:
    scenario: Scenario
    revenue: np.ndarray  # displayed, post-uplift monthly revenue
    lower: np.ndarray
    upper: np.ndarray
    base_business: np.ndarray
    from_marketing: np.ndarray
    from_initiatives: np.ndarray
    total_revenue: float
    total_spend: float
    revenue_per_spend: float
    guardrail_breaches: list


@dataclass
class ComparisonRow:
    name: str
    total_revenue: float
    total_spend: float
    revenue_per_spend: float
    delta_vs_baseline: float  # fraction, e.g. 0.013 for +1.3%


def apply_uplifts(base_revenue: np.ndarray, uplifts: list) -> tuple:
    """Splits a model revenue path into a permanent-uplift-only base series
    and a displayed series that also carries one-month spikes.

    Permanent uplifts compound: once applied at month k, every month from k
    onward is multiplied by (1 + pct). One-month uplifts multiply only their
    own month and never enter the base.
    """
    horizon = len(base_revenue)
    by_month = {}
    for u in uplifts:
        by_month.setdefault(u.month, []).append(u)

    base = np.empty(horizon)
    displayed = np.empty(horizon)
    permanent_multiplier = 1.0
    for i in range(horizon):
        month = i + 1
        one_month_factor = 1.0
        for u in by_month.get(month, []):
            if u.mode == PERMANENT:
                permanent_multiplier *= 1 + u.pct
            else:
                one_month_factor *= 1 + u.pct
        base[i] = base_revenue[i] * permanent_multiplier
        displayed[i] = base[i] * one_month_factor

    return base, displayed


def check_guardrails(fitted: FittedModel, monthly_budget) -> list:
    """Flags any month whose spend or month-over-month spend change falls
    outside the observed historical range."""
    breaches = []
    spend_lo, spend_hi = fitted.spend_range
    for i, spend in enumerate(monthly_budget, start=1):
        if spend < spend_lo or spend > spend_hi:
            breaches.append(GuardrailBreach(month=i, kind="spend_range", value=float(spend)))

    mom_lo, mom_hi = fitted.mom_change_range
    spend_history = [fitted.last_spend] + list(monthly_budget)
    for i in range(1, len(spend_history)):
        change = spend_history[i] / spend_history[i - 1] - 1
        if change < mom_lo or change > mom_hi:
            breaches.append(GuardrailBreach(month=i, kind="mom_change", value=float(change)))

    return breaches


def run_scenario(fitted: FittedModel, scenario: Scenario) -> ScenarioResult:
    """Forecasts a scenario end to end: model forecast, uplift application,
    and the base-business / marketing / initiatives decomposition."""
    horizon = len(scenario.monthly_budget)
    flat_budget = [fitted.last_spend] * horizon

    base_only = model_forecast(fitted, flat_budget, scenario.baseline_growth)["revenue"]
    with_marketing = model_forecast(fitted, scenario.monthly_budget, scenario.baseline_growth)
    _, displayed = apply_uplifts(with_marketing["revenue"], scenario.uplifts)
    uplift_multiplier = np.divide(
        displayed, with_marketing["revenue"], out=np.ones_like(displayed), where=with_marketing["revenue"] != 0
    )

    from_marketing = with_marketing["revenue"] - base_only
    from_initiatives = displayed - with_marketing["revenue"]

    total_spend = float(np.sum(scenario.monthly_budget))
    total_revenue = float(np.sum(displayed))

    return ScenarioResult(
        scenario=scenario,
        revenue=displayed,
        lower=with_marketing["lower"] * uplift_multiplier,
        upper=with_marketing["upper"] * uplift_multiplier,
        base_business=base_only,
        from_marketing=from_marketing,
        from_initiatives=from_initiatives,
        total_revenue=total_revenue,
        total_spend=total_spend,
        revenue_per_spend=total_revenue / total_spend,
        guardrail_breaches=check_guardrails(fitted, scenario.monthly_budget),
    )


def compare_scenarios(results: list, baseline_name: str) -> list:
    """Builds a comparison table, with each scenario's revenue delta versus
    the named baseline scenario."""
    baseline_total = next(r.total_revenue for r in results if r.scenario.name == baseline_name)
    return [
        ComparisonRow(
            name=r.scenario.name,
            total_revenue=r.total_revenue,
            total_spend=r.total_spend,
            revenue_per_spend=r.revenue_per_spend,
            delta_vs_baseline=(r.total_revenue - baseline_total) / baseline_total,
        )
        for r in results
    ]
