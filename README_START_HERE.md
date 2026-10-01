# START HERE — Spec Kit for `fin-adjustments-agent`

This folder is a **complete build specification**. It is written so that Claude Code can
implement the whole project from these files alone, phase by phase, without inventing
anything. Read the files in numeric order.

## What this project is (one paragraph)

A take-home for an **AI Agentic Engineer** role. The company builds an AI-native financial
reporting platform that turns an ERP trial balance (TB) + chart of accounts (COA) + manual
journal adjustments into four financial statements. They want (1) an **architecture
document** for the whole system and (2) a **working prototype of ONE slice** on their
intentionally messy data. We build the **Manual Adjustments Agent** slice: it validates each
journal entry with deterministic rules, decides ACCEPT / REJECT / QUARANTINE, uses an LLM
only to review intent, explain findings in plain English and propose fixes, routes
quarantined items to a human review queue, and posts accepted entries onto the TB with full
line-level lineage. Everything is observable (traces), evaluated (golden tests + output
faithfulness checks) and guarded (the LLM never produces a number that is used downstream).

## Files in this kit

| File | Purpose | Who reads it |
|---|---|---|
| `README_START_HERE.md` | This file | You + Claude Code |
| `CLAUDE.md` | Non-negotiable engineering rules. **Copy to repo root.** | Claude Code (always loaded) |
| `docs/00_ASSIGNMENT_ORIGINAL.pdf` | The original brief | Reference |
| `docs/01_PROJECT_BRIEF.md` | Brief distilled: deliverables, scoring rubric, slice choice, what hurts | Both |
| `docs/02_DATA_SPEC.md` | Every input file, schema, every known defect, **ground-truth expected outputs** | Claude Code (tests assert against this) |
| `docs/03_ARCHITECTURE.md` | The architecture document deliverable (full draft) | Both; refined in Phase 7 |
| `docs/04_BACKEND_SPEC.md` | Domain models, rule engine, decision matrix, LangGraph, LLM roles, guardrails, observability, evals, API contract | Claude Code |
| `docs/05_FRONTEND_SPEC.md` | Pages, components, design tokens, API usage, states | Claude Code |
| `docs/06_BUILD_PLAN.md` | Phases, acceptance criteria per phase, commands | Both |
| `docs/07_CLARIFYING_QUESTIONS.md` | The 3 questions to email before starting + fallback assumptions | You (send today) |
| `docs/08_ASSUMPTIONS.md` | Every accounting assumption, flagged for a finance reviewer | Both |
| `docs/09_REFLECTION_TEMPLATE.md` | Skeleton for the 1-page reflection, pre-filled with real observations | You |
| `docs/10_AI_USAGE_TEMPLATE.md` | Log of how AI tools were used; fill as you go | You |
| `prompts/MASTER_PROMPT.md` | The single prompt to paste into Claude Code for a one-shot build | You → Claude Code |
| `prompts/PHASE_*.md` | Per-phase prompts if you prefer to build incrementally (recommended) | You → Claude Code |
| `inputs/` | The raw data, **unchanged**. Never edit these. | Code reads them |

## How to run the build (Windows, PowerShell)

1. Create the repo folder and copy this kit into it:
   ```powershell
   mkdir fin-adjustments-agent; cd fin-adjustments-agent
   # copy the kit contents here, so you have: CLAUDE.md, docs/, inputs/, prompts/
   git init; git add .; git commit -m "chore: spec kit"
   ```
2. Open Claude Code in that folder:
   ```powershell
   claude
   ```
3. Paste `prompts/MASTER_PROMPT.md` (one-shot) **or** `prompts/PHASE_0.md` then `PHASE_1.md` … (incremental).
   Incremental is safer: you review and commit after each phase and the model keeps a
   smaller working context.
4. After each phase, run the acceptance commands listed in `docs/06_BUILD_PLAN.md`.
   Do not move to the next phase until they pass.
5. Fill `docs/10_AI_USAGE_TEMPLATE.md` with 1–2 lines every time Claude Code got something
   wrong or you overrode it. That log becomes a third of your reflection.

## Decisions already made (don't re-litigate during the build)

- **Slice:** Manual Adjustments Agent (see `01_PROJECT_BRIEF.md` §4 for why).
- **Money math:** `decimal.Decimal`, quantize to 0.01, `ROUND_HALF_UP`. Never `float`.
- **LLM boundary:** LLM receives validator *findings*, never raw ledgers; its outputs are
  prose or *proposals* that are re-validated by code. It cannot post, cannot downgrade a
  severity, cannot invent an account code or a number.
- **LLM provider:** provider-agnostic via LangChain `init_chat_model`; default **cassette
  mode** (recorded responses committed in repo) so the evaluator runs with **no API key**.
- **Agent framework:** LangGraph, one small graph (6 nodes, 1 conditional loop). Not a swarm.
- **Observability:** always-on JSONL trace per run (no dependency) + optional Langfuse.
- **Frontend:** Vite + React + TypeScript + Tailwind + shadcn/ui, built to static files and
  served by FastAPI. One process, one container.
- **Hosting:** Hugging Face Spaces (Docker) — free, public URL. Local: one command.
- **Zero infra cost:** no databases; run state lives in `output/runs/<run_id>/` as JSON.
