"""H-TB-03: a TB account missing from the chart of accounts cannot roll up into any subtotal, so
it is carried in an UNMAPPED bucket (A6) and must be mapped by a person, never guessed."""

from __future__ import annotations

from typing import Any

from finagent.domain.models import HealthFinding, HealthSeverity, TbRow
from finagent.domain.money import ZERO, dstr, fmt
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-TB-03"


def check(ctx: AuditContext) -> list[HealthFinding]:
    orphans: dict[str, list[TbRow]] = {}
    for row in ctx.tb_rows:
        if row.account_code not in ctx.coa:
            orphans.setdefault(row.account_code, []).append(row)
    if not orphans:
        return []

    items: list[dict[str, Any]] = []
    parts: list[str] = []
    for code in sorted(orphans):
        rows = orphans[code]
        debit = sum((r.debit for r in rows), ZERO)
        credit = sum((r.credit for r in rows), ZERO)
        name = rows[0].account_name
        items.append(
            {
                "account_code": code,
                "account_name": name,
                "debit": dstr(debit),
                "credit": dstr(credit),
                "rows": [r.row_index for r in rows],
            }
        )
        parts.append(f"{code} {name} (debit {fmt(debit)}, credit {fmt(credit)})")
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.HIGH,
            file="trial_balance.csv",
            title="Account not in COA (orphan)",
            message=(
                f"Not in the chart of accounts: {'; '.join(parts)}. Carried as an unmapped "
                "balance and excluded from every COA subtotal."
            ),
            evidence={"orphans": items},
            suggested_action=(
                "Map the account to an existing COA account or add it to the COA; until then it "
                "is shown as a reconciling line."
            ),
            policy_applied="orphan accounts held in UNMAPPED bucket",
            assumption="A6",
        )
    ]
