from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r011_intercompany
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry


def test_je008_flagged(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    [f] = r011_intercompany.check(entries["JE-008"], rule_ctx)
    assert f.rule_id == "R011" and f.severity == Severity.WARN
    assert f.evidence == {"ic_accounts": ["2170"]}
    assert f.assumption == "A14"
    assert "2170" in f.message


def test_only_je008_fires(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    for je, e in entries.items():
        if je != "JE-008":
            assert r011_intercompany.check(e, rule_ctx) == [], je


def test_counterparty_in_source_passes(rule_ctx: RuleContext) -> None:
    e = make_entry(("2170", "100.00", "0"), ("6100", "0", "100.00"), source="entity:UK-SUB")
    assert r011_intercompany.check(e, rule_ctx) == []


def test_counterparty_tag_is_case_insensitive(rule_ctx: RuleContext) -> None:
    e = make_entry(("2170", "100.00", "0"), ("6100", "0", "100.00"), memo="Entity:UK-SUB")
    assert r011_intercompany.check(e, rule_ctx) == []


def test_synthetic_without_counterparty_fires(rule_ctx: RuleContext) -> None:
    e = make_entry(("2170", "100.00", "0"), ("6100", "0", "100.00"), description="IC settle")
    [f] = r011_intercompany.check(e, rule_ctx)
    assert f.evidence == {"ic_accounts": ["2170"]}


def test_non_intercompany_accounts_pass(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"), description="Intercompany")
    assert r011_intercompany.check(e, rule_ctx) == []
