"""Tests for the "view or load a saved scenario" sidebar control. Previously
there was no way to see a saved scenario's actual budget without guessing --
this drives the real app.py via AppTest to confirm loading a scenario
populates the draft with its exact numbers, editable and inspectable.
"""

from streamlit.testing.v1 import AppTest

from src import copy


def _fresh_app():
    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    assert not at.exception
    return at


def _load_scenario(at, name):
    at.selectbox[0].set_value(name).run(timeout=30)
    assert not at.exception
    load_button = next(b for b in at.button if b.label == copy.LOAD_SCENARIO_BUTTON)
    load_button.click().run(timeout=30)
    assert not at.exception
    return at


def test_loading_aggressive_populates_the_draft_with_its_exact_budget():
    at = _fresh_app()
    aggressive_budget = list(at.session_state["scenarios"]["Aggressive"].monthly_budget)
    assert at.session_state["draft_budget"] != aggressive_budget  # sanity: draft starts blank

    at = _load_scenario(at, "Aggressive")

    assert at.session_state["draft_budget"] == aggressive_budget


def test_loading_a_scenario_with_an_uplift_populates_the_initiatives_table():
    at = _fresh_app()

    # Save a scenario with an uplift via the draft, so there's a saved
    # scenario with real initiatives to load back.
    at.session_state["draft_budget"] = [4_000_000] * 12
    at.session_state["draft_uplifts_df"] = at.session_state["draft_uplifts_df"]
    at.run(timeout=30)

    from src.scenarios import PERMANENT, Scenario, Uplift

    at.session_state["scenarios"]["WithUplift"] = Scenario(
        name="WithUplift",
        monthly_budget=[4_000_000] * 12,
        uplifts=[Uplift(month=7, pct=0.2, mode=PERMANENT, note="Test note")],
    )
    at.session_state["draft_budget"] = [0] * 12  # reset draft so loading is observable
    at.run(timeout=30)

    at = _load_scenario(at, "WithUplift")

    assert at.session_state["draft_budget"] == [4_000_000] * 12
    uplifts_df = at.session_state["draft_uplifts_df"]
    assert len(uplifts_df) == 1
    assert uplifts_df.iloc[0][copy.INITIATIVES_NOTE_COLUMN] == "Test note"
    assert uplifts_df.iloc[0][copy.INITIATIVES_UPLIFT_COLUMN] == 20.0
    assert uplifts_df.iloc[0][copy.INITIATIVES_MODE_COLUMN] == copy.UPLIFT_MODE_PERMANENT


def test_comparison_table_shows_each_scenarios_monthly_budget_range():
    at = _fresh_app()
    table = at.dataframe[0].value

    assert copy.HEADLINE_MONTHLY_BUDGET_COLUMN in table.columns
    plan_row = table[table["Scenario"] == "Plan"].iloc[0]
    # Plan is a flat budget, so its range collapses to a single figure.
    assert "-" not in plan_row[copy.HEADLINE_MONTHLY_BUDGET_COLUMN]
    assert plan_row[copy.HEADLINE_MONTHLY_BUDGET_COLUMN].startswith("€")
