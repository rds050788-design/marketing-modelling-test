"""Plotly chart builders (CLAUDE.md section 6, items 2-4). Pure functions,
no Streamlit dependency, so they can be exercised directly in tests -- the
same code path app.py calls, callable without a script-run context.
"""

from __future__ import annotations

import plotly.graph_objects as go

from src import copy
from src.formatting import format_currency
from src.theme import (
    BASE_SEGMENT_COLOR,
    DRAFT_COLOR,
    HISTORY_LINE_COLOR,
    INITIATIVES_SEGMENT_COLOR,
    MARKER_OUTLINE_COLOR,
    MARKETING_SEGMENT_COLOR,
    SCENARIO_COLORS,
)

# Presentation-only widening of the shown likely range for months whose
# budget goes outside the range the model was ever tested on -- the point
# forecast (revenue) is untouched; only how uncertain it *looks* changes.
UNRELIABLE_RANGE_WIDEN_FACTOR = 2.0
UNRELIABLE_OPACITY = 0.45


def display_name(result) -> str:
    """Scenario name, flagged with a warning icon if its budget goes
    outside the tested range. Use this wherever a scenario name is shown."""
    if result.guardrail_breaches:
        return f"{copy.GUARDRAIL_SCENARIO_MARKER} {result.scenario.name}"
    return result.scenario.name


def _rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def scenario_colors(saved_results: list) -> list:
    """One colour per saved scenario, in order -- the same assignment used
    by every chart, so a scenario is the same colour everywhere it appears."""
    return [SCENARIO_COLORS[i % len(SCENARIO_COLORS)] for i in range(len(saved_results))]


def _line_segments(flags: list) -> list:
    """Groups points into contiguous line segments by destination-point
    reliability, so a segment ending at an out-of-range month is styled
    differently from one that doesn't. flags[0] (the history anchor) is
    always reliable. Adjacent segments share their boundary point so the
    line still joins up with no visual gap. Returns (start, end, is_unreliable).
    """
    n = len(flags)
    if n < 2:
        return [(0, n - 1, False)]
    segments = []
    seg_start = 0
    seg_style = flags[1]
    for i in range(2, n):
        if flags[i] != seg_style:
            segments.append((seg_start, i - 1, seg_style))
            seg_start = i - 1
            seg_style = flags[i]
    segments.append((seg_start, n - 1, seg_style))
    return segments


