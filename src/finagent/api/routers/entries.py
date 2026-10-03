"""Entries, reviewer decisions and per-entry traces."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from finagent.adjustments.posting import latest_human_decisions
from finagent.api.deps import get_store
from finagent.api.service import (
    entries,
    entry_view,
    find_result,
    lineage_preview,
    record_decision,
    resolve_run,
    trace,
)

router = APIRouter(prefix="/api/runs/{run_id}", tags=["entries"])


class DecisionBody(BaseModel):
    action: str
    actor: str
    reason: str


@router.get("/entries")
def list_entries(run_id: str) -> list[dict[str, Any]]:
    store = get_store()
    return entries(store, resolve_run(store, run_id))


@router.get("/entries/{je_id}")
def get_entry(run_id: str, je_id: str) -> dict[str, Any]:
    store = get_store()
    rid = resolve_run(store, run_id)
    result = find_result(store, rid, je_id)
    human_all = [h for h in store.human_decisions(rid) if h.entry_id == je_id]
    view = entry_view(result, latest_human_decisions(human_all).get(je_id))
    view["human_decisions"] = [h.model_dump(mode="json") for h in human_all]
    view["lineage_preview"] = lineage_preview(store, rid, result)
    return view


@router.post("/entries/{je_id}/decision")
def decide(run_id: str, je_id: str, body: DecisionBody) -> dict[str, Any]:
    store = get_store()
    rid = resolve_run(store, run_id)
    return record_decision(store, rid, je_id, body.action, body.actor, body.reason)


@router.get("/trace/{je_id}")
def get_trace(run_id: str, je_id: str) -> list[dict[str, Any]]:
    store = get_store()
    rid = resolve_run(store, run_id)
    find_result(store, rid, je_id)
    return trace(store, rid, je_id)
