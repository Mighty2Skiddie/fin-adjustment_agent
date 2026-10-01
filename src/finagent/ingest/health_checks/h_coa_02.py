"""H-COA-02: a Header account with no children is an empty grouping; it suggests a missing
sub-ledger mapping and always reports a zero subtotal."""

from __future__ import annotations

from finagent.domain.models import AccountType, HealthFinding, HealthSeverity
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-COA-02"


def check(ctx: AuditContext) -> list[HealthFinding]:
    hits = sorted(
        (
            a
            for a in ctx.coa_accounts
            if a.account_type == AccountType.HEADER and not ctx.coa.has_children(a.code)
        ),
        key=lambda a: a.code,
    )
    if not hits:
        return []
    listed = ", ".join(f"{a.code} {a.name}" for a in hits)
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.MEDIUM,
            file="chart_of_accounts.csv",
            title="Header with no children",
            message=(
                f"{len(hits)} header account(s) have no accounts beneath them: {listed}. "
                "They will always show a zero subtotal."
            ),
            evidence={"accounts": [a.code for a in hits]},
            suggested_action=(
                "Confirm whether posting accounts are missing under these headers, or remove "
                "the unused headers from the chart of accounts."
            ),
        )
    ]
