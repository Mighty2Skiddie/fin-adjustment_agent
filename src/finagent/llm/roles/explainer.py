"""Explainer: explain the decision in a controller's language, using only the findings' numbers."""

from __future__ import annotations

from typing import Any

from finagent.adjustments.context import RuleContext
from finagent.domain.models import Decision, Finding, JournalEntry
from finagent.llm.guardrails import allowed_codes, allowed_numbers, check_text
from finagent.llm.payloads import entry_payload, findings_payload, guarded_call, untrusted_texts
from finagent.llm.providers import LlmClient
from finagent.llm.schemas import Explanation
from finagent.llm.templates import template_explanation
from finagent.observability.tracer import Tracer

ROLE = "explainer"


def build_payload(
    entry: JournalEntry, findings: list[Finding], decision: Decision, ctx: RuleContext
) -> dict[str, Any]:
    return {
        "role": ROLE,
        "decision": decision.value,
        "entry": entry_payload(entry, ctx.coa),
        "findings": findings_payload(findings),
    }


def run(
    entry: JournalEntry,
    findings: list[Finding],
    decision: Decision,
    ctx: RuleContext,
    client: LlmClient,
    tracer: Tracer | None = None,
) -> tuple[Explanation, dict[str, Any]]:
    numbers = allowed_numbers(entry, findings)
    codes = allowed_codes(entry, findings, ctx.coa)
    utr = untrusted_texts(entry)

    def check(e: Explanation) -> tuple[Explanation, list[str]]:
        text = "\n".join([e.summary, *e.details, e.next_step])
        return e, check_text(text, numbers, codes, utr)

    res = guarded_call(
        client,
        ROLE,
        Explanation,
        build_payload(entry, findings, decision, ctx),
        check,
        entry.id,
        tracer,
    )
    output = res.output or template_explanation(entry, findings, decision)
    meta: dict[str, Any] = {
        "role": ROLE,
        "source": "llm" if res.output is not None else "template",
        "model": res.model if res.output is not None else None,
        "attempts": res.attempts,
        "guardrail_fallback": res.guardrail_fallback,
        "cassette_miss": res.cassette_miss,
    }
    if tracer is not None:
        tracer.emit("llm.role", entry_id=entry.id, **meta)
    return output, meta
