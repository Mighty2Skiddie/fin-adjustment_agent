from __future__ import annotations

from decimal import Decimal

from finagent.adjustments.lineage import LineageSources, explain_line
from finagent.domain.money import ZERO
from finagent.ingest import loaders
from finagent.pipeline import RunOutcome


def test_components_sum_to_every_line(off_run: RunOutcome) -> None:
    assert off_run.posted is not None
    for ln in off_run.posted:
        assert ln.lineage, ln.account_code
        total = sum((r.amount for r in ln.lineage if r.amount is not None), ZERO)
        assert total == ln.net, ln.account_code


def test_accrued_expenses_drilldown(off_run: RunOutcome) -> None:
    """The auditor path in docs/ARCHITECTURE.md §7: 2120 = TB row + JE-001#2 + JE-009#2."""
    assert off_run.posted is not None
    line = next(ln for ln in off_run.posted if ln.account_code == "2120")
    tb = loaders.load_tb()
    raw = loaders.read_raw_lines(loaders.INPUTS / loaders.TB_FILE)
    sources = LineageSources(
        tb_rows={f"trial_balance.csv#{r.row_index}": r for r in tb},
        raw_lines={f"trial_balance.csv#{i}": text for i, text in enumerate(raw)},
        rates={r.id: r for r in loaders.load_fx()},
        entries={e.id: e for e in loaders.load_adjustments()},
    )
    out = explain_line(line, sources)
    assert out["reconciles"] is True
    refs = [(c["kind"], c["ref"], c["amount"]) for c in out["components"]]
    assert refs == [
        ("TB_ROW", "trial_balance.csv#17", "-1150000.00"),
        ("FX", "USD/period_end", None),
        ("JE", "JE-001#2", "-850000.00"),
        ("JE", "JE-009#2", "-75000.00"),
    ]
    assert out["components"][0]["source"]["raw"].startswith("2120,Accrued Expenses,USD")
    assert out["components"][2]["source"]["line"]["memo"] == "Accrual offset"
    assert line.credit == Decimal("2075000.00")
