from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r012_suspense
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry


def test_suspense_9999_escalates(rule_ctx: RuleContext) -> None:
    assert rule_ctx.base_ledger["9999"].mapped is False
    e = make_entry(("6100", "100.00", "0"), ("9999", "0", "100.00"))
    [f] = r012_suspense.check(e, rule_ctx)
    assert f.rule_id == "R012" and f.severity == Severity.ESCALATE
    assert f.evidence == {"accounts": ["9999"], "lines": [2]}
    assert "9999" in f.message


def test_repeated_unmapped_account_listed_once(rule_ctx: RuleContext) -> None:
    e = make_entry(("9999", "100.00", "0"), ("9999", "0", "40.00"), ("2120", "0", "60.00"))
    [f] = r012_suspense.check(e, rule_ctx)
    assert f.evidence == {"accounts": ["9999"], "lines": [1, 2]}


def test_mapped_accounts_pass(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"))
    assert r012_suspense.check(e, rule_ctx) == []


def test_account_absent_from_ledger_is_r002_not_r012(rule_ctx: RuleContext) -> None:
    assert "6315" not in rule_ctx.base_ledger
    e = make_entry(("6315", "100.00", "0"), ("2120", "0", "100.00"))
    assert r012_suspense.check(e, rule_ctx) == []


def test_no_real_entry_fires(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    for e in entries.values():
        assert r012_suspense.check(e, rule_ctx) == []
