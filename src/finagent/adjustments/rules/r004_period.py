"""R004: an entry dated outside the reporting period belongs to a different close.

Posting it here would misstate this period, so it is blocked (ASSUMPTIONS A9). A date we
cannot read is flagged rather than guessed at.
"""

from __future__ import annotations

from datetime import date

from finagent.adjustments.context import RuleContext
from finagent.domain.models import Finding, JournalEntry, Severity

RULE_ID = "R004"
SEVERITY = Severity.BLOCK
TITLE = "Entry dated outside the period"
UNPARSABLE_TITLE = "Entry date could not be read"


def _parse(text: str) -> date | None:
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def check(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    start = ctx.settings.period.start
    end = ctx.settings.period.end
    evidence: dict[str, object] = {"date": entry.date, "period_start": start, "period_end": end}
    entry_date = _parse(entry.date)
    if entry_date is None:
        return [
            Finding(
                rule_id=RULE_ID,
                severity=Severity.WARN,
                title=UNPARSABLE_TITLE,
                message=(
                    f"The entry date '{entry.date}' is not a recognisable date (expected "
                    f"YYYY-MM-DD), so we cannot confirm it falls between {start} and {end}."
                ),
                evidence=evidence,
                suggested_action="Ask the preparer to correct the date to YYYY-MM-DD format.",
                assumption="A9",
            )
        ]
    if date.fromisoformat(start) <= entry_date <= date.fromisoformat(end):
        return []
    return [
        Finding(
            rule_id=RULE_ID,
            severity=SEVERITY,
            title=TITLE,
            message=(
                f"The entry is dated {entry_date.isoformat()}, outside the period "
                f"{start} to {end}. Out-of-period postings need a separate workflow."
            ),
            evidence=evidence,
            suggested_action=(
                "Confirm the correct date; if it belongs to another period, post it there."
            ),
            assumption="A9",
        )
    ]
