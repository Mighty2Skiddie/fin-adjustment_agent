# PHASE 1 — Domain, ingest, FX, Data Health audit

Read `CLAUDE.md`, `docs/02_DATA_SPEC.md` (§1–§6 fully), `docs/04_BACKEND_SPEC.md` §2–§3.

1. Implement `src/finagent/domain/{money,models,coa_tree,ids}.py` exactly as specified. Write
   `tests/domain/test_money.py` (quantize HALF_UP, parse from JSON float via str, formatting) and
   a repo-hygiene test that fails if the string `float(` appears anywhere under
   `src/finagent/domain`, `src/finagent/ingest`, `src/finagent/adjustments`.
2. Implement `ingest/loaders.py`, `ingest/fx.py` (`RateBook` with all three missing-rate
   policies and `is_fallback` rate ids), `ingest/normalize.py` (`build_base_ledger`: translate →
   sum per account with full lineage → mark unmapped → translation-difference line → H-TB-01).
3. Implement one module per health check in `ingest/health_checks/` for every ID in
   `docs/02_DATA_SPEC.md` §6 (H-TB-01..06, H-COA-01..06, H-PP-01..04, H-FX-01..02,
   H-ADJ-01..02). Each returns `list[HealthFinding]` with evidence values as Decimal strings.
4. Implement `ingest/health_audit.py`: runs all checks, writes `output/health.json` and renders
   `output/DEFECT_LOG.md` (grouped by file, severity-ordered, with a header line stating how
   many findings were listed in the brief vs found: the brief's table lists 10 — TB 3, COA 2, adjustments 3, prior TB 1, FX 1; count ours).
5. Wire `finagent audit` in `cli.py` with a Rich table.
6. Tests: `tests/ingest/test_loaders.py`, `test_fx.py` (every policy), `test_normalize.py`,
   `test_health_audit.py` asserting EVERY exact value in `docs/02_DATA_SPEC.md` §6 (e.g. H-TB-01
   evidence raw Δ "-4800.00", usd_only Δ "-1242500.00", pe_gbp_avg Δ "182460.20", pe_gbp_open Δ
   "177100.30"; GBP translated "521147.20"; prior usd_only Δ "1737000.00"; etc.).
7. Run acceptance from `docs/06_BUILD_PLAN.md` Phase 1. Commit `feat(ingest): data health audit`.
   Paste `output/DEFECT_LOG.md` in your summary.
