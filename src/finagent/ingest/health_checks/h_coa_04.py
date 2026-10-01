"""H-COA-04: balance-sheet posting accounts without a cash-flow category fall out of the
indirect cash-flow bridge unless they are derived lines (e.g. retained earnings, OCI)."""

from __future__ import annotations

from finagent.domain.models import AccountType, HealthFinding, HealthSeverity, Statement
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-COA-04"


def check(ctx: AuditContext) -> list[HealthFinding]:
    hits = sorted(
        (
            a
            for a in ctx.coa_accounts
            if a.statement == Statement.BS
            and a.account_type != AccountType.HEADER
            and not (a.cf_category or "").strip()
        ),
        key=lambda a: a.code,
    )
    if not hits:
        return []
    listed = ", ".join(f"{a.code} {a.name}" for a in hits)
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.LOW,
            file="chart_of_accounts.csv",
            title="BS posting accounts with no cf_category",
            message=(
                f"{len(hits)} balance-sheet account(s) have no cash-flow category: {listed}. "
                "This is defensible for derived lines such as retained earnings and OCI."
            ),
            evidence={"accounts": [a.code for a in hits]},
            suggested_action=(
                "Confirm these are derived balances (from profit or translation) and not cash "
                "movements; otherwise assign a cash-flow category."
            ),
        )
    ]
