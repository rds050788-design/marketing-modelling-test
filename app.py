"""Revenue Scenario Planner -- Streamlit UI (CLAUDE.md section 6).

This checkpoint covers the sidebar inputs, pre-seeded scenarios, and range
guardrails. Charts, the tutorial, and export are added in later checkpoints.
"""

import io

import pandas as pd
import streamlit as st

from src import copy
from src.charts import build_driver_chart, build_forecast_chart, display_name
from src.formatting import format_currency, format_date, format_percent
from src.model import FORECAST_HORIZON, fit_model, load_history
from src.scenarios import ONE_MONTH, PERMANENT, Scenario, Uplift, check_guardrails, compare_scenarios, run_scenario

st.set_page_config(page_title=copy.APP_TITLE, page_icon="📈", layout="wide")


@st.cache_resource
def get_model():
    history = load_history()
    fitted = fit_model(history)
    return history, fitted


HISTORY, FITTED = get_model()

FORECAST_MONTHS = pd.date_range(
    start=HISTORY["year_month"].iloc[-1] + pd.DateOffset(months=1),
    periods=FORECAST_HORIZON,
    freq="MS",
)
MONTH_LABELS = [format_date(d) for d in FORECAST_MONTHS]
MONTH_LABEL_TO_INDEX = {label: i + 1 for i, label in enumerate(MONTH_LABELS)}


def default_budget(multiplier: float) -> list:
    return [round(FITTED.last_spend * multiplier)] * FORECAST_HORIZON


def preset_scenarios() -> dict:
    return {
        "Conservative": Scenario("Conservative", default_budget(0.9)),
        "Plan": Scenario("Plan", default_budget(1.0)),
        "Aggressive": Scenario("Aggressive", default_budget(1.15)),
    }


def uplifts_from_editor(df: pd.DataFrame) -> list:
    uplifts = []
    for _, row in df.iterrows():
        month_label = row.get(copy.INITIATIVES_MONTH_COLUMN)
        pct = row.get(copy.INITIATIVES_UPLIFT_COLUMN)
        mode_label = row.get(copy.INITIATIVES_MODE_COLUMN)
        note = row.get(copy.INITIATIVES_NOTE_COLUMN)
        if month_label is None or pct is None or pd.isna(pct):
            continue
        month = MONTH_LABEL_TO_INDEX.get(month_label)
        if month is None:
            continue
        mode = PERMANENT if mode_label == copy.UPLIFT_MODE_PERMANENT else ONE_MONTH
        uplifts.append(Uplift(month=month, pct=float(pct) / 100, mode=mode, note=note or ""))
    return uplifts


if "scenarios" not in st.session_state:
    st.session_state.scenarios = preset_scenarios()
if "draft_budget" not in st.session_state:
    st.session_state.draft_budget = default_budget(1.0)
if "draft_uplifts_df" not in st.session_state:
    st.session_state.draft_uplifts_df = pd.DataFrame(
        columns=[
            copy.INITIATIVES_MONTH_COLUMN,
            copy.INITIATIVES_UPLIFT_COLUMN,
            copy.INITIATIVES_MODE_COLUMN,
            copy.INITIATIVES_NOTE_COLUMN,
        ]
    )
if "draft_baseline_growth_pct" not in st.session_state:
    st.session_state.draft_baseline_growth_pct = round(FITTED.intercept * 100, 1)
if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True

title_col, reopen_col = st.columns([20, 1])
with title_col:
    st.title(copy.APP_TITLE)
with reopen_col:
    if st.button(copy.WELCOME_REOPEN_BUTTON, help=copy.WELCOME_REOPEN_TOOLTIP):
        st.session_state.show_welcome = True
st.caption(copy.APP_TAGLINE)

if st.session_state.show_welcome:
    with st.container(border=True):
        st.markdown(f"**{copy.WELCOME_TITLE}**")
        for i, step in enumerate(copy.WELCOME_STEPS, start=1):
            st.markdown(f"{i}. {step}")
        dismiss_col, example_col = st.columns(2)
        with dismiss_col:
            if st.button(copy.WELCOME_DISMISS_BUTTON, use_container_width=True):
                st.session_state.show_welcome = False
                st.rerun()
        with example_col:
            if st.button(copy.WELCOME_EXAMPLE_BUTTON, use_container_width=True):
                st.session_state.scenarios[copy.WELCOME_EXAMPLE_SCENARIO_NAME] = Scenario(
                    name=copy.WELCOME_EXAMPLE_SCENARIO_NAME,
                    monthly_budget=default_budget(1.0),
                    uplifts=[Uplift(month=6, pct=0.15, mode=PERMANENT, note=copy.WELCOME_EXAMPLE_UPLIFT_NOTE)],
                )
                st.session_state.show_welcome = False
                st.rerun()

