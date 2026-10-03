"""What a model is allowed to see: one entry, its findings, a small COA excerpt. Never the TB.

User-supplied text (description, source, memos) is wrapped in `<untrusted_data>` tags
(engineering rule 11). The payload dict is also the cassette key input, so it must be
deterministic: no timestamps, no run ids.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import orjson
from pydantic import BaseModel

from finagent.adjustments.context import total_credit, total_debit
from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import Finding, JournalEntry
from finagent.llm.providers import CallMeta, LlmClient
from finagent.llm.templates import ordered
from finagent.observability.tracer import Tracer


def neutralise_tags(text: str) -> str:
    """Angle brackets become look-alike entities so user text can never close the wrapper
    (a memo containing `</untrusted_data>` would otherwise escape it). `&` is left alone:
    it is common in account names ("T&E") and escaping it would re-key every cassette."""
    return text.replace("<", "&lt;").replace(">", "&gt;")


def untrusted(text: str) -> str:
    return f"<untrusted_data>{neutralise_tags(text)}</untrusted_data>"


def untrusted_texts(entry: JournalEntry) -> list[str]:
    return [entry.description, entry.source, *(ln.memo for ln in entry.lines)]


def entry_payload(entry: JournalEntry, coa: CoaTree) -> dict[str, Any]:
    return {
        "id": entry.id,
        "date": entry.date,
        "description": untrusted(entry.description),
        "source": untrusted(entry.source),
        "lines": [
            {
                "line": i,
                "account": ln.account,
                "account_name": coa.name_of(ln.account) or "(not in chart of accounts)",
                "debit": str(ln.debit),
                "credit": str(ln.credit),
                "memo": untrusted(ln.memo),
            }
            for i, ln in enumerate(entry.lines, start=1)
        ],
        "total_debit": str(total_debit(entry.lines)),
        "total_credit": str(total_credit(entry.lines)),
    }


def findings_payload(findings: list[Finding]) -> list[dict[str, Any]]:
    return [
        {
            "rule_id": f.rule_id,
            "severity": f.severity.value,
            "title": f.title,
            "message": f.message,
            "evidence": f.evidence,
            "suggested_action": f.suggested_action,
        }
        for f in ordered(findings)
    ]


def coa_excerpt(entry: JournalEntry, coa: CoaTree) -> list[dict[str, str]]:
    """Accounts on the entry, their siblings, and every cash account (so 'settlement' can be
    judged against cash). A few dozen rows at most — never the full ledger."""
    codes: set[str] = set()
    for ln in entry.lines:
        acc = coa.get(ln.account)
        if acc is None:
            continue
        codes.add(acc.code)
        if acc.parent_code is not None:
            codes |= {c.code for c in coa.children(acc.parent_code)}
    codes |= {a.code for a in coa.accounts() if (a.cf_category or "").lower() == "cash"}
    return [
        {"code": a.code, "name": a.name, "type": a.account_type.value}
        for a in coa.accounts()
        if a.code in codes and not coa.is_structural_header(a.code)
    ]


def render_user_message(payload: dict[str, Any]) -> str:
    body = orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode()
    return f"Input (JSON):\n{body}\n\nRespond only with the requested schema."


@dataclass
class GuardedResult[T: BaseModel]:
    output: T | None
    last_cleaned: T | None = None  # the last output after guardrail clean-up, even if it failed
    attempts: int = 0
    violations: list[str] = field(default_factory=list[str])
    guardrail_fallback: bool = False
    metas: list[CallMeta] = field(default_factory=list[CallMeta])

    @property
    def model(self) -> str | None:
        for m in reversed(self.metas):
            if m.model:
                return m.model
        return None

    @property
    def cassette_miss(self) -> bool:
        return any(m.cassette_miss for m in self.metas)


def guarded_call[T: BaseModel](
    client: LlmClient,
    role: str,
    schema: type[T],
    payload: dict[str, Any],
    check: Callable[[T], tuple[T, list[str]]],
    entry_id: str,
    tracer: Tracer | None,
) -> GuardedResult[T]:
    """Call -> guardrails -> (on violation) one retry with violations appended -> fallback."""
    result: GuardedResult[T] = GuardedResult(output=None)
    current = payload
    for attempt in range(1 + client.settings.llm.max_retries):
        obj, meta = client.structured(
            role, schema, current, render_user_message(current), entry_id=entry_id
        )
        result.metas.append(meta)
        result.attempts = attempt + 1
        if obj is None:
            break
        cleaned, violations = check(obj)
        result.last_cleaned = cleaned
        if tracer is not None:
            tracer.emit(
                "guardrail.result",
                entry_id=entry_id,
                role=role,
                attempt=attempt + 1,
                passed=not violations,
                violations=violations,
            )
        if not violations:
            result.output, result.violations = cleaned, []
            return result
        result.violations = violations
        current = {**payload, "previous_violations": violations}
    result.guardrail_fallback = bool(result.violations)
    return result
