from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r010_duplicate_entry
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry


def test_no_real_entry_fires(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    for e in entries.values():
        assert r010_duplicate_entry.check(e, rule_ctx) == []


def test_copy_of_je001_is_flagged(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    original = entries["JE-001"]
    copy = original.model_copy(update={"id": "JE-099", "description": "Bonus accrual again"})
    ctx = rule_ctx.model_copy(update={"batch": [*rule_ctx.batch, copy]})
    [f] = r010_duplicate_entry.check(copy, ctx)
    assert f.rule_id == "R010" and f.severity == Severity.WARN
    assert f.evidence == {"duplicate_of": ["JE-001"]}
    assert "JE-001" in f.message
    [g] = r010_duplicate_entry.check(original, ctx)
    assert g.evidence == {"duplicate_of": ["JE-099"]}


def test_line_order_does_not_matter(rule_ctx: RuleContext) -> None:
    a = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"), id="T-001")
    b = make_entry(("2120", "0", "100.00"), ("6100", "100.00", "0"), id="T-002")
    ctx = rule_ctx.model_copy(update={"batch": [a, b]})
    [f] = r010_duplicate_entry.check(a, ctx)
    assert f.evidence == {"duplicate_of": ["T-002"]}


def test_different_amount_is_not_duplicate(rule_ctx: RuleContext) -> None:
    a = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"), id="T-001")
    b = make_entry(("6100", "100.01", "0"), ("2120", "0", "100.01"), id="T-002")
    ctx = rule_ctx.model_copy(update={"batch": [a, b]})
    assert r010_duplicate_entry.check(a, ctx) == []


def test_extra_repeated_line_is_not_duplicate(rule_ctx: RuleContext) -> None:
    a = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"), id="T-001")
    b = make_entry(
        ("6100", "100.00", "0"), ("6100", "100.00", "0"), ("2120", "0", "100.00"), id="T-002"
    )
    ctx = rule_ctx.model_copy(update={"batch": [a, b]})
    assert r010_duplicate_entry.check(a, ctx) == []


def test_same_id_is_not_its_own_duplicate(rule_ctx: RuleContext) -> None:
    a = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"), id="T-001")
    ctx = rule_ctx.model_copy(update={"batch": [a]})
    assert r010_duplicate_entry.check(a, ctx) == []
