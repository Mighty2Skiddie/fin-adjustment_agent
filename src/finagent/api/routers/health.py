"""Data health for a run, grouped for the UI, plus the TB balance under each FX policy."""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter

from finagent.api.deps import get_store
from finagent.api.service import resolve_run
from finagent.ingest.health_audit import BRIEF_LISTED, FILE_LABELS, FILE_ORDER
from finagent.ingest.normalize import POLICY_TO_VARIANT, VARIANT_LABELS

router = APIRouter(prefix="/api/runs/{run_id}", tags=["health"])


@router.get("/health")
def health(run_id: str) -> dict[str, Any]:
    store = get_store()
    rid = resolve_run(store, run_id)
    findings = store.health(rid)
    manifest = store.manifest(rid)
    by_file: dict[str, list[dict[str, Any]]] = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f.model_dump(mode="json"))
    tb01 = next((f for f in findings if f.id == "H-TB-01"), None)
    active = POLICY_TO_VARIANT.get(manifest.fx_policy or "", "")
    variants: list[dict[str, Any]] = []
    for key, label in VARIANT_LABELS.items():
        values: dict[str, Any] = dict(tb01.evidence.get(key, {})) if tb01 else {}
        variants.append({"key": key, "label": label, **values, "active": key == active})
    return {
        "findings": [f.model_dump(mode="json") for f in findings],
        "by_file": by_file,
        "by_severity": dict(Counter(str(f.severity) for f in findings)),
        "files": [
            {
                "file": name,
                "label": FILE_LABELS[name],
                "listed_in_brief": BRIEF_LISTED.get(name, 0),
                "found": len(by_file.get(name, [])),
            }
            for name in FILE_ORDER
        ],
        "brief_listed_total": sum(BRIEF_LISTED.values()),
        "fx_variants": variants,
        "fx_policy": manifest.fx_policy,
        "materiality_tolerance": tb01.evidence.get("materiality_tolerance") if tb01 else None,
    }