def build_forecast_chart(history, forecast_months, saved_results: list, draft_result) -> go.Figure:
    """History solid, forecast dashed, shaded likely range, one colour per
    scenario. The live draft gets a reserved colour, a thicker line, and a
    distinct dash pattern so it never blends in with a saved scenario -- it
    is the one line on this chart that moves as the sidebar is edited.

    Months whose budget goes outside the range the model was tested on are
    drawn as a dotted, dimmed segment with a visually widened likely range
    -- the forecast number itself is unchanged, only how certain it looks.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=history["year_month"],
            y=history["total_revenue"],
            mode="lines",
            name=copy.CHART_FORECAST_HISTORY_LABEL,
            line=dict(color=HISTORY_LINE_COLOR, width=2),
            text=[format_currency(v) for v in history["total_revenue"]],
            hovertemplate="%{x|%b %Y}<br>%{text}<extra>" + copy.CHART_FORECAST_HISTORY_LABEL + "</extra>",
        )
    )

    last_x = history["year_month"].iloc[-1]
    last_y = float(history["total_revenue"].iloc[-1])
    forecast_months = list(forecast_months)

    def add_scenario_trace(result, color: str, width: int, dash: str):
        name = display_name(result)
        x = [last_x] + forecast_months
        y = [last_y] + list(result.revenue)
        lower = [last_y] + list(result.lower)
        upper = [last_y] + list(result.upper)

        breach_months = {b.month for b in result.guardrail_breaches}
        flags = [False] + [(m + 1) in breach_months for m in range(len(forecast_months))]
        segments = _line_segments(flags)

        for seg_i, (start, end, unreliable) in enumerate(segments):
            seg_x = x[start : end + 1]
            seg_y = y[start : end + 1]
            seg_lower = lower[start : end + 1]
            seg_upper = upper[start : end + 1]

            if unreliable:
                mid = [(lo + hi) / 2 for lo, hi in zip(seg_lower, seg_upper)]
                half = [(hi - lo) / 2 * UNRELIABLE_RANGE_WIDEN_FACTOR for lo, hi in zip(seg_lower, seg_upper)]
                seg_lower = [m - h for m, h in zip(mid, half)]
                seg_upper = [m + h for m, h in zip(mid, half)]

            fig.add_trace(
                go.Scatter(
                    x=seg_x + seg_x[::-1],
                    y=seg_upper + seg_lower[::-1],
                    fill="toself",
                    fillcolor=_rgba(color, 0.25 if unreliable else 0.15),
                    line=dict(width=0),
                    hoverinfo="skip",
                    showlegend=False,
                    name=f"{name} {copy.CHART_FORECAST_LIKELY_RANGE_LABEL}",
                )
            )

            seg_text = [format_currency(v) for v in seg_y]
            hovertemplate = "%{x|%b %Y}<br>%{text}"
            if unreliable:
                hovertemplate += "<br><i>" + copy.GUARDRAIL_UNRELIABLE_HOVER + "</i>"
            hovertemplate += "<extra>" + name + "</extra>"

            fig.add_trace(
                go.Scatter(
                    x=seg_x,
                    y=seg_y,
                    mode="lines+markers",
                    name=name,
                    legendgroup=name,
                    showlegend=(seg_i == 0),
                    opacity=UNRELIABLE_OPACITY if unreliable else 1.0,
                    line=dict(color=color, width=width, dash="dot" if unreliable else dash),
                    marker=dict(size=4),
                    text=seg_text,
                    hovertemplate=hovertemplate,
                )
            )

        if result.scenario.uplifts:
            ux = [forecast_months[u.month - 1] for u in result.scenario.uplifts]
            uy = [result.revenue[u.month - 1] for u in result.scenario.uplifts]
            texts = [u.note or copy.CHART_UPLIFT_DEFAULT_NOTE for u in result.scenario.uplifts]
            fig.add_trace(
                go.Scatter(
                    x=ux,
                    y=uy,
                    mode="markers",
                    marker=dict(size=11, symbol="star", color=color, line=dict(width=1, color=MARKER_OUTLINE_COLOR)),
                    name=f"{name} initiatives",
                    text=texts,
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                )
            )

    for result, color in zip(saved_results, scenario_colors(saved_results)):
        add_scenario_trace(result, color, width=2, dash="dash")

    add_scenario_trace(draft_result, DRAFT_COLOR, width=3, dash="longdash")

    fig.update_layout(
        title=copy.CHART_FORECAST_TITLE,
        yaxis=dict(tickprefix="€", tickformat="~s"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60),
    )
    return fig


def build_driver_chart(saved_results: list, draft_result) -> go.Figure:
    """Stacked bars splitting each scenario's 12-month total into base
    business, from marketing, and from initiatives (section 6, item 4).

    Decomposition (see decisions.md): base business is baseline growth
    compounding from the last actual month, with a flat budget held at the
    last observed level and no initiatives. From marketing is the
    difference between the scenario's actual budget path and that
    flat-budget counterfactual, initiatives excluded. From initiatives is
    the uplift contribution on top. The three always sum to the scenario's
    total revenue (see ScenarioResult / run_scenario in src/scenarios.py,
    and tests/test_scenarios.py for the summation guarantee).

    Aggregated per scenario, not per month: the VP is choosing between
    plans, so this chart answers "why does this one win" -- the composition
    of the difference between scenarios -- rather than explaining the
    model's month-to-month mechanism.
    """
    results = list(saved_results) + [draft_result]
    names = [display_name(r) for r in results]
    base = [float(r.base_business.sum()) for r in results]
    marketing = [float(r.from_marketing.sum()) for r in results]
    initiatives = [float(r.from_initiatives.sum()) for r in results]

    fig = go.Figure()
    for label, values, color in (
        (copy.CHART_DRIVERS_BASE_LABEL, base, BASE_SEGMENT_COLOR),
        (copy.CHART_DRIVERS_MARKETING_LABEL, marketing, MARKETING_SEGMENT_COLOR),
        (copy.CHART_DRIVERS_INITIATIVES_LABEL, initiatives, INITIATIVES_SEGMENT_COLOR),
    ):
        fig.add_trace(
            go.Bar(
                name=label,
                x=values,
                y=names,
                orientation="h",
                marker=dict(color=color),
                text=[format_currency(v) for v in values],
                textposition="auto",
                hovertemplate="%{y}<br>" + label + ": %{text}<extra></extra>",
            )
        )

    fig.update_layout(
        title=copy.CHART_DRIVERS_TITLE,
        barmode="relative",
        xaxis=dict(tickprefix="€", tickformat="~s"),
        yaxis=dict(autorange="reversed"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60),
    )
    return fig
