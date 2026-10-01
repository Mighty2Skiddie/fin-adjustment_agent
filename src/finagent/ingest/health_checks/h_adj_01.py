"""H-ADJ-01: batch-level totals give the reviewer a control figure before per-entry rules run;
a batch that does not balance points straight at the entries that cause it."""

from __future__ import annotations

from finagent.domain.models import HealthFinding, HealthSeverity
from finagent.domain.money import ZERO, dstr, fmt
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-ADJ-01"


def check(ctx: AuditContext) -> list[HealthFinding]:
    if not ctx.entries:
        return []
    lines = [ln for e in ctx.entries for ln in e.lines]
    total_debit = sum((ln.debit for ln in lines), ZERO)
    total_credit = sum((ln.credit for ln in lines), ZERO)
    difference = total_debit - total_credit
    unbalanced = [
        e.id
        for e in ctx.entries
        if sum((ln.debit for ln in e.lines), ZERO) != sum((ln.credit for ln in e.lines), ZERO)
    ]
    tail = (
        f" The difference comes from {', '.join(unbalanced)}."
        if unbalanced
        else " Every entry balances."
    )
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.INFO,
            file="manual_adjustments.json",
            title="Batch summary",
            message=(
                f"{len(ctx.entries)} entries with {len(lines)} lines: debits {fmt(total_debit)} "
                f"vs credits {fmt(total_credit)} (difference {fmt(difference)}).{tail}"
            ),
            evidence={
                "entries": len(ctx.entries),
                "lines": len(lines),
                "total_debit": dstr(total_debit),
                "total_credit": dstr(total_credit),
                "difference": dstr(difference),
                "unbalanced_entries": unbalanced,
            },
            suggested_action=(
                "Review the unbalanced entries listed; they will be rejected by the balance rule."
                if unbalanced
                else "No action needed."
            ),
        )
    ]
