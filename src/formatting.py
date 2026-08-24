"""Currency, date, and percentage formatting for user-facing display
(CLAUDE.md section 5). Numbers reach the UI through these functions, never
as raw floats or ISO dates.
"""

from __future__ import annotations

import pandas as pd


def format_currency(value: float) -> str:
    """Formats a monetary value as e.g. "€18.2M", never a raw number."""
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000_000:
        return f"{sign}€{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{sign}€{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{sign}€{value / 1_000:.0f}K"
    return f"{sign}€{value:.0f}"


def format_date(value) -> str:
    """Formats a date as e.g. "Nov 2026", never "2026-11"."""
    return pd.Timestamp(value).strftime("%b %Y")


def format_percent(value: float, signed: bool = False) -> str:
    """Formats a fraction as a percentage, e.g. 0.129 -> "12.9%"."""
    pct = value * 100
    if signed:
        return f"{pct:+.1f}%"
    return f"{pct:.1f}%"
