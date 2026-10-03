"""Intent Reviewer: does the description say what the lines do? May only *add* an R013 finding."""

from __future__ import annotations

from typing import Any

from finagent.adjustments.context import RuleContext
from finagent.domain.models import Finding, JournalEntry
from finagent.llm.guardrails import (
    allowed_codes,
    allowed_numbers,
    check_escalate_only,
    check_intent_review,
)
from finagent.llm.payloads import (
    coa_excerpt,
    entry_payload,
    findings_payload,
    guarded_call,
    untrusted_texts,
)
from finagent.llm.providers import LlmClient
from finagent.llm.schemas import IntentReview
from finagent.observability.tracer import Tracer

ROLE = "intent_reviewer"


def build_payload(entry: JournalEntry, findings: list[Finding], ctx: RuleContext) -> dict[str, Any]:
    return {
        "role": ROLE,
        "entry": entry_payload(entry, ctx.coa),
        "coa_excerpt": coa_excerpt(entry, ctx.coa),
        "findings": findings_payload(findings),
    }


def run(
    entry: JournalEntry,
    findings: list[Finding],
    ctx: RuleContext,
    client: LlmClient,
    tracer: Tracer | None = None,
) -> tuple[Finding | None, dict[str, Any]]:
    numbers = allowed_numbers(entry, findings)
    codes = allowed_codes(entry, findings, ctx.coa)
    utr = untrusted_texts(entry)
    res = guarded_call(
        client,
        ROLE,
        IntentReview,
        build_payload(entry, findings, ctx),
        lambda r: check_intent_review(r, numbers, codes, utr),
        entry.id,
        tracer,
    )
    finding = None
    if res.output is not None:
        finding = check_escalate_only(res.output, client.settings.llm.intent_escalate_confidence)
    meta: dict[str, Any] = {
        "role": ROLE,
        "source": "llm" if res.output is not None else "none",
        "model": res.model,
        "attempts": res.attempts,
        "guardrail_fallback": res.guardrail_fallback,
        "cassette_miss": res.cassette_miss,
        "consistent": res.output.consistent if res.output is not None else None,
        "added_finding": finding.rule_id if finding else None,
    }
    if tracer is not None:
        tracer.emit("llm.role", entry_id=entry.id, **meta)
    return finding, meta
