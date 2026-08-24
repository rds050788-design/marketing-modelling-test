"""Tests for scenario objects, uplift application, and comparison metrics
(CLAUDE.md sections 4 and 6)."""

import numpy as np
import pytest

from src.model import fit_model, load_history
from src.scenarios import (
    ONE_MONTH,
    PERMANENT,
    Scenario,
    Uplift,
    apply_uplifts,
    check_guardrails,
    compare_scenarios,
    run_scenario,
)


@pytest.fixture(scope="module")
def fitted():
    return fit_model(load_history())


@pytest.fixture
def flat_budget(fitted):
    return [fitted.last_spend] * 12


def test_one_month_uplift_does_not_compound(fitted, flat_budget):
    base = np.full(12, 1_000_000.0)
    _, displayed = apply_uplifts(base, [Uplift(month=3, pct=0.15, mode=ONE_MONTH)])

    assert displayed[2] == pytest.approx(1_150_000.0)
    # Every other month is untouched, including months after the spike.
    for i in [0, 1, 3, 4, 11]:
        assert displayed[i] == pytest.approx(1_000_000.0)


def test_permanent_uplift_compounds_into_later_months(fitted):
    base = np.full(12, 1_000_000.0)
    _, displayed = apply_uplifts(base, [Uplift(month=3, pct=0.15, mode=PERMANENT)])

    for i in [0, 1]:
        assert displayed[i] == pytest.approx(1_000_000.0)
    for i in range(2, 12):
        assert displayed[i] == pytest.approx(1_150_000.0)


def test_one_month_vs_permanent_uplift_matches_spec_magnitude(fitted, flat_budget):
    # Section 4: a single +15% uplift in month 3 of a 12-month horizon
    # should add roughly +1.1% (one-month) vs roughly +13.0% (permanent)
    # to the 12-month total, a ~12x difference from the same input.
    baseline = run_scenario(fitted, Scenario(name="Baseline", monthly_budget=flat_budget))
    one_month = run_scenario(
        fitted,
        Scenario(name="OneMonth", monthly_budget=flat_budget, uplifts=[Uplift(3, 0.15, ONE_MONTH)]),
    )
    permanent = run_scenario(
        fitted,
        Scenario(name="Permanent", monthly_budget=flat_budget, uplifts=[Uplift(3, 0.15, PERMANENT)]),
    )

    one_month_delta = one_month.total_revenue / baseline.total_revenue - 1
    permanent_delta = permanent.total_revenue / baseline.total_revenue - 1

    assert one_month_delta == pytest.approx(0.011, abs=0.003)
    assert permanent_delta == pytest.approx(0.13, abs=0.02)
    assert permanent_delta > 10 * one_month_delta


def test_decomposition_sums_to_displayed_revenue(fitted, flat_budget):
    scenario = Scenario(name="Plan", monthly_budget=flat_budget, uplifts=[Uplift(6, 0.1, PERMANENT, "Battle pass")])
    result = run_scenario(fitted, scenario)

    reconstructed = result.base_business + result.from_marketing + result.from_initiatives
    np.testing.assert_allclose(reconstructed, result.revenue, rtol=1e-9)


@pytest.mark.parametrize(
    "name,multiplier,uplifts",
    [
        ("Conservative", 0.9, []),
        ("Plan", 1.0, []),
        ("Aggressive", 1.15, []),
        ("Draft", 1.05, [Uplift(4, 0.12, PERMANENT, "Test initiative")]),
    ],
)
def test_decomposition_sums_to_total_for_every_default_scenario(fitted, name, multiplier, uplifts):
    # Guards the revenue-driver chart's decomposition (CLAUDE.md section 6,
    # item 4): base business + from marketing + from initiatives must equal
    # the scenario total, for every scenario the app pre-seeds plus a draft
    # carrying an uplift -- both per month and summed over the horizon.
    budget = [fitted.last_spend * multiplier] * 12
    result = run_scenario(fitted, Scenario(name=name, monthly_budget=budget, uplifts=uplifts))

    reconstructed = result.base_business + result.from_marketing + result.from_initiatives
    np.testing.assert_allclose(reconstructed, result.revenue, rtol=1e-9)
    assert reconstructed.sum() == pytest.approx(result.total_revenue, rel=1e-9)


def test_comparison_metrics_and_delta_vs_baseline(fitted, flat_budget):
    aggressive_budget = [b * 1.3 for b in flat_budget]
    baseline = Scenario(name="Baseline", monthly_budget=flat_budget)
    aggressive = Scenario(name="Aggressive", monthly_budget=aggressive_budget)

    results = [run_scenario(fitted, baseline), run_scenario(fitted, aggressive)]
    rows = compare_scenarios(results, baseline_name="Baseline")

    by_name = {row.name: row for row in rows}
    assert by_name["Baseline"].delta_vs_baseline == pytest.approx(0.0)
    assert by_name["Aggressive"].delta_vs_baseline > 0
    assert by_name["Aggressive"].total_spend > by_name["Baseline"].total_spend
    assert by_name["Baseline"].revenue_per_spend == pytest.approx(
        by_name["Baseline"].total_revenue / by_name["Baseline"].total_spend
    )


def test_guardrail_flags_out_of_range_spend(fitted):
    spend_lo, spend_hi = fitted.spend_range
    over_budget = [spend_hi * 2] * 12
    breaches = check_guardrails(fitted, over_budget)

    assert len(breaches) >= 12
    assert all(b.kind == "spend_range" for b in breaches if b.value == spend_hi * 2)


def test_guardrail_flags_out_of_range_mom_change(fitted):
    budget = [fitted.last_spend, fitted.last_spend * 3] + [fitted.last_spend * 3] * 10
    breaches = check_guardrails(fitted, budget)

    assert any(b.kind == "mom_change" and b.month == 2 for b in breaches)


def test_guardrails_clean_for_a_modest_flat_budget(fitted, flat_budget):
    assert check_guardrails(fitted, flat_budget) == []
