"""Run state as JSON files under `output/runs/<run_id>/`. The only place that writes them.

System outputs (`decisions.json`, `posted_tb.*`, ...) are derived and rewritten identically on
re-run; `human_decisions.json` and `audit_log.jsonl` are append-only event stores that survive
re-runs, so an approval is never lost by recomputing.
"""

from __future__ import annotations

import csv
import io
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson

from finagent.config import ROOT
from finagent.domain.models import (
    EntryResult,
    HealthFinding,
    HumanDecision,
    PostedLine,
    RunManifest,
)

RUNS_DIR = ROOT / "output" / "runs"
JSON_OPTS = orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def dumps(obj: Any) -> bytes:
    return orjson.dumps(obj, option=JSON_OPTS) + b"\n"


def write_atomic(path: Path, data: bytes) -> None:
    """Write via temp file + replace so a concurrent reader never sees a truncated file."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    tmp.write_bytes(data)
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            # Windows refuses to replace a file another thread has open for reading.
            if attempt == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.01)


class RunStore:
    def __init__(self, runs_dir: Path | None = None) -> None:
        self.runs_dir = runs_dir or RUNS_DIR

    # ---- paths -----------------------------------------------------------------------------
    def run_dir(self, run_id: str) -> Path:
        return self.runs_dir / run_id

    def exists(self, run_id: str) -> bool:
        return (self.run_dir(run_id) / "manifest.json").is_file()

    def latest(self) -> str | None:
        p = self.runs_dir / "LATEST"
        if not p.is_file():
            return None
        rid = p.read_text(encoding="utf-8").strip()
        return rid or None

    def list_runs(self) -> list[RunManifest]:
        if not self.runs_dir.is_dir():
            return []
        out = [
            self.manifest(d.name)
            for d in self.runs_dir.iterdir()
            if d.is_dir() and (d / "manifest.json").is_file()
        ]
        latest = self.latest()
        return sorted(out, key=lambda m: (m.run_id != latest, m.created_at), reverse=False)

    # ---- writes ----------------------------------------------------------------------------
    def write_run(
        self,
        manifest: RunManifest,
        health: list[HealthFinding],
        base_ledger: list[PostedLine],
        results: list[EntryResult],
        posted: list[PostedLine] | None,
    ) -> Path:
        d = self.run_dir(manifest.run_id)
        d.mkdir(parents=True, exist_ok=True)
        previous = self.manifest(manifest.run_id) if self.exists(manifest.run_id) else None
        if previous is not None:
            # Keep the original creation time so a re-run is byte-identical where it can be.
            manifest = manifest.model_copy(update={"created_at": previous.created_at})
        (d / "manifest.json").write_bytes(dumps(manifest.model_dump(mode="json")))
        (d / "health.json").write_bytes(dumps([f.model_dump(mode="json") for f in health]))
        (d / "base_ledger.json").write_bytes(
            dumps([ln.model_dump(mode="json") for ln in base_ledger])
        )
        (d / "decisions.json").write_bytes(dumps([r.model_dump(mode="json") for r in results]))
        if posted is None:
            failed = d / "failed"
            failed.mkdir(exist_ok=True)
            (failed / "decisions.json").write_bytes((d / "decisions.json").read_bytes())
            for name in ("posted_tb.csv", "posted_tb.json"):
                (d / name).unlink(missing_ok=True)
        else:
            shutil.rmtree(d / "failed", ignore_errors=True)
            self.write_posted(manifest.run_id, posted)
        if not (d / "human_decisions.json").exists():
            (d / "human_decisions.json").write_bytes(dumps([]))
        (self.runs_dir / "LATEST").write_text(manifest.run_id + "\n", encoding="utf-8")
        return d

    def write_posted(self, run_id: str, posted: list[PostedLine]) -> None:
        d = self.run_dir(run_id)
        write_atomic(d / "posted_tb.json", dumps([ln.model_dump(mode="json") for ln in posted]))
        write_atomic(d / "posted_tb.csv", posted_csv(posted).encode("utf-8"))

    def append_audit(self, run_id: str, event: str, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = {"ts": now_iso(), "run_id": run_id, "event": event, **fields}
        path = self.run_dir(run_id) / "audit_log.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as fh:
            fh.write(orjson.dumps(record, option=orjson.OPT_SORT_KEYS) + b"\n")
        return record

    def append_human_decision(self, run_id: str, decision: HumanDecision) -> None:
        existing = self.human_decisions(run_id)
        existing.append(decision)
        write_atomic(
            self.run_dir(run_id) / "human_decisions.json",
            dumps([h.model_dump(mode="json") for h in existing]),
        )

    # ---- reads -----------------------------------------------------------------------------
    def _read(self, run_id: str, name: str) -> Any:
        return orjson.loads((self.run_dir(run_id) / name).read_bytes())

    def manifest(self, run_id: str) -> RunManifest:
        return RunManifest.model_validate(self._read(run_id, "manifest.json"))

    def health(self, run_id: str) -> list[HealthFinding]:
        return [HealthFinding.model_validate(x) for x in self._read(run_id, "health.json")]

    def base_ledger(self, run_id: str) -> list[PostedLine]:
        return [PostedLine.model_validate(x) for x in self._read(run_id, "base_ledger.json")]

    def results(self, run_id: str) -> list[EntryResult]:
        return [EntryResult.model_validate(x) for x in self._read(run_id, "decisions.json")]

    def human_decisions(self, run_id: str) -> list[HumanDecision]:
        path = self.run_dir(run_id) / "human_decisions.json"
        if not path.is_file():
            return []
        return [HumanDecision.model_validate(x) for x in orjson.loads(path.read_bytes())]

    def audit_log(self, run_id: str) -> list[dict[str, Any]]:
        path = self.run_dir(run_id) / "audit_log.jsonl"
        if not path.is_file():
            return []
        return [orjson.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


def posted_csv(posted: list[PostedLine]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["account_code", "account_name", "debit", "credit", "net", "mapped", "lineage_json"])
    for ln in posted:
        lineage = orjson.dumps([r.model_dump(mode="json") for r in ln.lineage]).decode()
        w.writerow(
            [ln.account_code, ln.account_name, ln.debit, ln.credit, ln.net, ln.mapped, lineage]
        )
    return buf.getvalue()
