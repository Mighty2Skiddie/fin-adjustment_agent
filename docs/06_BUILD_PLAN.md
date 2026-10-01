# 06 — Build plan: phases, acceptance criteria, commands

Each phase is one Claude Code session (prompt in `prompts/PHASE_n.md`). A phase is done
when every acceptance check passes **and** the work is committed. Windows commands are
PowerShell; everything also runs in bash.

## Phase 0 — Scaffold & tooling (≈30 min)

Install prerequisites once (skip what you have):
```powershell
winget install --id astral-sh.uv -e            # uv (Python package manager)
winget install --id OpenJS.NodeJS.LTS -e       # Node 20+
winget install --id Git.Git -e
uv python install 3.12
```
Claude Code creates: `pyproject.toml` (project `finagent`, `[project.scripts] finagent = "finagent.cli:app"`, extras `llm-google`, `llm-groq`, `llm-anthropic`, `observability`), `uv.lock`, `.pre-commit-config.yaml` (ruff, ruff-format, pyright), `.github/workflows/ci.yml` (uv sync → ruff → pyright → pytest → `finagent audit` → `finagent eval`), `.env.example`, `config/default.yaml`, `README.md` skeleton, empty package tree per `CLAUDE.md`, `frontend/` via `npm create vite@latest frontend -- --template react-ts` + Tailwind + shadcn init.

Acceptance:
```powershell
uv sync; uv run finagent --help                 # shows audit/run/eval/serve/record-cassettes
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

Build `llm/`, `graph/`. If you have a free API key: `uv run finagent record-cassettes`
then commit `evals/cassettes/`. If not, Claude Code writes cassette JSON by hand that
satisfies the schemas and the expected behaviour in `02_DATA_SPEC §7` (label them
`"recorded_at": "hand-authored"` in the file so this is transparent) — the pipeline, guardrails
and UI are exercised identically. Replace with real recordings later.

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

`api/` per `04 §9`, then the six pages per `05`. Build with real data from the committed run.

Acceptance:
```powershell
uv run finagent serve                           # http://localhost:8000 serves the app
uv run pytest tests/api -q
cd frontend; npm run build; npm run lint; cd ..
```
Manual: approve JE-003 with a reason → ledger shows 1110 + 11,200.00 with a HUMAN lineage
ref; audit log has the event; try approving JE-002 → blocked with the explanation.

## Phase 7 — Deliverables & deploy (≈2.5 h)

1. `docs/ARCHITECTURE.md` finalised (copy of `03_ARCHITECTURE.md` with screenshots, a real
   trace excerpt, final numbers) → export PDF (`pandoc` or print-to-PDF).
2. `docs/REFLECTION.md` from `09_REFLECTION_TEMPLATE.md` (one page).
3. `docs/AI_USAGE.md` from `10_AI_USAGE_TEMPLATE.md`.
4. `README.md`: 3-command setup, screenshots, links, scope boundary, how to run live LLM.
5. Commit a completed run under `output/` so the evaluator sees artifacts without running.
6. Deploy to Hugging Face Spaces (Docker Space, port 7860): create Space → `git remote add hf …`
   → push. Set `LLM_MODE=cassette` as a Space variable. Verify public URL.
7. Final CI green, tag `v1.0.0`.

## Time and cut list

Total ≈ 12 h. If you must cut: Langfuse (keep JSONL), Evals page (keep CLI report),
keyboard shortcuts, dark mode. Never cut: the architecture doc, the health audit, golden
tests, lineage, the clarifying questions.
