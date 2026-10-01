from __future__ import annotations

from decimal import Decimal

import orjson
import pytest

from finagent.domain.money import MoneyParseError, dstr, fmt, fmt_signed, parse_money, q


def test_quantize_half_up() -> None:
    assert q(Decimal("1.005")) == Decimal("1.01")
    assert q(Decimal("-1.005")) == Decimal("-1.01")
    assert q(Decimal("2.004")) == Decimal("2.00")


def test_parse_from_json_float_goes_through_str() -> None:
    assert parse_money(orjson.loads(b"0.1")) == Decimal("0.10")
    assert parse_money(orjson.loads(b"850000.0")) == Decimal("850000.00")
    # Decimal(<float>) would expose the binary expansion; parse_money must not.
    assert str(parse_money(orjson.loads(b"1.1"))) == "1.10"


def test_parse_strings_and_ints() -> None:
    assert parse_money("1,234.5") == Decimal("1234.50")
    assert parse_money("") == Decimal("0.00")
    assert parse_money(7) == Decimal("7.00")


@pytest.mark.parametrize("bad", ["abc", True])
def test_parse_rejects_garbage(bad: str | bool) -> None:
    with pytest.raises(MoneyParseError):
        parse_money(bad)


def test_formatting() -> None:
    assert fmt(Decimal("1234567.8")) == "1,234,567.80"
    assert fmt(Decimal("-4800")) == "-4,800.00"
    assert fmt_signed(Decimal("182460.2")) == "+182,460.20"
    assert fmt_signed(Decimal("-4800")) == "-4,800.00"
    assert fmt_signed(Decimal("0")) == "0.00"
    assert dstr(Decimal("-4800")) == "-4800.00"
