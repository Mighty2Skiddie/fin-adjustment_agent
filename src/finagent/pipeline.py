"""End-to-end run: inputs -> health -> base ledger -> per-entry decisions -> posting -> store.

The per-entry step is the LangGraph processor (graph/adjustments_graph.py); `--llm-mode off`
runs the same graph with templates instead of the LLM. Decisions always come from
`decisions.decide`. `processor` is injectable so tests can simulate a broken step.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from finagent.adjustments.context import RuleContext, build_rule_context
from finagent.adjustments.posting import (
    PostingInvariantError,
    all_lines_have_lineage,
    ledger_imbalance,
    lineage_sums_ok,
    post,
)
from finagent.config import Settings
from finagent.domain.ids import code_version, run_id, sha256_file
from finagent.domain.models import (
    Decision,
    EntryResult,
    HealthFinding,
    HumanDecision,
    JournalEntry,
    PostedLine,
    RunManifest,
)
from finagent.ingest import loaders
from finagent.ingest.fx import MissingRateError
from finagent.ingest.health_audit import build_context, run_checks
from finagent.ingest.health_checks.base import AuditContext
from finagent.ingest.normalize import build_base_ledger
from finagent.observability.langfuse_hooks import flush as langfuse_flush
from finagent.observability.langfuse_hooks import langfuse_status
from finagent.observability.tracer import Tracer
from finagent.store.run_store import RunStore, now_iso

EntryProcessor = Callable[[list[JournalEntry], RuleContext, str, Tracer], list[EntryResult]]


@dataclass
class Prepared:
    settings: Settings
    audit: AuditContext
    health: list[HealthFinding]
    base_ledger: list[PostedLine] | None
    rule_ctx: RuleContext | None
    input_hashes: dict[str, str]
    run_id: str
    code_version: str
    blocked_reason: str | None = None


@dataclass
class RunOutcome:
    manifest: RunManifest
    results: list[EntryResult]
    posted: list[PostedLine] | None
    health: list[HealthFinding] = field(default_factory=list[HealthFinding])


def input_hashes() -> dict[str, str]:
    return {name: sha256_file(loaders.INPUTS / name) for name in loaders.INPUT_FILES}


def prepare(settings: Settings, version: str | None = None) -> Prepared:
    audit = build_context(settings)
    health = run_checks(audit)
    hashes = input_hashes()
    cv = version or code_version()
    rid = run_id(hashes, settings.config_hash(), cv)
    try:
        ledger, _ = build_base_ledger(audit.tb_rows, audit.coa, audit.ratebook, settings)
    except MissingRateError as exc:
        return Prepared(settings, audit, health, None, None, hashes, rid, cv, str(exc))
    ctx = build_rule_context(
        settings, audit.coa, audit.tb_rows, audit.ratebook, audit.entries, ledger
    )
    return Prepared(settings, audit, health, ledger, ctx, hashes, rid, cv)


def llm_outputs_guarded(results: list[EntryResult], events: list[dict[str, Any]]) -> bool:
    """Every LLM output that was used passed its guardrails (or the role fell back).

    Checked from the trace, independently of the roles' own bookkeeping: an `llm.role` with
    source "llm" must be preceded by a passing `guardrail.result` for the same entry and role,
    and an entry may only carry `explanation_source="llm"` if such a role event exists.
    """
    passed = {
        (e.get("entry_id"), e.get("role"))
        for e in events
        if e["event"] == "guardrail.result" and e.get("passed") is True
    }
    unguarded = [
        e
        for e in events
        if e["event"] == "llm.role"
        and e.get("source") == "llm"
        and (e.get("entry_id"), e.get("role")) not in passed
        and not e.get("guardrail_fallback")
    ]
    if unguarded:
        return False
    llm_explained = {
        e.get("entry_id")
        for e in events
        if e["event"] == "llm.role" and e.get("role") == "explainer" and e.get("source") == "llm"
    }
    return all(
        r.explanation_source in {"llm", "template", "none"}
        and (r.explanation_source != "llm" or r.entry.id in llm_explained)
        for r in results
    )


def check_invariants(
    prep: Prepared,
    results: list[EntryResult],
    posted: list[PostedLine] | None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, bool]:
    base = prep.base_ledger or []
    entries = prep.audit.entries
    inv = {
        "all_entries_decided": len(results) == len(entries)
        and {r.entry.id for r in results} == {e.id for e in entries},
        "imbalance_unchanged": posted is not None
        and ledger_imbalance(posted) == ledger_imbalance(base),
        "every_line_has_lineage": posted is not None and all_lines_have_lineage(posted),
        "lineage_reconciles": posted is not None and lineage_sums_ok(posted),
        "unmapped_not_in_coa_subtotals": posted is not None
        and all(ln.mapped == (ln.account_code in prep.audit.coa) for ln in posted),
        "llm_outputs_guarded": llm_outputs_guarded(results, events or []),
    }
    return inv


def post_with_overlay(
    prep: Prepared, results: list[EntryResult], human: list[HumanDecision]
) -> list[PostedLine] | None:
    if prep.base_ledger is None:
        return None
    try:
        return post(prep.base_ledger, results, human, prep.audit.coa)
    except PostingInvariantError:
        return None


def run_pipeline(
    settings: Settings,
    store: RunStore | None = None,
    processor: EntryProcessor | None = None,
) -> RunOutcome:
    store = store or RunStore()
    prep = prepare(settings)
    tracer = Tracer(prep.run_id, store.runs_dir.parent / "traces")
    tracer.emit("run.start", llm_mode=settings.llm.mode, fx_policy=settings.fx.missing_rate_policy)
    results: list[EntryResult] = []
    posted: list[PostedLine] | None = None
    if prep.rule_ctx is not None:
        from finagent.graph.adjustments_graph import graph_processor

        process: EntryProcessor = processor or graph_processor(settings)
        results = process(prep.audit.entries, prep.rule_ctx, prep.run_id, tracer)
        human = store.human_decisions(prep.run_id) if store.exists(prep.run_id) else []
        with tracer.node("post"):
            posted = post_with_overlay(prep, results, human)
    invariants = check_invariants(prep, results, posted, tracer.events)
    for name, ok in invariants.items():
        tracer.emit("invariant", name=name, passed=ok)
    if prep.blocked_reason is not None:
        status = "BLOCKED"
    elif all(invariants.values()):
        status = "OK"
    else:
        status = "FAILED_INVARIANT"
    tracer.emit("run.end", status=status)
    counts = {d.value.lower(): sum(1 for r in results if r.decision == d) for d in Decision}
    manifest = RunManifest(
        run_id=prep.run_id,
        created_at=now_iso(),
        code_version=prep.code_version,
        input_hashes=prep.input_hashes,
        config_hash=settings.config_hash(),
        llm_mode=settings.llm.mode,
        counts=counts,
        invariants=invariants,
        status=status,
        fx_policy=settings.fx.missing_rate_policy,
        period=settings.period.id,
        metrics={**tracer.summary(), "langfuse": langfuse_status(settings)[1]},
    )
    tracer.flush()
    langfuse_flush(settings)
    store.write_run(
        manifest,
        prep.health,
        prep.base_ledger or [],
        results,
        posted if status == "OK" else None,
    )
    existed = len(store.audit_log(prep.run_id)) > 0
    if not existed:
        store.append_audit(prep.run_id, "run.created", status=status, llm_mode=settings.llm.mode)
        for r in results:
            store.append_audit(
                prep.run_id,
                "decision.system",
                entry_id=r.entry.id,
                after=r.decision.value,
                rule_ids=[f.rule_id for f in r.findings],
            )
        if status == "OK":
            store.append_audit(prep.run_id, "post.completed", lines=len(posted or []))
    else:
        store.append_audit(prep.run_id, "run.recomputed", status=status)
    return RunOutcome(store.manifest(prep.run_id), results, posted, prep.health)