with st.sidebar:
    st.header(copy.BUDGET_SECTION_HEADER)

    budget_df = pd.DataFrame(
        {
            copy.BUDGET_MONTH_COLUMN: MONTH_LABELS,
            copy.BUDGET_AMOUNT_COLUMN: [b / 1_000_000 for b in st.session_state.draft_budget],
        }
    )
    edited_budget_df = st.data_editor(
        budget_df,
        column_config={
            copy.BUDGET_MONTH_COLUMN: st.column_config.TextColumn(disabled=True),
            copy.BUDGET_AMOUNT_COLUMN: st.column_config.NumberColumn(
                format="€%.2f", min_value=0.0, step=0.01, help=copy.BUDGET_TABLE_HELP
            ),
        },
        hide_index=True,
        use_container_width=True,
        key="budget_editor",
    )
    st.session_state.draft_budget = [
        round(v * 1_000_000) for v in edited_budget_df[copy.BUDGET_AMOUNT_COLUMN].tolist()
    ]

    scale_col, apply_col = st.columns([2, 1])
    with scale_col:
        scale_pct = st.number_input(copy.BUDGET_SCALE_LABEL, value=0, step=5, help=copy.BUDGET_SCALE_HELP)
    with apply_col:
        st.write("")
        st.write("")
        if st.button("Apply", key="apply_scale"):
            factor = 1 + scale_pct / 100
            st.session_state.draft_budget = [round(b * factor) for b in st.session_state.draft_budget]
            st.rerun()

    breaches = check_guardrails(FITTED, st.session_state.draft_budget)
    spend_hi = any(b.kind == "spend_range" and b.value > FITTED.spend_range[1] for b in breaches)
    spend_lo = any(b.kind == "spend_range" and b.value < FITTED.spend_range[0] for b in breaches)
    mom_out = any(b.kind == "mom_change" for b in breaches)
    if spend_hi:
        st.warning(copy.GUARDRAIL_SPEND_TOO_HIGH)
    if spend_lo:
        st.warning(copy.GUARDRAIL_SPEND_TOO_LOW)
    if mom_out:
        st.warning(copy.GUARDRAIL_MOM_CHANGE)

    st.header(copy.INITIATIVES_SECTION_HEADER)
    st.caption(copy.INITIATIVES_TABLE_HELP)

    edited_uplifts_df = st.data_editor(
        st.session_state.draft_uplifts_df,
        column_config={
            copy.INITIATIVES_MONTH_COLUMN: st.column_config.SelectboxColumn(
                options=MONTH_LABELS, default=MONTH_LABELS[0]
            ),
            copy.INITIATIVES_UPLIFT_COLUMN: st.column_config.NumberColumn(
                format="%.1f%%", step=1.0
            ),
            copy.INITIATIVES_MODE_COLUMN: st.column_config.SelectboxColumn(
                options=copy.UPLIFT_MODE_OPTIONS,
                default=copy.UPLIFT_MODE_PERMANENT,
                help=copy.INITIATIVES_MODE_HELP,
            ),
            copy.INITIATIVES_NOTE_COLUMN: st.column_config.TextColumn(
                default="", help=copy.INITIATIVES_NOTE_PLACEHOLDER
            ),
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="uplifts_editor",
    )
    st.session_state.draft_uplifts_df = edited_uplifts_df

    baseline_growth_pct = st.number_input(
        copy.BASELINE_GROWTH_LABEL,
        value=st.session_state.draft_baseline_growth_pct,
        step=0.1,
        format="%.1f",
        help=copy.BASELINE_GROWTH_HELP,
    )
    st.session_state.draft_baseline_growth_pct = baseline_growth_pct

    st.divider()
    scenario_name = st.text_input(
        copy.SAVE_SCENARIO_NAME_LABEL, key="new_scenario_name", help=copy.SAVE_SCENARIO_NAME_HELP
    )
    if st.button(copy.SAVE_SCENARIO_BUTTON, use_container_width=True):
        name = scenario_name.strip()
        if name:
            st.session_state.scenarios[name] = Scenario(
                name=name,
                monthly_budget=list(st.session_state.draft_budget),
                baseline_growth=st.session_state.draft_baseline_growth_pct / 100,
                uplifts=uplifts_from_editor(st.session_state.draft_uplifts_df),
            )
            st.rerun()

draft_scenario = Scenario(
    name=copy.HEADLINE_DRAFT_SCENARIO_LABEL,
    monthly_budget=list(st.session_state.draft_budget),
    baseline_growth=st.session_state.draft_baseline_growth_pct / 100,
    uplifts=uplifts_from_editor(st.session_state.draft_uplifts_df),
)
draft_result = run_scenario(FITTED, draft_scenario)

saved_results = [run_scenario(FITTED, s) for s in st.session_state.scenarios.values()]
baseline_name = "Plan" if "Plan" in st.session_state.scenarios else saved_results[0].scenario.name

# Every visual below reflects both saved scenarios and the live draft, so an
# edit in the sidebar is visible everywhere, not just in the headline cards.
all_results = saved_results + [draft_result]
rows = compare_scenarios(all_results, baseline_name=baseline_name)
rows_by_name = {row.name: row for row in rows}
draft_row = rows_by_name[draft_scenario.name]

st.caption(copy.HEADLINE_SECTION_CAPTION.format(baseline=baseline_name))
metric_cols = st.columns(4)
metric_cols[0].metric(copy.HEADLINE_TOTAL_REVENUE, format_currency(draft_row.total_revenue))
metric_cols[1].metric(copy.HEADLINE_TOTAL_SPEND, format_currency(draft_row.total_spend))
metric_cols[2].metric(copy.HEADLINE_REVENUE_PER_SPEND, f"€{draft_row.revenue_per_spend:.2f}")
metric_cols[3].metric(copy.HEADLINE_VS_BASELINE, format_percent(draft_row.delta_vs_baseline, signed=True))

forecast_fig = build_forecast_chart(HISTORY, FORECAST_MONTHS, saved_results, draft_result)
st.plotly_chart(forecast_fig, use_container_width=True)

st.subheader(copy.CHART_COMPARE_TITLE)
comparison_table = pd.DataFrame(
    [
        {
            "Scenario": display_name(result),
            copy.HEADLINE_TOTAL_REVENUE: format_currency(row.total_revenue),
            copy.HEADLINE_TOTAL_SPEND: format_currency(row.total_spend),
            copy.HEADLINE_REVENUE_PER_SPEND: f"€{row.revenue_per_spend:.2f}",
            copy.HEADLINE_VS_BASELINE: format_percent(row.delta_vs_baseline, signed=True),
            copy.CHART_DRIVERS_BASE_LABEL: format_currency(result.base_business.sum()),
            copy.CHART_DRIVERS_MARKETING_LABEL: format_currency(result.from_marketing.sum()),
            copy.CHART_DRIVERS_INITIATIVES_LABEL: format_currency(result.from_initiatives.sum()),
        }
        for result, row in zip(all_results, rows)
    ]
)
st.dataframe(comparison_table, hide_index=True, use_container_width=True)
if any(result.guardrail_breaches for result in all_results):
    st.caption(copy.GUARDRAIL_SCENARIO_FOOTNOTE)

export_table = pd.DataFrame(
    [
        {
            "Scenario": display_name(result),
            copy.HEADLINE_TOTAL_REVENUE: row.total_revenue,
            copy.HEADLINE_TOTAL_SPEND: row.total_spend,
            copy.HEADLINE_REVENUE_PER_SPEND: row.revenue_per_spend,
            copy.HEADLINE_VS_BASELINE: row.delta_vs_baseline * 100,
            copy.CHART_DRIVERS_BASE_LABEL: float(result.base_business.sum()),
            copy.CHART_DRIVERS_MARKETING_LABEL: float(result.from_marketing.sum()),
            copy.CHART_DRIVERS_INITIATIVES_LABEL: float(result.from_initiatives.sum()),
        }
        for result, row in zip(all_results, rows)
    ]
)
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    export_table.to_excel(writer, index=False, sheet_name="Comparison")
st.download_button(
    copy.EXPORT_BUTTON_LABEL,
    data=excel_buffer.getvalue(),
    file_name="revenue_scenario_comparison.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.subheader(copy.CHART_DRIVERS_TITLE)
driver_fig = build_driver_chart(saved_results, draft_result)
st.plotly_chart(driver_fig, use_container_width=True)
