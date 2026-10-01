"""H-PP-03: a closed prior-period TB holds balance-sheet accounts only; a P&L balance means
the prior year was not closed to retained earnings, or the file is not what it claims."""

from __future__ import annotations

from finagent.domain.models import HealthFinding, HealthSeverity, Statement
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-PP-03"


def check(ctx: AuditContext) -> list[HealthFinding]:
    pl_prefixes = {r.code[:1] for r in ctx.coa.roots() if r.statement == Statement.PL}
    hits: set[str] = set()
    for row in ctx.prior_rows:
        acc = ctx.coa.get(row.account_code)
        if acc is not None:
            if acc.statement == Statement.PL:
                hits.add(row.account_code)
        elif row.account_code[:1] in pl_prefixes:
            hits.add(row.account_code)
    if not hits:
        return []
    codes = sorted(hits)
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.MEDIUM,
            file="prior_period_tb.csv",
            title="P&L account present in a balance-sheet-only prior TB",
            message=(
                "The prior-period TB should contain balance-sheet accounts only, but holds "
                f"P&L account(s) {', '.join(codes)}. The prior year may not have been closed "
                "to retained earnings."
            ),
            evidence={"accounts": codes},
            suggested_action=(
                "Confirm with the preparer whether the prior TB is post-close; if not, close "
                "the P&L balances to retained earnings before using it for opening balances."
            ),
            assumption="A15",
        )
    ]
