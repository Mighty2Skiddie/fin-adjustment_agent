"""R007: a manual FX revaluation on top of system translation counts the same gain twice.

When the system translates foreign-currency balances at the period-end rate itself, a manual
reval entry duplicates it. R007b also checks the booked amount against both rate bases
(ASSUMPTIONS D6).
"""

from __future__ import annotations

from decimal import Decimal

from finagent.adjustments.context import RuleContext, net_by_account
from finagent.domain.models import Finding, JournalEntry, Severity
from finagent.domain.money import ZERO, dstr, fmt, q

RULE_ID = "R007"
SEVERITY = Severity.ESCALATE
TITLE = "FX revaluation would be double-counted"

SECONDARY_RULE_ID = "R007b"
SECONDARY_SEVERITY = Severity.WARN
SECONDARY_TITLE = "Revaluation amount does not match either rate basis"

FX_ACCOUNT_NAME_PREFIX = "FX Gain/Loss"
"""FX P&L accounts are identified by COA name so a renumbered chart still matches."""


def fx_accounts(ctx: RuleContext) -> set[str]:
    return {a.code for a in ctx.coa.accounts() if a.name.startswith(FX_ACCOUNT_NAME_PREFIX)}


def _label(code: str, ctx: RuleContext) -> str:
    name = ctx.coa.name_of(code)
    return f"{code} {name}" if name else code


def _expected(account: str, ctx: RuleContext) -> tuple[Decimal, Decimal, list[str]]:
    """Expected reval on the average and opening bases, plus currencies that cannot be valued."""
    functional = ctx.settings.functional_currency
    avg_basis = ZERO
    opening_basis = ZERO
    excluded: set[str] = set()
    for row in ctx.tb_rows:
        if row.account_code != account or row.currency == functional:
            continue
        pe = ctx.ratebook.get(row.currency, "period_end")
        avg = ctx.ratebook.get(row.currency, "period_average")
        opening = ctx.ratebook.get(row.currency, "opening")
        if pe is None or avg is None or opening is None:
            excluded.add(row.currency)
            continue
        local = row.debit - row.credit
        avg_basis = q(avg_basis + q(local * (pe.rate - avg.rate)))
        opening_basis = q(opening_basis + q(local * (pe.rate - opening.rate)))
    return avg_basis, opening_basis, sorted(excluded)


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    if ctx.settings.fx.translation_mode != "system":
        return []
    nets = net_by_account(entry.lines)
    fx_codes = fx_accounts(ctx)
    touched_fx = [acc for acc in nets if acc in fx_codes]
    if not touched_fx:
        return []
    fx_account = touched_fx[0]
    functional = ctx.settings.functional_currency
    findings: list[Finding] = []
    for account, net in nets.items():
        if account in fx_codes:
            continue
        currencies = [c for c in ctx.currencies_of(account) if c != functional]
        if not currencies:
            continue
        booked = abs(net)
        avg_basis, opening_basis, excluded = _expected(account, ctx)
        evidence: dict[str, str | list[str]] = {
            "fx_account": fx_account,
            "revalued_account": account,
            "currencies": currencies,
            "booked": dstr(booked),
            "expected_avg_basis": dstr(avg_basis),
            "expected_opening_basis": dstr(opening_basis),
            "excluded_currencies": excluded,
        }
        ccy_text = ", ".join(currencies)
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity=SEVERITY,
                title=TITLE,
                message=(
                    f"The system already translates the {ccy_text} balances of "
                    f"{_label(account, ctx)} at the period-end rate (or the configured "
                    "fallback where one is missing), so this "
                    f"{fmt(booked)} entry to {_label(fx_account, ctx)} would count the same "
                    "FX gain or loss twice."
                ),
                evidence=dict(evidence),
                suggested_action=(
                    "Confirm with finance who owns FX revaluation (Clarifying Q1) before "
                    "approving; if the system translation stands, reject this entry."
                ),
            )
        )
        if booked not in (avg_basis, opening_basis):
            excluded_note = (
                f" Excluded from the expected amounts ({', '.join(excluded)}): the rate table "
                "lacks a period-end, average or opening rate needed to value it."
                if excluded
                else ""
            )
            findings.append(
                Finding(
                    rule_id=SECONDARY_RULE_ID,
                    severity=SECONDARY_SEVERITY,
                    title=SECONDARY_TITLE,
                    message=(
                        f"Booked {fmt(booked)} matches neither {fmt(avg_basis)} "
                        f"(period-end vs average rate) nor {fmt(opening_basis)} "
                        f"(period-end vs opening rate).{excluded_note}"
                    ),
                    evidence=dict(evidence),
                    suggested_action=(
                        "Ask the preparer for the revaluation workings and which rate basis "
                        "they used."
                    ),
                    assumption="D6",
                )
            )
    return findings
