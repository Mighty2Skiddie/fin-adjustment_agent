"""R008: a posting that pushes an account to the wrong side of its normal balance is suspicious.

It is only a warning: sign always comes from debit - credit (ASSUMPTIONS A7);
`normal_balance` is only a hint.
"""

from __future__ import annotations

from finagent.adjustments.context import RuleContext, net_by_account
from finagent.domain.models import Finding, JournalEntry, NormalBalance, Severity
from finagent.domain.money import ZERO, dstr, fmt, q

RULE_ID = "R008"
SEVERITY = Severity.WARN
TITLE = "Balance would flip against its normal side"

GAIN_LOSS_PREFIXES = ("73", "74")
"""Gain/loss accounts legitimately swing either way (typed Expense, often Cr; H-TB-04, A7)."""


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for account, movement in net_by_account(entry.lines).items():
        if account.startswith(GAIN_LOSS_PREFIXES):
            continue
        acc = ctx.coa.get(account)
        if acc is None or acc.normal_balance is None:
            continue
        before = ctx.base_net(account)
        after = q(before + movement)
        if acc.normal_balance == NormalBalance.DEBIT:
            flipped = before >= ZERO and after < ZERO
        else:
            flipped = before <= ZERO and after > ZERO
        if not flipped:
            continue
        side = acc.normal_balance.value.lower()
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity=SEVERITY,
                title=TITLE,
                message=(
                    f"{account} {acc.name} normally carries a {side} balance; this entry "
                    f"moves it from {fmt(before)} to {fmt(after)} "
                    "(positive = debit, negative = credit)."
                ),
                evidence={
                    "account": account,
                    "before": dstr(before),
                    "after": dstr(after),
                    "normal_balance": acc.normal_balance.value,
                },
                suggested_action=(
                    "Check the entry is posted to the right account and side; if the reversal "
                    "is intended, note why before approving."
                ),
                assumption="A7",
            )
        )
    return findings
