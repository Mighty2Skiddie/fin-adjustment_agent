# Engineering rules

These are the rules this repository follows. The specs in `docs/01` to `docs/06` describe
what to build. The specs are the source of truth.

When a spec is unclear, we choose the option that is:

- more **deterministic** (same input gives the same output),
- more **auditable** (easy to check later), and
- more **conservative** (for example, QUARANTINE instead of ACCEPT).

We then write the choice down in `docs/08_ASSUMPTIONS.md`, under "Decisions made during build".

## Hard rules

Breaking any of these rules is a bug.

1. **Money is always `Decimal`.**
   Every amount is a `decimal.Decimal` read from text. It never passes through `float`.
   We round to 0.01 with `ROUND_HALF_UP`. `pandas` may read a CSV only with `dtype=str`,
   and the values become `Decimal` right away. No `float` is allowed in
   `src/finagent/domain`, `ingest` or `adjustments`.

2. **The AI model never does the maths.**
   No prompt contains the trial balance (the list of every account and its total).
   A prompt holds only the rule findings and the one entry under review.
   Every model answer must fit a fixed Pydantic schema (a strict data shape).
   After every model call, the code runs the checks in `src/finagent/llm/guardrails.py`.
   If a check fails, the call is tried once more with the error added.
   If it fails again, the system uses a fixed text template and records `guardrail_fallback=true`.

3. **The AI model can only make things stricter.**
   The Intent Reviewer may raise an entry's severity (for example, add an ESCALATE finding).
   It can never remove, lower or override a finding made by a rule.

4. **No silent fixes.**
   Fix proposals are attached to the entry as suggestions. They are never applied
   automatically. A human approves quarantined entries. A rejected entry can never be
   approved. It must be edited and sent again as a new version.

5. **Never clean the files in `inputs/`.**
   The data stays exactly as delivered. We find and report defects. We never correct
   them in the files.

6. **Every finding has evidence.**
   A `Finding` has `rule_id`, `severity`, `message`, `evidence` (the exact source rows and
   values used) and `suggested_action`. A finding without evidence is not allowed.

7. **Runs are repeatable.**
   `run_id` = the first 12 characters of a sha256 hash of the inputs, the config and the
   code version. Running again with the same inputs (in cassette mode) gives a
   byte-identical `decisions.json`. Human decisions are stored separately. They are never
   part of the `run_id`.

8. **The sign comes from debit and credit, never from account type.**
   Net amount = debit − credit. The fields `account_type` and `normal_balance` are used only
   for warnings, never for maths.

9. **One rule per file, one test file per rule.**
   For example, `src/finagent/adjustments/rules/r001_balance.py` is tested by
   `tests/rules/test_r001_balance.py`. Each rule file exposes `RULE_ID`, `SEVERITY`, `TITLE`
   and `check(entry, ctx) -> list[Finding]`.

10. **Tests come before features.**
    Every phase ends with `uv run pytest -q` passing, and with
    `uv run ruff check . && uv run ruff format --check . && uv run pyright` clean.

11. **Memos are untrusted.**
    The journal entry (JE) `description` and `memo` text come from users. In prompts this
    text sits inside `<untrusted_data>` tags. The system prompt tells the model to treat it
    as data, never as instructions.

12. **The correct answers are in `docs/02_DATA_SPEC.md` §6–§8.**
    Tests must check those exact decisions, defect IDs and numbers. If the code disagrees
    with them, the code is wrong. The only exception: the spec itself has a maths error.
    Then we fix the spec and record it in `docs/08_ASSUMPTIONS.md`.

## Stack

**Backend**

- Python 3.12. `uv` manages the environment and the lock file (`uv.lock`).
- Quality tools: `ruff` (lint and format), `pyright` (strict on `src/`), `pytest`,
  `pytest-cov`, `pre-commit`.
- Libraries: `pydantic` v2, `pydantic-settings`, `langgraph`, `langchain-core`,
  `langchain` (for `init_chat_model`), `fastapi`, `uvicorn[standard]`, `python-dotenv`,
  `pyyaml`, `typer` (command line), `rich`, `rapidfuzz` (fuzzy account-name matching),
  `orjson`.
- AI provider packages are optional extras: `llm-google` (Gemini), `llm-groq`,
  `llm-anthropic`, `llm-openai`. The default is Gemini, replayed from recordings.
- Optional extra `observability` adds `langfuse`. The app runs without it.

**Frontend**

- Node 20+, Vite, React 19, TypeScript (strict), Tailwind CSS 4, shadcn/ui,
  `@tanstack/react-query`, `react-router-dom`, `lucide-react`, `sonner` (toasts),
  `react-markdown`, IBM Plex fonts. Lint with `oxlint`. No chart library: the numbers are
  shown in tables.
