"""H-TB-01: the TB does not balance, and by how much depends on the FX policy."""

from __future__ import annotations

from finagent.domain.models import HealthFinding
from finagent.ingest.fx import MissingRateError
from finagent.ingest.health_checks.base import AuditContext
from finagent.ingest.normalize import tb_imbalance_finding, tb_totals

CHECK_ID = "H-TB-01"


def check(ctx: AuditContext) -> list[HealthFinding]:
    try:
        d, c = tb_totals(ctx.tb_rows, ctx.ratebook, ctx.settings.fx.balance_sheet_rate)
    except MissingRateError:
        # `block` policy: report the variants against raw totals; translation is not possible.
        d, c = tb_totals(ctx.tb_rows, None, ctx.settings.fx.balance_sheet_rate)
    if d == c:
        return []
    return [tb_imbalance_finding(ctx.tb_rows, ctx.ratebook, ctx.settings, d, c)]
