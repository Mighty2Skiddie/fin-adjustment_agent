"""H-TB-06: an intercompany balance in a single-entity TB cannot be eliminated without the
counterparty's books, so it is flagged and left un-eliminated (ASSUMPTIONS A14)."""

from __future__ import annotations

from typing import Any

from finagent.domain.models import HealthFinding, HealthSeverity, TbRow
from finagent.domain.money import ZERO, dstr, fmt
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-TB-06"
KEYWORD = "intercompany"


def check(ctx: AuditContext) -> list[HealthFinding]:
    groups: dict[str, list[TbRow]] = {}
    for row in ctx.tb_rows:
        acc = ctx.coa.get(row.account_code)
        names = [row.account_name] + ([acc.name] if acc is not None else [])
        if any(KEYWORD in n.lower() for n in names):
            groups.setdefault(row.account_code, []).append(row)

    accounts: list[dict[str, Any]] = []
    parts: list[str] = []
    for code in sorted(groups):
        rows = groups[code]
        debit = sum((r.debit for r in rows), ZERO)
        credit = sum((r.credit for r in rows), ZERO)
        if debit - credit == ZERO:
            continue
        acc = ctx.coa.get(code)
        name = acc.name if acc is not None else rows[0].account_name
        accounts.append(
            {
                "account_code": code,
                "account_name": name,
                "debit": dstr(debit),
                "credit": dstr(credit),
            }
        )
        parts.append(f"{code} {name} (debit {fmt(debit)}, credit {fmt(credit)})")
    if not accounts:
        return []
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.MEDIUM,
            file="trial_balance.csv",
            title="Intercompany balance without counterparty",
            message=(
                f"Intercompany balance in a single-entity trial balance: {'; '.join(parts)}. "
                "It cannot be eliminated without the counterparty entity's books."
            ),
            evidence={"accounts": accounts},
            suggested_action=(
                "Obtain the counterparty entity's trial balance and agree the balance before "
                "any consolidation."
            ),
            policy_applied="intercompany balances not eliminated",
            assumption="A14",
        )
    ]
