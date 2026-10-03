# 06 — Build plan: phases, acceptance criteria, commands

The work was done in phases. A phase is done when every acceptance check passes **and**
the work is committed. Windows commands are PowerShell. Everything also runs in bash.

Status when this page was last checked: the git history has 3 commits. The last one is
`c170718 feat(ingest): data health audit`. The work from Phase 2 onward is in the working
tree but not yet committed, and there is no `v1.0.0` tag yet. The run manifest shows this
as `code_version: c170718+5684ecb9` (the last commit plus a hash of the uncommitted code).

## Phase 0 — Scaffold & tooling (≈30 min)

Install prerequisites once (skip what you have):
```powershell
winget install --id astral-sh.uv -e            # uv (Python package manager)
winget install --id OpenJS.NodeJS.LTS -e       # Node 20+
winget install --id Git.Git -e
uv python install 3.12
```
Phase 0 creates: `pyproject.toml` (project `finagent`, `[project.scripts] finagent = "finagent.cli:app"`, extras `llm-google`, `llm-groq`, `llm-anthropic`, `observability`; `llm-openai` was added later), `uv.lock`, `.pre-commit-config.yaml` (ruff, ruff-format, pyright), `.github/workflows/ci.yml` (uv sync → ruff → pyright → pytest → `finagent audit` → `finagent eval`), `.env.example`, `config/default.yaml`, `README.md` skeleton, empty package tree per `docs/ENGINEERING_RULES.md`, `frontend/` via `npm create vite@latest frontend -- --template react-ts` + Tailwind + shadcn init.

Acceptance:
```powershell
uv sync; uv run finagent --help                 # shows audit/run/eval/serve/record-cassettes/show
uv run pytest -q                                # 1 smoke test passes
cd frontend; npm ci; npm run build; cd ..       # dist/ exists
git log --oneline | Select-Object -First 1      # "chore: scaffold project"
```

## Phase 1 — Domain, ingest, FX, Data Health audit (≈1.5 h)

Build `domain/`, `ingest/` (loaders, fx, normalize), all `health_checks/`, `health_audit.py`,
`finagent audit`.

Acceptance:
```powershell
uv run finagent audit
Get-Content output\DEFECT_LOG.md                # every ID from 02_DATA_SPEC §6 present
uv run pytest tests/ingest -q                   # asserts exact numbers (71,259,460.20 / 182,460.20 / 1,737,000.00 / 521,147.20 …)
```
Checks the reviewer makes: `float(` absent from domain/ingest; H-TB-01 shows all four
policy variants; GBP line carries `is_fallback=True` rate id `GBP/period_average`.

## Phase 2 — Rules, decisions, impact, posting, lineage (≈1.5 h)

Build `adjustments/` fully, with `llm.mode=off` (template explanations). `finagent run`
produces `output/runs/<id>/` with `decisions.json`, `posted_tb.csv`, `manifest.json`.

Acceptance:
```powershell
uv run finagent run --llm-mode off
uv run pytest tests/rules tests/adjustments -q  # golden: 6 ACCEPTED / 2 REJECTED / 2 QUARANTINED; posting numbers from 02 §8; lineage sums
```
Run twice → identical `decisions.json` (idempotency test).

## Phase 3 — LLM roles, guardrails, cassettes, graph (≈1.5 h)

Build `llm/` and `graph/`. With a free API key, run `uv run finagent record-cassettes`,
then commit `evals/cassettes/`. The plan allowed hand-written cassettes (labelled
`"recorded_at": "hand-authored"`) if no key was available. In the end all cassettes are
real recordings (decision D17).

Acceptance:
```powershell
uv run finagent run --llm-mode cassette         # explanation_source "llm" for non-accepted entries
uv run pytest tests/llm tests/graph -q          # guardrail violations → retry → fallback; loop stops at 2; adversarial memo ignored
```

## Phase 4 — Observability & run store (≈45 min)

`observability/tracer.py`, `store/run_store.py`, audit log, manifest metrics, optional Langfuse.

Acceptance: `output/traces/<run_id>.jsonl` has `rule.result`, `llm.call`, `guardrail.result`,
`decision`, `invariant` events; `manifest.json.metrics` populated; `LATEST` pointer written.

## Phase 5 — Evals (≈1 h)

`evals/golden`, synthetic set, `checks.py`, `run_evals.py`, CI gate.

Acceptance:
```powershell
uv run finagent eval
Get-Content output\evals\report.md              # decision_accuracy 1.0, faithfulness 1.0
```

## Phase 6 — API + frontend (≈3 h)

`api/` per `04 §9`, then the pages per `05` (six run pages plus About). Build with real data from the committed run.

Acceptance:
```powershell
uv run finagent serve                           # http://localhost:8000 serves the app
uv run pytest tests/api -q
cd frontend; npm run build; npm run lint; cd ..
```
Manual: approve JE-003 with a reason → ledger shows 1110 + 11,200.00 with a HUMAN lineage
ref; audit log has the event; try approving JE-002 → blocked with the explanation.

## Phase 7 — Deliverables & deploy (≈2.5 h)

1. `docs/ARCHITECTURE.md` finished (with screenshots, diagrams in `docs/diagrams/`, a real
   trace excerpt and final numbers) → export to PDF (`docs/ARCHITECTURE.pdf`).
2. `docs/REFLECTION.md` (one page).
3. `docs/AI_USAGE.md`.
4. `README.md`: 3-command setup, screenshots, links, scope boundary, how to run live LLM.
5. Commit a completed run under `output/` so the evaluator sees artifacts without running.
6. Deploy to Hugging Face Spaces (Docker Space, port 7860): create the Space → `git remote add hf …`
   → push. Set `LLM_MODE=cassette` as a Space variable. Check the public URL. Steps are in
   `docs/DEPLOY.md`.
7. Final CI green, tag `v1.0.0`.

## Time and cut list

Total ≈ 12 h. If you must cut: Langfuse (keep JSONL), Evals page (keep CLI report),
keyboard shortcuts, dark mode. Never cut: the architecture doc, the health audit, golden
tests, lineage, the clarifying questions.
