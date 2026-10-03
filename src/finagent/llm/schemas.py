"""Structured outputs for the three LLM roles. A model can only fill these schemas; there is
no free-form "action" field, so a prompt-injected instruction has nowhere to go."""

from __future__ import annotations

from pydantic import BaseModel, Field

from finagent.domain.models import JeLine


class IntentReview(BaseModel):
    consistent: bool
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(max_length=400)
    implied_accounts: list[str] = Field(default_factory=list[str])  # whitelisted by guardrails


class Explanation(BaseModel):
    summary: str = Field(max_length=300)  # one sentence a controller reads first
    details: list[str] = Field(max_length=5)  # one bullet per finding, same order as findings
    next_step: str = Field(max_length=200)


class ProposedFix(BaseModel):
    label: str
    rationale: str
    lines: list[JeLine]


class FixProposals(BaseModel):
    candidates: list[ProposedFix] = Field(default_factory=list[ProposedFix], max_length=3)
    needs_human_input: str | None = None  # question for the preparer when a fix isn't inferable


class ClarityScore(BaseModel):
    """LLM-as-judge rubric for explanation clarity (evals, live mode only)."""

    score: int = Field(ge=1, le=5)
    reason: str = Field(max_length=200)
