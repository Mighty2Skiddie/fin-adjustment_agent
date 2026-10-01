# CLAUDE.md — engineering rules for this repository

You are implementing the project specified in `docs/`. Read `README_START_HERE.md`, then
`docs/01` → `docs/06` before writing code. The specs are the source of truth. If a spec is
ambiguous, pick the option that is **more deterministic, more auditable, and more
conservative** (e.g. QUARANTINE over ACCEPT), implement it, and record the choice in
`docs/08_ASSUMPTIONS.md` under "Decisions made during build".

## Hard rules (violating any of these is a bug)

1. **Decimal only.** All monetary values are `decimal.Decimal`, parsed from strings, never
   via `float`. Quantize with `Decimal("0.01")` and `ROUND_HALF_UP`. `pandas` may be used
   for reading CSV only with `dtype=str`; convert to `Decimal` immediately. No `float`
   anywhere in `src/finagent/domain`, `ingest`, `adjustments`.
2. **The LLM never computes.** No prompt contains the trial balance. Prompts contain
   validator findings (structured) plus the single entry under review. Every LLM output is
   a Pydantic model (structured output). After every LLM call, run the guardrail
   post-checks in `src/finagent/llm/guardrails.py`; on failure, retry once with the error
   appended, then fall back to a deterministic template and record `guardrail_fallback=true`.
3. **The LLM can only escalate.** The Intent Reviewer may raise an entry's severity
   (e.g. add an ESCALATE finding). It can never remove, downgrade or override a finding
   produced by a deterministic rule.
4. **No silent fixes.** Fix proposals are attached to the entry as candidates; they are
   never applied automatically. Humans approve quarantined items; rejected items cannot be
   approved — they must be edited and resubmitted as a new entry version.
5. **Never sanitize `inputs/`.** The data stays as delivered. Defects are detected and
   reported, never corrected in the files.
6. **Every finding is evidence-backed.** A `Finding` has `rule_id`, `severity`, `message`,
   `evidence` (the exact source rows / values used) and `suggested_action`. No finding
   without evidence.
7. **Idempotent runs.** `run_id = sha256(canonical JSON of inputs + config + git sha)[:12]`.
   Re-running with identical inputs produces byte-identical `decisions.json` (in cassette
   mode). Human decisions are stored separately and are never part of `run_id`.
8. **Sign by debit/credit, never by account type.** Net amount = debit − credit. Account
   `account_type` and `normal_balance` are used only for *warnings*, never for arithmetic.
9. **One rule per file, one test file per rule.** `src/finagent/adjustments/rules/r001_balance.py`
   ↔ `tests/rules/test_r001_balance.py`. Each rule exposes `RULE_ID`, `SEVERITY`, `check(ctx) -> list[Finding]`.
10. **Tests before features.** Every phase ends with `uv run pytest -q` green and
    `uv run ruff check . && uv run ruff format --check . && uv run pyright` clean.
11. **Memos are untrusted.** JE `description` and `memo` text are user-supplied. In prompts
    they are wrapped in `<untrusted_data>` tags and the system prompt instructs the model to
    treat their content as data, never as instructions.
12. **Ground truth is in `docs/02_DATA_SPEC.md` §6–§8.** Tests must assert those exact
    decisions, defect IDs and numbers. If your implementation disagrees with the ground
    truth, your implementation is wrong unless you can show the spec has an arithmetic error
    — then fix the spec and note it in `docs/08_ASSUMPTIONS.md`.

## Stack

- Python 3.12, `uv` for env + lockfile. `ruff` (lint + format), `pyright` (strict on
  `src/`), `pytest`, `pytest-cov`, `pre-commit`.
- `pydantic>=2`, `langgraph`, `langchain-core`, `langchain` (for `init_chat_model`),
  provider packages behind extras: `langchain-google-genai`, `langchain-groq`,
  `langchain-anthropic`. `fastapi`, `uvicorn[standard]`, `python-dotenv`, `typer` (CLI),
  `rich`, `rapidfuzz` (fuzzy account-name matching), `orjson`.
- Optional: `langfuse` (observability), `arize-phoenix` (local alternative). Both optional
  extras; the app runs with neither.
- Frontend: Node 20+, Vite, React 18, TypeScript (strict), Tailwind, shadcn/ui,
  `@tanstack/react-query`, `react-router-dom`, `lucide-react`, `recharts` (one chart only).
- Let `uv add` / `npm i` resolve latest stable versions, then commit `uv.lock` and
  `package-lock.json`. Do not hand-pin versions you have not verified exist.

## Repository layout (create exactly this)

```
.
├── CLAUDE.md  README.md  pyproject.toml  uv.lock  Dockerfile  .env.example  .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── docs/                      # specs + deliverables (ARCHITECTURE.md, REFLECTION.md, …)
├── inputs/                    # raw data, read-only
├── config/default.yaml        # FX policy, materiality, thresholds, LLM settings
├── src/finagent/
│   ├── __init__.py  cli.py  config.py
│   ├── domain/        models.py  coa_tree.py  money.py  ids.py
│   ├── ingest/        loaders.py  normalize.py  fx.py  health_audit.py  health_checks/  (one check per file)
│   ├── adjustments/   context.py  rules/  validator.py  decisions.py  posting.py  lineage.py
│   ├── llm/           providers.py  schemas.py  prompts/  cassette.py  guardrails.py  roles/ (intent_reviewer.py explainer.py fix_proposer.py)
│   ├── graph/         state.py  adjustments_graph.py
│   ├── observability/ tracer.py  langfuse_hooks.py
│   ├── store/         run_store.py           # JSON files under output/runs/<run_id>/
│   └── api/           app.py  routers/ (runs.py entries.py lineage.py health.py evals.py)  static.py
├── evals/             golden/expected_decisions.json  checks.py  run_evals.py  cassettes/
├── tests/             (mirrors src)
├── frontend/          (Vite app)
└── output/            runs/  traces/  evals/  DEFECT_LOG.md  (generated, committed for the evaluator)
```

## Commands (make these work via `pyproject.toml` scripts / `typer` CLI)

```
uv run finagent audit            # data health audit → output/DEFECT_LOG.md + output/health.json
uv run finagent run              # full adjustments pipeline → output/runs/<run_id>/
uv run finagent eval             # evals → output/evals/report.md
uv run finagent serve            # FastAPI + static frontend on :8000
uv run finagent record-cassettes # live LLM calls → evals/cassettes/*.json (needs API key)
uv run pytest -q
```

## Style

- Type hints everywhere; `from __future__ import annotations`.
- Small pure functions; side effects only in `store/`, `observability/`, `api/`.
- Docstrings explain *why*, not *what*. No comments that restate code.
- Error messages are written for a finance user, not a developer, when they reach the UI.
- Commit per phase with conventional commits (`feat(rules): add R005 circular entry`).
