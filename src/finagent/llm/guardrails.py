"""Post-checks run after every LLM output (engineering rule 2).

A model output is only used if every number in it already exists in the findings or the entry,
every account code exists in the COA / entry / findings, and nothing it says can lower a
deterministic finding. Violations trigger one retry with the violations appended; a second
failure falls back to the deterministic template (`guardrail_fallback=true`).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from typing import Any

from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import Finding, JournalEntry, Severity
from finagent.domain.money import ZERO, q
from finagent.llm.payloads import untrusted as untrusted_wrap
from finagent.llm.schemas import FixProposals, IntentReview, ProposedFix

# Identifiers that contain digits but are not amounts: JE ids, rule ids, health ids, dates,
# periods, assumption / decision / clarifying-question ids.
_IDENTIFIERS = re.compile(
    r"\b(?:JE|SYN)-\d+\b|\b[A-Z]{2,5}-\d{1,3}\b|\bR\d{3}[a-z]?\b|\bH-[A-Z]+-\d+\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{4}-Q\d\b"
    r"|\bQ\d\b|\b[AD]\d{1,2}\b|\bv\d+\b|#\d+"
)
# A letter or underscore before the digits does not hide an amount ("USD3600", "x3,600.00").
_NUMBER = re.compile(r"(?<![\d.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|(?<![\d.])-?\d+(?:\.\d+)?%?")
# Amounts as they are written in evidence and entries: thousands separators or cents.
_MONEY = re.compile(r"(?<![\d.])-?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d{2})(?![\d%])")
_CODE = re.compile(r"(?<![\w.,])\d{4}(?![\d,]|\.\d)")
_BARE_CODE = re.compile(r"\d{4}")
SMALL_INTEGERS = {Decimal(i) for i in range(11)}  # line counts, "two lines", "line 2"
_INJECTION_WORDS = ("ignore", "disregard", "override", "approve", "bypass", "instruction")


def _to_decimal(token: str) -> Decimal | None:
    try:
        return Decimal(token.replace(",", "").rstrip("%"))
    except InvalidOperation:
        return None


def _strip_identifiers(text: str) -> str:
    return _IDENTIFIERS.sub(" ", text)


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():  # pyright: ignore[reportUnknownVariableType]
            yield from _walk_strings(v)
    elif isinstance(value, list):
        for v in value:  # pyright: ignore[reportUnknownVariableType]
            yield from _walk_strings(v)
    elif isinstance(value, int) and not isinstance(value, bool):
        yield str(value)


def _with_pct_forms(d: Decimal) -> set[Decimal]:
    """A ratio like 0.2667 may be written as 26.67%, 26.7% or 27%."""
    out = {d}
    if ZERO < abs(d) <= Decimal("5"):
        pct = d * 100
        out |= {pct, pct.quantize(Decimal("0.1")), pct.quantize(Decimal("1")), q(pct)}
    return {x.normalize() for x in out}


def allowed_numbers(entry: JournalEntry, findings: Iterable[Finding]) -> set[Decimal]:
    """Every number a model may mention: entry amounts, totals, and anything in the findings."""
    allowed: set[Decimal] = set(SMALL_INTEGERS)
    total_d = total_c = ZERO
    for ln in entry.lines:
        allowed |= {ln.debit, ln.credit}
        total_d += ln.debit
        total_c += ln.credit
    allowed |= {total_d, total_c, abs(total_d - total_c)}
    texts: list[str] = []
    for f in findings:
        texts += [f.message, f.title, f.suggested_action or ""]
        texts += list(_walk_strings(f.evidence))
    for t in texts:
        for tok in _NUMBER.findall(_strip_identifiers(t)):
            d = _to_decimal(tok)
            if d is not None:
                allowed |= _with_pct_forms(abs(d))
    return {abs(x).normalize() for x in allowed}


def allowed_amounts(entry: JournalEntry, findings: Iterable[Finding]) -> set[Decimal]:
    """Amounts a fix candidate line may carry: the entry's amounts and totals, and money-shaped
    values in the findings. Unlike `allowed_numbers`, no small integers, percentages, ratios or
    account codes — a candidate posting 5.00 or 7,310.00 would otherwise pass as "from input"."""
    out: set[Decimal] = set()
    total_d = total_c = ZERO
    for ln in entry.lines:
        out |= {ln.debit, ln.credit}
        total_d += ln.debit
        total_c += ln.credit
    out |= {total_d, total_c, abs(total_d - total_c)}
    for f in findings:
        for t in [f.message, f.title, f.suggested_action or "", *_walk_strings(f.evidence)]:
            for tok in _MONEY.findall(_strip_identifiers(t)):
                d = _to_decimal(tok)
                if d is not None:
                    out.add(d)
    return {abs(x).normalize() for x in out if x != ZERO}


def check_numbers(text: str, allowed: set[Decimal]) -> list[str]:
    """Amounts must come from the input. A standalone 4-digit token is an account code and is
    left to `check_account_codes` — an invented "3600" still fails there, since it is not a COA
    code. Digits glued to letters ("USD3600") are not a code and are checked as an amount."""
    violations: list[str] = []
    stripped = _strip_identifiers(text)
    for m in _NUMBER.finditer(stripped):
        tok = m.group()
        before = stripped[m.start() - 1] if m.start() > 0 else " "
        if _BARE_CODE.fullmatch(tok) and not (before.isalnum() or before == "_"):
            continue
        d = _to_decimal(tok)
        if d is None:
            continue
        if abs(d).normalize() not in allowed:
            violations.append(f"number {tok} does not appear in the findings or the entry")
    return violations


def allowed_codes(entry: JournalEntry, findings: Iterable[Finding], coa: CoaTree) -> set[str]:
    codes = set(coa.codes()) | {ln.account for ln in entry.lines}
    for f in findings:
        for t in [f.message, *_walk_strings(f.evidence)]:
            codes |= set(_CODE.findall(t))
    return codes


def check_account_codes(text: str, allowed: set[str]) -> list[str]:
    return [
        f"account code {code} is not in the chart of accounts, the entry or the findings"
        for code in _CODE.findall(_strip_identifiers(text))
        if code not in allowed
    ]


def check_injection_echo(text: str, untrusted: Iterable[str]) -> list[str]:
    """The model must not repeat an instruction smuggled into a memo or description."""
    out = text.lower()
    violations: list[str] = []
    for raw in untrusted:
        for sentence in re.split(r"[.!?\n]", raw.lower()):
            s = " ".join(sentence.split())
            if len(s) >= 12 and any(w in s for w in _INJECTION_WORDS) and s in out:
                # Violations go back to the model on retry, so the quoted text stays wrapped.
                violations.append(
                    f"output repeats an instruction from user-entered text: {untrusted_wrap(s)}"
                )
    return violations


def check_text(
    text: str, numbers: set[Decimal], codes: set[str], untrusted: Iterable[str]
) -> list[str]:
    return [
        *check_numbers(text, numbers),
        *check_account_codes(text, codes),
        *check_injection_echo(text, untrusted),
    ]


def check_escalate_only(
    review: IntentReview, threshold: Decimal = Decimal("0.70")
) -> Finding | None:
    """Convert a review into an R013 finding. It can only ever *add* a finding (rule 3)."""
    if review.consistent:
        return None
    confidence = q(Decimal(str(review.confidence)))
    severity = Severity.ESCALATE if confidence >= threshold else Severity.WARN
    return Finding(
        rule_id="R013",
        severity=severity,
        title="Description does not match the lines",
        message=review.reason,
        evidence={
            "llm_reason": review.reason,
            "confidence": str(confidence),
            "implied_accounts": list(review.implied_accounts),
        },
        suggested_action="Ask the preparer to confirm what the entry is meant to do.",
        produced_by="llm:intent_reviewer",
        assumption="A17",
    )


def check_intent_review(
    review: IntentReview, numbers: set[Decimal], codes: set[str], untrusted: Iterable[str]
) -> tuple[IntentReview, list[str]]:
    """Text checks on the reason; unknown implied account codes are dropped, not fatal."""
    violations = check_text(review.reason, numbers, codes, untrusted)
    kept = [c for c in review.implied_accounts if c in codes]
    return review.model_copy(update={"implied_accounts": kept}), violations


def _candidate_violations(
    c: ProposedFix,
    coa: CoaTree,
    numbers: set[Decimal],
    amounts: set[Decimal],
    codes: set[str],
    untrusted: list[str],
) -> list[str]:
    v: list[str] = []
    for ln in c.lines:
        if ln.account not in coa:
            v.append(f"candidate '{c.label}' uses account {ln.account}, not in the chart")
        for amt in (ln.debit, ln.credit):
            if amt < ZERO:
                v.append(f"candidate '{c.label}' uses negative amount {amt}")
            elif amt != ZERO and amt.normalize() not in amounts:
                v.append(f"candidate '{c.label}' uses amount {amt} not found in the input")
    texts = [c.label, c.rationale, *(ln.memo for ln in c.lines if ln.memo)]
    v += check_text(". ".join(texts), numbers, codes, untrusted)
    return v


def check_fix_candidates(
    fixes: FixProposals,
    coa: CoaTree,
    numbers: set[Decimal] | None = None,
    codes: set[str] | None = None,
    untrusted: Iterable[str] = (),
    amounts: set[Decimal] | None = None,
) -> tuple[FixProposals, list[str]]:
    """Drop candidates that reference unknown codes or invented amounts; report the drops.
    Line amounts are held to `amounts` (see `allowed_amounts`); without it, to `numbers` minus
    the small integers that are only allowed for prose ("two lines")."""
    nums = numbers if numbers is not None else set[Decimal]()
    amts = amounts if amounts is not None else {n for n in nums if n not in SMALL_INTEGERS}
    cds = codes if codes is not None else coa.codes()
    utr = list(untrusted)
    kept: list[ProposedFix] = []
    dropped: list[str] = []
    for c in fixes.candidates:
        v = (
            _candidate_violations(c, coa, nums, amts, cds, utr)
            if numbers is not None
            else [
                f"candidate '{c.label}' uses account {ln.account}, not in the chart"
                for ln in c.lines
                if ln.account not in coa
            ]
        )
        if v:
            dropped += v
        else:
            kept.append(c)
    question_violations = (
        check_text(fixes.needs_human_input, nums, cds, utr)
        if fixes.needs_human_input and numbers is not None
        else []
    )
    return fixes.model_copy(update={"candidates": kept}), dropped + question_violations
