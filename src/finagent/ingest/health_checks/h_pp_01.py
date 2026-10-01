"""H-PP-01: an unbalanced prior-period TB cannot supply opening balances, so any SOCIE or
cash-flow walk built from it would inherit the imbalance (ASSUMPTIONS A15)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from finagent.domain.models import HealthFinding, HealthSeverity
from finagent.domain.money import ZERO, dstr, fmt, fmt_signed
from finagent.ingest.fx import MissingRateError
from finagent.ingest.health_checks.base import AuditContext
from finagent.ingest.normalize import tb_totals

CHECK_ID = "H-PP-01"
OPENING_RATE = "opening"


def _variant(d: Decimal, c: Decimal) -> dict[str, str]:
    return {"debit": dstr(d), "credit": dstr(c), "delta": dstr(d - c)}


def check(ctx: AuditContext) -> list[HealthFinding]:
    rows = ctx.prior_rows
    if not rows:
        return []
    func = ctx.settings.functional_currency
    raw_d, raw_c = tb_totals(rows, None, OPENING_RATE)
    func_d, func_c = tb_totals(rows, None, OPENING_RATE, only_currency=func)
    open_totals: tuple[Decimal, Decimal] | None
    try:
        open_totals = tb_totals(rows, ctx.ratebook, OPENING_RATE)
    except MissingRateError:
        open_totals = None

    deltas = [raw_d - raw_c, func_d - func_c]
    if open_totals is not None:
        deltas.append(open_totals[0] - open_totals[1])
    if all(d == ZERO for d in deltas):
        return []

    evidence: dict[str, Any] = {
        "raw": _variant(raw_d, raw_c),
        "usd_only": _variant(func_d, func_c),
    }
    opening_text = "translation at opening rates is not possible because a rate is missing"
    if open_totals is not None:
        evidence["opening"] = _variant(*open_totals)
        opening_text = (
            f"translated at opening rates, debits {fmt(open_totals[0])} and difference "
            f"{fmt_signed(open_totals[0] - open_totals[1])}"
        )
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.HIGH,
            file="prior_period_tb.csv",
            title="Prior TB does not balance",
            message=(
                f"The prior-period trial balance does not balance: debits {fmt(raw_d)} vs "
                f"credits {fmt(raw_c)} (difference {fmt_signed(raw_d - raw_c)}); {func} rows "
                f"only {fmt_signed(func_d - func_c)}; {opening_text}. Opening balances taken "
                "from it are unreliable for the equity and cash-flow walks."
            ),
            evidence=evidence,
            suggested_action=(
                "Obtain a balanced, post-close prior-period TB before using it for opening "
                "balances; use it for comparatives only until then."
            ),
            policy_applied="prior TB used for comparatives only",
            assumption="A15",
        )
    ]
