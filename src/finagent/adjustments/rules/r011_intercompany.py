"""R011: an intercompany posting without a named counterparty cannot be matched or eliminated.

We hold a single-entity trial balance (ASSUMPTIONS A14), so the counterparty must at least be
named in the entry ("entity:<code>") for consolidation to follow it up.
"""

from __future__ import annotations

from finagent.adjustments.context import RuleContext, entry_text
from finagent.domain.models import Finding, JournalEntry, Severity

RULE_ID = "R011"
SEVERITY = Severity.WARN
TITLE = "Intercompany entry without counterparty"


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    ic_accounts: list[str] = []
    for ln in entry.lines:
        if "intercompany" in ctx.coa.name_of(ln.account).lower() and ln.account not in ic_accounts:
            ic_accounts.append(ln.account)
    if not ic_accounts or "entity:" in entry_text(entry).lower():
        return []
    labels = ", ".join(f"{a} {ctx.coa.name_of(a)}" for a in ic_accounts)
    return [
        Finding(
            rule_id=RULE_ID,
            severity=SEVERITY,
            title=TITLE,
            message=(
                f"This entry posts to {labels} but does not say which group company is on "
                "the other side, so the balance cannot be matched or eliminated."
            ),
            evidence={"ic_accounts": ic_accounts},
            suggested_action=(
                "Ask the preparer to name the counterparty (for example 'entity:UK-SUB') "
                "and resubmit."
            ),
            assumption="A14",
        )
    ]
