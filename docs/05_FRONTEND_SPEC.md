# 05 — Frontend specification

Vite + React 18 + TypeScript (strict) + Tailwind + shadcn/ui + TanStack Query + React Router.
Lives in `frontend/`, builds to `frontend/dist`, served by FastAPI. The audience is **a
controller reviewing a close** and **an evaluator judging an engineer**. The UI must feel like
a serious finance tool, not a dashboard demo.

## 1. Design direction (make these choices, don't default)

**Concept: "the working paper".** Auditors annotate working papers with tick marks, cross-
references and margin notes. The UI borrows that: a quiet paper-like surface, dense tabular
numbers, and a single accent used only for things a human must act on.

Tokens (`frontend/src/styles/tokens.css`, exposed as Tailwind theme):

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#F7F6F2` | `#15171A` | page background (warm off-white, not cream-and-terracotta) |
| `--ink` | `#1C1F23` | `#E8E6E1` | text |
| `--rule` | `#D9D6CE` | `#2C3036` | hairlines, table rules |
| `--ledger-green` | `#2F6B4F` | `#6FB592` | ACCEPTED, passing invariants |
| `--ledger-red` | `#A33A2E` | `#E07A6B` | REJECTED, BLOCK |
| `--ledger-amber` | `#B07A1F` | `#E0B35C` | QUARANTINED, ESCALATE, assumptions |
| `--act` | `#1F4E8C` | `#7FA8E0` | the one accent: buttons that change state, selected row |

Type: **IBM Plex Sans** for UI, **IBM Plex Mono** with `font-variant-numeric: tabular-nums`
for every number and code (one family in two cuts — distinct but related). Scale: 13/15/18/
24/32 px. Numbers right-aligned, negatives shown with a leading minus (not parentheses —
this is a review tool, not a printed statement), two decimals always, thousands separators.

Layout: left rail navigation (56 px, icons + labels), content max-width 1280 px, left-
aligned. Tables are the primary element; cards only for the entry detail. One memorable
element: the **Review Queue entry row expands in place** into findings + explanation + fix
candidates + impact, like unfolding a working paper — no modal, no page change.

Motion: only on user action (expand, approve). No page-load animations. Respect
`prefers-reduced-motion`. Visible focus rings. Keyboard: `j/k` move between entries, `Enter`
expands, `a`/`r` open approve/reject when allowed.

Copy: sentence case, plain verbs. "Approve and post" (button) → toast "Approved and posted".
Errors say what happened and what to do. Empty queue: "No entries need review — 6 accepted
automatically." Assumptions get an amber "assumption" chip that links to the assumption text.

## 2. Routes and pages

```
/                      → redirect to /runs/latest/health
/runs/:runId/health    Data Health
/runs/:runId/queue     Review Queue (default landing after health is acknowledged)
/runs/:runId/entries/:jeId   Entry detail + trace (also reachable by expanding in queue; detail route is for deep links)
/runs/:runId/ledger    Post-adjustment TB + lineage
/runs/:runId/audit     Audit log + run manifest + metrics
/runs/:runId/evals     Evaluation report
/about                 Architecture summary (renders docs/ARCHITECTURE.md), links to repo, Langfuse trace (if any)
```
`latest` resolves via `GET /api/runs` (first item). A top bar shows run id, period, FX policy
in effect, LLM mode (cassette/live/off) and counts (6 · 2 · 2).

### 2.1 Data Health (`/health`)
Purpose: show the evaluator we found every defect, including unlisted ones.
- Header strip: four numbers — defects found, critical, files affected, "listed in brief vs
  found by us" (the brief lists 10; we report the count our audit produces). Each number has a small label beneath; no gradient.
- Table grouped by file (TB, COA, Prior TB, FX, Adjustments batch): ID, severity chip, title,
  evidence (monospace, expandable), policy applied (with assumption chip where relevant).
- Side panel "TB balance under each FX policy": a 4-row table (raw / USD-only / period-end
  GBP→avg / period-end GBP→opening) with Δ, the active one highlighted. This replaces a chart;
  the numbers are the point.
- Button: "Continue to review queue".

### 2.2 Review Queue (`/queue`)
- Filter chips: All · Needs review (quarantined) · Rejected · Accepted. Default: Needs review
  first, then rejected, then accepted (stable sort by severity then id).
- Table columns: JE id · description · date · total (debits) · decision chip · findings count
  · effective state (system / approved by X / rejected by X) · chevron.
