"""Engineering rule 7: identical inputs give the same run_id and a byte-identical decisions.json."""

from __future__ import annotations

from pathlib import Path

from finagent.config import Settings, load_settings
from finagent.pipeline import run_pipeline
from finagent.store.run_store import RunStore


def test_two_runs_identical(settings: Settings, tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    a = run_pipeline(settings, store)
    first = (store.run_dir(a.manifest.run_id) / "decisions.json").read_bytes()
    posted_first = (store.run_dir(a.manifest.run_id) / "posted_tb.csv").read_bytes()
    b = run_pipeline(settings, store)
    assert a.manifest.run_id == b.manifest.run_id
    assert (store.run_dir(b.manifest.run_id) / "decisions.json").read_bytes() == first
    assert (store.run_dir(b.manifest.run_id) / "posted_tb.csv").read_bytes() == posted_first
    events = [e["event"] for e in store.audit_log(a.manifest.run_id)]
    assert events.count("run.created") == 1 and events[-1] == "run.recomputed"


def test_config_change_changes_run_id(settings: Settings, tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    a = run_pipeline(settings, store)
    other = load_settings(
        {"llm": {"mode": "off"}, "fx": {"missing_rate_policy": "fallback_opening"}}
    )
    b = run_pipeline(other, store)
    assert a.manifest.run_id != b.manifest.run_id
    assert store.latest() == b.manifest.run_id


def test_block_policy_blocks_run(tmp_path: Path) -> None:
    s = load_settings({"llm": {"mode": "off"}, "fx": {"missing_rate_policy": "block"}})
    out = run_pipeline(s, RunStore(tmp_path))
    assert out.manifest.status == "BLOCKED"
    assert out.posted is None
    assert not (tmp_path / out.manifest.run_id / "posted_tb.csv").exists()
