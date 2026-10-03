"""Always-on JSONL trace, one file per run (`output/traces/<run_id>.jsonl`). No dependencies.

Every node, rule result, LLM call, guardrail verdict, decision and invariant is an event, so a
reviewer can replay *why* an entry got its decision without re-running anything.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import orjson

from finagent.store.run_store import now_iso


class Tracer:
    def __init__(self, run_id: str, trace_dir: Path | None = None) -> None:
        self.run_id = run_id
        self.trace_dir = trace_dir
        self.events: list[dict[str, Any]] = []

    @property
    def path(self) -> Path | None:
        return None if self.trace_dir is None else self.trace_dir / f"{self.run_id}.jsonl"

    def emit(self, event: str, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = {"ts": now_iso(), "run_id": self.run_id, "event": event}
        record.update({k: v for k, v in fields.items() if v is not None})
        self.events.append(record)
        return record

    @contextmanager
    def node(self, name: str, **fields: Any) -> Generator[None]:
        start = time.perf_counter()
        self.emit("node.enter", node=name, **fields)
        try:
            yield
        finally:
            ms = round((time.perf_counter() - start) * 1000, 3)
            self.emit("node.exit", node=name, duration_ms=ms, **fields)

    def for_entry(self, entry_id: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e.get("entry_id") == entry_id]

    def flush(self) -> Path | None:
        """Write the whole run's events (a re-run replaces the file: traces describe one run)."""
        path = self.path
        if path is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            for e in self.events:
                fh.write(orjson.dumps(e) + b"\n")
        return path

    def summary(self) -> dict[str, Any]:
        """Run-level metrics stored in the manifest."""
        decisions = [e for e in self.events if e["event"] == "decision"]
        llm = [e for e in self.events if e["event"] == "llm.call"]
        roles = [e for e in self.events if e["event"] == "llm.role"]
        n = len(decisions) or 1
        latencies = [e["latency_ms"] for e in llm if isinstance(e.get("latency_ms"), int | float)]
        hits = [e for e in llm if e.get("cassette_hit") is True]
        cassette_calls = [e for e in llm if e.get("mode") == "cassette"]
        fallbacks = [e for e in roles if e.get("guardrail_fallback") is True]
        return {
            "auto_accept_rate": _ratio(
                sum(1 for e in decisions if e.get("decision") == "ACCEPTED"), n
            ),
            "quarantine_rate": _ratio(
                sum(1 for e in decisions if e.get("decision") == "QUARANTINED"), n
            ),
            "reject_rate": _ratio(sum(1 for e in decisions if e.get("decision") == "REJECTED"), n),
            "llm_calls": len(llm),
            "llm_roles_run": len(roles),
            "guardrail_fallback_rate": _ratio(len(fallbacks), len(roles) or 1),
            "cassette_hit_rate": _ratio(len(hits), len(cassette_calls) or 1),
            "provider_fallbacks": sum(1 for e in llm if e.get("provider_fallback") is True),
            "p50_latency_ms": round(statistics.median(latencies), 3) if latencies else 0,
        }


def _ratio(num: int, den: int) -> str:
    """Rates as strings (4 dp): the manifest stays float-free like every other output."""
    return f"{num / den:.4f}"


def load_trace(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [orjson.loads(line) for line in path.read_bytes().splitlines() if line.strip()]
