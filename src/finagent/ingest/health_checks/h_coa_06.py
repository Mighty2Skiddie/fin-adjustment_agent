"""H-COA-06: contra accounts carry a normal balance opposite to their type's natural side;
correct, but any logic that signs by account type would misstate them."""

from __future__ import annotations

from finagent.domain.models import AccountType, HealthFinding, HealthSeverity, NormalBalance
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-COA-06"

_NATURAL_SIDE: dict[AccountType, NormalBalance] = {
    AccountType.ASSET: NormalBalance.DEBIT,
    AccountType.EXPENSE: NormalBalance.DEBIT,
    AccountType.LIABILITY: NormalBalance.CREDIT,
    AccountType.EQUITY: NormalBalance.CREDIT,
    AccountType.REVENUE: NormalBalance.CREDIT,
}


def check(ctx: AuditContext) -> list[HealthFinding]:
    details: list[dict[str, str]] = []
    for a in sorted(ctx.coa_accounts, key=lambda acc: acc.code):
        natural = _NATURAL_SIDE.get(a.account_type)
        if natural is None or a.normal_balance is None or a.normal_balance == natural:
            continue
        details.append(
            {
                "code": a.code,
                "account_type": a.account_type.value,
                "normal_balance": a.normal_balance.value,
            }
        )
    if not details:
        return []
    listed = ", ".join(f"{d['code']} ({d['account_type']}/{d['normal_balance']})" for d in details)
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.INFO,
            file="chart_of_accounts.csv",
            title="Contra accounts with reversed normal balance (correct, but must be handled)",
            message=(
                f"{len(details)} contra account(s) have a normal balance opposite to their "
                f"account type: {listed}. Balances are signed by debit and credit, so they are "
                "handled correctly."
            ),
            evidence={"accounts": [d["code"] for d in details], "details": details},
            suggested_action=(
                "No change needed; reviewers should expect these accounts to carry the opposite "
                "sign to their category."
            ),
            policy_applied="Sign is always debit minus credit; account type drives warnings only.",
            assumption="A7",
        )
    ]
