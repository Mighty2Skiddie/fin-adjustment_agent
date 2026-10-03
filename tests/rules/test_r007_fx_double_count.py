from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r007_fx_double_count
from finagent.config import load_settings
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry

JE003_EVIDENCE = {
    "fx_account": "7310",
    "revalued_account": "1110",
    "currencies": ["EUR", "GBP"],
    "booked": "11200.00",
    "expected_avg_basis": "10730.20",
    "expected_opening_basis": "19809.60",
    "excluded_currencies": ["GBP"],
}


def test_fx_accounts_found_from_coa(rule_ctx: RuleContext) -> None:
    assert r007_fx_double_count.fx_accounts(rule_ctx) == {"7300", "7310"}


def test_je003_double_count_and_mismatch(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    findings = r007_fx_double_count.check(entries["JE-003"], rule_ctx)
    assert [(f.rule_id, f.severity) for f in findings] == [
        ("R007", Severity.ESCALATE),
        ("R007b", Severity.WARN),
    ]
    for f in findings:
        assert f.evidence == JE003_EVIDENCE
    assert "11,200.00" in findings[0].message
    assert "Q1" in (findings[0].suggested_action or "")
    assert "10,730.20" in findings[1].message and "19,809.60" in findings[1].message
    assert findings[1].assumption == "D6"


def test_only_je003_fires_on_real_data(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    for je_id, e in entries.items():
        if je_id != "JE-003":
            assert r007_fx_double_count.check(e, rule_ctx) == []


def test_erp_pretranslated_does_not_fire(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    ctx = rule_ctx.model_copy(
        update={"settings": load_settings({"fx": {"translation_mode": "erp_pretranslated"}})}
    )
    assert r007_fx_double_count.check(entries["JE-003"], ctx) == []


def test_booked_on_average_basis_escalates_without_mismatch(rule_ctx: RuleContext) -> None:
    e = make_entry(("1110", "10730.20", "0"), ("7310", "0", "10730.20"))
    [f] = r007_fx_double_count.check(e, rule_ctx)
    assert f.rule_id == "R007"
    assert f.evidence["booked"] == "10730.20"


def test_booked_on_opening_basis_escalates_without_mismatch(rule_ctx: RuleContext) -> None:
    e = make_entry(("1110", "0", "19809.60"), ("7300", "19809.60", "0"))
    [f] = r007_fx_double_count.check(e, rule_ctx)
    assert f.evidence["fx_account"] == "7300"
    assert f.evidence["booked"] == "19809.60"


def test_usd_only_counter_account_does_not_fire(rule_ctx: RuleContext) -> None:
    e = make_entry(("1250", "500.00", "0"), ("7310", "0", "500.00"))
    assert r007_fx_double_count.check(e, rule_ctx) == []


def test_no_fx_account_does_not_fire(rule_ctx: RuleContext) -> None:
    e = make_entry(("1110", "500.00", "0"), ("6100", "0", "500.00"))
    assert r007_fx_double_count.check(e, rule_ctx) == []
