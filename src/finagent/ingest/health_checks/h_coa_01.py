"""H-COA-01: accounts whose cash-flow category is a `TBD` placeholder cannot be placed in the
cash-flow statement, so any movement on them would be classified by guesswork."""

from __future__ import annotations

from finagent.domain.models import HealthFinding, HealthSeverity
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-COA-01"


def check(ctx: AuditContext) -> list[HealthFinding]:
    hits = sorted(
        (a for a in ctx.coa_accounts if (a.cf_category or "").strip().upper() == "TBD"),
        key=lambda a: a.code,
    )
    if not hits:
        return []
    listed = ", ".join(f"{a.code} {a.name}" for a in hits)
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.HIGH,
            file="chart_of_accounts.csv",
            title="Ambiguous cash-flow category (TBD)",
            message=(
                f"{len(hits)} account(s) have a cash-flow category of 'TBD': {listed}. "
                "Their movements cannot be placed in operating, investing or financing activities."
            ),
            evidence={
                "accounts": [a.code for a in hits],
                "names": [a.name for a in hits],
            },
            suggested_action=(
                "Ask the controller to assign a cash-flow category (Operating, Investing or "
                "Financing) to each account before the cash-flow statement is prepared."
            ),
        )
    ]
