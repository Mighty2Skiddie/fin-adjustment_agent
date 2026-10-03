"""Deterministic explanations built only from rule findings.

Used when the LLM is off, missing from the cassette, or fails its guardrails twice. Every
number and account code here comes verbatim from a finding message, so the template passes
the same faithfulness checks the model output must pass.
"""

from __future__ import annotations

from finagent.adjustments.decisions import max_severity
from finagent.domain.models import SEVERITY_RANK, Decision, Finding, JournalEntry
from finagent.llm.schemas import Explanation

_SUMMARY = {
    Decision.REJECTED: "{id} was rejected: {title}.",
    Decision.QUARANTINED: "{id} needs a reviewer before it can post: {title}.",
    Decision.ACCEPTED: "{id} posted automatically: all blocking checks passed.",
}
_DEFAULT_NEXT = {
    Decision.REJECTED: "Edit the entry and resubmit it as a new version.",
    Decision.QUARANTINED: "Review the findings, then approve or reject with a reason.",
    Decision.ACCEPTED: "No action needed.",
}


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _lower_first(text: str) -> str:
    """Sentence-case a title mid-sentence without breaking acronyms ("FX revaluation")."""
    first = text.split(" ", 1)[0]
    if first.isupper() and len(first) > 1:
        return text
    return text[:1].lower() + text[1:]


def ordered(findings: list[Finding]) -> list[Finding]:
    """Most severe first; stable within a severity (rule order)."""
    return sorted(findings, key=lambda f: -SEVERITY_RANK[f.severity])


def template_explanation(
    entry: JournalEntry, findings: list[Finding], decision: Decision
) -> Explanation:
    top = ordered(findings)
    worst = max_severity(findings)
    lead = next((f for f in top if f.severity == worst), None)
    title = _lower_first(lead.title) if lead else "no findings"
    summary = _SUMMARY[decision].format(id=entry.id, title=title)
    details = [_clip(f"{f.rule_id}: {f.message}", 400) for f in top[:5]]
    action = lead.suggested_action if lead and lead.suggested_action else None
    return Explanation(
        summary=_clip(summary, 300),
        details=details,
        next_step=_clip(action or _DEFAULT_NEXT[decision], 200),
    )


def render(explanation: Explanation) -> str:
    """Plain-text form stored as `EntryResult.explanation`."""
    bullets = "\n".join(f"- {d}" for d in explanation.details)
    return f"{explanation.summary}\n{bullets}\nNext step: {explanation.next_step}".strip()
