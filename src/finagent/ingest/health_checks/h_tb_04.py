"""H-TB-04: a credit balance on a debit-normal account is not necessarily wrong (gain/loss
accounts typed Expense), but it proves sign must come from debit - credit, never type (A7)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from finagent.domain.models import HealthFinding, HealthSeverity, NormalBalance
from finagent.domain.money import ZERO, dstr, fmt
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-TB-04"


def check(ctx: AuditContext) -> list[HealthFinding]:
    # Raw nets: FX rates are positive, so translation never flips the sign being tested.
    nets: dict[str, Decimal] = {}
    for row in ctx.tb_rows:
        nets[row.account_code] = nets.get(row.account_code, ZERO) + row.debit - row.credit

    accounts: list[dict[str, Any]] = []
    listed: list[str] = []
    for code in sorted(nets):
        acc = ctx.coa.get(code)
        if acc is None or acc.normal_balance != NormalBalance.DEBIT or nets[code] >= ZERO:
            continue
        accounts.append(
            {
                "account_code": code,
                "net": dstr(nets[code]),
                "normal_balance": acc.normal_balance.value,
            }
        )
        listed.append(f"{code} {acc.name} (credit balance {fmt(-nets[code])})")
    if not accounts:
        return []
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.MEDIUM,
            file="trial_balance.csv",
            title="Credit balance on accounts whose COA normal balance is Debit",
            message=(
                f"These debit-normal accounts carry credit balances: {', '.join(listed)}. This "
                "can be legitimate (e.g. gains booked to Expense-typed accounts); amounts keep "
                "their debit-minus-credit sign."
            ),
            evidence={"accounts": accounts},
            suggested_action=(
                "Review whether each credit balance is expected (gain, reversal) or a mis-posting."
            ),
            policy_applied="sign = debit - credit; normal balance used for warnings only",
            assumption="A7",
        )
    ]