- React 19 replaced the planned React 18 (see decision D1).

**Versions**

`uv add` and `npm i` choose the latest stable versions. We commit `uv.lock` and
`package-lock.json`. We do not hand-pin versions we have not checked.

## Repository layout

```
.
├── README.md  pyproject.toml  uv.lock  Dockerfile  .dockerignore  .gitignore
├── .env.example  .pre-commit-config.yaml  .gitattributes  .python-version
├── .github/workflows/ci.yml
├── docs/
│   ├── 00_ASSIGNMENT_ORIGINAL.pdf
│   ├── 01_PROJECT_BRIEF.md … 08_ASSUMPTIONS.md   # source specs (there is no 03)
│   ├── ARCHITECTURE.md  ARCHITECTURE.pdf  DEPLOY.md
│   ├── REFLECTION.md  AI_USAGE.md  ENGINEERING_RULES.md
│   ├── diagrams/      # architecture, entry-workflow, data-lineage,
│   │                  # decision-lifecycle, approve-sequence (.html)
│   └── screenshots/   # 01-data-health.png … 04-trace-je008.png
├── inputs/            # raw data, read-only
├── config/default.yaml   # FX policy, materiality, thresholds, LLM settings
├── src/finagent/
│   ├── __init__.py  cli.py  config.py  pipeline.py
│   ├── domain/        models.py  coa_tree.py  money.py  ids.py
│   ├── ingest/        loaders.py  normalize.py  fx.py  fuzzy.py  health_audit.py
│   │                  health_checks/   (one check per file, h_tb_01.py …)
│   ├── adjustments/   context.py  rules/  validator.py  decisions.py  impact.py
│   │                  posting.py  lineage.py
│   ├── llm/           providers.py  schemas.py  payloads.py  templates.py  cassette.py
│   │                  guardrails.py  prompts/ (*.md)
│   │                  roles/ (intent_reviewer.py  explainer.py  fix_proposer.py)
│   ├── graph/         state.py  adjustments_graph.py
│   ├── observability/ tracer.py  langfuse_hooks.py
│   ├── store/         run_store.py      # JSON files under output/runs/<run_id>/
│   └── api/           app.py  deps.py  service.py  static.py
│                      routers/ (runs.py  entries.py  lineage.py  health.py  evals.py)
├── evals/             checks.py  run_evals.py
│                      golden/ (expected_decisions.json  synthetic_entries.json)
│                      cassettes/ (intent_reviewer/  explainer/  fix_proposer/  judge/)
├── tests/             # mirrors src/
├── frontend/          # Vite app, builds to frontend/dist
└── output/            # generated, committed so a reader sees results without running
    ├── DEFECT_LOG.md  health.json
    ├── runs/          LATEST  <run_id>/
    ├── traces/        <run_id>.jsonl
    └── evals/         report.md  report.json
```

## Commands

The `finagent` command is defined in `pyproject.toml` and built with `typer`.

| Command | What it does |
|---|---|
| `uv run finagent audit [--fx-policy …]` | Data health audit. Writes `output/DEFECT_LOG.md` and `output/health.json`. |
| `uv run finagent run [--fx-policy …] [--llm-mode …]` | Full adjustments pipeline. Writes `output/runs/<run_id>/`. |
| `uv run finagent eval [--llm-mode …]` | Golden and synthetic evals. Writes `output/evals/report.md`. Exits with 1 if the quality gate fails. |
| `uv run finagent serve [--port 8000] [--host 127.0.0.1]` | API and web app on port 8000 (the container uses 7860). Creates the first run if none exists. |
| `uv run finagent record-cassettes [--clean]` | Live AI calls. Writes `evals/cassettes/<role>/*.json`. Needs an API key. |
| `uv run finagent show [run_id]` | Prints a stored run: manifest, metrics, invariants and decisions. The default is `latest`. |
| `uv run pytest -q` | Runs all tests. |

Options: `--fx-policy` is `block`, `fallback_average` or `fallback_opening`.
`--llm-mode` is `cassette`, `live` or `off`.

## Style

- Type hints everywhere. Every module with code starts with `from __future__ import annotations`.
- Small pure functions. Side effects only in `store/`, `observability/` and `api/`.
- Docstrings explain *why*, not *what*. No comments that repeat the code.
- Error messages that reach the UI are written for a finance user, not a developer.
- One commit per phase, using conventional commit messages
  (for example `feat(rules): add R005 circular entry`).
