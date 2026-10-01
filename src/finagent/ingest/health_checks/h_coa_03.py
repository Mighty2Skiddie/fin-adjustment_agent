"""H-COA-03: an account without a normal balance cannot be checked for abnormal-sign
balances, so sign warnings silently skip it."""

from __future__ import annotations

from finagent.domain.models import HealthFinding, HealthSeverity
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-COA-03"


def check(ctx: AuditContext) -> list[HealthFinding]:
    hits = sorted((a for a in ctx.coa_accounts if a.normal_balance is None), key=lambda a: a.code)
    if not hits:
        return []
    listed = ", ".join(f"{a.code} {a.name}" for a in hits)
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.MEDIUM,
            file="chart_of_accounts.csv",
            title="Missing normal_balance",
            message=(
                f"{len(hits)} account(s) have no normal balance (Debit or Credit): {listed}. "
                "Unusual-sign warnings cannot be raised for them."
            ),
            evidence={"accounts": [a.code for a in hits]},
            suggested_action=(
                "Set the normal balance for these accounts. Amounts are unaffected, because "
                "balances are always computed as debit minus credit."
            ),
            assumption="A7",
        )
    ]