- Expanded row (the memorable element), four columns on wide screens, stacked on narrow:
  1. **Lines** — account code (mono) + name, debit, credit; orphan codes in red with "not in
     COA" tag; same-account-both-sides highlighted.
  2. **Findings** — list; each: rule id (mono), severity chip, title, message; "show
     evidence" toggles a key/value table. LLM-produced findings carry a small "reviewer"
     badge.
  3. **Explanation** — summary sentence (18 px), bullets, next step. Footer: source chip
     `LLM · gemini-2.5-flash · cassette` or `template fallback`, link "view trace".
  4. **Fix candidates** — each card: label, rationale, proposed lines, revalidation result
     ("Resolves" green / "Does not resolve: R005" red). Buttons: "Copy as JSON". If
     `needs_human_input`, show it as a question with a quote mark style.
  Below: **Impact preview** — compact table of touched roots with Δ and NI/A/L/E deltas.
  Action bar (only for QUARANTINED): "Approve and post" (accent), "Reject" (outline). Both
  open a small inline form: actor name (persisted in localStorage), reason (min 10 chars),
  confirm. For REJECTED entries the bar explains: "Rejected entries can't be approved. Edit
  the entry and resubmit as a new version." For ACCEPTED: "Posted automatically — all checks passed."

### 2.3 Entry detail (`/entries/:jeId`)
Same content as expanded row plus a **Trace timeline**: vertical list of events from
`GET /trace/:jeId` — node enter/exit with durations, each rule result, each LLM call
(role, model, mode, tokens, latency, cassette hit), guardrail verdicts, decision, human
decisions. Raw JSON toggle. "Download trace" link.

### 2.4 Ledger (`/ledger`)
- Totals strip: debits, credits, imbalance (red if non-zero and above materiality, with the
  translation-difference note), invariants list with green/red ticks.
- Table: account code · name · debit · credit · net · mapped (UNMAPPED tagged) · sources count.
  Grouping toggle: flat / by COA root. Search box.
- Click a row → right drawer **Lineage**: the line amount, then components with kind badges
  (TB row, FX rate incl. "fallback" tag, JE line, human decision), each showing the raw
  source (CSV row text, JE line JSON, decision record) and its contribution; a footer that
  sums components and shows "= line amount ✓". Deep link `?account=2120`.

### 2.5 Audit (`/audit`)
Manifest (run id, created, code version, input hashes, config hash, LLM mode), metrics
(auto-accept rate, quarantine rate, guardrail fallback rate, LLM calls, cassette hit rate,
p50 latency), and the audit log table (ts, event, entry, actor, before → after, reason).
"Download audit log (JSONL)".

### 2.6 Evals (`/evals`)
Summary table from `report.json`: decision accuracy, per-rule precision/recall, explanation
faithfulness (numbers / codes), schema validity, fallback rate; then per-entry expected vs
actual with a diff highlight. If the report is missing: empty state "Run `finagent eval`".

### 2.7 About (`/about`)
Renders `ARCHITECTURE.md` (fetched from `/api/docs/architecture`, served as markdown) with the
topology diagram as pre-formatted text, plus links: repository, Langfuse public trace (env
`VITE_LANGFUSE_TRACE_URL`, hidden when absent), the three clarifying questions.

## 3. Components (`frontend/src/components`)

`AppShell`, `RunTopBar`, `SeverityChip`, `DecisionChip`, `AssumptionChip`, `Money` (formats
string → tabular mono, red for negative), `AccountCode`, `DataTable` (generic, sortable,
sticky header, dense rows 36 px), `ExpandableRow`, `FindingList`, `EvidenceTable`,
`ExplanationCard`, `FixCandidateCard`, `ImpactPreview`, `DecisionForm`, `LineageDrawer`,
`TraceTimeline`, `JsonToggle`, `EmptyState`, `ErrorState`, `KeyboardHints`.

## 4. Data layer (`frontend/src/api`)

`client.ts` (fetch wrapper, base `/api`, typed errors), `types.ts` (mirrors backend models;
money as `string`), `queries.ts` (TanStack Query hooks per endpoint; `useDecision` mutation
invalidates `entries`, `posted-tb`, `audit-log`). Optimistic UI is **not** used — finance
users should see the server-confirmed state.

## 5. States

Every page handles loading (skeleton rows, not spinners), error (`ErrorState` with retry and
the server's `message_for_user`), and empty. Decision form validation inline. 404 for an
unknown run id with a link to the latest run.

## 6. Build + serve

`npm run build` → `frontend/dist`. Dev: `npm run dev` on 5173 proxying `/api` to 8000
(`vite.config.ts` proxy). Production: FastAPI mounts `dist` with SPA fallback. Env:
`VITE_LANGFUSE_TRACE_URL` optional. Lighthouse-level hygiene: semantic tables, labelled
buttons, contrast ≥ 4.5:1 for text.

## 7. Screenshots to capture for the README/architecture doc (Phase 7)

1. Data Health with the FX-policy table. 2. Review Queue with JE-003 expanded (double-count
finding + fix candidates). 3. Ledger lineage drawer for `2120`. 4. Trace timeline for JE-008.
