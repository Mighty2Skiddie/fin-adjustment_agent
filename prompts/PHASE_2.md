# PHASE 2 — Rules, decisions, impact, posting, lineage

Read `CLAUDE.md`, `docs/02_DATA_SPEC.md` §7–§9, `docs/04_BACKEND_SPEC.md` §4.

1. Implement `adjustments/rules/base.py`, one file per rule R001–R012 (R013 is the LLM finding,
   created in Phase 3), registry `ALL_RULES`, `validator.run_rules`, `decisions.decide`.
2. Implement `adjustments/impact.py` (ancestor walk; NI/A/L/E deltas), `adjustments/posting.py`
   (accepted + human-approved overlay; JE and HUMAN lineage refs; imbalance-unchanged
   assertion; `posted_tb.csv/json`), `adjustments/lineage.py` (`explain_line`).
3. Implement `llm/templates.py` now (deterministic explanation text from findings) so `--llm-mode off`
   yields `explanation_source="template"` for non-accepted entries.
4. `finagent run [--fx-policy] [--llm-mode off]` producing `output/runs/<run_id>/` with
   `manifest.json`, `health.json`, `base_ledger.json`, `decisions.json`, `posted_tb.*`,
   `audit_log.jsonl`, and `output/runs/LATEST`. Implement `store/run_store.py` minimally here
   (full metrics in Phase 4). `run_id` per `CLAUDE.md` rule 7.
5. Tests: `tests/rules/test_r0XX_*.py` for every rule (positive + negative);
   `tests/adjustments/test_golden_decisions.py` asserting the exact decision and rule ids per
   entry from `docs/02_DATA_SPEC.md` §7 (6 ACCEPTED / 2 REJECTED / 2 QUARANTINED);
   `test_posting.py` asserting every row of §8; `test_lineage.py` (components sum to each line);
   `test_impact.py`; `test_idempotency.py` (two runs → identical `decisions.json`).
6. Acceptance per `docs/06_BUILD_PLAN.md` Phase 2. Commit `feat(adjustments): rule engine, posting, lineage`.
   Paste the decision table.
