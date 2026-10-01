# PHASE 5 — Evals

Read `docs/04_BACKEND_SPEC.md` §10.

1. `evals/golden/expected_decisions.json` from `docs/02_DATA_SPEC.md` §7;
   `evals/golden/synthetic_entries.json` with ≥12 variants as listed, each with expected decision
   and rule ids.
2. `evals/checks.py` (decision_accuracy, per-rule precision/recall, explanation_faithfulness for
   numbers and codes, schema_validity, fallback_rate; `llm_judge_clarity` only when live).
3. `evals/run_evals.py` → `output/evals/report.md` + `report.json`; `finagent eval`.
4. CI step fails when golden decision_accuracy < 1.0 or faithfulness < 1.0.
5. Commit `feat(evals): golden + synthetic evaluation harness`. Paste `report.md`.
