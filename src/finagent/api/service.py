"""Read models for the API: stored system results + the human-decision overlay.

System decisions are immutable; every view the UI shows is recomputed from them plus
`human_decisions.json`, so the server-confirmed state is always the single source of truth.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from typing import Any

from finagent.adjustments.lineage import LineageSources, explain_line
from finagent.adjustments.posting import (
    PostingInvariantError,
    all_lines_have_lineage,
    effective_decision,
    latest_human_decisions,
    ledger_imbalance,
    lineage_sums_ok,
    post,
    totals,
)
from finagent.domain.coa_tree import CoaTree
from finagent.domain.ids import decision_id
from finagent.domain.models import (
    Decision,
    EntryResult,
    HumanAction,
    HumanDecision,
    PostedLine,
)
from finagent.ingest import loaders
from finagent.observability.tracer import load_trace
from finagent.store.run_store import RunStore, now_iso

MIN_REASON = 10
MAX_ACTOR = 200
MAX_REASON = 2000
# ponytail: one process-wide lock (single uvicorn worker); use a file lock if workers > 1.
_DECISION_LOCK = threading.Lock()


class ApiError(Exception):
    """An error with a message written for a finance user (shown verbatim in the UI)."""

    def __init__(self, status: int, code: str, message_for_user: str, detail: Any = None) -> None:
        super().__init__(message_for_user)
        self.status = status
        self.code = code
        self.message_for_user = message_for_user
        self.detail = detail


@lru_cache(maxsize=1)
def coa_tree() -> CoaTree:
    return CoaTree(loaders.load_coa())


@lru_cache(maxsize=1)
def lineage_sources_base() -> LineageSources:
    tb = loaders.load_tb()
    raw = loaders.read_raw_lines(loaders.INPUTS / loaders.TB_FILE)
    return LineageSources(
        tb_rows={f"{r.source_file}#{r.row_index}": r for r in tb},
        raw_lines={f"{loaders.TB_FILE}#{i}": text for i, text in enumerate(raw)},
        rates={r.id: r for r in loaders.load_fx()},
    )


def resolve_run(store: RunStore, run_id: str) -> str:
    rid = store.latest() if run_id == "latest" else run_id
    if rid is None or not store.exists(rid):
        raise ApiError(
            404,
            "run_not_found",
            f"Run '{run_id}' was not found. Open the latest run instead.",
            {"latest": store.latest()},
        )
    return rid


def entry_view(result: EntryResult, human: HumanDecision | None) -> dict[str, Any]:
    eff = effective_decision(result, human)
    out = result.model_dump(mode="json")
    out["effective_decision"] = eff.value
    out["human_decision"] = human.model_dump(mode="json") if human else None
    out["effective_state"] = f"{human.action.value.lower()} by {human.actor}" if human else "system"
    return out


def entries(store: RunStore, rid: str) -> list[dict[str, Any]]:
    human = latest_human_decisions(store.human_decisions(rid))
    return [entry_view(r, human.get(r.entry.id)) for r in store.results(rid)]


def find_result(store: RunStore, rid: str, je_id: str) -> EntryResult:
    for r in store.results(rid):
        if r.entry.id == je_id:
            return r
    raise ApiError(404, "entry_not_found", f"Entry {je_id} is not part of run {rid}.")


def posted_lines(store: RunStore, rid: str) -> list[PostedLine]:
    base = store.base_ledger(rid)
    try:
        return post(base, store.results(rid), store.human_decisions(rid), coa_tree())
    except PostingInvariantError as exc:
        raise ApiError(
            409,
            "posting_invariant_failed",
            "The adjusted trial balance would no longer reconcile, so nothing was posted.",
            str(exc),
        ) from exc


def posted_tb(store: RunStore, rid: str) -> dict[str, Any]:
    base = store.base_ledger(rid)
    lines = posted_lines(store, rid)
    t = totals(lines)
    return {
        "lines": [ln.model_dump(mode="json") for ln in lines],
        "totals": {k: str(v) for k, v in t.items()},
        "invariants": {
            "imbalance_unchanged": ledger_imbalance(lines) == ledger_imbalance(base),
            "every_line_has_lineage": all_lines_have_lineage(lines),
            "lineage_reconciles": lineage_sums_ok(lines),
            "debits_equal_credits": t["imbalance"] == 0,
        },
        "human_decisions": len(store.human_decisions(rid)),
    }


def lineage(store: RunStore, rid: str, account: str) -> dict[str, Any]:
    line = next((ln for ln in posted_lines(store, rid) if ln.account_code == account), None)
    if line is None:
        raise ApiError(404, "account_not_found", f"Account {account} has no posted balance.")
    base = lineage_sources_base()
    sources = LineageSources(
        tb_rows=base.tb_rows,
        raw_lines=base.raw_lines,
        rates=base.rates,
        entries={r.entry.id: r.entry for r in store.results(rid)},
        human={h.id: h for h in store.human_decisions(rid)},
    )
    return explain_line(line, sources)


def lineage_preview(store: RunStore, rid: str, result: EntryResult) -> list[dict[str, Any]]:
    """Where this entry's lines land (or would land) in the posted TB."""
    lines = {ln.account_code: ln for ln in posted_lines(store, rid)}
    out: list[dict[str, Any]] = []
    for idx, ln in enumerate(result.entry.lines, start=1):
        posted = lines.get(ln.account)
        ref = f"{result.entry.id}#{idx}"
        out.append(
            {
                "line": idx,
                "account": ln.account,
                "posted": posted is not None and any(r.ref == ref for r in posted.lineage),
                "account_balance": str(posted.net) if posted else None,
            }
        )
    return out


