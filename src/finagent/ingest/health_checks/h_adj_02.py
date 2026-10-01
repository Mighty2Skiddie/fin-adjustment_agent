"""H-ADJ-02: an adjustment posting to an account the chart does not contain has nowhere to land;
it must be caught at batch level before anyone guesses a mapping."""

from __future__ import annotations

from finagent.domain.models import HealthFinding, HealthSeverity
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-ADJ-02"


def check(ctx: AuditContext) -> list[HealthFinding]:
    unknown: dict[str, list[str]] = {}
    for e in ctx.entries:
        for ln in e.lines:
            if ln.account not in ctx.coa:
                ids = unknown.setdefault(ln.account, [])
                if e.id not in ids:
                    ids.append(e.id)
    if not unknown:
        return []
    accounts = sorted(unknown)
    entries = sorted({eid for ids in unknown.values() for eid in ids})
    detail = "; ".join(f"{a} (used by {', '.join(unknown[a])})" for a in accounts)
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.MEDIUM,
            file="manual_adjustments.json",
            title="Batch references account not in COA",
            message=(
                f"The batch posts to accounts that are not in the chart of accounts: {detail}. "
                "These lines cannot be posted as written."
            ),
            evidence={"accounts": accounts, "entries": entries},
            suggested_action=(
                "Either add the account to the chart of accounts under the right parent, "
                "or correct the entry to an existing account and resubmit."
            ),
        )
    ]
