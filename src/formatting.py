"""Currency, date, and percentage formatting for user-facing display
(CLAUDE.md section 5). Numbers reach the UI through these functions, never
as raw floats or ISO dates.
"""

from __future__ import annotations

import pandas as pd


def format_currency(value: float) -> str:
    """Formats a monetary value as e.g. "€18.2M", never a raw number.

    Below €1,000 (including exactly zero -- the draft's default state)
    still renders in the millions convention used everywhere else in this
    app ("€0.0M"), rather than a bare "€0" that breaks the pattern next to
    every other value in the same table column.
    """
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000_000:
        return f"{sign}€{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{sign}€{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{sign}€{value / 1_000:.0f}K"
    return f"{sign}€{value / 1_000_000:.1f}M"


def format_currency_range(low: float, high: float) -> str:
    """Formats a monthly currency range, e.g. (3_500_000, 3_500_000) ->
    "€3.5M" when flat, or (3_500_000, 4_200_000) -> "€3.5M - €4.2M" when it
    varies month to month."""
    if low == high:
        return format_currency(low)
    return f"{format_currency(low)} - {format_currency(high)}"


def format_date(value) -> str:
    """Formats a date as e.g. "Nov 2026", never "2026-11"."""
    return pd.Timestamp(value).strftime("%b %Y")


def format_percent(value: float, signed: bool = False) -> str:
    """Formats a fraction as a percentage, e.g. 0.129 -> "12.9%".

    Two scenarios with the same inputs can differ by a fraction of a cent
    after passing through independently computed paths -- without this,
    that shows up as "+0.0%" for one and "-0.0%" for the other, which reads
    as a real difference. Rounding to zero always displays as "+0.0%".
    """
    pct = value * 100
    if signed:
        formatted = f"{pct:+.1f}%"
        return "+0.0%" if formatted == "-0.0%" else formatted
    return f"{pct:.1f}%"
