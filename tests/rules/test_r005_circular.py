from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r005_circular
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry


def test_je008_same_account_both_sides(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    [f] = r005_circular.check(entries["JE-008"], rule_ctx)
    assert f.rule_id == "R005" and f.severity == Severity.BLOCK
    assert f.title == "Entry changes nothing"
    assert f.evidence == {"per_account_net": {"2170": "0.00"}, "distinct_accounts": 1}
    assert f.assumption == "A10"
    assert "2170" in f.message and "same account" in f.message


def test_only_je008_fires_on_real_data(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    fired = [je for je, e in entries.items() if r005_circular.check(e, rule_ctx)]
    assert fired == ["JE-008"]


def test_multi_line_loop_blocks(rule_ctx: RuleContext) -> None:
    e = make_entry(
        ("6100", "50.00", "0"),
        ("2120", "0", "50.00"),
        ("2120", "50.00", "0"),
        ("1110", "0", "50.00"),
        ("1110", "50.00", "0"),
        ("6100", "0", "50.00"),
    )
    [f] = r005_circular.check(e, rule_ctx)
    assert f.evidence == {
        "per_account_net": {"6100": "0.00", "2120": "0.00", "1110": "0.00"},
        "distinct_accounts": 3,
    }


def test_partial_loop_passes(rule_ctx: RuleContext) -> None:
    e = make_entry(
        ("6100", "50.00", "0"),
        ("2120", "0", "50.00"),
        ("2120", "50.00", "0"),
        ("1110", "0", "50.00"),
    )
    assert r005_circular.check(e, rule_ctx) == []


def test_real_entries_that_move_balances_pass(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    for je in ("JE-001", "JE-010"):
        assert r005_circular.check(entries[je], rule_ctx) == []


def test_all_zero_lines_left_to_r006(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "0", "0"), ("2120", "0", "0"))
    assert r005_circular.check(e, rule_ctx) == []
