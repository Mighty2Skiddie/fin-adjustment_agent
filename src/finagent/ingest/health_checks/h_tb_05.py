"""H-TB-05: the brief described roughly 80 accounts; a materially different count suggests the
file is a different extract than the one described, which a reviewer should know."""

from __future__ import annotations

from decimal import Decimal

from finagent.domain.models import HealthFinding, HealthSeverity
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-TB-05"

BRIEF_SAYS = "~80 accounts"
BRIEF_EXPECTED_ACCOUNTS = 80
# "~80" tolerates small drift; beyond 10% the file is materially different from the brief.
TOLERANCE_PCT = Decimal("0.10")


def check(ctx: AuditContext) -> list[HealthFinding]:
    rows = len(ctx.tb_rows)
    unique_codes = len({r.account_code for r in ctx.tb_rows})
    if abs(unique_codes - BRIEF_EXPECTED_ACCOUNTS) <= TOLERANCE_PCT * BRIEF_EXPECTED_ACCOUNTS:
        return []
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.INFO,
            file="trial_balance.csv",
            title="Row count differs from brief",
            message=(
                f'The brief says "{BRIEF_SAYS}" but the trial balance has {rows} rows covering '
                f"{unique_codes} unique account codes."
            ),
            evidence={"rows": rows, "unique_codes": unique_codes, "brief_says": BRIEF_SAYS},
            suggested_action="Confirm this is the complete trial balance extract for the period.",
        )
    ]
