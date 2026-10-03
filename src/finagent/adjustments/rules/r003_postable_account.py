"""R003: header accounts only total their sub-accounts; an amount posted to one directly is
invisible in the detail and distorts roll-ups. Only accounts typed Header are blocked —
structural-but-postable parents such as 8000/3300 are not (ASSUMPTIONS A8).
"""

from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.domain.models import Finding, JournalEntry, Severity

RULE_ID = "R003"
SEVERITY = Severity.BLOCK
TITLE = "Posting to a header account"


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    headers: list[str] = []
    lines: list[int] = []
    for i, ln in enumerate(entry.lines, start=1):
        if ln.account in ctx.coa and not ctx.coa.is_postable(ln.account):
            lines.append(i)
            if ln.account not in headers:
                headers.append(ln.account)
    if not headers:
        return []
    named = ", ".join(f"{c} {ctx.coa.name_of(c)}" for c in headers)
    line_refs = ", ".join(str(n) for n in lines)
    line_word = "lines" if len(lines) > 1 else "line"
    verb = (
        "are header accounts that only total their"
        if len(headers) > 1
        else "is a header account that only totals its"
    )
    return [
        Finding(
            rule_id=RULE_ID,
            severity=SEVERITY,
            title=TITLE,
            message=(
                f"{named} {verb} sub-accounts ({line_word} {line_refs}); "
                "amounts cannot be posted to header accounts directly."
            ),
            evidence={"header_accounts": headers, "lines": lines},
            suggested_action="Repost the line to the appropriate sub-account and resubmit.",
            assumption="A8",
        )
    ]
