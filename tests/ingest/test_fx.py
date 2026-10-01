from __future__ import annotations

from decimal import Decimal

import pytest

from finagent.domain.models import TbRow
from finagent.ingest.fx import MissingRateError, RateBook, translate
from finagent.ingest.loaders import load_fx, load_tb


@pytest.fixture(scope="module")
def gbp_row() -> TbRow:
    return load_tb()[2]


def test_exact_rate() -> None:
    r = RateBook(load_fx(), "fallback_average").rate_for("EUR", "period_end")
    assert r.id == "EUR/period_end" and not r.is_fallback and r.rate == Decimal("1.095")


def test_functional_currency_has_implicit_unit_rate() -> None:
    assert RateBook(load_fx(), "block").rate_for("USD", "opening").rate == Decimal("1")


def test_fallback_average(gbp_row: TbRow) -> None:
    r = RateBook(load_fx(), "fallback_average").rate_for("GBP", "period_end")
    assert r.is_fallback and r.id == "GBP/period_average"
    assert r.requested_rate_type == "period_end"
    assert translate(gbp_row, r) == (Decimal("521147.20"), Decimal("0.00"))


def test_fallback_opening(gbp_row: TbRow) -> None:
    r = RateBook(load_fx(), "fallback_opening").rate_for("GBP", "period_end")
    assert r.is_fallback and r.id == "GBP/opening"
    assert translate(gbp_row, r)[0] == Decimal("515787.30")


def test_block_raises() -> None:
    with pytest.raises(MissingRateError) as exc:
        RateBook(load_fx(), "block").rate_for("GBP", "period_end")
    assert exc.value.currency == "GBP"


def test_fallback_missing_too_raises() -> None:
    with pytest.raises(MissingRateError):
        RateBook(load_fx(), "fallback_average").rate_for("JPY", "period_end")


def test_eur_translation() -> None:
    r = RateBook(load_fx(), "fallback_average").rate_for("EUR", "period_end")
    assert translate(load_tb()[1], r)[0] == Decimal("903813.00")
