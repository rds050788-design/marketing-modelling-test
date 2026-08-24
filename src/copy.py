"""Every user-facing string in the app, in one place (CLAUDE.md section 5).

Nothing here may use statistical vocabulary: elasticity, coefficient,
p-value, confidence interval, adstock, carryover, log, regression, MAPE,
R-squared, bootstrap, significance. The translation table in section 5 is
used verbatim below.
"""

# --- App framing ---------------------------------------------------------

APP_TITLE = "Revenue Scenario Planner"
APP_TAGLINE = "Forecast next year's revenue under different marketing budgets and plans."

# --- First-run tutorial (section 7) ---------------------------------------

WELCOME_TITLE = "This tool forecasts revenue for the next 12 months."
WELCOME_STEPS = [
    "Three example scenarios are already loaded. The chart compares them.",
    "Your plan starts blank — type a monthly marketing figure in the table on the "
    "left to begin building it.",
    "Add a game initiative and choose whether it permanently lifts revenue or is a "
    "one-month spike.",
    "Save it as a new scenario to compare against the others.",
]
WELCOME_DISMISS_BUTTON = "Got it"
WELCOME_EXAMPLE_BUTTON = "Show me an example"
WELCOME_REOPEN_BUTTON = "?"
WELCOME_REOPEN_TOOLTIP = "Show the introduction again"
WELCOME_EXAMPLE_SCENARIO_NAME = "Example: Battle pass launch"
WELCOME_EXAMPLE_UPLIFT_NOTE = "Battle pass launch"

# --- Sidebar: marketing budget ---------------------------------------------

BUDGET_SECTION_HEADER = "Marketing budget"
BUDGET_TABLE_HELP = "Type a monthly marketing budget for each of the next 12 months."
BUDGET_SCALE_LABEL = "Scale the whole budget by a percentage"
BUDGET_SCALE_HELP = (
    "Quickly raise or lower every month's budget by the same percentage, "
    "instead of editing each one."
)
BUDGET_SCALE_APPLY_BUTTON = "Apply"
BUDGET_MONTH_COLUMN = "Month"
BUDGET_AMOUNT_COLUMN = "Marketing budget (€M)"

# --- Sidebar: game initiatives ---------------------------------------------

INITIATIVES_SECTION_HEADER = "Game initiatives"
INITIATIVES_TABLE_HELP = (
    "Add planned initiatives — like a battle pass or seasonal event — and how much "
    "extra revenue you expect them to bring."
)
INITIATIVES_MONTH_COLUMN = "Month"
INITIATIVES_UPLIFT_COLUMN = "Uplift %"
INITIATIVES_MODE_COLUMN = "Mode"
INITIATIVES_NOTE_COLUMN = "Note"
INITIATIVES_NOTE_PLACEHOLDER = "e.g. Battle pass launch"

UPLIFT_MODE_PERMANENT = "Permanent lift to the revenue base"
UPLIFT_MODE_ONE_MONTH = "One-month spike"
UPLIFT_MODE_OPTIONS = [UPLIFT_MODE_PERMANENT, UPLIFT_MODE_ONE_MONTH]
INITIATIVES_MODE_HELP = (
    "Permanent lift to the revenue base: revenue stays higher every month after this "
    "one. One-month spike: revenue is higher for this month only."
)

# --- Sidebar: baseline growth -----------------------------------------------

BASELINE_GROWTH_LABEL = "Revenue growth per month without extra marketing (%)"
BASELINE_GROWTH_HELP = (
    "Revenue grows about 3.5% a month on its own, without extra marketing. Adjust "
    "this if you expect the game's natural growth to speed up or slow down."
)

# --- Sidebar: save scenario --------------------------------------------------

SAVE_SCENARIO_NAME_LABEL = "Scenario name"
SAVE_SCENARIO_NAME_HELP = "Give this combination of budget and initiatives a name."
SAVE_SCENARIO_BUTTON = "Save scenario"

# --- Guardrails (amber, non-blocking) ---------------------------------------

GUARDRAIL_SPEND_TOO_HIGH = "This budget is far larger than anything tried before — treat with caution"
GUARDRAIL_SPEND_TOO_LOW = "This budget is far smaller than anything tried before — treat with caution"
GUARDRAIL_ZERO_BUDGET = (
    "A €0 budget is far outside the range this model was built on, so that month's "
    "forecast reflects your baseline growth only — not a modelled marketing effect."
)
GUARDRAIL_MOM_CHANGE = (
    "This is a much bigger month-to-month change in spend than we've seen before — "
    "treat with caution"
)
GUARDRAIL_SCENARIO_MARKER = "*"
GUARDRAIL_SCENARIO_FOOTNOTE = (
    "* This scenario's budget goes outside the range tested in the underlying data — "
    "treat its forecast with extra caution."
)

# --- Headline metrics (section 6, item 1) -----------------------------------

HEADLINE_TOTAL_REVENUE = "Total 12-month revenue"
HEADLINE_TOTAL_SPEND = "Total marketing spend"
HEADLINE_REVENUE_PER_SPEND = "Revenue per €1 spent"
HEADLINE_VS_BASELINE = "Change vs the baseline scenario"
HEADLINE_DRAFT_SCENARIO_LABEL = "Current plan (unsaved)"
HEADLINE_SECTION_CAPTION = "Your current plan, compared to the {baseline} scenario"

# --- Charts (section 6, items 2-4) ------------------------------------------

CHART_FORECAST_TITLE = "Revenue forecast"
CHART_FORECAST_HISTORY_LABEL = "History"
CHART_FORECAST_LIKELY_RANGE_LABEL = "Likely range"
CHART_UPLIFT_DEFAULT_NOTE = "Game initiative"
CHART_COMPARE_TITLE = "Compare scenarios"
CHART_DRIVERS_TITLE = "Where revenue comes from"
CHART_DRIVERS_BASE_LABEL = "Base business"
CHART_DRIVERS_MARKETING_LABEL = "From marketing"
CHART_DRIVERS_INITIATIVES_LABEL = "From initiatives"

# --- How this works (section 5) ---------------------------------------------

HOW_THIS_WORKS_HEADER = "How this works"
HOW_THIS_WORKS_BULLETS = [
    "Revenue grows about 3.5% a month on its own, without extra marketing.",
    "Every 10% more marketing adds roughly 2% more revenue that month.",
    "Marketing keeps working into the following month.",
    "Tested against the last 8 months, forecasts landed within about 1%.",
]

# --- Export -------------------------------------------------------------------

EXPORT_BUTTON_LABEL = "Download comparison as Excel"
