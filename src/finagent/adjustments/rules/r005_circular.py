"""R005: an entry that nets to zero on every account cannot change any balance.

Approving it is meaningless and usually signals a keying error (e.g. the same account on
both sides), so it is blocked (ASSUMPTIONS A10). All-zero entries are R006's concern.
"""

from __future__ import annotations

from finagent.adjustments.context import RuleContext, net_by_account
from finagent.domain.models import Finding, JournalEntry, Severity
from finagent.domain.money import ZERO, dstr

RULE_ID = "R005"
SEVERITY = Severity.BLOCK
TITLE = "Entry changes nothing"


def _label(code: str, ctx: RuleContext) -> str:
    acct = ctx.coa.get(code)
    return f"{code} {acct.name}" if acct is not None else code


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    if not any(ln.debit != ZERO or ln.credit != ZERO for ln in entry.lines):
        return []
    nets = net_by_account(entry.lines)
    if any(v != ZERO for v in nets.values()):
        return []
    labels = ", ".join(_label(c, ctx) for c in nets)
    if len(nets) == 1:
        message = f"The entry debits and credits the same account {labels}, so no balance changes."
    else:
        message = (
            f"After netting, every account in the entry ({labels}) moves by 0.00, "
            "so no balance changes."
        )
    return [
        Finding(
            rule_id=RULE_ID,
            severity=SEVERITY,
            title=TITLE,
            message=message,
            evidence={
                "per_account_net": {code: dstr(v) for code, v in nets.items()},
                "distinct_accounts": len(nets),
            },
            suggested_action=(
                "Ask the preparer which accounts were meant to move, then resubmit the entry."
            ),
            assumption="A10",
        )
    ]
