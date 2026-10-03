from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r001_balance
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry


def test_je002_out_of_balance(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    [f] = r001_balance.check(entries["JE-002"], rule_ctx)
    assert f.rule_id == "R001" and f.severity == Severity.BLOCK
    assert f.evidence == {
        "total_debit": "28500.00",
        "total_credit": "25000.00",
        "difference": "3500.00",
    }
    assert "3,500.00" in f.message


def test_balanced_entries_pass(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    for je in ("JE-001", "JE-003", "JE-005", "JE-008", "JE-010"):
        assert r001_balance.check(entries[je], rule_ctx) == []


def test_one_cent_imbalance_blocks(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "100.01", "0"), ("2120", "0", "100.00"))
    [f] = r001_balance.check(e, rule_ctx)
    assert f.evidence["difference"] == "0.01"
