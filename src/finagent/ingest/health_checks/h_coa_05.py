"""H-COA-05: an account that is not typed Header but has children both aggregates and could
be posted to, so a direct posting would be ambiguous against its subtotal."""

from __future__ import annotations

from finagent.domain.models import AccountType, HealthFinding, HealthSeverity
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-COA-05"


def check(ctx: AuditContext) -> list[HealthFinding]:
    hits = sorted(
        (
            a
            for a in ctx.coa_accounts
            if a.account_type != AccountType.HEADER and ctx.coa.has_children(a.code)
        ),
        key=lambda a: a.code,
    )
    if not hits:
        return []
    children = {a.code: sorted(c.code for c in ctx.coa.children(a.code)) for a in hits}
    listed = "; ".join(f"{a.code} {a.name} (children {', '.join(children[a.code])})" for a in hits)
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.MEDIUM,
            file="chart_of_accounts.csv",
            title="Non-header accounts that have children",
            message=(
                f"{len(hits)} account(s) have sub-accounts but are not marked as headers: "
                f"{listed}. They are treated as subtotals, so direct postings to them "
                "are ambiguous."
            ),
            evidence={"accounts": [a.code for a in hits], "children": children},
            suggested_action=(
                "Mark these accounts as headers in the chart of accounts, or move their "
                "sub-accounts; do not post directly to them."
            ),
            policy_applied="Accounts with children are treated as structural subtotals.",
            assumption="A8",
        )
    ]
