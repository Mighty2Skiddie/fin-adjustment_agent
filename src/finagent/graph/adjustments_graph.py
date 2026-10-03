"""One small LangGraph per entry: validate -> intent_review -> decide -> explain -> propose_fix
-> revalidate_candidates, with one conditional loop (propose_fix again, at most 2 iterations).

Nodes are plain functions of (state, deps) so they are tested without the graph. LangGraph
contributes the loop and a single place to hang tracing — not autonomy: there are no tools,
no planning, and the decision is always `decisions.decide(findings)`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph  # pyright: ignore[reportMissingTypeStubs]

from finagent.adjustments.context import RuleContext
from finagent.adjustments.decisions import decide as decide_from_findings
from finagent.adjustments.decisions import resolves
from finagent.adjustments.impact import compute_impact
from finagent.adjustments.rules import ALL_RULES
from finagent.adjustments.validator import run_rules
from finagent.config import Settings
from finagent.domain.ids import trace_id
from finagent.domain.models import Decision, EntryResult, Finding, FixCandidate, JournalEntry
from finagent.graph.state import EntryState
from finagent.llm.providers import LlmClient
from finagent.llm.roles import explainer, fix_proposer, intent_reviewer
from finagent.llm.templates import render
from finagent.observability.tracer import Tracer

MAX_FIX_ITERATIONS = 2
NodeUpdate = dict[str, Any]  # a partial state update; LangGraph merges it into EntryState


@dataclass
class Deps:
    ctx: RuleContext
    client: LlmClient
    tracer: Tracer


def _eid(state: EntryState) -> str:
    return state["entry"].id


# ---- nodes ---------------------------------------------------------------------------------
def validate(state: EntryState, deps: Deps) -> NodeUpdate:
    entry = state["entry"]
    findings: list[Finding] = []
    with deps.tracer.node("validate", entry_id=entry.id):
        for rule in ALL_RULES:
            start = time.perf_counter()
            produced = rule.check(entry, deps.ctx)
            ms = round((time.perf_counter() - start) * 1000, 3)
            if not produced:
                deps.tracer.emit(
                    "rule.result",
                    entry_id=entry.id,
                    rule_id=rule.RULE_ID,
                    severity="PASS",
                    duration_ms=ms,
                )
            for f in produced:
                deps.tracer.emit(
                    "rule.result",
                    entry_id=entry.id,
                    rule_id=f.rule_id,
                    severity=f.severity.value,
                    duration_ms=ms,
                    evidence=f.evidence,
                )
            findings.extend(produced)
    return {"findings": findings}


def intent_review(state: EntryState, deps: Deps) -> NodeUpdate:
    """May append R013; never removes or edits an existing finding (engineering rule 3)."""
    entry = state["entry"]
    with deps.tracer.node("intent_review", entry_id=entry.id):
        if not deps.client.enabled:
            return {}
        finding, _ = intent_reviewer.run(
            entry, state["findings"], deps.ctx, deps.client, deps.tracer
        )
    if finding is None:
        return {}
    deps.tracer.emit(
        "rule.result",
        entry_id=entry.id,
        rule_id=finding.rule_id,
        severity=finding.severity.value,
        produced_by=finding.produced_by,
        evidence=finding.evidence,
    )
    return {"findings": [*state["findings"], finding]}


def decide(state: EntryState, deps: Deps) -> NodeUpdate:
    with deps.tracer.node("decide", entry_id=_eid(state)):
        decision = decide_from_findings(state["findings"])
    deps.tracer.emit("decision", entry_id=_eid(state), decision=decision.value, by="system")
    return {"decision": decision}


def explain(state: EntryState, deps: Deps) -> NodeUpdate:
    entry = state["entry"]
    decision = state["decision"] or Decision.ACCEPTED
    with deps.tracer.node("explain", entry_id=entry.id):
        exp, meta = explainer.run(
            entry, state["findings"], decision, deps.ctx, deps.client, deps.tracer
        )
    return {
        "explanation": render(exp),
        "explanation_detail": exp.model_dump(mode="json"),
        "explanation_source": str(meta["source"]),
        "explanation_model": meta.get("model"),
    }


def propose_fix(state: EntryState, deps: Deps) -> NodeUpdate:
    entry = state["entry"]
    iteration = state.get("iteration", 0) + 1
    previous = state.get("fix_candidates", []) if iteration > 1 else []
    with deps.tracer.node("propose_fix", entry_id=entry.id, iteration=iteration):
        proposals, _ = fix_proposer.run(
            entry, state["findings"], deps.ctx, deps.client, deps.tracer, previous, iteration
        )
    candidates = [
        FixCandidate(label=c.label, rationale=c.rationale, lines=c.lines)
        for c in proposals.candidates
    ]
    return {
        "fix_candidates": candidates,
        "needs_human_input": proposals.needs_human_input,
        "iteration": iteration,
    }


def candidate_entry(entry: JournalEntry, candidate: FixCandidate) -> JournalEntry:
    return entry.model_copy(update={"lines": candidate.lines, "version": entry.version + 1})


def revalidate_candidates(state: EntryState, deps: Deps) -> NodeUpdate:
    """The same deterministic rules decide whether a proposal would work (never the model)."""
    entry = state["entry"]
    out: list[FixCandidate] = []
    with deps.tracer.node("revalidate_candidates", entry_id=entry.id):
        for c in state.get("fix_candidates", []):
            findings = run_rules(candidate_entry(entry, c), deps.ctx)
            checked = c.model_copy(
                update={"revalidation": findings, "resolves": resolves(findings)}
            )
            deps.tracer.emit(
                "fix.revalidated",
                entry_id=entry.id,
                label=c.label,
                resolves=checked.resolves,
                rule_ids=[f.rule_id for f in findings],
            )
            out.append(checked)
    return {"fix_candidates": out}


# ---- edges ---------------------------------------------------------------------------------
def after_decide(state: EntryState) -> str:
    return END if state["decision"] == Decision.ACCEPTED else "explain"


def after_revalidate(state: EntryState) -> str:
    """Retry only when the model proposed something and none of it resolves the entry."""
    candidates = state.get("fix_candidates", [])
    if (
        candidates
        and not any(c.resolves for c in candidates)
        and state.get("iteration", 0) < MAX_FIX_ITERATIONS
    ):
        return "propose_fix"
    return END


def build_graph(deps: Deps) -> Any:
    g: Any = StateGraph(EntryState)
    g.add_node("validate", partial(validate, deps=deps))
    g.add_node("intent_review", partial(intent_review, deps=deps))
    g.add_node("decide", partial(decide, deps=deps))
    g.add_node("explain", partial(explain, deps=deps))
    g.add_node("propose_fix", partial(propose_fix, deps=deps))
    g.add_node("revalidate_candidates", partial(revalidate_candidates, deps=deps))
    g.add_edge(START, "validate")
    g.add_edge("validate", "intent_review")
    g.add_edge("intent_review", "decide")
    g.add_conditional_edges("decide", after_decide, ["explain", END])
    g.add_edge("explain", "propose_fix")
    g.add_edge("propose_fix", "revalidate_candidates")
    g.add_conditional_edges("revalidate_candidates", after_revalidate, ["propose_fix", END])
    return g.compile()


def run_entry(graph: Any, entry: JournalEntry, deps: Deps, run: str) -> EntryResult:
    tid = trace_id(run, entry.id, entry.version)
    deps.tracer.emit("entry.start", entry_id=entry.id, trace_id=tid)
    initial: EntryState = {
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
        "trace_id": tid,
    }
    final: EntryState = graph.invoke(initial)
    decision = final.get("decision") or decide_from_findings(final.get("findings", []))
    return EntryResult(
        entry=entry,
        findings=final.get("findings", []),
        decision=decision,
        explanation=final.get("explanation"),
        explanation_source=final.get("explanation_source", "none"),
        explanation_detail=final.get("explanation_detail"),
        explanation_model=final.get("explanation_model"),
        fix_candidates=final.get("fix_candidates", []),
        needs_human_input=final.get("needs_human_input"),
        impact=compute_impact(entry, deps.ctx.coa),
        trace_id=tid,
    )


def run_batch(
    entries: list[JournalEntry], ctx: RuleContext, run: str, client: LlmClient, tracer: Tracer
) -> list[EntryResult]:
    """Entries run one after another. They are independent, so this can run in parallel later."""
    deps = Deps(ctx=ctx, client=client, tracer=tracer)
    graph = build_graph(deps)
    return [run_entry(graph, e, deps, run) for e in entries]


def graph_processor(settings: Settings) -> Any:
    def process(
        entries: list[JournalEntry], ctx: RuleContext, run: str, tracer: Tracer
    ) -> list[EntryResult]:
        return run_batch(entries, ctx, run, LlmClient(settings, tracer), tracer)

    return process
