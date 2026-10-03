"""R009: an adjustment that moves a large share of an account's existing balance deserves a look.

It is a review aid, never a blocker (ASSUMPTIONS A13, decision D4): measured per account on the
entry's net movement, so lines that cancel within the entry do not count.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from finagent.adjustments.context import RuleContext, net_by_account
from finagent.domain.models import Finding, JournalEntry, Severity
from finagent.domain.money import ZERO, dstr, fmt

RULE_ID = "R009"
SEVERITY = Severity.INFO
TITLE = "Large relative to the account balance"

_PCT = Decimal("0.0001")


def _label(code: str, ctx: RuleContext) -> str:
    name = ctx.coa.name_of(code)
    return f"{code} {name}" if name else code


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    thresholds = ctx.settings.thresholds
    findings: list[Finding] = []
    for account, net in net_by_account(entry.lines).items():
        if account not in ctx.base_ledger:
            continue
        amount = abs(net)
        base = abs(ctx.base_net(account))
        if amount == ZERO or base == ZERO:
            continue
        pct = (amount / base).quantize(_PCT, rounding=ROUND_HALF_UP)
        ratio = amount / base
        if ratio >= thresholds.magnitude_warn_pct:
            severity, threshold = Severity.WARN, thresholds.magnitude_warn_pct
        elif ratio >= thresholds.magnitude_info_pct:
            severity, threshold = Severity.INFO, thresholds.magnitude_info_pct
        else:
            continue
        share = (pct * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity=severity,
                title=TITLE,
                message=(
                    f"This entry moves {fmt(amount)} on {_label(account, ctx)}, which is "
                    f"{share}% of its current balance of {fmt(base)}."
                ),
                evidence={
                    "account": account,
                    "amount": dstr(amount),
                    "base_balance": dstr(base),
                    "pct": str(pct),
                    "threshold": str(threshold),
                },
                suggested_action=(
                    "Confirm the amount with the preparer and check the supporting schedule."
                ),
                assumption="A13",
            )
        )
    return findings
