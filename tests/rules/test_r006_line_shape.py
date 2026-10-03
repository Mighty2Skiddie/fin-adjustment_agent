from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r006_line_shape
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry


def test_real_entries_are_well_formed(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    for je in entries.values():
        assert r006_line_shape.check(je, rule_ctx) == []


def test_single_line_blocks(rule_ctx: RuleContext) -> None:
    [f] = r006_line_shape.check(make_entry(("6100", "100.00", "0")), rule_ctx)
    assert f.rule_id == "R006" and f.severity == Severity.BLOCK
    assert f.title == "Malformed entry lines"
    assert f.evidence == {"offending_line_indexes": [1], "reason": "fewer than two lines"}


def test_no_lines_blocks(rule_ctx: RuleContext) -> None:
    [f] = r006_line_shape.check(make_entry(), rule_ctx)
    assert f.evidence == {"offending_line_indexes": [], "reason": "fewer than two lines"}


def test_both_sides_on_one_line(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "100.00", "0"), ("2120", "5.00", "105.00"))
    [f] = r006_line_shape.check(e, rule_ctx)
    assert f.evidence == {
        "offending_line_indexes": [2],
        "reason": "line has both a debit and a credit",
    }


def test_negative_amount(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "-100.00", "0"), ("2120", "100.00", "0"))
    [f] = r006_line_shape.check(e, rule_ctx)
    assert f.evidence == {"offending_line_indexes": [1], "reason": "negative amount"}


def test_empty_line(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"), ("1110", "0", "0"))
    [f] = r006_line_shape.check(e, rule_ctx)
    assert f.evidence == {"offending_line_indexes": [3], "reason": "line has no amount"}
    assert "3" in f.message


def test_one_finding_per_reason(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "0", "0"), ("2120", "0", "0"), ("1110", "-1.00", "0"))
    findings = r006_line_shape.check(e, rule_ctx)
    assert [f.evidence for f in findings] == [
        {"offending_line_indexes": [3], "reason": "negative amount"},
        {"offending_line_indexes": [1, 2], "reason": "line has no amount"},
    ]


def test_well_formed_entry_passes(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"))
    assert r006_line_shape.check(e, rule_ctx) == []
