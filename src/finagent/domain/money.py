"""Money helpers. Every monetary value in the system passes through `parse_money` and `q`.

Amounts arrive as CSV strings or JSON numbers. JSON numbers are already binary floats by the
time the JSON parser hands them over, so they are converted through `str()` (shortest repr,
e.g. `850000.0` -> `"850000.0"`) and never through `Decimal(<float>)`, which would expose the
binary expansion.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class MoneyParseError(ValueError):
    """Raised when a value cannot be read as an amount."""


def q(x: Decimal) -> Decimal:
    """Quantize to cents, half-up (the convention finance users expect)."""
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def parse_decimal(value: str | int | float | Decimal) -> Decimal:
    """Exact decimal from a string/int, or from a float via its shortest string form."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise MoneyParseError(f"not an amount: {value!r}")
    text = str(value).strip().replace(",", "")
    if text == "":
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise MoneyParseError(f"not an amount: {value!r}") from exc


def parse_money(value: str | int | float | Decimal) -> Decimal:
    return q(parse_decimal(value))


def fmt(x: Decimal) -> str:
    """`1234567.8` -> `1,234,567.80`; negatives keep a leading minus."""
    return f"{q(x):,.2f}"


def fmt_signed(x: Decimal) -> str:
    """Always show the sign: `+182,460.20` / `-4,800.00`."""
    v = q(x)
    return f"+{v:,.2f}" if v > 0 else f"{v:,.2f}"


def dstr(x: Decimal) -> str:
    """Canonical evidence string for an amount: `-4800.00` (no separators)."""
    return str(q(x))
