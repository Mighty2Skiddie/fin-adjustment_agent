"""R012: an unmapped bucket such as 9999 Suspense has no home on the statements, so adding to
it grows a balance nobody has explained. Accounts absent from the ledger entirely are R002's
concern, not this rule's.
"""

from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.domain.models import Finding, JournalEntry, Severity

RULE_ID = "R012"
SEVERITY = Severity.ESCALATE
TITLE = "Posts to an unmapped account"


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    accounts: list[str] = []
    lines: list[int] = []
    for i, ln in enumerate(entry.lines, start=1):
        posted = ctx.base_ledger.get(ln.account)
        if posted is not None and not posted.mapped:
            lines.append(i)
            if ln.account not in accounts:
                accounts.append(ln.account)
    if not accounts:
        return []
    named = ", ".join(f"{c} {ctx.base_ledger[c].account_name}".rstrip() for c in accounts)
    line_refs = ", ".join(str(n) for n in lines)
    line_word = "lines" if len(lines) > 1 else "line"
    return [
        Finding(
            rule_id=RULE_ID,
            severity=SEVERITY,
            title=TITLE,
            message=(
                f"The entry posts to {named} ({line_word} {line_refs}), which is not mapped to "
                "any financial statement line."
            ),
            evidence={"accounts": accounts, "lines": lines},
            suggested_action=(
                "Post to the correct mapped account instead, or have the controller approve "
                "the use of the unmapped account with a written explanation."
            ),
        )
    ]
