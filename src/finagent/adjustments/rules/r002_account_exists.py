"""R002: a line posting to an account the chart of accounts does not know cannot be reported.

We never auto-map: a missing code may be a typo or a genuinely new account, and only the
controller can tell. R002b lists the closest existing accounts as an informational aid; it has
no minimum score because it is a ranked list for a human, not a mapping decision.
"""

from __future__ import annotations

from finagent.adjustments.context import RuleContext, net_by_account
from finagent.domain.models import Finding, JeLine, JournalEntry, Severity
from finagent.domain.money import ZERO
from finagent.ingest import fuzzy

RULE_ID = "R002"
SEVERITY = Severity.ESCALATE
TITLE = "Account not in chart of accounts"

CANDIDATE_RULE_ID = "R002b"
CANDIDATE_SEVERITY = Severity.INFO
CANDIDATE_TITLE = "Closest existing accounts"
CANDIDATE_LIMIT = 3


def _would_create_noop(entry: JournalEntry, missing: str, candidate: str) -> bool:
    """A candidate already on another line that nets every account to zero after remapping
    would turn the entry into a circular no-op, so it must never be proposed as the fix."""
    if not any(ln.account == candidate for ln in entry.lines if ln.account != missing):
        return False
    remapped = [
        JeLine(
            account=candidate if ln.account == missing else ln.account,
            debit=ln.debit,
            credit=ln.credit,
            memo=ln.memo,
        )
        for ln in entry.lines
    ]
    return all(v == ZERO for v in net_by_account(remapped).values())


def _candidate_finding(entry: JournalEntry, missing: str, ctx: RuleContext) -> Finding:
    """The query uses the memo of the first line carrying the missing code plus the entry
    description, so the ranking is deterministic when a code appears on several lines."""
    first_line = next(ln for ln in entry.lines if ln.account == missing)
    query = f"{first_line.memo} {entry.description}"
    ranked = fuzzy.rank_candidates(query, ctx.coa, code_hint=missing, limit=CANDIDATE_LIMIT)
    candidates: list[dict[str, str | bool]] = [
        {
            "code": acc.code,
            "name": acc.name,
            "score": fuzzy.score_str(score),
            "would_create_noop": _would_create_noop(entry, missing, acc.code),
        }
        for acc, score in ranked
    ]
    noop = [f"{c['code']} {c['name']}" for c in candidates if c["would_create_noop"] is True]
    listed = ", ".join(f"{c['code']} {c['name']}" for c in candidates) or "none found"
    if noop:
        message = (
            f"Closest existing accounts to {missing}: {listed}. Remapping {missing} to "
            f"{', '.join(noop)} would cancel the entry, because that account is already on the "
            "other side (circular: the entry would move nothing)."
        )
        action = f"Add {missing} to the chart of accounts, or reject the entry; do not remap."
    else:
        message = (
            f"Closest existing accounts to {missing}: {listed}. "
            "These are suggestions only and have not been applied."
        )
        action = (
            f"Decide whether {missing} should be added to the chart of accounts or the line "
            "corrected to one of these accounts."
        )
    return Finding(
        rule_id=CANDIDATE_RULE_ID,
        severity=CANDIDATE_SEVERITY,
        title=CANDIDATE_TITLE,
        message=message,
        evidence={"missing_account": missing, "candidates": candidates},
        suggested_action=action,
        assumption="D7",
    )


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    missing: list[str] = []
    lines: list[int] = []
    for i, ln in enumerate(entry.lines, start=1):
        if ln.account not in ctx.coa:
            lines.append(i)
            if ln.account not in missing:
                missing.append(ln.account)
    if not missing:
        return []
    codes = ", ".join(missing)
    line_refs = ", ".join(str(n) for n in lines)
    findings = [
        Finding(
            rule_id=RULE_ID,
            severity=SEVERITY,
            title=TITLE,
            message=(
                f"{'Accounts' if len(missing) > 1 else 'Account'} {codes} "
                f"{'are' if len(missing) > 1 else 'is'} not in the chart of accounts "
                f"({'lines' if len(lines) > 1 else 'line'} {line_refs}), so the "
                "entry cannot be reported until the account is set up or the line is corrected."
            ),
            evidence={"missing_accounts": missing, "lines": lines},
            suggested_action=(
                f"Add {codes} to the chart of accounts under its parent range, or correct the "
                "account on the line. Accounts are never mapped automatically."
            ),
        )
    ]
    findings.extend(_candidate_finding(entry, code, ctx) for code in missing)
    return findings
