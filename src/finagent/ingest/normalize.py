"""Build the base ledger: translate -> sum per account with lineage -> mark unmapped -> plug.

Duplicates are *summed*, not dropped (bundle README convention, ASSUMPTIONS A5); every source
row stays in the lineage so the summation is auditable. A remaining imbalance is never silently
absorbed: it is posted to the configured translation-difference account with its own
`TRANSLATION_DIFF` lineage ref and raised as H-TB-01 (ASSUMPTIONS A3).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

from finagent.config import Settings
from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import (
    FxRate,
    HealthFinding,
    HealthSeverity,
    LineageKind,
    LineageRef,
    PostedLine,
    TbRow,
)
from finagent.domain.money import ZERO, dstr, fmt, fmt_signed, q
from finagent.ingest.fx import MissingRateError, RateBook, translate

VARIANT_LABELS: dict[str, str] = {
    "raw": "Raw amounts, no translation",
    "usd_only": "Functional-currency rows only",
    "pe_gbp_avg": "Period-end rates, missing rate -> period average",
    "pe_gbp_open": "Period-end rates, missing rate -> opening",
}
POLICY_TO_VARIANT = {"fallback_average": "pe_gbp_avg", "fallback_opening": "pe_gbp_open"}


def tb_totals(
    rows: Iterable[TbRow], rates: RateBook | None, rate_type: str, only_currency: str | None = None
) -> tuple[Decimal, Decimal]:
    """Σdebit, Σcredit; translated per row when a rate book is given."""
    d = c = ZERO
    for row in rows:
        if only_currency is not None and row.currency != only_currency:
            continue
        if rates is None:
            d += row.debit
            c += row.credit
        else:
            td, tc = translate(row, rates.rate_for(row.currency, rate_type))
            d += td
            c += tc
    return q(d), q(c)


def imbalance_variants(
    rows: list[TbRow], fx_rates: list[FxRate], functional_currency: str, rate_type: str
) -> dict[str, dict[str, str]]:
    """The TB balance under every FX policy: the imbalance depends on a human's choice."""
    out: dict[str, dict[str, str]] = {}

    def put(key: str, d: Decimal, c: Decimal) -> None:
        out[key] = {"debit": dstr(d), "credit": dstr(c), "delta": dstr(d - c)}

    put("raw", *tb_totals(rows, None, rate_type))
    put("usd_only", *tb_totals(rows, None, rate_type, only_currency=functional_currency))
    for policy, key in POLICY_TO_VARIANT.items():
        put(key, *tb_totals(rows, RateBook(fx_rates, policy, functional_currency), rate_type))
    return out


def materiality_tolerance(settings: Settings, total_debit: Decimal) -> Decimal:
    """The stricter of the absolute and relative tolerances (conservative; decision D9)."""
    rel = q(total_debit * settings.materiality.imbalance_tolerance_pct)
    return min(settings.materiality.imbalance_tolerance_abs, rel)


@dataclass
class _Acc:
    name: str
    debit: Decimal = ZERO
    credit: Decimal = ZERO
    lineage: list[LineageRef] = field(default_factory=list[LineageRef])


