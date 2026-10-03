"""R010: the same lines submitted twice would double the adjustment.

Two entries with identical (account, debit, credit) lines are flagged for a human to confirm;
we cannot know whether a genuine repeat was intended.
"""

from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.domain.models import Finding, JournalEntry, Severity
from finagent.domain.money import dstr

RULE_ID = "R010"
SEVERITY = Severity.WARN
TITLE = "Possible duplicate entry"


def _signature(entry: JournalEntry) -> list[tuple[str, str, str]]:
    return sorted((ln.account, dstr(ln.debit), dstr(ln.credit)) for ln in entry.lines)


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    mine = _signature(entry)
    dupes = sorted(
        {other.id for other in ctx.batch if other.id != entry.id and _signature(other) == mine}
    )
    if not dupes:
        return []
    return [
        Finding(
            rule_id=RULE_ID,
            severity=SEVERITY,
            title=TITLE,
            message=(
                f"This entry has exactly the same accounts and amounts as {', '.join(dupes)}. "
                "Posting both would record the adjustment twice."
            ),
            evidence={"duplicate_of": dupes},
            suggested_action="Confirm with the preparer that both entries are intended.",
        )
    ]
