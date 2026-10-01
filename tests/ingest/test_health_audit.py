"""Integration: every ID and headline value from docs/02_DATA_SPEC.md §6, end to end."""

from __future__ import annotations

from pathlib import Path

import orjson
import pytest

from finagent.config import Settings
from finagent.domain.models import HealthFinding
from finagent.ingest.health_audit import render_defect_log, run_checks, write_audit
from finagent.ingest.health_checks.base import AuditContext

EXPECTED_SEVERITY = {
    "H-TB-01": "CRITICAL",
    "H-TB-02": "HIGH",
    "H-TB-03": "HIGH",
    "H-TB-04": "MEDIUM",
    "H-TB-05": "INFO",
    "H-TB-06": "MEDIUM",
    "H-COA-01": "HIGH",
    "H-COA-02": "MEDIUM",
    "H-COA-03": "MEDIUM",
    "H-COA-04": "LOW",
    "H-COA-05": "MEDIUM",
    "H-COA-06": "INFO",
    "H-PP-01": "HIGH",
    "H-PP-02": "HIGH",
    "H-PP-03": "MEDIUM",
    "H-PP-04": "INFO",
    "H-FX-01": "CRITICAL",
    "H-FX-02": "INFO",
    "H-ADJ-01": "INFO",
    "H-ADJ-02": "MEDIUM",
}


@pytest.fixture(scope="module")
def findings(audit_ctx: AuditContext) -> dict[str, HealthFinding]:
    out = run_checks(audit_ctx)
    by = {f.id: f for f in out}
    assert len(by) == len(out), "each check reports one finding on this data"
    return by


def test_every_spec_id_with_severity(findings: dict[str, HealthFinding]) -> None:
    assert {k: str(v.severity) for k, v in findings.items()} == EXPECTED_SEVERITY


def test_every_finding_has_evidence_and_file(findings: dict[str, HealthFinding]) -> None:
    for f in findings.values():
        assert f.evidence and f.file and f.title and f.message


def test_headline_numbers(findings: dict[str, HealthFinding]) -> None:
    tb01 = findings["H-TB-01"].evidence
    assert tb01["raw"]["delta"] == "-4800.00"
    assert tb01["usd_only"]["delta"] == "-1242500.00"
    assert tb01["pe_gbp_avg"] == {
        "debit": "71259460.20",
        "credit": "71077000.00",
        "delta": "182460.20",
    }
    assert tb01["pe_gbp_open"]["delta"] == "177100.30"
    fx = findings["H-FX-01"].evidence["missing"][0]
    assert (fx["fallback_average"], fx["fallback_opening"]) == ("521147.20", "515787.30")
    assert findings["H-PP-01"].evidence["usd_only"]["delta"] == "1737000.00"
    assert findings["H-PP-01"].evidence["opening"]["delta"] == "2980009.80"
    assert findings["H-PP-02"].evidence["orphans"][0]["candidates"][0]["code"] == "6900"
    assert findings["H-ADJ-01"].evidence["difference"] == "3500.00"
    assert findings["H-TB-02"].evidence["duplicates"][0]["summed"] == "283500.00"


def test_sorted_by_file_then_severity(audit_ctx: AuditContext) -> None:
    ids = [f.id for f in run_checks(audit_ctx)]
    assert ids[0] == "H-TB-01"
    assert ids.index("H-TB-05") > ids.index("H-TB-06")  # INFO after MEDIUM within a file
    assert ids.index("H-COA-01") > ids.index("H-TB-05")


def test_writes_json_and_defect_log(
    audit_ctx: AuditContext, settings: Settings, tmp_path: Path
) -> None:
    out = run_checks(audit_ctx)
    json_path, md_path = write_audit(out, settings, tmp_path)
    assert len(orjson.loads(json_path.read_bytes())) == 20
    md = md_path.read_text(encoding="utf-8")
    assert "Listed in the brief: 10 · found by this audit: 20" in md
    for fid in EXPECTED_SEVERITY:
        assert f"| {fid} |" in md
    assert md == render_defect_log(out, settings)
