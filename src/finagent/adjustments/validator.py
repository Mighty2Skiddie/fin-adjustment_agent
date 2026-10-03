"""Run every deterministic rule against one entry."""

from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import ALL_RULES
from finagent.domain.models import Finding, JournalEntry


def run_rules(entry: JournalEntry, ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rule in ALL_RULES:
        findings.extend(rule.check(entry, ctx))
    return findings
