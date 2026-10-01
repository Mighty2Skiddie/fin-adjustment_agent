"""H-FX-01: a balance-sheet amount in a currency with no balance-sheet rate cannot be translated
honestly; whichever fallback the policy picks changes the reported figure, so it is surfaced."""

from __future__ import annotations

from typing import Any

from finagent.domain.models import HealthFinding, HealthSeverity, TbRow
from finagent.domain.money import ZERO, dstr, fmt, q
from finagent.ingest.fx import FALLBACK_RATE_TYPE
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-FX-01"


def check(ctx: AuditContext) -> list[HealthFinding]:
    functional = ctx.settings.functional_currency
    rate_type = ctx.settings.fx.balance_sheet_rate
    policy = ctx.settings.fx.missing_rate_policy
    label = rate_type.replace("_", "-")

    by_currency: dict[str, list[TbRow]] = {}
    for row in ctx.tb_rows:
        if row.currency == functional or ctx.ratebook.has(row.currency, rate_type):
            continue
        by_currency.setdefault(row.currency, []).append(row)
    if not by_currency:
        return []

    missing: list[dict[str, Any]] = []
    parts: list[str] = []
    for currency, rows in sorted(by_currency.items()):
        local = sum((r.debit - r.credit for r in rows), ZERO)
        item: dict[str, Any] = {
            "currency": currency,
            "rate_type": rate_type,
            "affected_rows": [
                {
                    "account_code": r.account_code,
                    "row": r.row_index,
                    "local_amount": dstr(r.debit - r.credit),
                }
                for r in rows
            ],
        }
        alternatives: list[str] = []
        for fb_policy, fb_type in FALLBACK_RATE_TYPE.items():
            fb = ctx.ratebook.get(currency, fb_type)
            if fb is not None:
                translated = q(local * fb.rate)
                item[fb_policy] = dstr(translated)
                alternatives.append(f"{fmt(translated)} at the {fb_type.replace('_', '-')} rate")
        missing.append(item)
        accounts = ", ".join(sorted({r.account_code for r in rows}))
        options = "; ".join(alternatives) or "no fallback rate available"
        parts.append(
            f"There is no {label} rate for {currency}, which affects {accounts} "
            f"({currency} {fmt(local)}; {options})"
        )

    evidence: dict[str, Any] = {"missing": missing, "policy": policy}
    fb_type = FALLBACK_RATE_TYPE.get(policy)
    if fb_type is not None:
        ids = [f"{c}/{fb_type}" for c in sorted(by_currency)]
        evidence["fallback_rate_id"] = ids[0] if len(ids) == 1 else ids

    outcome = (
        "Posting is blocked until a rate is supplied"
        if fb_type is None
        else f"The {fb_type.replace('_', '-')} rate is used instead; every affected line is flagged"
    )
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.CRITICAL,
            file="fx_rates.csv",
            title="Missing period-end rate",
            message=f"{'. '.join(parts)}. {outcome}.",
            evidence=evidence,
            suggested_action=(
                f"Obtain the {label} rate from treasury and add it to the rate file; "
                "until then, confirm which fallback rate finance accepts."
            ),
            policy_applied=f"fx.missing_rate_policy={policy}",
            assumption="A4",
        )
    ]
