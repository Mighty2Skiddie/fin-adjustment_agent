"""Identifiers. Run and trace ids are content hashes so re-runs are byte-identical."""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from pathlib import Path

import orjson


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(obj: object) -> bytes:
    return orjson.dumps(obj, option=orjson.OPT_SORT_KEYS)


def run_id(input_hashes: dict[str, str], config_hash: str, code_version: str) -> str:
    """sha256(canonical JSON of inputs + config + code version)[:12] (CLAUDE.md rule 7)."""
    payload = {"inputs": input_hashes, "config": config_hash, "code": code_version}
    return sha256_bytes(canonical_json(payload))[:12]


def trace_id(run: str, entry_id: str, version: int = 1) -> str:
    """Deterministic per entry within a run, so decisions.json stays byte-identical."""
    return sha256_bytes(f"{run}:{entry_id}:v{version}".encode())[:16]


def decision_id() -> str:
    """Human decisions are events, not derived data: a random id is correct here."""
    return uuid.uuid4().hex


def code_version(repo: Path | None = None) -> str:
    """Short git sha, or "nogit" when not in a repository (e.g. inside the container)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "nogit"
    sha = out.stdout.strip()
    return sha if out.returncode == 0 and sha else "nogit"
