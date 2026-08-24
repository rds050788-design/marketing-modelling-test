"""Tests that app.py's own wiring connects sidebar edits to every visual --
not just that the underlying chart/scenario functions are correct in
isolation (tests/test_charts.py covers that), but that app.py actually
calls them with the live draft's current state.

These drive the real app.py end to end via AppTest and st.session_state,
the same session_state key the sidebar's data_editor writes to. This is
the layer where the original bug lived: build_forecast_chart and
run_scenario were both correct, but app.py fed the chart, comparison
table, and guardrail footnote from a `results` list that never included
the draft. A structurally-identical regression -- wiring a visual to the
wrong list again -- would not be caught by tests/test_charts.py, since
that module never touches app.py at all.
"""

import json

import pytest
from streamlit.testing.v1 import AppTest

from src.model import fit_model, load_history


def _run_with_draft_budget(budget):
    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    assert not at.exception
    at.session_state["draft_budget"] = list(budget)
    at.run(timeout=30)
    assert not at.exception
    return at


def _draft_chart_trace(at):
    chart = at.get("plotly_chart")[0]
    spec = json.loads(chart.proto.spec)
    return spec["data"][-1]  # the draft is always added last, see src/charts.py


def _draft_table_row(at):
    table = at.dataframe[0].value
    draft_rows = table[table["Scenario"].str.startswith("Current plan")]
    assert len(draft_rows) == 1
    return draft_rows.iloc[0]


@pytest.fixture
def baseline_budget():
    # A fixed, known-nonzero reference budget -- deliberately not read from
    # the app's own default draft state, which is zero by design (the
    # draft starts blank; see app.py). Scaling zero by any factor is still
    # zero, which would make every test below vacuously pass or fail for
    # the wrong reason.
    fitted = fit_model(load_history())
    return [fitted.last_spend] * 12


def test_chart_reacts_to_draft_budget_change_in_the_real_app(baseline_budget):
    at_low = _run_with_draft_budget([b * 0.8 for b in baseline_budget])
    at_high = _run_with_draft_budget([b * 1.3 for b in baseline_budget])

    y_low = _draft_chart_trace(at_low)["y"]
    y_high = _draft_chart_trace(at_high)["y"]

    assert y_low != y_high
    assert y_high[-1] > y_low[-1]


def test_comparison_table_reacts_to_draft_budget_change_in_the_real_app(baseline_budget):
    at_low = _run_with_draft_budget([b * 0.8 for b in baseline_budget])
    at_high = _run_with_draft_budget([b * 1.3 for b in baseline_budget])

    row_low = _draft_table_row(at_low)
    row_high = _draft_table_row(at_high)

    assert row_low["Total 12-month revenue"] != row_high["Total 12-month revenue"]


def test_draft_guardrail_marker_appears_on_chart_and_table_when_draft_goes_out_of_range(baseline_budget):
    at = _run_with_draft_budget([b * 3 for b in baseline_budget])

    assert _draft_chart_trace(at)["name"].endswith("*")
    assert _draft_table_row(at)["Scenario"].endswith("*")


def test_fresh_app_load_with_zero_draft_budget_does_not_raise():
    # The draft starts at zero for all 12 months by design (see app.py) --
    # this is now the state of every single app load, not an edge case.
    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    assert not at.exception
    assert at.session_state["draft_budget"] == [0] * 12


def test_setting_a_single_month_to_zero_does_not_raise(baseline_budget):
    budget = list(baseline_budget)
    budget[4] = 0
    at = _run_with_draft_budget(budget)
    assert not at.exception
