"""Plotly chart builders (CLAUDE.md section 6, items 2-4). Pure functions,
no Streamlit dependency, so they can be exercised directly in tests -- the
same code path app.py calls, callable without a script-run context.
"""

from __future__ import annotations

import plotly.graph_objects as go

from src import copy
from src.formatting import format_currency

SCENARIO_COLORS = ["#3b82f6", "#f97316", "#10b981", "#a855f7", "#ef4444", "#14b8a6"]
DRAFT_COLOR = "#111827"  # reserved for the live draft; never reused for a saved scenario


def display_name(result) -> str:
    """Scenario name, flagged with the guardrail marker if its budget goes
    outside the tested range. Use this wherever a scenario name is shown."""
    if result.guardrail_breaches:
        return f"{result.scenario.name} {copy.GUARDRAIL_SCENARIO_MARKER}"
    return result.scenario.name


def _rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def build_forecast_chart(history, forecast_months, saved_results: list, draft_result) -> go.Figure:
    """History solid, forecast dashed, shaded likely range, one colour per
    scenario. The live draft gets a reserved colour, a thicker line, and a
    distinct dash pattern so it never blends in with a saved scenario -- it
    is the one line on this chart that moves as the sidebar is edited.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=history["year_month"],
            y=history["total_revenue"],
            mode="lines",
            name=copy.CHART_FORECAST_HISTORY_LABEL,
            line=dict(color="#6b7280", width=2),
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

        fig.add_trace(
            go.Scatter(
                x=x + x[::-1],
                y=upper + lower[::-1],
                fill="toself",
                fillcolor=_rgba(color, 0.15),
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
                name=f"{name} {copy.CHART_FORECAST_LIKELY_RANGE_LABEL}",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines+markers",
                name=name,
                line=dict(color=color, width=width, dash=dash),
                marker=dict(size=4),
                text=[format_currency(v) for v in y],
                hovertemplate="%{x|%b %Y}<br>%{text}<extra>" + name + "</extra>",
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
                    marker=dict(size=11, symbol="star", color=color, line=dict(width=1, color="white")),
                    name=f"{name} initiatives",
                    text=texts,
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                )
            )

    for i, result in enumerate(saved_results):
        color = SCENARIO_COLORS[i % len(SCENARIO_COLORS)]
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
