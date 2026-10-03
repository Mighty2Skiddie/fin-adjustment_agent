"""Run the golden + synthetic evaluation and write `output/evals/report.{md,json}`.

The golden set is the 10 real entries (expected values from docs/02_DATA_SPEC.md §7); the
synthetic set exercises every rule plus the LLM boundary (adversarial memos, intent mismatch).
CI fails when golden decision accuracy or explanation faithfulness drops below 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson

from evals.checks import (
    Case,
    adversarial_echo_free,
    decision_accuracy,
    deterministic_ids,
    expected_decision,
    explanation_faithfulness,
    fallback_rate,
    llm_ids,
    ratio,
    rule_precision_recall,
    schema_validity,
)
from finagent.config import ROOT, Settings
from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import EntryResult
from finagent.graph.adjustments_graph import run_batch
from finagent.ingest.loaders import entry_from_dict
from finagent.llm.payloads import entry_payload, findings_payload
from finagent.llm.providers import LlmClient
from finagent.llm.schemas import ClarityScore
from finagent.observability.tracer import Tracer
from finagent.pipeline import prepare

GOLDEN = ROOT / "evals" / "golden" / "expected_decisions.json"
SYNTHETIC = ROOT / "evals" / "golden" / "synthetic_entries.json"
OUT_DIR = ROOT / "output" / "evals"
GATE = "golden decision_accuracy == 1.0 and explanation faithfulness (numbers, codes) == 1.0"
ENTRY_HEADER = (
    "| Entry | Set | Expected | Actual | Expected rules | Actual rules | LLM findings "
    "| Explanation | Match |"
)


@dataclass
class EvalResult:
    report: dict[str, Any]
    passed: bool


def load_cases() -> tuple[list[Case], list[Case], list[dict[str, Any]]]:
    golden_raw: dict[str, Any] = orjson.loads(GOLDEN.read_bytes())
    golden = [
        Case(
            id=je,
            source="golden",
            category="rules",
            expected_decision=v["decision"],
            expected_rule_ids=list(v["rule_ids"]),
            expected_llm_rule_ids=list(v.get("llm_rule_ids", [])),
        )
        for je, v in golden_raw.items()
        if not je.startswith("_")
    ]
    syn_raw: dict[str, Any] = orjson.loads(SYNTHETIC.read_bytes())
    entries: list[dict[str, Any]] = []
    synthetic: list[Case] = []
    for c in syn_raw["cases"]:
        exp: dict[str, Any] = c["expected"]
        rule_ids = [x for x in exp["rule_ids"] if x != "R013"]
        synthetic.append(
            Case(
                id=c["entry"]["id"],
                source="synthetic",
                category=c.get("category", "rules"),
                expected_decision=exp["decision"],
                expected_rule_ids=rule_ids,
                expected_llm_rule_ids=[x for x in exp["rule_ids"] if x == "R013"],
                adversarial=c.get("adversarial"),
                off_decision=exp.get("off_decision"),
                llm_allowed=list(exp.get("llm_allowed", [])),
            )
        )
        entries.append(c["entry"])
    return golden, synthetic, entries


def _judge(client: LlmClient, results: list[EntryResult], coa: CoaTree) -> dict[str, Any] | None:
    """LLM-as-judge clarity (1-5). Live/record only: a judge replayed from tape measures nothing."""
    if client.mode not in {"live", "record"}:
        return None
    scores: dict[str, int] = {}
    for r in results:
        if r.explanation_source != "llm" or not r.explanation:
            continue
        payload = {
            "role": "judge",
            "decision": r.decision.value,
            "entry": entry_payload(r.entry, coa),
            "findings": findings_payload(r.findings),
            "explanation": r.explanation,
        }
        obj, _ = client.structured(
            "judge", ClarityScore, payload, orjson.dumps(payload).decode(), r.entry.id
        )
        if obj is not None:
            scores[r.entry.id] = obj.score
    if not scores:
        return None
    mean = sum(scores.values()) / len(scores)
    return {"mean": f"{mean:.2f}", "scores": scores}


def _row(case: Case, r: EntryResult, llm_enabled: bool) -> dict[str, Any]:
    exp_decision = expected_decision(case, llm_enabled)
    exp_ids = sorted(case.expected_rule_ids)
    got_ids = sorted(deterministic_ids(r))
    exp_llm = sorted(case.expected_llm_rule_ids) if llm_enabled else []
    got_llm = sorted(llm_ids(r))
    return {
        "id": case.id,
        "source": case.source,
        "category": case.category,
        "expected_decision": exp_decision,
        "actual_decision": r.decision.value,
        "expected_rule_ids": exp_ids,
        "actual_rule_ids": got_ids,
        "expected_llm_rule_ids": exp_llm,
        "actual_llm_rule_ids": got_llm,
        "explanation_source": r.explanation_source,
        "llm_extra_allowed": sorted(set(got_llm) - set(exp_llm)),
        "match": exp_decision == r.decision.value
        and exp_ids == got_ids
        and set(exp_llm) <= set(got_llm) <= set(exp_llm) | set(case.llm_allowed),
    }


def _miss_rate(calls: list[dict[str, Any]]) -> str:
    replayed = [e for e in calls if e.get("mode") == "cassette"]
    if not replayed:
        return "n/a (no cassette calls)"
    return ratio(sum(1 for e in replayed if e.get("cassette_miss")), len(replayed))


def run_evals(settings: Settings, out_dir: Path | None = None) -> EvalResult:
    prep = prepare(settings)
    if prep.rule_ctx is None:
        raise RuntimeError(
            f"Evaluation needs a base ledger; the run is blocked: {prep.blocked_reason}"
        )
    ctx = prep.rule_ctx
    golden, synthetic, syn_entries = load_cases()
    tracer = Tracer(f"eval-{prep.run_id}")
    client = LlmClient(settings, tracer)
    llm_enabled = client.enabled

    golden_results = {
        r.entry.id: r for r in run_batch(prep.audit.entries, ctx, prep.run_id, client, tracer)
    }
    syn_results = {
        r.entry.id: r
        for r in run_batch(
            [entry_from_dict(e) for e in syn_entries], ctx, prep.run_id, client, tracer
        )
    }
    g_pairs = [(c, golden_results[c.id]) for c in golden]
    s_pairs = [(c, syn_results[c.id]) for c in synthetic]
    rule_pairs = g_pairs + [(c, r) for c, r in s_pairs if c.category == "rules"]
    intent_pairs = [(c, r) for c, r in s_pairs if c.category == "intent"]
    all_results = [r for _, r in g_pairs + s_pairs]

    faith = explanation_faithfulness(all_results, ctx.coa)
    schema, schema_errors = schema_validity(all_results)
    echo, echo_bad = adversarial_echo_free(s_pairs)
    llm_golden_ok = sum(
        1 for c, r in g_pairs if sorted(llm_ids(r)) == sorted(c.expected_llm_rule_ids)
    )
    calls = [e for e in tracer.events if e["event"] == "llm.call"]
    summary: dict[str, Any] = {
        "llm_mode": settings.llm.mode,
        "decision_accuracy_golden": decision_accuracy(g_pairs, llm_enabled),
        "decision_accuracy_synthetic_rules": decision_accuracy(
            [p for p in s_pairs if p[0].category == "rules"], llm_enabled
        ),
        "decision_accuracy_intent": decision_accuracy(intent_pairs, llm_enabled),
        "intent_reviewer_agreement_golden": ratio(llm_golden_ok, len(g_pairs))
        if llm_enabled
        else "n/a (llm off)",
        "explanation_faithfulness_numbers": faith.numbers,
        "explanation_faithfulness_codes": faith.codes,
        "outputs_checked_for_faithfulness": faith.checked,
        "schema_validity": schema,
        "adversarial_echo_free": echo,
        "guardrail_fallback_rate": fallback_rate(tracer.events),
        "cassette_miss_rate": _miss_rate(calls),
        "llm_calls": len(calls),
        "cases": {"golden": len(golden), "synthetic": len(synthetic)},
    }
    judge = _judge(client, all_results, ctx.coa)
    summary["llm_judge_clarity"] = judge["mean"] if judge else "n/a (live mode only)"
    passed = (
        summary["decision_accuracy_golden"] == "1.0000"
        and faith.numbers == "1.0000"
        and faith.codes == "1.0000"
    )
    report: dict[str, Any] = {
        "run_id": prep.run_id,
        "passed": passed,
        "gate": GATE,
        "summary": summary,
        "per_rule": rule_precision_recall(rule_pairs),
        "entries": [_row(c, r, llm_enabled) for c, r in g_pairs + s_pairs],
        "faithfulness_violations": faith.violations,
        "schema_errors": schema_errors,
        "adversarial_echo_cases": echo_bad,
        "judge": judge,
    }
    write_report(report, out_dir or OUT_DIR)
    return EvalResult(report, passed)


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Evaluation report",
        "",
        f"*Generated by `finagent eval` for run `{report['run_id']}` "
        f"(LLM mode `{s['llm_mode']}`).*",
        "",
        f"**Gate: {'PASSED' if report['passed'] else 'FAILED'}** — {report['gate']}.",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for k, v in s.items():
        if k == "cases":
            v = f"{v['golden']} golden + {v['synthetic']} synthetic"
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        "## Per-rule precision / recall",
        "",
        "| Rule | TP | FP | FN | Precision | Recall |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for rid, m in report["per_rule"].items():
        lines.append(
            f"| {rid} | {m['tp']} | {m['fp']} | {m['fn']} | {m['precision']} | {m['recall']} |"
        )
    lines += [
        "",
        "## Per-entry: expected vs actual",
        "",
        ENTRY_HEADER,
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for e in report["entries"]:
        mark = "✓" if e["match"] else "**✗**"
        exp_rules = ", ".join(e["expected_rule_ids"]) or "—"
        got_rules = ", ".join(e["actual_rule_ids"]) or "—"
        llm = ", ".join(e["actual_llm_rule_ids"]) or "—"
        if e["llm_extra_allowed"]:
            llm += " (allowed)"
        lines.append(
            f"| {e['id']} | {e['source']}/{e['category']} | {e['expected_decision']} | "
            f"{e['actual_decision']} | {exp_rules} | {got_rules} | {llm} | "
            f"{e['explanation_source']} | {mark} |"
        )
    if report["faithfulness_violations"]:
        lines += ["", "## Faithfulness violations", ""]
        for eid, v in report["faithfulness_violations"].items():
            lines.append(f"- {eid}: {'; '.join(v)}")
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_bytes(
        orjson.dumps(report, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    (out_dir / "report.md").write_text(render_markdown(report), encoding="utf-8", newline="\n")
