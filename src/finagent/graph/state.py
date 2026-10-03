"""Per-entry graph state."""

from __future__ import annotations

from typing import Any, TypedDict

from finagent.domain.models import Decision, Finding, FixCandidate, JournalEntry


class EntryState(TypedDict):
    entry: JournalEntry
    findings: list[Finding]
    decision: Decision | None
    explanation: str | None
    explanation_source: str
    explanation_detail: dict[str, Any] | None
    explanation_model: str | None
    fix_candidates: list[FixCandidate]
    needs_human_input: str | None
    iteration: int
    trace_id: str
