"""H-TB-02: the same account repeated in the same currency is summed (A5), but a repeat in one
currency is the classic shape of a double-posting, so it is surfaced rather than merged quietly."""

from __future__ import annotations

from typing import Any

from finagent.domain.models import HealthFinding, HealthSeverity, TbRow
from finagent.domain.money import ZERO, dstr, fmt
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-TB-02"


def check(ctx: AuditContext) -> list[HealthFinding]:
    groups: dict[tuple[str, str], list[TbRow]] = {}
    for row in ctx.tb_rows:
        groups.setdefault((row.account_code, row.currency), []).append(row)

    duplicates: list[dict[str, Any]] = []
    parts: list[str] = []
    for (code, currency), rows in sorted(groups.items()):
        if len(rows) < 2:
            continue
        amounts = [abs(r.debit - r.credit) for r in rows]
        summed = abs(sum((r.debit - r.credit for r in rows), ZERO))
        duplicates.append(
            {
                "account_code": code,
                "currency": currency,
                "rows": [r.row_index for r in rows],
                "amounts": [dstr(a) for a in amounts],
                "summed": dstr(summed),
            }
        )
        parts.append(
            f"{code} {currency} appears {len(rows)} times "
            f"({', '.join(fmt(a) for a in amounts)}), summed to {fmt(summed)}"
        )
    if not duplicates:
        return []
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.HIGH,
            file="trial_balance.csv",
            title="Duplicate account rows in the same currency",
            message=(
                f"{'; '.join(parts)}. The rows are added together as the TB convention requires, "
                "but a repeated row in one currency may be a double-posting."
            ),
            evidence={"duplicates": duplicates},
            suggested_action=(
                "Confirm with the TB preparer whether each repeated row is a separate balance "
                "or a double-posting; if duplicated, the account is overstated by the extra row."
            ),
            policy_applied="duplicate same-currency rows are summed",
            assumption="A5",
        )
    ]
