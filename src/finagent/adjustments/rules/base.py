"""Rule interface. One rule per module; each exposes `RULE_ID`, `SEVERITY`, `TITLE` and
`check(entry, ctx) -> list[Finding]`. Rules are pure: same entry + context, same findings."""

from __future__ import annotations

from typing import Protocol

from finagent.adjustments.context import RuleContext
from finagent.domain.models import Finding, JournalEntry, Severity


class Rule(Protocol):
    RULE_ID: str
    SEVERITY: Severity
    TITLE: str

    def check(self, entry: JournalEntry, ctx: RuleContext) -> list[Finding]: ...


__all__ = ["Rule", "RuleContext"]
