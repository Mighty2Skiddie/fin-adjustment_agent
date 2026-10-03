"""Post-adjustment TB (with the human overlay) and line-level lineage."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from finagent.api.deps import get_store
from finagent.api.service import lineage, posted_tb, resolve_run

router = APIRouter(prefix="/api/runs/{run_id}", tags=["ledger"])


@router.get("/posted-tb")
def get_posted_tb(run_id: str) -> dict[str, Any]:
    store = get_store()
    return posted_tb(store, resolve_run(store, run_id))


@router.get("/lineage/{account_code}")
def get_lineage(run_id: str, account_code: str) -> dict[str, Any]:
    store = get_store()
    return lineage(store, resolve_run(store, run_id), account_code)
