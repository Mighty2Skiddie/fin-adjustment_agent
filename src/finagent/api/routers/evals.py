"""Evaluation report and the architecture document."""

from __future__ import annotations

from typing import Any

import orjson
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from finagent.api.deps import get_store
from finagent.api.service import ApiError, resolve_run
from finagent.config import ROOT

router = APIRouter(prefix="/api", tags=["evals"])

ARCHITECTURE_DOCS = (ROOT / "docs" / "ARCHITECTURE.md",)


@router.get("/runs/{run_id}/evals")
def get_evals(run_id: str) -> dict[str, Any]:
    store = get_store()
    resolve_run(store, run_id)
    path = store.runs_dir.parent / "evals" / "report.json"
    if not path.is_file():
        raise ApiError(404, "evals_missing", "No evaluation report yet. Run `finagent eval`.")
    report: dict[str, Any] = orjson.loads(path.read_bytes())
    return report


@router.get("/docs/architecture", response_class=PlainTextResponse)
def architecture() -> str:
    for path in ARCHITECTURE_DOCS:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise ApiError(404, "doc_missing", "The architecture document is not available.")