def build_base_ledger(
    tb_rows: list[TbRow], coa: CoaTree, ratebook: RateBook, settings: Settings
) -> tuple[list[PostedLine], list[HealthFinding]]:
    """Raises `MissingRateError` under the `block` policy: no rate, no ledger."""
    rate_type = settings.fx.balance_sheet_rate
    groups: dict[str, _Acc] = {}
    for row in tb_rows:
        rate = ratebook.rate_for(row.currency, rate_type)
        td, tc = translate(row, rate)
        g = groups.setdefault(row.account_code, _Acc(name=row.account_name))
        g.debit += td
        g.credit += tc
        g.lineage.append(
            LineageRef(
                kind=LineageKind.TB_ROW,
                ref=f"{row.source_file}#{row.row_index}",
                amount=td - tc,
                note=f"{row.currency} Dr {fmt(row.debit)} Cr {fmt(row.credit)}",
            )
        )
        fx_note = f"rate {rate.rate}"
        if rate.is_fallback:
            fx_note += f" (fallback: {row.currency}/{rate.requested_rate_type} missing)"
        g.lineage.append(LineageRef(kind=LineageKind.FX, ref=rate.id, note=fx_note))

    lines: dict[str, PostedLine] = {}
    for code, g in groups.items():
        acc = coa.get(code)
        lines[code] = PostedLine(
            account_code=code,
            account_name=acc.name if acc else g.name,
            debit=g.debit,
            credit=g.credit,
            net=g.debit - g.credit,
            mapped=acc is not None,
            lineage=g.lineage,
        )

    total_d = q(sum((ln.debit for ln in lines.values()), ZERO))
    total_c = q(sum((ln.credit for ln in lines.values()), ZERO))
    delta = total_d - total_c
    findings: list[HealthFinding] = []
    if delta != ZERO:
        plug_code = settings.fx.translation_difference_account
        plug_ref = LineageRef(
            kind=LineageKind.TRANSLATION_DIFF,
            ref=f"translation_difference:{plug_code}",
            amount=-delta,
            note="System line balancing the translated TB (ASSUMPTIONS A3)",
        )
        existing = lines.get(plug_code)
        plug_d = -delta if delta < ZERO else ZERO
        plug_c = delta if delta > ZERO else ZERO
        if existing is None:
            lines[plug_code] = PostedLine(
                account_code=plug_code,
                account_name=coa.name_of(plug_code) or "Translation difference",
                debit=plug_d,
                credit=plug_c,
                net=plug_d - plug_c,
                mapped=plug_code in coa,
                lineage=[plug_ref],
            )
        else:
            nd, nc = existing.debit + plug_d, existing.credit + plug_c
            lines[plug_code] = existing.model_copy(
                update={
                    "debit": nd,
                    "credit": nc,
                    "net": nd - nc,
                    "lineage": [*existing.lineage, plug_ref],
                }
            )
        findings.append(tb_imbalance_finding(tb_rows, ratebook, settings, total_d, total_c))
    return [lines[c] for c in sorted(lines)], findings


def tb_imbalance_finding(
    tb_rows: list[TbRow],
    ratebook: RateBook,
    settings: Settings,
    total_d: Decimal,
    total_c: Decimal,
) -> HealthFinding:
    delta = total_d - total_c
    tolerance = materiality_tolerance(settings, total_d)
    variants = imbalance_variants(
        tb_rows, ratebook.rates(), settings.functional_currency, settings.fx.balance_sheet_rate
    )
    above = abs(delta) > tolerance
    plug = settings.fx.translation_difference_account
    variant_text = "; ".join(f"{k} {fmt_signed(Decimal(v['delta']))}" for k, v in variants.items())
    return HealthFinding(
        id="H-TB-01",
        severity=HealthSeverity.CRITICAL if above else HealthSeverity.LOW,
        file="trial_balance.csv",
        title="TB does not balance; imbalance depends on FX policy",
        message=(
            f"After translation the trial balance is out by {fmt_signed(delta)} "
            f"(debits {fmt(total_d)}, credits {fmt(total_c)}). Under other FX policies: "
            f"{variant_text}. The difference is posted to {plug} as a flagged "
            "translation-difference line, never silently absorbed."
        ),
        evidence={
            **variants,
            "active_policy": settings.fx.missing_rate_policy,
            "active_delta": dstr(delta),
            "materiality_tolerance": dstr(tolerance),
            "above_materiality": "true" if above else "false",
            "translation_difference_account": plug,
        },
        suggested_action=(
            "Confirm the FX policy (Clarifying Q1) and investigate the source TB imbalance "
            "before relying on statements."
        ),
        policy_applied=f"fx.missing_rate_policy={settings.fx.missing_rate_policy}",
        assumption="A3",
    )


__all__ = [
    "MissingRateError",
    "VARIANT_LABELS",
    "build_base_ledger",
    "imbalance_variants",
    "materiality_tolerance",
    "tb_imbalance_finding",
    "tb_totals",
]
