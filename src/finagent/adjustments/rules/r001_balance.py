"""R001: an entry whose debits and credits differ cannot be posted.

We cannot tell which side is right, so the entry is blocked and the preparer decides
(ASSUMPTIONS A11: rejected entries are edited and resubmitted, never approved).
"""

from __future__ import annotations

from finagent.adjustments.context import RuleContext, total_credit, total_debit
from finagent.domain.models import Finding, JournalEntry, Severity
from finagent.domain.money import dstr, fmt

RULE_ID = "R001"
SEVERITY = Severity.BLOCK
TITLE = "Entry does not balance"


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    debit = total_debit(entry.lines)
    credit = total_credit(entry.lines)
    if debit == credit:
        return []
    diff = abs(debit - credit)
    return [
        Finding(
            rule_id=RULE_ID,
            severity=SEVERITY,
            title=TITLE,
            message=(
                f"Debits total {fmt(debit)} but credits total {fmt(credit)}, "
                f"a difference of {fmt(diff)}. We cannot tell which side is correct."
            ),
            evidence={
                "total_debit": dstr(debit),
                "total_credit": dstr(credit),
                "difference": dstr(diff),
            },
            suggested_action="Ask the preparer which amount is right, then resubmit the entry.",
            assumption="A11",
        )
    ]
