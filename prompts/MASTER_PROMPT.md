# MASTER PROMPT — paste into Claude Code at the repo root

You are implementing a complete project from a specification kit that is already in this
repository. Do not ask me what to build; the kit answers that. Work in **plan mode first**,
then execute phase by phase, committing after each phase.

## Step 1 — Read, in this order, completely

1. `README_START_HERE.md`
2. `CLAUDE.md` (rules — these override your defaults)
3. `docs/01_PROJECT_BRIEF.md`
4. `docs/02_DATA_SPEC.md` (ground truth — tests must assert these values exactly)
5. `docs/03_ARCHITECTURE.md`
6. `docs/04_BACKEND_SPEC.md`
7. `docs/05_FRONTEND_SPEC.md`
8. `docs/06_BUILD_PLAN.md`
9. `docs/07_CLARIFYING_QUESTIONS.md`, `docs/08_ASSUMPTIONS.md`
10. Skim `inputs/*` — never modify them.

Then write a short plan (file list per phase, no code) and show it to me. Wait for "go".

## Step 2 — Execute Phases 0 → 7 from `docs/06_BUILD_PLAN.md`

For every phase:
- Implement exactly the modules named in `docs/04_BACKEND_SPEC.md` / `docs/05_FRONTEND_SPEC.md`
  for that phase. Use the names as written.
- Write the tests listed for the phase **before or alongside** the code; ground-truth
  numbers come from `docs/02_DATA_SPEC.md`.
- Run the phase's acceptance commands from `docs/06_BUILD_PLAN.md`. Fix until green:
  `uv run pytest -q`, `uv run ruff check . && uv run ruff format --check .`, `uv run pyright`.
- If you hit an ambiguity, choose the more deterministic / conservative option, implement
  it, and append one line to `docs/08_ASSUMPTIONS.md` → "Decisions made during build".
- If your computed number disagrees with the spec, stop, print both values with the
  Decimal computation, and ask me before changing either.
- Commit with a conventional message. Print a 5-line phase summary: files added, tests
  count, anything deferred.

## Non-negotiables (repeated from CLAUDE.md because they matter most)

- `decimal.Decimal` for all money; `float(` must not appear in `src/finagent/{domain,ingest,adjustments}`.
- The LLM never sees the trial balance and never produces a number used downstream.
- Deterministic rules decide; the LLM explains, reviews intent (escalate-only) and proposes.
- Nothing is auto-fixed. Rejected entries cannot be approved.
- Every finding has evidence. Every posted line has lineage. Runs are idempotent.
- Cassette mode by default; the app must run end-to-end with **no API key**.
- Do not touch `inputs/`.

## Phase gates where you must pause and show me output

- End of Phase 1: paste `output/DEFECT_LOG.md`.
- End of Phase 2: paste the decision table from `finagent run --llm-mode off`.
- End of Phase 3: paste one full trace for JE-008 and the explanation for JE-003.
- End of Phase 6: tell me the URL and the manual checks to perform.
- End of Phase 7: list every deliverable file and its location.

Begin with Step 1.
