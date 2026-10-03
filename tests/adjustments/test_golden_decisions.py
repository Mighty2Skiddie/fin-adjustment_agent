"""Ground truth: docs/02_DATA_SPEC.md §7 (rule_ids as corrected by decision D4)."""

from __future__ import annotations

from collections import Counter

from finagent.domain.models import EntryResult, Severity
from finagent.pipeline import RunOutcome

EXPECTED: dict[str, tuple[str, list[str]]] = {
    "JE-001": ("ACCEPTED", ["R009"]),
    "JE-002": ("REJECTED", ["R001"]),
    "JE-003": ("QUARANTINED", ["R007", "R007b", "R009"]),
    "JE-004": ("ACCEPTED", ["R009", "R009"]),
    "JE-005": ("QUARANTINED", ["R002", "R002b"]),
    "JE-006": ("ACCEPTED", ["R009"]),
    "JE-007": ("ACCEPTED", ["R009"]),
    "JE-008": ("REJECTED", ["R005", "R011"]),
    "JE-009": ("ACCEPTED", []),
    "JE-010": ("ACCEPTED", ["R009"]),
}


def _by_id(run: RunOutcome) -> dict[str, EntryResult]:
    return {r.entry.id: r for r in run.results}


def test_decisions_and_rule_ids(off_run: RunOutcome) -> None:
    got = {
        je: (r.decision.value, [f.rule_id for f in r.findings]) for je, r in _by_id(off_run).items()
    }
    assert got == EXPECTED


def test_counts(off_run: RunOutcome) -> None:
    assert Counter(r.decision.value for r in off_run.results) == {
        "ACCEPTED": 6,
        "REJECTED": 2,
        "QUARANTINED": 2,
    }
    assert off_run.manifest.counts == {"accepted": 6, "quarantined": 2, "rejected": 2}
    assert off_run.manifest.status == "OK"


def test_severities(off_run: RunOutcome) -> None:
    by = _by_id(off_run)
    sev = {f.rule_id: f.severity for f in by["JE-003"].findings}
    assert sev == {"R007": Severity.ESCALATE, "R007b": Severity.WARN, "R009": Severity.INFO}
    assert {f.rule_id: f.severity for f in by["JE-008"].findings} == {
        "R005": Severity.BLOCK,
        "R011": Severity.WARN,
    }
    assert [f.severity for f in by["JE-001"].findings] == [Severity.WARN]  # 2120 at 73.91%
    assert all(f.severity == Severity.INFO for f in by["JE-004"].findings)


def test_spec_evidence_values(off_run: RunOutcome) -> None:
    by = _by_id(off_run)
    r001 = by["JE-002"].findings[0].evidence
    assert (r001["total_debit"], r001["total_credit"], r001["difference"]) == (
        "28500.00",
        "25000.00",
        "3500.00",
    )
    r007b = next(f for f in by["JE-003"].findings if f.rule_id == "R007b").evidence
    assert r007b["booked"] == "11200.00"
    assert r007b["expected_avg_basis"] == "10730.20"
    assert r007b["expected_opening_basis"] == "19809.60"
    r002b = next(f for f in by["JE-005"].findings if f.rule_id == "R002b").evidence
    top = r002b["candidates"][0]
    assert top["code"] == "6310" and top["would_create_noop"] is True
    je4 = {f.evidence["account"]: f.evidence["pct"] for f in by["JE-004"].findings}
    assert je4["1121"].startswith("0.243")
    je6 = by["JE-006"].findings[0].evidence
    assert (je6["account"], je6["base_balance"]) == ("6500", "850000.00")


def test_explanations_only_for_non_accepted(off_run: RunOutcome) -> None:
    for r in off_run.results:
        if r.decision.value == "ACCEPTED":
            assert r.explanation_source == "none" and r.explanation is None
        else:
            assert r.explanation_source == "template" and r.explanation


def test_every_finding_has_evidence(off_run: RunOutcome) -> None:
    for r in off_run.results:
        for f in r.findings:
            assert f.evidence and f.message and f.title
