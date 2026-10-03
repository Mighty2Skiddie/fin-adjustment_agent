from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r003_postable_account
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry


def test_header_6000_blocks(rule_ctx: RuleContext) -> None:
    e = make_entry(("6000", "100.00", "0"), ("2120", "0", "100.00"))
    [f] = r003_postable_account.check(e, rule_ctx)
    assert f.rule_id == "R003" and f.severity == Severity.BLOCK
    assert f.evidence == {"header_accounts": ["6000"], "lines": [1]}
    assert "6000 Operating Expenses" in f.message
    assert f.assumption == "A8"


def test_postable_6100_passes(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"))
    assert r003_postable_account.check(e, rule_ctx) == []


def test_structural_but_postable_parents_pass(rule_ctx: RuleContext) -> None:
    # 8000 and 3300 have children but are not typed Header (A8): not R003's concern.
    e = make_entry(("8000", "100.00", "0"), ("3300", "0", "100.00"))
    assert r003_postable_account.check(e, rule_ctx) == []


def test_missing_account_is_not_r003(rule_ctx: RuleContext) -> None:
    e = make_entry(("6315", "100.00", "0"), ("2120", "0", "100.00"))
    assert r003_postable_account.check(e, rule_ctx) == []


def test_repeated_header_listed_once(rule_ctx: RuleContext) -> None:
    e = make_entry(("6000", "50.00", "0"), ("6000", "50.00", "0"), ("2120", "0", "100.00"))
    [f] = r003_postable_account.check(e, rule_ctx)
    assert f.evidence == {"header_accounts": ["6000"], "lines": [1, 2]}


def test_no_real_entry_fires(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    for e in entries.values():
        assert r003_postable_account.check(e, rule_ctx) == []
