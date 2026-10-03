"""Full pipeline in cassette mode (recorded LLM responses, no API key, no network).

Decisions match the deterministic ground truth (docs/02_DATA_SPEC.md §7); the Intent Reviewer
only adds R013 on JE-008, which is already REJECTED, so no decision moves.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from finagent.config import load_settings
from finagent.domain.models import EntryResult, JeLine, Severity
from finagent.pipeline import RunOutcome, run_pipeline
from finagent.store.run_store import RunStore
from tests.adjustments.test_golden_decisions import EXPECTED as OFF_EXPECTED

EXPECTED: dict[str, tuple[str, list[str]]] = {
    **OFF_EXPECTED,
    "JE-008": ("REJECTED", ["R005", "R011", "R013"]),
}
LLM_EXPLAINED = {"JE-002", "JE-003", "JE-005", "JE-008"}


def _cassette_run(runs: Path) -> RunOutcome:
    with pytest.MonkeyPatch.context() as mp:
        for var in ("GOOGLE_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY"):
            mp.delenv(var, raising=False)
        return run_pipeline(load_settings({"llm": {"mode": "cassette"}}), RunStore(runs))


@pytest.fixture(scope="module")
def runs_dirs(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    return (
        tmp_path_factory.mktemp("cassette_a") / "runs",
        tmp_path_factory.mktemp("cassette_b") / "runs",
    )


@pytest.fixture(scope="module")
def cassette_run(runs_dirs: tuple[Path, Path]) -> RunOutcome:
    """Cassette run with every provider key unset: replay needs no key and no network."""
    return _cassette_run(runs_dirs[0])


def _by_id(run: RunOutcome) -> dict[str, EntryResult]:
    return {r.entry.id: r for r in run.results}


def _amounts_of(lines: list[JeLine]) -> list[tuple[str, Decimal, Decimal]]:
    return [(ln.account, ln.debit, ln.credit) for ln in lines]


def _amounts(r: EntryResult) -> list[list[tuple[str, Decimal, Decimal]]]:
    return [_amounts_of(c.lines) for c in r.fix_candidates]


def test_decisions_and_rule_ids(cassette_run: RunOutcome) -> None:
    got = {
        je: (r.decision.value, [f.rule_id for f in r.findings])
        for je, r in _by_id(cassette_run).items()
    }
    assert got == EXPECTED


def test_decisions_identical_to_off_mode(cassette_run: RunOutcome, off_run: RunOutcome) -> None:
    off = {r.entry.id: r.decision for r in off_run.results}
    assert {r.entry.id: r.decision for r in cassette_run.results} == off
    assert cassette_run.manifest.counts == off_run.manifest.counts
    assert cassette_run.manifest.status == "OK"
    assert cassette_run.manifest.llm_mode == "cassette"


def test_je008_r013_escalates_from_intent_reviewer(cassette_run: RunOutcome) -> None:
    findings = _by_id(cassette_run)["JE-008"].findings
    r013 = [f for f in findings if f.rule_id == "R013"]
    assert len(r013) == 1
    assert r013[0].severity == Severity.ESCALATE
    assert r013[0].produced_by == "llm:intent_reviewer"
    assert all(f.produced_by == "rule" for f in findings if f.rule_id != "R013")
    assert {f.rule_id: f.severity for f in findings if f.rule_id != "R013"} == {
        "R005": Severity.BLOCK,
        "R011": Severity.WARN,
    }


def test_only_je008_has_llm_findings(cassette_run: RunOutcome) -> None:
    for r in cassette_run.results:
        if r.entry.id != "JE-008":
            assert all(f.produced_by == "rule" for f in r.findings), r.entry.id


def test_explanation_sources(cassette_run: RunOutcome) -> None:
    for je, r in _by_id(cassette_run).items():
        if je in LLM_EXPLAINED:
            assert r.explanation_source == "llm", je
            assert r.explanation_model, je
            assert r.explanation, je
        else:
            assert r.decision.value == "ACCEPTED"
            assert r.explanation_source == "none", je
            assert r.explanation is None and r.explanation_model is None, je
            assert r.fix_candidates == [], je
            assert r.needs_human_input is None, je


def test_je002_fix_candidates(cassette_run: RunOutcome) -> None:
    r = _by_id(cassette_run)["JE-002"]
    assert _amounts(r) == [
        [("6300", Decimal("28500.00"), Decimal("0")), ("6310", Decimal("0"), Decimal("28500.00"))],
        [("6300", Decimal("25000.00"), Decimal("0")), ("6310", Decimal("0"), Decimal("25000.00"))],
    ]
    assert all(c.resolves for c in r.fix_candidates)
    assert all(
        not any(f.severity in (Severity.BLOCK, Severity.ESCALATE) for f in c.revalidation)
        for c in r.fix_candidates
    )
    assert r.needs_human_input
    assert r.decision.value == "REJECTED"  # a resolving proposal is never applied


def test_je008_fix_candidate_resolves(cassette_run: RunOutcome) -> None:
    r = _by_id(cassette_run)["JE-008"]
    target = [
        ("2170", Decimal("320000.00"), Decimal("0")),
        ("1110", Decimal("0"), Decimal("320000.00")),
    ]
    matching = [c for c in r.fix_candidates if _amounts_of(c.lines) == target]
    assert len(matching) == 1
    assert matching[0].resolves is True
    assert r.decision.value == "REJECTED"


def test_je005_needs_human_input_without_candidates(cassette_run: RunOutcome) -> None:
    r = _by_id(cassette_run)["JE-005"]
    assert r.fix_candidates == []
    assert r.needs_human_input
    assert r.decision.value == "QUARANTINED"


def test_manifest_metrics(cassette_run: RunOutcome) -> None:
    m = cassette_run.manifest.metrics
    assert m["cassette_hit_rate"] == "1.0000"
    assert m["guardrail_fallback_rate"] == "0.0000"
    assert m["provider_fallbacks"] == 0
    assert isinstance(m["llm_calls"], int) and m["llm_calls"] > 0


def test_two_cassette_runs_byte_identical(
    cassette_run: RunOutcome, runs_dirs: tuple[Path, Path]
) -> None:
    second = _cassette_run(runs_dirs[1])
    assert second.manifest.run_id == cassette_run.manifest.run_id
    a_root, b_root = runs_dirs
    a_ids = [p for p in a_root.iterdir() if p.is_dir()]
    b_ids = [p for p in b_root.iterdir() if p.is_dir()]
    assert len(a_ids) == 1 and len(b_ids) == 1
    assert a_ids[0].name == b_ids[0].name  # same run_id
    a = (a_ids[0] / "decisions.json").read_bytes()
    b = (b_ids[0] / "decisions.json").read_bytes()
    assert a == b
