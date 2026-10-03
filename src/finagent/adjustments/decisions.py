"""Severity -> decision. The single place where findings become a decision.

BLOCK -> REJECTED, else ESCALATE -> QUARANTINED, else ACCEPTED. LLM findings (R013) go
through the same function, and the Intent Reviewer can only *add* findings (engineering rule 3),
so a model can raise a decision but never lower one.
"""

from __future__ import annotations

from collections.abc import Iterable

from finagent.domain.models import SEVERITY_RANK, Decision, Finding, Severity


def max_severity(findings: Iterable[Finding]) -> Severity | None:
    worst: Severity | None = None
    for f in findings:
        if worst is None or SEVERITY_RANK[f.severity] > SEVERITY_RANK[worst]:
            worst = f.severity
    return worst


def decide(findings: Iterable[Finding]) -> Decision:
    worst = max_severity(findings)
    if worst == Severity.BLOCK:
        return Decision.REJECTED
    if worst == Severity.ESCALATE:
        return Decision.QUARANTINED
    return Decision.ACCEPTED


def resolves(findings: Iterable[Finding]) -> bool:
    """A fix candidate resolves the entry only if its revalidation has no BLOCK/ESCALATE."""
    return decide(findings) == Decision.ACCEPTED
