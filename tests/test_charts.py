"""Tests for chart builders (CLAUDE.md section 6, items 2-4).

The forecast chart previously plotted only saved scenarios; the live draft
(what app.py's sidebar is currently editing) was computed but never reached
the chart, so editing the budget moved the headline cards but not the chart
line. These tests call build_forecast_chart directly with two different
draft budgets -- the same function app.py calls -- and assert the chart's
own trace data actually changes, so this class of bug fails a test rather
than requiring a person to notice it in the browser.
"""

import pandas as pd
import pytest

from src.charts import build_driver_chart, build_forecast_chart, display_name
from src.model import FORECAST_HORIZON, fit_model, load_history
from src.scenarios import Scenario, Uplift, run_scenario


@pytest.fixture(scope="module")
def history():
    return load_history()


@pytest.fixture(scope="module")
def fitted(history):
    return fit_model(history)


@pytest.fixture
def forecast_months(history):
    return pd.date_range(
        start=history["year_month"].iloc[-1] + pd.DateOffset(months=1),
        periods=FORECAST_HORIZON,
        freq="MS",
    )


def _draft_line_trace(fig, draft_result):
    trace = fig.data[-1]
    assert trace.name == display_name(draft_result)
    return trace


def test_chart_line_moves_when_draft_budget_changes(fitted, history, forecast_months):
    low_budget = [fitted.last_spend * 0.8] * FORECAST_HORIZON
    high_budget = [fitted.last_spend * 1.3] * FORECAST_HORIZON

    draft_low = run_scenario(fitted, Scenario(name="Draft", monthly_budget=low_budget))
    draft_high = run_scenario(fitted, Scenario(name="Draft", monthly_budget=high_budget))

    fig_low = build_forecast_chart(history, forecast_months, saved_results=[], draft_result=draft_low)
    fig_high = build_forecast_chart(history, forecast_months, saved_results=[], draft_result=draft_high)

    y_low = list(_draft_line_trace(fig_low, draft_low).y)
    y_high = list(_draft_line_trace(fig_high, draft_high).y)

    assert y_low != y_high
    assert y_high[-1] > y_low[-1]


def test_chart_includes_draft_alongside_saved_scenarios(fitted, history, forecast_months):
    saved = [run_scenario(fitted, Scenario(name="Plan", monthly_budget=[fitted.last_spend] * FORECAST_HORIZON))]
    draft = run_scenario(
        fitted, Scenario(name="Draft", monthly_budget=[fitted.last_spend * 1.3] * FORECAST_HORIZON)
    )

    fig = build_forecast_chart(history, forecast_months, saved_results=saved, draft_result=draft)
    trace_names = [t.name for t in fig.data]

    assert "Plan" in trace_names
    assert display_name(draft) in trace_names


def test_chart_uplift_marker_uses_the_users_note(fitted, history, forecast_months):
    draft = run_scenario(
        fitted,
        Scenario(
            name="Draft",
            monthly_budget=[fitted.last_spend] * FORECAST_HORIZON,
            uplifts=[Uplift(month=3, pct=0.15, note="Battle pass launch")],
        ),
    )
    fig = build_forecast_chart(history, forecast_months, saved_results=[], draft_result=draft)

    marker_traces = [t for t in fig.data if t.name and t.name.endswith("initiatives")]
    assert len(marker_traces) == 1
    assert marker_traces[0].text[0] == "Battle pass launch"


def test_driver_chart_segments_sum_to_scenario_totals(fitted):
    saved = [
        run_scenario(fitted, Scenario(name="Conservative", monthly_budget=[fitted.last_spend * 0.9] * FORECAST_HORIZON)),
        run_scenario(fitted, Scenario(name="Plan", monthly_budget=[fitted.last_spend] * FORECAST_HORIZON)),
    ]
    draft = run_scenario(
        fitted,
        Scenario(
            name="Draft",
            monthly_budget=[fitted.last_spend * 1.15] * FORECAST_HORIZON,
            uplifts=[Uplift(month=4, pct=0.12, note="Test initiative")],
        ),
    )

    fig = build_driver_chart(saved, draft)
    base_trace, marketing_trace, initiatives_trace = fig.data

    names = list(base_trace.y)
    assert names == [display_name(r) for r in saved] + [display_name(draft)]

    all_results = saved + [draft]
    for i, result in enumerate(all_results):
        segment_sum = base_trace.x[i] + marketing_trace.x[i] + initiatives_trace.x[i]
        assert segment_sum == pytest.approx(result.total_revenue, rel=1e-9)
