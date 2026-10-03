from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r009_magnitude
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry

EXPECTED: dict[str, list[tuple[str, str, Severity]]] = {
    "JE-001": [("2120", "0.7391", Severity.WARN)],
    "JE-002": [],
    "JE-003": [("7310", "0.2667", Severity.INFO)],
    "JE-004": [("6600", "0.4737", Severity.INFO), ("1121", "0.2432", Severity.INFO)],
    "JE-005": [],
    "JE-006": [("6500", "0.2529", Severity.INFO)],
    "JE-007": [("8200", "0.3167", Severity.INFO)],
    "JE-008": [],
    "JE-009": [],
    "JE-010": [("2140", "0.2500", Severity.INFO)],
}


def test_real_entries_match_ground_truth(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    assert set(entries) == set(EXPECTED)
    for je, expected in EXPECTED.items():
        got = [
            (f.evidence["account"], f.evidence["pct"], f.severity)
            for f in r009_magnitude.check(entries[je], rule_ctx)
        ]
        assert got == expected, je


def test_je001_warn_evidence(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    [f] = r009_magnitude.check(entries["JE-001"], rule_ctx)
    assert f.rule_id == "R009" and f.severity == Severity.WARN
    assert f.evidence == {
        "account": "2120",
        "amount": "850000.00",
        "base_balance": "1150000.00",
        "pct": "0.7391",
        "threshold": "0.50",
    }
    assert f.assumption == "A13"
    assert "850,000.00" in f.message and "1,150,000.00" in f.message


def test_je004_info_evidence(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    findings = r009_magnitude.check(entries["JE-004"], rule_ctx)
    assert findings[1].evidence == {
        "account": "1121",
        "amount": "45000.00",
        "base_balance": "185000.00",
        "pct": "0.2432",
        "threshold": "0.20",
    }


def test_offsetting_lines_on_one_account_do_not_fire(rule_ctx: RuleContext) -> None:
    e = make_entry(("2170", "320000.00", "0"), ("2170", "0", "320000.00"))
    assert r009_magnitude.check(e, rule_ctx) == []


def test_small_movement_passes(rule_ctx: RuleContext) -> None:
    e = make_entry(("6500", "100.00", "0"), ("2120", "0", "100.00"))
    assert r009_magnitude.check(e, rule_ctx) == []


def test_exact_info_threshold_fires_info(rule_ctx: RuleContext) -> None:
    # 2140 base balance is 800,000.00; 160,000.00 is exactly 20%.
    e = make_entry(("2140", "160000.00", "0"), ("6500", "0", "160000.00"))
    [f] = [f for f in r009_magnitude.check(e, rule_ctx) if f.evidence["account"] == "2140"]
    assert f.severity == Severity.INFO
    assert f.evidence["pct"] == "0.2000" and f.evidence["threshold"] == "0.20"


def test_exact_warn_threshold_fires_warn(rule_ctx: RuleContext) -> None:
    e = make_entry(("2140", "400000.00", "0"), ("6500", "0", "400000.00"))
    [f] = [f for f in r009_magnitude.check(e, rule_ctx) if f.evidence["account"] == "2140"]
    assert f.severity == Severity.WARN
    assert f.evidence["pct"] == "0.5000" and f.evidence["threshold"] == "0.50"


def test_just_below_info_threshold_passes(rule_ctx: RuleContext) -> None:
    e = make_entry(("2140", "159999.99", "0"), ("6100", "0", "159999.99"))
    assert all(f.evidence["account"] != "2140" for f in r009_magnitude.check(e, rule_ctx))


def test_account_not_in_ledger_is_skipped(rule_ctx: RuleContext) -> None:
    assert "6315" not in rule_ctx.base_ledger
    e = make_entry(("6315", "999999.00", "0"), ("2120", "0", "1.00"))
    assert all(f.evidence["account"] != "6315" for f in r009_magnitude.check(e, rule_ctx))


def test_never_blocks_or_escalates(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    for e in entries.values():
        for f in r009_magnitude.check(e, rule_ctx):
            assert f.severity in (Severity.INFO, Severity.WARN)
