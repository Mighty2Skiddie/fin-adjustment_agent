"""H-PP-04: retained earnings and reserves roll forward by profit, OCI and distributions;
with no dividend account in sight the movement cannot be explained from the bundle."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from finagent.domain.models import AccountType, HealthFinding, HealthSeverity, TbRow
from finagent.domain.money import ZERO, dstr, fmt
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-PP-04"
DISTRIBUTION_RE = re.compile(r"dividend|distribution", re.IGNORECASE)
CAPITAL_CF_CATEGORY = "financing"


def _credit_balances(rows: list[TbRow], currency: str) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for row in rows:
        if row.currency == currency:
            out[row.account_code] = out.get(row.account_code, ZERO) + row.credit - row.debit
    return out


def _is_reserve(ctx: AuditContext, code: str) -> bool:
    """Retained earnings and reserves are the equity accounts not classed as capital
    (financing) transactions, which leaves out share capital, APIC and treasury stock."""
    acc = ctx.coa.get(code)
    if acc is None or acc.account_type != AccountType.EQUITY:
        return False
    if ctx.coa.is_structural_header(code):
        return False
    return (acc.cf_category or "").strip().lower() != CAPITAL_CF_CATEGORY


def check(ctx: AuditContext) -> list[HealthFinding]:
    func = ctx.settings.functional_currency
    prior = _credit_balances(ctx.prior_rows, func)
    current = _credit_balances(ctx.tb_rows, func)

    movements: list[dict[str, Any]] = []
    parts: list[str] = []
    for code in sorted(set(prior) & set(current)):
        if not _is_reserve(ctx, code):
            continue
        delta = current[code] - prior[code]
        if delta == ZERO:
            continue
        movements.append(
            {
                "account_code": code,
                "prior": dstr(prior[code]),
                "current": dstr(current[code]),
                "delta": dstr(delta),
            }
        )
        parts.append(
            f"{code} {ctx.coa.name_of(code)} {fmt(prior[code])} to {fmt(current[code])} "
            f"(change {fmt(delta)})"
        )
    if not movements:
        return []

    named: dict[str, str] = {a.code: a.name for a in ctx.coa_accounts}
    for row in [*ctx.tb_rows, *ctx.prior_rows]:
        named.setdefault(row.account_code, row.account_name)
    distribution = sorted(code for code, name in named.items() if DISTRIBUTION_RE.search(name))

    if distribution:
        visibility = f"Possible distribution account(s): {', '.join(distribution)}."
    else:
        visibility = "No dividend or distribution account appears in the COA or either TB."
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.INFO,
            file="prior_period_tb.csv",
            title="Retained earnings movement with no dividend/distribution account visible",
            message=(
                f"Reserves moved between periods: {'; '.join(parts)}. {visibility} "
                "Whether opening equity can be walked depends on Clarifying Q2."
            ),
            evidence={"movements": movements, "distribution_accounts_found": distribution},
            suggested_action=(
                "Answer Clarifying Q2: confirm the prior TB is post-close and whether any "
                "dividends or distributions were declared in the period."
            ),
            assumption="A15",
        )
    ]
