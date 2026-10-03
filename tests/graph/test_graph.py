"""Per-entry graph: nodes in isolation, the bounded fix loop, and escalate-only intent review.

A scripted fake client stands in for the model; nothing here touches the network or cassettes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

import pytest
from langgraph.graph import END  # pyright: ignore[reportMissingTypeStubs]
from pydantic import BaseModel

from finagent.adjustments.context import RuleContext
from finagent.config import Settings, load_settings
from finagent.domain.models import (
    Decision,
    EntryResult,
    Finding,
    FixCandidate,
    JeLine,
    JournalEntry,
    Severity,
)
from finagent.graph.adjustments_graph import (
    MAX_FIX_ITERATIONS,
    Deps,
    after_decide,
    after_revalidate,
    build_graph,
    decide,
    intent_review,
    revalidate_candidates,
    run_entry,
    validate,
)
from finagent.graph.state import EntryState
from finagent.llm.providers import CallMeta, LlmClient
from finagent.llm.schemas import FixProposals, IntentReview, ProposedFix
from finagent.observability.tracer import Tracer

T = TypeVar("T", bound=BaseModel)
# (payload, 1-based call number for this role) -> scripted output, or None for "no answer"
Script = Callable[[dict[str, Any], int], BaseModel | None]


class FakeClient(LlmClient):
    """Returns scripted outputs per role and records every payload it was sent."""

    def __init__(self, tracer: Tracer | None = None, **scripts: Script) -> None:
        super().__init__(
            load_settings({"llm": {"mode": "cassette", "cassette_dir": "nonexistent"}}), tracer
        )
        self.scripts = scripts
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def count(self, role: str) -> int:
        return sum(1 for r, _ in self.calls if r == role)

    def payloads(self, role: str) -> list[dict[str, Any]]:
        return [p for r, p in self.calls if r == role]

    def structured(
        self,
        role: str,
        schema: type[T],
        payload: dict[str, Any],
        user_message: str,
        entry_id: str | None = None,
    ) -> tuple[T | None, CallMeta]:
        self.calls.append((role, payload))
        script = self.scripts.get(role)
        out = script(payload, self.count(role)) if script is not None else None
        meta = CallMeta(role=role, mode="fake", model="fake-model", provider="fake")
        if self.tracer is not None:
            self.tracer.emit("llm.call", entry_id=entry_id, role=role, mode="fake")
        if isinstance(out, schema):
            return out, meta
        return None, meta


def consistent(_: dict[str, Any], __: int) -> BaseModel:
    return IntentReview(consistent=True, confidence=0.95, reason="The lines match.")


def inconsistent(confidence: float) -> Script:
    def script(_: dict[str, Any], __: int) -> BaseModel:
        return IntentReview(
            consistent=False,
            confidence=confidence,
            reason="The description does not describe what the lines do.",
        )

    return script


def lines(*spec: tuple[str, str, str]) -> list[JeLine]:
    return [JeLine.model_validate({"account": a, "debit": d, "credit": c}) for a, d, c in spec]


def propose(*spec: tuple[str, str, str]) -> Script:
    def script(_: dict[str, Any], __: int) -> BaseModel:
        return FixProposals(
            candidates=[
                ProposedFix(
                    label="Match the amounts",
                    rationale="Keep both sides equal.",
                    lines=lines(*spec),
                )
            ]
        )

    return script


def no_candidates(_: dict[str, Any], __: int) -> BaseModel:
    return FixProposals(candidates=[], needs_human_input="Which amount is correct?")


UNBALANCED = (("6300", "28500.00", "0"), ("6310", "0", "25000.00"))  # JE-002 as booked
BALANCED = (("6300", "28500.00", "0"), ("6310", "0", "28500.00"))


def state_for(entry: JournalEntry, **extra: Any) -> EntryState:
    state: EntryState = {
        "entry": entry,
        "findings": [],
        "decision": None,
        "explanation": None,
        "explanation_source": "none",
        "explanation_detail": None,
        "explanation_model": None,
        "fix_candidates": [],
        "needs_human_input": None,
        "iteration": 0,
        "trace_id": "t",
    }
    state.update(extra)  # pyright: ignore[reportCallIssue, reportArgumentType]
    return state


def run_one(
    entry: JournalEntry, ctx: RuleContext, client: FakeClient, tracer: Tracer
) -> EntryResult:
    deps = Deps(ctx=ctx, client=client, tracer=tracer)
    return run_entry(build_graph(deps), entry, deps, "testrun")


def node_entries(tracer: Tracer, entry_id: str) -> list[str]:
    return [e["node"] for e in tracer.for_entry(entry_id) if e["event"] == "node.enter"]


def candidate(resolves: bool) -> FixCandidate:
    return FixCandidate(label="c", rationale="r", lines=lines(*BALANCED), resolves=resolves)


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)


# ---- nodes without the graph -----------------------------------------------------------------
def test_validate_node_runs_rules_and_traces(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    deps = Deps(ctx=rule_ctx, client=FakeClient(), tracer=tracer)
    out = validate(state_for(entries["JE-002"]), deps)
    assert [f.rule_id for f in out["findings"]] == ["R001"]
    results = [e for e in tracer.events if e["event"] == "rule.result"]
    assert any(e["rule_id"] == "R001" and e["severity"] == "BLOCK" for e in results)
    assert any(e["severity"] == "PASS" for e in results)
    assert node_entries(tracer, "JE-002") == ["validate"]


def test_decide_node_is_decisions_decide(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    deps = Deps(ctx=rule_ctx, client=FakeClient(), tracer=tracer)
    entry = entries["JE-002"]
    findings = validate(state_for(entry), deps)["findings"]
    assert decide(state_for(entry, findings=findings), deps) == {"decision": Decision.REJECTED}
    assert decide(state_for(entry), deps) == {"decision": Decision.ACCEPTED}
    events = [e for e in tracer.events if e["event"] == "decision"]
    assert [e["decision"] for e in events] == ["REJECTED", "ACCEPTED"]
    assert all(e["by"] == "system" for e in events)


def test_intent_review_node_skipped_when_llm_off(
    settings: Settings, entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    deps = Deps(ctx=rule_ctx, client=LlmClient(settings, tracer), tracer=tracer)
    assert intent_review(state_for(entries["JE-009"]), deps) == {}
    assert not [e for e in tracer.events if e["event"] == "llm.call"]


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (Decision.ACCEPTED, END),
        (Decision.QUARANTINED, "explain"),
        (Decision.REJECTED, "explain"),
    ],
)
def test_after_decide(entries: dict[str, JournalEntry], decision: Decision, expected: str) -> None:
    assert after_decide(state_for(entries["JE-001"], decision=decision)) == expected


def test_after_revalidate(entries: dict[str, JournalEntry]) -> None:
    e = entries["JE-002"]
    assert after_revalidate(state_for(e, iteration=1)) == END  # zero candidates
    bad = [candidate(False), candidate(False)]
    assert after_revalidate(state_for(e, fix_candidates=bad, iteration=1)) == "propose_fix"
    assert after_revalidate(state_for(e, fix_candidates=bad, iteration=MAX_FIX_ITERATIONS)) == END
    mixed = [candidate(False), candidate(True)]
    assert after_revalidate(state_for(e, fix_candidates=mixed, iteration=1)) == END


def test_revalidate_candidates_uses_rules(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    deps = Deps(ctx=rule_ctx, client=FakeClient(), tracer=tracer)
    good = FixCandidate(label="good", rationale="r", lines=lines(*BALANCED))
    bad = FixCandidate(label="bad", rationale="r", lines=lines(*UNBALANCED))
    out = revalidate_candidates(state_for(entries["JE-002"], fix_candidates=[good, bad]), deps)
    got = {c.label: c for c in out["fix_candidates"]}
    assert got["good"].resolves is True
    assert got["bad"].resolves is False
    assert "R001" in [f.rule_id for f in got["bad"].revalidation]
    revals = [e for e in tracer.events if e["event"] == "fix.revalidated"]
    assert [(e["label"], e["resolves"]) for e in revals] == [("good", True), ("bad", False)]


# ---- the bounded fix loop --------------------------------------------------------------------
def test_fix_loop_stops_at_max_iterations(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    client = FakeClient(tracer, intent_reviewer=consistent, fix_proposer=propose(*UNBALANCED))
    deps = Deps(ctx=rule_ctx, client=client, tracer=tracer)
    final: EntryState = build_graph(deps).invoke(state_for(entries["JE-002"]))
    assert MAX_FIX_ITERATIONS == 2
    assert final["iteration"] == 2
    assert client.count("fix_proposer") == 2
    first, second = client.payloads("fix_proposer")
    assert "previous_candidates" not in first
    prev = second["previous_candidates"]
    assert len(prev) == 1
    assert [ln["account"] for ln in prev[0]["lines"]] == ["6300", "6310"]
    assert "R001" in [f["rule_id"] for f in prev[0]["revalidation"]]
    assert final["fix_candidates"] and not any(c.resolves for c in final["fix_candidates"])
    assert final["decision"] == Decision.REJECTED
    iters = [
        e["iteration"]
        for e in tracer.for_entry("JE-002")
        if e["event"] == "node.enter" and e["node"] == "propose_fix"
    ]
    assert iters == [1, 2]


def test_fix_loop_does_not_rerun_when_candidate_resolves(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    client = FakeClient(tracer, intent_reviewer=consistent, fix_proposer=propose(*BALANCED))
    result = run_one(entries["JE-002"], rule_ctx, client, tracer)
    assert client.count("fix_proposer") == 1
    assert [c.resolves for c in result.fix_candidates] == [True]
    assert result.decision == Decision.REJECTED  # proposals never change the decision


def test_fix_loop_does_not_rerun_with_zero_candidates(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    client = FakeClient(tracer, intent_reviewer=consistent, fix_proposer=no_candidates)
    result = run_one(entries["JE-002"], rule_ctx, client, tracer)
    assert client.count("fix_proposer") == 1
    assert result.fix_candidates == []
    assert result.needs_human_input == "Which amount is correct?"


def test_accepted_entry_skips_explain_and_fix(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    client = FakeClient(tracer, intent_reviewer=consistent, fix_proposer=propose(*BALANCED))
    result = run_one(entries["JE-001"], rule_ctx, client, tracer)
    assert result.decision == Decision.ACCEPTED
    assert node_entries(tracer, "JE-001") == ["validate", "intent_review", "decide"]
    assert client.count("intent_reviewer") == 1
    assert client.count("explainer") == 0 and client.count("fix_proposer") == 0
    assert result.explanation is None and result.explanation_source == "none"
    assert result.fix_candidates == []


# ---- intent reviewer can only add ------------------------------------------------------------
def _snapshot(findings: list[Finding]) -> list[dict[str, Any]]:
    return [f.model_dump(mode="json") for f in findings]


def test_intent_reviewer_adds_r013_on_rejected_entry(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    entry = entries["JE-002"]
    base_tracer = Tracer("base")
    base = validate(state_for(entry), Deps(rule_ctx, FakeClient(), base_tracer))["findings"]
    tracer = Tracer("t")
    client = FakeClient(tracer, intent_reviewer=inconsistent(0.9), fix_proposer=no_candidates)
    result = run_one(entry, rule_ctx, client, tracer)
    assert _snapshot(result.findings[: len(base)]) == _snapshot(base)
    assert [f.rule_id for f in result.findings] == ["R001", "R013"]
    r013 = result.findings[-1]
    assert r013.severity == Severity.ESCALATE
    assert r013.produced_by == "llm:intent_reviewer"
    assert r013.evidence["confidence"] == "0.90"
    assert result.decision == Decision.REJECTED  # BLOCK still wins


@pytest.mark.parametrize(
    ("confidence", "severity", "decision"),
    [
        (0.9, Severity.ESCALATE, Decision.QUARANTINED),
        (0.7, Severity.ESCALATE, Decision.QUARANTINED),
        (0.5, Severity.WARN, Decision.ACCEPTED),
    ],
)
def test_intent_reviewer_escalates_accepted_entry(
    entries: dict[str, JournalEntry],
    rule_ctx: RuleContext,
    confidence: float,
    severity: Severity,
    decision: Decision,
) -> None:
    entry = entries["JE-009"]  # no deterministic findings at all
    tracer = Tracer("t")
    client = FakeClient(tracer, intent_reviewer=inconsistent(confidence))
    result = run_one(entry, rule_ctx, client, tracer)
    assert [(f.rule_id, f.severity) for f in result.findings] == [("R013", severity)]
    assert result.decision == decision
    if decision == Decision.QUARANTINED:
        assert result.explanation_source == "template"  # fake explainer gave no answer
        assert client.count("explainer") >= 1
    else:
        assert client.count("explainer") == 0


def test_consistent_review_adds_nothing(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    client = FakeClient(tracer, intent_reviewer=consistent)
    result = run_one(entries["JE-001"], rule_ctx, client, tracer)
    assert [f.rule_id for f in result.findings] == ["R009"]
    assert result.decision == Decision.ACCEPTED


# ---- trace -----------------------------------------------------------------------------------
def test_trace_has_rule_llm_guardrail_and_decision_events(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    tracer = Tracer("t")
    client = FakeClient(tracer, intent_reviewer=consistent, fix_proposer=propose(*BALANCED))
    result = run_one(entries["JE-002"], rule_ctx, client, tracer)
    kinds = {e["event"] for e in tracer.for_entry("JE-002")}
    assert {
        "entry.start",
        "node.enter",
        "node.exit",
        "rule.result",
        "llm.call",
        "llm.role",
        "guardrail.result",
        "decision",
        "fix.revalidated",
    } <= kinds
    starts = [e for e in tracer.events if e["event"] == "entry.start"]
    assert starts[0]["trace_id"] == result.trace_id
    guard = [e for e in tracer.events if e["event"] == "guardrail.result"]
    assert {g["role"] for g in guard} == {"intent_reviewer", "fix_proposer"}
    assert all(g["passed"] for g in guard)
