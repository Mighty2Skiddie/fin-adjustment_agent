"""H-PP-02: a prior-period account missing from the current COA breaks comparatives; a
rename is likely, but the mapping is a judgement a human must approve (ASSUMPTIONS A16)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from finagent.domain.models import HealthFinding, HealthSeverity
from finagent.domain.money import ZERO, dstr, fmt
from finagent.ingest.fuzzy import rank_candidates, score_str
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-PP-02"


def check(ctx: AuditContext) -> list[HealthFinding]:
    names: dict[str, str] = {}
    amounts: dict[str, Decimal] = {}
    for row in ctx.prior_rows:
        if row.account_code in ctx.coa:
            continue
        names.setdefault(row.account_code, row.account_name)
        amounts[row.account_code] = amounts.get(row.account_code, ZERO) + row.debit - row.credit
    if not names:
        return []

    orphans: list[dict[str, Any]] = []
    parts: list[str] = []
    for code in sorted(names):
        ranked = rank_candidates(names[code], ctx.coa, code_hint=code)
        orphans.append(
            {
                "account_code": code,
                "account_name": names[code],
                "amount": dstr(amounts[code]),
                "candidates": [
                    {"code": acc.code, "name": acc.name, "score": score_str(score)}
                    for acc, score in ranked
                ],
            }
        )
        text = f"{code} {names[code]} ({fmt(amounts[code])})"
        if ranked:
            text += f", closest current account {ranked[0][0].code} {ranked[0][0].name}"
        parts.append(text)
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.HIGH,
            file="prior_period_tb.csv",
            title="Account not in COA (renamed)",
            message=(
                f"The prior-period TB uses {len(orphans)} account(s) not in the current chart "
                f"of accounts: {'; '.join(parts)}. The account was probably renamed."
            ),
            evidence={"orphans": orphans},
            suggested_action=(
                "Review the proposed mapping; it requires human approval before prior-period "
                "comparatives are restated to the current account."
            ),
            assumption="A16",
        )
    ]
