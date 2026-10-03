"""Runs: create (idempotent), list, manifest, audit log, effective config."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from finagent.api.deps import get_store
from finagent.api.service import ApiError, resolve_run
from finagent.config import load_settings
from finagent.pipeline import prepare, run_pipeline

router = APIRouter(prefix="/api", tags=["runs"])

SECRET_ENV = (
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)


@router.post("/runs", response_model=None)
def create_run(body: dict[str, Any] | None = Body(default=None)) -> Any:  # noqa: B008
    overrides: dict[str, Any] = (body or {}).get("config_overrides") or {}
    try:
        settings = load_settings(overrides)
    except Exception as exc:  # noqa: BLE001 - bad overrides are a user error, not a crash
        raise ApiError(400, "invalid_config", "Those settings are not valid.", str(exc)) from exc
    store = get_store()
    rid = prepare(settings).run_id
    if store.exists(rid):
        return JSONResponse(status_code=409, content={"run_id": rid, "existing": True})
    out = run_pipeline(settings, store)
    return {"run_id": out.manifest.run_id, "status": out.manifest.status}


@router.get("/runs")
def list_runs() -> list[dict[str, Any]]:
    store = get_store()
    latest = store.latest()
    return [
        {
            "run_id": m.run_id,
            "created_at": m.created_at,
            "counts": m.counts,
            "status": m.status,
            "llm_mode": m.llm_mode,
            "fx_policy": m.fx_policy,
            "period": m.period,
            "latest": m.run_id == latest,
        }
        for m in store.list_runs()
    ]


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    store = get_store()
    rid = resolve_run(store, run_id)
    m = store.manifest(rid)
    return {**m.model_dump(mode="json"), "latest": rid == store.latest()}


@router.get("/runs/{run_id}/audit-log")
def audit_log(run_id: str) -> list[dict[str, Any]]:
    store = get_store()
    return store.audit_log(resolve_run(store, run_id))


@router.get("/config")
def config() -> dict[str, Any]:
    """Effective settings. Secrets are reported as set / not set, never their values."""
    data = load_settings().model_dump(mode="json")
    keys = {k: ("set" if os.environ.get(k) else "not set") for k in SECRET_ENV}
    return {**data, "secrets": keys}
