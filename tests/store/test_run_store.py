from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from finagent.adjustments.context import RuleContext
from finagent.config import Settings, load_settings
from finagent.domain.models import (
    Decision,
    EntryResult,
    HumanAction,
    HumanDecision,
    JournalEntry,
    LineageKind,
)
from finagent.graph.adjustments_graph import graph_processor
from finagent.observability.tracer import Tracer
from finagent.pipeline import run_pipeline
from finagent.store.run_store import RunStore


def _force_accept_je002(
    entries: list[JournalEntry], ctx: RuleContext, run: str, tracer: Tracer
) -> list[EntryResult]:
    """Simulate a defect that lets an unbalanced entry through as ACCEPTED."""
    results = graph_processor(load_settings({"llm": {"mode": "off"}}))(entries, ctx, run, tracer)
    return [
        r.model_copy(update={"decision": Decision.ACCEPTED}) if r.entry.id == "JE-002" else r
        for r in results
    ]


def test_manifest_fields(settings: Settings, tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    out = run_pipeline(settings, store)
    m = store.manifest(out.manifest.run_id)
    assert len(m.run_id) == 12 and m.status == "OK"
    assert set(m.input_hashes) == {
        "chart_of_accounts.csv",
        "trial_balance.csv",
        "prior_period_tb.csv",
        "fx_rates.csv",
        "manual_adjustments.json",
    }
    assert all(len(h) == 64 for h in m.input_hashes.values())
    assert len(m.config_hash) == 64 and m.code_version
    assert m.llm_mode == "off" and m.fx_policy == "fallback_average" and m.period == "2024-Q4"
    assert m.counts == {"accepted": 6, "quarantined": 2, "rejected": 2}
    assert m.metrics["auto_accept_rate"] == "0.6000"
    assert store.latest() == m.run_id
    assert [r.run_id for r in store.list_runs()] == [m.run_id]


def test_run_files_written(settings: Settings, tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    rid = run_pipeline(settings, store).manifest.run_id
    names = {p.name for p in store.run_dir(rid).iterdir()}
    assert {
        "manifest.json",
        "health.json",
        "base_ledger.json",
        "decisions.json",
        "human_decisions.json",
        "posted_tb.csv",
        "posted_tb.json",
        "audit_log.jsonl",
    } <= names
    assert (tmp_path.parent / "traces" / f"{rid}.jsonl").is_file()
    assert len(store.results(rid)) == 10 and len(store.health(rid)) == 20
    assert store.human_decisions(rid) == []


def test_audit_log_events(settings: Settings, tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    rid = run_pipeline(settings, store).manifest.run_id
    events = store.audit_log(rid)
    kinds = [e["event"] for e in events]
    assert kinds[0] == "run.created" and kinds[-1] == "post.completed"
    assert kinds.count("decision.system") == 10
    je2 = next(e for e in events if e.get("entry_id") == "JE-002")
    assert je2["after"] == "REJECTED" and je2["rule_ids"] == ["R001"]


def test_failed_invariant_writes_failed_dir_not_posted_tb(
    settings: Settings, tmp_path: Path
) -> None:
    store = RunStore(tmp_path)
    out = run_pipeline(settings, store, processor=_force_accept_je002)
    m = out.manifest
    assert m.status == "FAILED_INVARIANT"
    assert m.invariants["imbalance_unchanged"] is False
    d = store.run_dir(m.run_id)
    assert (d / "failed" / "decisions.json").is_file()
    assert not (d / "posted_tb.csv").exists() and not (d / "posted_tb.json").exists()
    assert "post.completed" not in [e["event"] for e in store.audit_log(m.run_id)]


def test_failed_run_then_good_run_cleans_failed_dir(settings: Settings, tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    bad = run_pipeline(settings, store, processor=_force_accept_je002)
    good = run_pipeline(settings, store)
    assert bad.manifest.run_id == good.manifest.run_id  # same inputs/config/code
    d = store.run_dir(good.manifest.run_id)
    assert good.manifest.status == "OK"
    assert not (d / "failed").exists() and (d / "posted_tb.csv").exists()


def test_human_decisions_survive_rerun_and_overlay_posting(
    settings: Settings, tmp_path: Path
) -> None:
    store = RunStore(tmp_path)
    rid = run_pipeline(settings, store).manifest.run_id
    store.append_human_decision(
        rid,
        HumanDecision(
            id="h1",
            entry_id="JE-003",
            action=HumanAction.APPROVED,
            actor="Controller",
            reason="Treasury confirmed manual reval",
            ts=datetime(2025, 1, 6, tzinfo=UTC).isoformat(),
            before_decision=Decision.QUARANTINED,
        ),
    )
    out = run_pipeline(settings, store)
    assert out.manifest.run_id == rid
    assert [h.id for h in store.human_decisions(rid)] == ["h1"]
    assert out.posted is not None
    cash = next(ln for ln in out.posted if ln.account_code == "1110")
    assert any(r.kind == LineageKind.HUMAN and r.ref == "decision:h1" for r in cash.lineage)