def trace(store: RunStore, rid: str, je_id: str) -> list[dict[str, Any]]:
    path = store.runs_dir.parent / "traces" / f"{rid}.jsonl"
    events = [e for e in load_trace(path) if e.get("entry_id") == je_id]
    for h in store.human_decisions(rid):
        if h.entry_id == je_id:
            events.append(
                {
                    "ts": h.ts,
                    "event": "decision.human",
                    "entry_id": je_id,
                    "action": h.action.value,
                    "actor": h.actor,
                    "reason": h.reason,
                }
            )
    return events


def record_decision(
    store: RunStore, rid: str, je_id: str, action: str, actor: str, reason: str
) -> dict[str, Any]:
    """Apply a reviewer's decision. Only QUARANTINED entries can be decided, and only once:
    rejected entries must be edited and resubmitted as a new version (engineering rule 4)."""
    result = find_result(store, rid, je_id)
    if result.decision == Decision.REJECTED:
        raise ApiError(
            400,
            "entry_rejected",
            "Rejected entries can't be approved. Edit the entry and resubmit it as a new version.",
            {"system_decision": result.decision.value},
        )
    if result.decision == Decision.ACCEPTED:
        raise ApiError(
            400,
            "entry_already_posted",
            "This entry passed every check and was posted automatically; there is nothing to "
            "approve or reject.",
        )
    try:
        act = HumanAction(action)
    except ValueError as exc:
        raise ApiError(400, "invalid_action", "Choose either approve or reject.") from exc
    actor_clean, reason_clean = actor.strip(), reason.strip()
    if not actor_clean:
        raise ApiError(400, "actor_required", "Enter your name so the decision is attributable.")
    if len(reason_clean) < MIN_REASON:
        raise ApiError(
            400,
            "reason_too_short",
            f"Give a reason of at least {MIN_REASON} characters; it goes into the audit log.",
        )
    if len(actor_clean) > MAX_ACTOR:
        raise ApiError(400, "actor_too_long", f"Keep your name under {MAX_ACTOR} characters.")
    if len(reason_clean) > MAX_REASON:
        raise ApiError(400, "reason_too_long", f"Keep the reason under {MAX_REASON} characters.")
    with _DECISION_LOCK:
        return _record_decision_locked(store, rid, result, act, actor_clean, reason_clean)


def _record_decision_locked(
    store: RunStore,
    rid: str,
    result: EntryResult,
    act: HumanAction,
    actor_clean: str,
    reason_clean: str,
) -> dict[str, Any]:
    """Check-then-write must be atomic, or two reviewers can both 'win' the same entry."""
    je_id = result.entry.id
    existing = latest_human_decisions(store.human_decisions(rid)).get(je_id)
    if existing is not None:
        raise ApiError(
            409,
            "already_decided",
            f"{je_id} was already {existing.action.value.lower()} by {existing.actor}. "
            "Decisions are final; resubmit a new version to change it.",
        )
    decision = HumanDecision(
        id=decision_id(),
        entry_id=je_id,
        entry_version=result.entry.version,
        action=act,
        actor=actor_clean,
        reason=reason_clean,
        ts=now_iso(),
        before_decision=result.decision,
    )
    store.append_human_decision(rid, decision)
    after = effective_decision(result, decision)
    lines = posted_lines(store, rid)
    store.write_posted(rid, lines)
    store.append_audit(
        rid,
        "decision.human",
        entry_id=je_id,
        decision_id=decision.id,
        actor=decision.actor,
        reason=decision.reason,
        before=result.decision.value,
        after=after.value,
    )
    if act == HumanAction.APPROVED:
        store.append_audit(rid, "post.completed", entry_id=je_id, lines=len(lines))
    return entry_view(result, decision)
