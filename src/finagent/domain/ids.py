"""Identifiers. Run and trace ids are content hashes so re-runs are byte-identical."""

from __future__ import annotations

import hashlib
import os
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
    """sha256(canonical JSON of inputs + config + code version)[:12] (engineering rule 7)."""
    payload = {"inputs": input_hashes, "config": config_hash, "code": code_version}
    return sha256_bytes(canonical_json(payload))[:12]


def trace_id(run: str, entry_id: str, version: int = 1) -> str:
    """Deterministic per entry within a run, so decisions.json stays byte-identical."""
    return sha256_bytes(f"{run}:{entry_id}:v{version}".encode())[:16]


def decision_id() -> str:
    """Human decisions are events, not derived data: a random id is correct here."""
    return uuid.uuid4().hex


def _git(args: list[str], repo: Path | None) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def source_hash(src: Path) -> str:
    """Content hash of the package source, so uncommitted code changes still change run_id."""
    h = hashlib.sha256()
    for p in sorted(src.rglob("*")):
        if p.is_file() and p.suffix in {".py", ".md"}:
            h.update(p.relative_to(src).as_posix().encode())
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:8]


def code_version(repo: Path | None = None) -> str:
    """Short git sha; `<sha>+<src hash>` when src/ has uncommitted changes; "nogit" outside git.

    Override with FINAGENT_CODE_VERSION (e.g. in the container, where .git is absent).
    """
    override = os.environ.get("FINAGENT_CODE_VERSION")
    if override:
        return override
    sha = _git(["rev-parse", "--short", "HEAD"], repo)
    if not sha:
        return "nogit"
    src = Path(__file__).resolve().parents[1]
    dirty = _git(["status", "--porcelain", "--", str(src)], repo)
    return f"{sha}+{source_hash(src)}" if dirty else sha
