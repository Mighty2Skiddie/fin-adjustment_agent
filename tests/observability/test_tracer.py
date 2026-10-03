from __future__ import annotations

from pathlib import Path

import pytest

from finagent.config import load_settings
from finagent.observability.langfuse_hooks import callbacks, langfuse_status
from finagent.observability.tracer import Tracer, load_trace
from finagent.pipeline import RunOutcome, run_pipeline
from finagent.store.run_store import RunStore

REQUIRED_EVENTS = {
    "run.start",
    "entry.start",
    "node.enter",
    "node.exit",
    "rule.result",
    "llm.call",
    "llm.role",
    "guardrail.result",
    "decision",
    "fix.revalidated",
    "invariant",
    "run.end",
}


@pytest.fixture(scope="module")
def cassette_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[RunOutcome, Path]:
    mp = pytest.MonkeyPatch()
    for key in ("GOOGLE_API_KEY", "GROQ_API_KEY"):
        mp.delenv(key, raising=False)
    runs = tmp_path_factory.mktemp("obs") / "runs"
    out = run_pipeline(load_settings({"llm": {"mode": "cassette"}}), RunStore(runs))
    mp.undo()
    return out, runs.parent / "traces" / f"{out.manifest.run_id}.jsonl"


def test_trace_file_has_every_event_type(cassette_run: tuple[RunOutcome, Path]) -> None:
    _, path = cassette_run
    events = load_trace(path)
    assert {e["event"] for e in events} >= REQUIRED_EVENTS
    assert all(e["run_id"] == cassette_run[0].manifest.run_id for e in events)


def test_rule_results_cover_every_rule_for_every_entry(
    cassette_run: tuple[RunOutcome, Path],
) -> None:
    events = load_trace(cassette_run[1])
    deterministic = {f"R{i:03d}" for i in range(1, 13)}
    for je in (f"JE-{i:03d}" for i in range(1, 11)):
        seen = {e["rule_id"] for e in events if e["event"] == "rule.result" and e["entry_id"] == je}
        assert deterministic <= seen, je


def test_llm_call_events_carry_model_and_cassette_info(
    cassette_run: tuple[RunOutcome, Path],
) -> None:
    calls = [e for e in load_trace(cassette_run[1]) if e["event"] == "llm.call"]
    assert len(calls) == 18
    for c in calls:
        assert c["mode"] == "cassette" and c["cassette_hit"] is True
        assert c["model"] and c["prompt_hash"] and "latency_ms" in c and "input_tokens" in c


def test_one_decision_event_per_entry(cassette_run: tuple[RunOutcome, Path]) -> None:
    decisions = [e for e in load_trace(cassette_run[1]) if e["event"] == "decision"]
    assert sorted(e["entry_id"] for e in decisions) == [f"JE-{i:03d}" for i in range(1, 11)]


def test_invariant_events_match_manifest(cassette_run: tuple[RunOutcome, Path]) -> None:
    out, path = cassette_run
    inv = {e["name"]: e["passed"] for e in load_trace(path) if e["event"] == "invariant"}
    assert inv == out.manifest.invariants
    assert all(inv.values())


def test_manifest_metrics(cassette_run: tuple[RunOutcome, Path]) -> None:
    m = cassette_run[0].manifest.metrics
    assert m["auto_accept_rate"] == "0.6000"
    assert m["quarantine_rate"] == "0.2000"
    assert m["reject_rate"] == "0.2000"
    assert m["llm_calls"] == 18
    assert m["cassette_hit_rate"] == "1.0000"
    assert m["guardrail_fallback_rate"] == "0.0000"
    assert "p50_latency_ms" in m and "langfuse" in m


def test_node_context_manager_records_duration() -> None:
    t = Tracer("r1")
    with t.node("validate", entry_id="JE-1"):
        pass
    enter, exit_ = t.events
    assert (enter["event"], exit_["event"]) == ("node.enter", "node.exit")
    assert exit_["duration_ms"] >= 0 and t.for_entry("JE-1") == t.events


def test_tracer_without_dir_does_not_write() -> None:
    t = Tracer("r2")
    t.emit("x")
    assert t.flush() is None


def test_emit_drops_none_fields() -> None:
    assert "model" not in Tracer("r3").emit("llm.call", model=None)


def test_langfuse_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    s = load_settings()
    enabled, reason = langfuse_status(s)
    assert not enabled and "disabled" in reason
    assert callbacks(s) == []


def test_langfuse_needs_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    s = load_settings({"observability": {"langfuse_enabled": True}})
    enabled, reason = langfuse_status(s)
    assert not enabled and "LANGFUSE_PUBLIC_KEY" in reason
    assert callbacks(s) == []
