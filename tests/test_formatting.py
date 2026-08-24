"""Tests for currency, date, and percentage formatting (CLAUDE.md section 5)."""

from src.formatting import format_currency, format_date, format_percent


def test_format_currency_millions():
    assert format_currency(18_200_000) == "€18.2M"


def test_format_currency_billions():
    assert format_currency(1_500_000_000) == "€1.5B"


def test_format_currency_thousands():
    assert format_currency(2_600) == "€3K"


def test_format_currency_negative():
    assert format_currency(-4_400_000) == "-€4.4M"


def test_format_date_month_year():
    assert format_date("2026-11-01") == "Nov 2026"
    assert format_date("2026-11") == "Nov 2026"


def test_format_percent_unsigned():
    assert format_percent(0.129) == "12.9%"


def test_format_percent_signed():
    assert format_percent(0.129, signed=True) == "+12.9%"
    assert format_percent(-0.048, signed=True) == "-4.8%"


def test_format_percent_signed_zero_never_shows_a_minus_sign():
    # Two scenarios with identical inputs can land a hair apart after
    # independently computed floating-point paths; a tiny negative delta
    # must not render as "-0.0%" next to another scenario's clean "+0.0%".
    assert format_percent(0.0, signed=True) == "+0.0%"
    assert format_percent(-1e-12, signed=True) == "+0.0%"
    assert format_percent(-0.00001, signed=True) == "+0.0%"
