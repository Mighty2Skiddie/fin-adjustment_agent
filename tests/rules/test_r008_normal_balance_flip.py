from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r008_normal_balance_flip
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry


def test_no_real_entry_flips(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    for e in entries.values():
        assert r008_normal_balance_flip.check(e, rule_ctx) == []


def test_debit_account_credited_past_zero(rule_ctx: RuleContext) -> None:
    e = make_entry(("1250", "0", "400000.00"), ("6100", "400000.00", "0"))
    [f] = r008_normal_balance_flip.check(e, rule_ctx)
    assert f.rule_id == "R008" and f.severity == Severity.WARN
    assert f.evidence == {
        "account": "1250",
        "before": "320000.00",
        "after": "-80000.00",
        "normal_balance": "Debit",
    }
    assert "-80,000.00" in f.message


def test_partial_reduction_does_not_flip(rule_ctx: RuleContext) -> None:
    e = make_entry(("1250", "0", "320000.00"), ("6100", "320000.00", "0"))
    assert r008_normal_balance_flip.check(e, rule_ctx) == []


def test_credit_account_debited_past_zero(rule_ctx: RuleContext) -> None:
    before = rule_ctx.base_net("2120")
    assert before < 0
    amount = str(-before + 100)
    e = make_entry(("2120", amount, "0"), ("1110", "0", amount))
    [f] = r008_normal_balance_flip.check(e, rule_ctx)
    assert f.evidence["account"] == "2120"
    assert f.evidence["after"] == "100.00"
    assert f.evidence["normal_balance"] == "Credit"


def test_gain_loss_accounts_skipped(rule_ctx: RuleContext) -> None:
    e = make_entry(
        ("7310", "0", "99999999.00"), ("7400", "0", "1.00"), ("1110", "100000000.00", "0")
    )
    assert r008_normal_balance_flip.check(e, rule_ctx) == []
