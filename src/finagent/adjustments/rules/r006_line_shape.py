"""R006: lines that are not a single positive debit or credit cannot be posted reliably.

Ambiguous lines (both sides, neither side, negative amounts) hide the preparer's intent,
so the entry is blocked rather than reinterpreted.
"""

from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.domain.models import Finding, JournalEntry, Severity
from finagent.domain.money import ZERO

RULE_ID = "R006"
SEVERITY = Severity.BLOCK
TITLE = "Malformed entry lines"

FEWER_THAN_TWO = "fewer than two lines"
BOTH_SIDES = "line has both a debit and a credit"
NEGATIVE = "negative amount"
NO_AMOUNT = "line has no amount"

_MESSAGES: dict[str, str] = {
    FEWER_THAN_TWO: "The entry has fewer than two lines, so it cannot record both sides.",
    BOTH_SIDES: "Line(s) {lines} carry both a debit and a credit; each line must be one side only.",
    NEGATIVE: "Line(s) {lines} contain a negative amount; use the opposite side instead.",
    NO_AMOUNT: "Line(s) {lines} have neither a debit nor a credit amount.",
}

_ACTIONS: dict[str, str] = {
    FEWER_THAN_TWO: "Ask the preparer to add the missing side of the entry and resubmit.",
    BOTH_SIDES: "Split each such line into a separate debit line and credit line.",
    NEGATIVE: "Replace negative amounts with positive amounts on the opposite side.",
    NO_AMOUNT: "Remove empty lines or enter the intended amount.",
}


def _finding(reason: str, indexes: list[int]) -> Finding:
    lines = ", ".join(str(i) for i in indexes)
    return Finding(
        rule_id=RULE_ID,
        severity=SEVERITY,
        title=TITLE,
        message=_MESSAGES[reason].format(lines=lines),
        evidence={"offending_line_indexes": indexes, "reason": reason},
        suggested_action=_ACTIONS[reason],
    )


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    if len(entry.lines) < 2:
        findings.append(_finding(FEWER_THAN_TWO, list(range(1, len(entry.lines) + 1))))
    both: list[int] = []
    negative: list[int] = []
    empty: list[int] = []
    for i, ln in enumerate(entry.lines, start=1):
        if ln.debit < ZERO or ln.credit < ZERO:
            negative.append(i)
        if ln.debit > ZERO and ln.credit > ZERO:
            both.append(i)
        if ln.debit == ZERO and ln.credit == ZERO:
            empty.append(i)
    for reason, idx in ((BOTH_SIDES, both), (NEGATIVE, negative), (NO_AMOUNT, empty)):
        if idx:
            findings.append(_finding(reason, idx))
    return findings
