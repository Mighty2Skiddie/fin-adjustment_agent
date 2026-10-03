from __future__ import annotations

from decimal import Decimal

from finagent.domain.models import AccountType
from finagent.ingest import loaders


def test_coa() -> None:
    coa = loaders.load_coa()
    # 72 accounts: the file has 73 lines including the header.
    assert len(coa) == 72
    by = {a.code: a for a in coa}
    assert by["1000"].parent_code is None and by["1000"].account_type == AccountType.HEADER
    assert by["7000"].normal_balance is None
    assert by["1210"].name == "Property, Plant & Equipment - Cost"


def test_tb_rows_and_indices() -> None:
    tb = loaders.load_tb()
    assert len(tb) == 62
    assert len({r.account_code for r in tb}) == 59
    assert tb[0].row_index == 0 and tb[0].source_file == "trial_balance.csv"
    gbp = tb[2]
    assert (gbp.account_code, gbp.currency, gbp.debit) == ("1110", "GBP", Decimal("412300.00"))
    assert [r.debit for r in tb if r.account_code == "6310"] == [
        Decimal("245000.00"),
        Decimal("38500.00"),
    ]


def test_prior_tb() -> None:
    prior = loaders.load_prior_tb()
    assert len(prior) == 33
    assert prior[-1].account_code == "6905"


def test_fx() -> None:
    rates = loaders.load_fx()
    assert len(rates) == 7
    ids = {r.id: r.rate for r in rates}
    assert ids["EUR/period_end"] == Decimal("1.095")
    assert "GBP/period_end" not in ids


def test_adjustments_amounts_are_exact_decimals() -> None:
    entries = loaders.load_adjustments()
    assert len(entries) == 10
    assert sum(len(e.lines) for e in entries) == 20
    je2 = entries[1]
    assert je2.id == "JE-002"
    assert je2.lines[0].debit == Decimal("28500.00")
    assert je2.lines[1].credit == Decimal("25000.00")
    assert entries[7].lines[0].account == entries[7].lines[1].account == "2170"


def test_raw_lines_for_lineage() -> None:
    lines = loaders.read_raw_lines(loaders.INPUTS / loaders.TB_FILE)
    assert lines[2] == "1110,Cash and Cash Equivalents,GBP,412300.00,0.00"
