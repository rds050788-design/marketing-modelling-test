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

from src.charts import build_comparison_chart, build_forecast_chart, display_name
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


def test_comparison_chart_includes_draft_and_reacts_to_budget_change(fitted):
    saved = [run_scenario(fitted, Scenario(name="Plan", monthly_budget=[fitted.last_spend] * FORECAST_HORIZON))]
    draft_low = run_scenario(fitted, Scenario(name="Draft", monthly_budget=[fitted.last_spend * 0.8] * FORECAST_HORIZON))
    draft_high = run_scenario(fitted, Scenario(name="Draft", monthly_budget=[fitted.last_spend * 1.3] * FORECAST_HORIZON))

    fig_low = build_comparison_chart(saved, draft_low)
    fig_high = build_comparison_chart(saved, draft_high)

    names = list(fig_low.data[0].y)
    assert "Plan" in names
    assert display_name(draft_low) in names

    totals_low = dict(zip(fig_low.data[0].y, fig_low.data[0].x))
    totals_high = dict(zip(fig_high.data[0].y, fig_high.data[0].x))
    assert totals_low[display_name(draft_low)] != totals_high[display_name(draft_high)]
    assert totals_low["Plan"] == totals_high["Plan"]


def test_comparison_chart_marks_out_of_range_scenario(fitted):
    spend_hi = fitted.spend_range[1]
    breaching = run_scenario(fitted, Scenario(name="Aggressive", monthly_budget=[spend_hi * 2] * FORECAST_HORIZON))
    clean_draft = run_scenario(fitted, Scenario(name="Draft", monthly_budget=[fitted.last_spend] * FORECAST_HORIZON))

    fig = build_comparison_chart([breaching], clean_draft)
    names = list(fig.data[0].y)

    assert "Aggressive *" in names
    assert display_name(clean_draft) in names
    assert not display_name(clean_draft).endswith("*")
