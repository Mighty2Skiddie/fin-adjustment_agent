# PHASE 7 — Deliverables & deploy

Read `docs/06_BUILD_PLAN.md` Phase 7, `docs/09_REFLECTION_TEMPLATE.md`, `docs/10_AI_USAGE_TEMPLATE.md`.

1. Produce `docs/ARCHITECTURE.md` from `docs/03_ARCHITECTURE.md`: insert screenshots, a real
   trace excerpt for JE-008, the final Data Health counts, the final decision table, and a
   "Prototype evidence" column filled from actual output. Keep every section. Export
   `docs/ARCHITECTURE.pdf` (use `pandoc` if available; otherwise instruct me to print to PDF).
2. Draft `docs/REFLECTION.md` (one page) from the template using the real `AI_USAGE` log I provide.
3. Finalise `README.md`: 3-command local run (`uv sync`, `uv run finagent run`, `uv run finagent serve`),
   Docker run, HF Spaces link, screenshots, scope boundary, how to switch to live LLM, how to
   record cassettes, deliverables index (architecture, reflection, AI usage, clarifying questions,
   assumptions, defect log, output run, traces, evals).
4. Force-add one completed run: `output/runs/<run_id>/`, `output/runs/LATEST`,
   `output/traces/<run_id>.jsonl`, `output/DEFECT_LOG.md`, `output/evals/`.
5. `Dockerfile` (multi-stage per `docs/04_BACKEND_SPEC.md` §13) and `.dockerignore`; build and run
   locally on 7860 to verify. Write `docs/DEPLOY.md` with the Hugging Face Spaces steps
   (Docker Space, push, set `LLM_MODE=cassette`).
6. CI green; tag `v1.0.0`; commit `docs: final deliverables`. List every deliverable and its path.
