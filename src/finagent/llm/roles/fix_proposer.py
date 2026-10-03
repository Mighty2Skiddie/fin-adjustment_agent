"""Fix Proposer: propose corrected line sets. Proposals only — code re-validates, humans decide."""

from __future__ import annotations

from typing import Any

from finagent.adjustments.context import RuleContext
from finagent.domain.models import Finding, FixCandidate, JournalEntry
from finagent.llm.guardrails import (
    allowed_amounts,
    allowed_codes,
    allowed_numbers,
    check_fix_candidates,
)
from finagent.llm.payloads import (
    coa_excerpt,
    entry_payload,
    findings_payload,
    guarded_call,
    untrusted_texts,
)
from finagent.llm.providers import LlmClient
from finagent.llm.schemas import FixProposals
from finagent.llm.templates import ordered
from finagent.observability.tracer import Tracer

ROLE = "fix_proposer"


def template_question(findings: list[Finding]) -> str:
    top = ordered(findings)
    action = next((f.suggested_action for f in top if f.suggested_action), None)
    return action or "Please confirm the intended lines for this entry and resubmit it."


def build_payload(
    entry: JournalEntry,
    findings: list[Finding],
    ctx: RuleContext,
    previous: list[FixCandidate],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": ROLE,
        "entry": entry_payload(entry, ctx.coa),
        "findings": findings_payload(findings),
        "coa_excerpt": coa_excerpt(entry, ctx.coa),
    }
    if previous:
        payload["previous_candidates"] = [
            {
                "label": c.label,
                "lines": [ln.model_dump(mode="json") for ln in c.lines],
                "revalidation": [
                    {"rule_id": f.rule_id, "severity": f.severity.value, "message": f.message}
                    for f in c.revalidation
                ],
            }
            for c in previous
        ]
    return payload


def run(
    entry: JournalEntry,
    findings: list[Finding],
    ctx: RuleContext,
    client: LlmClient,
    tracer: Tracer | None = None,
    previous: list[FixCandidate] | None = None,
    iteration: int = 1,
) -> tuple[FixProposals, dict[str, Any]]:
    # Amounts a candidate may use: the entry's and the findings' — never new numbers.
    numbers = allowed_numbers(entry, findings)
    amounts = allowed_amounts(entry, findings)
    codes = allowed_codes(entry, findings, ctx.coa)
    utr = untrusted_texts(entry)
    dropped: list[str] = []

    def check(f: FixProposals) -> tuple[FixProposals, list[str]]:
        cleaned, violations = check_fix_candidates(f, ctx.coa, numbers, codes, utr, amounts)
        dropped.extend(violations)
        return cleaned, violations

    res = guarded_call(
        client,
        ROLE,
        FixProposals,
        build_payload(entry, findings, ctx, previous or []),
        check,
        entry.id,
        tracer,
    )
    output = res.output
    if output is None and res.last_cleaned is not None:
        # The retry still had violations: keep only candidates that passed every check, and
        # replace the (possibly unfaithful) question with a deterministic one.
        output = res.last_cleaned.model_copy(
            update={"needs_human_input": template_question(findings)}
        )
    if output is None:
        output = FixProposals(candidates=[], needs_human_input=template_question(findings))
    elif output.needs_human_input is None and not output.candidates:
        output = output.model_copy(update={"needs_human_input": template_question(findings)})
    meta: dict[str, Any] = {
        "role": ROLE,
        "source": "llm" if res.output is not None or res.last_cleaned is not None else "template",
        "model": res.model,
        "attempts": res.attempts,
        "guardrail_fallback": res.guardrail_fallback,
        "cassette_miss": res.cassette_miss,
        "candidates": len(output.candidates),
        "dropped": dropped or None,
        "iteration": iteration,
    }
    if tracer is not None:
        tracer.emit("llm.role", entry_id=entry.id, **meta)
    return output, meta
