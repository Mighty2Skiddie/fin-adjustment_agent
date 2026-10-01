# Architecture — Agentic ERP Trial Balance → Financial Statements

*Submission for the AI Agentic Engineer take-home. Prototype slice: Manual Adjustments Agent.*
*(Phase 7 of the build refines this draft with real screenshots, trace excerpts and final numbers.)*

## 0. Thesis in three sentences

Generating financial statements is **arithmetic over a tree with hard invariants**, wrapped
in **messy semantics** (what does this account mean, is this journal entry what it claims to
be, which rate should apply). Arithmetic and invariants belong to deterministic code with
tests; semantics is where an LLM earns its keep — as a **bounded reviewer and translator**,
never as a calculator. The system is therefore a deterministic *ledger kernel* with three
narrow LLM roles plugged into it behind guardrails and human gates, not a swarm of agents
passing spreadsheets to each other.

## 1. Problem decomposition — eight sub-problems, three reliability classes

| # | Sub-problem | Reliability class | Who | Failure mode if wrong |
|---|---|---|---|---|
| 1 | Ingest + normalise (schemas, Decimal, dedupe, orphans) | **Exact** | code | Garbage in, undetected |
| 2 | FX translation (rate selection, rounding, translation difference) | **Exact + policy** | code, policy from config/human | Unbalanced TB, double-counted reval |
| 3 | COA mapping of unmapped / ambiguous accounts | **Judgment** | LLM proposes → code validates → human approves | Hallucinated mapping silently misstates a line |
| 4 | Manual adjustment validation + posting | **Exact** | code | D≠C, circular, out-of-period |
| 5 | Adjustment intent review + explanation + fix proposal | **Judgment** | LLM, escalate-only, structured output | Opaque rejections, wrong auto-fix |
| 6 | Statement assembly (BS, P&L, CF, SOCIE) | **Exact** | code (aggregation over COA tree) | Wrong subtotal |
| 7 | Tie-outs: A = L + E; NI → RE; ΔCash = CF total; SOCIE opening→closing | **Exact** | code | Statements that do not reconcile |
| 8 | Lineage + audit (cell → source rows), idempotency, human override log | **Exact** | code | Unauditable output = unusable |

"Exact" means: pure functions, Decimal, property tests, zero tolerance. "Exact + policy" means
the arithmetic is exact but *which* arithmetic to run is a configured decision made by a
human (e.g. missing-rate fallback). "Judgment" means an LLM may propose, confidence is
scored, and nothing it says reaches a statement without passing an Exact check and, below a
confidence threshold, a human.

## 2. Agent topology — and why not more agents

```
                   ┌────────────────────────────────────────────────┐
  inputs/ ───────► │  LEDGER KERNEL (deterministic, tested)         │
                   │  ingest → fx → coa_tree → health_audit         │
                   │  adjustments.rules → decisions → posting       │
                   │  statements → tie_outs → lineage               │
                   └───────┬───────────────┬────────────────┬───────┘
                           │ findings      │ unmapped       │ anomalies
                           ▼               ▼                ▼
                 ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
                 │ ROLE A       │  │ ROLE B       │  │ ROLE C           │
                 │ Intent       │  │ Mapper       │  │ Narrative        │
                 │ Reviewer +   │  │ (propose +   │  │ Verifier         │
                 │ Explainer +  │  │  confidence) │  │ (read-only       │
                 │ Fix Proposer │  │              │  │  "does this look │
                 └──────┬───────┘  └──────┬───────┘  │  right")         │
                        │ structured      │          └────────┬─────────┘
                        ▼                 ▼                   ▼
                   GUARDRAILS (schema, number/code whitelist, escalate-only, retry≤1, fallback)
                        │
                        ▼
                   HUMAN GATES (review queue: quarantined items, low-confidence mappings)
                        │
                        ▼
                   POST → statements → /output + audit log
```

**Orchestration**: a LangGraph `StateGraph` per batch with six nodes
(`load → validate → intent_review → explain → propose_fix → decide/post`) and one
conditional edge (`propose_fix → validate` for at most 2 iterations). Nodes are plain
functions; the LLM nodes are three *roles* with distinct prompts and output schemas, not
three autonomous agents with their own loops and tools.

**Why a single orchestrated graph and not an "Orchestrator + Mapper + Adjuster + Builder +
Validator" sub-agent crew:**
1. Four of the five proposed sub-agents (Adjuster, Statement Builder, Validator, most of
   Mapper) have *exact* answers. Giving them to an LLM converts tested arithmetic into
   probabilistic arithmetic for no gain.
2. Multi-agent handoffs multiply the places where a number can be paraphrased. The brief's
   own evaluation criterion is "every number reconciles back to source entries" — a
   message-passing swarm is structurally hostile to that.
3. The valuable LLM work is three narrow transformations. Three roles with three prompts
   and three Pydantic schemas is the right granularity; three agents with planning loops is
   the 12-agent-swarm red flag in miniature.
4. Determinism and idempotency are a requirement (§6). A graph of pure nodes replays
   byte-identically; a crew of agents does not.

Where would more autonomy be justified? Only in the Mapper when a *new ERP* is onboarded
(hundreds of unmapped accounts, needs retrieval over the COA plus prior mappings, several
rounds of clarification). That is a bounded research task and still ends in a human
approving a mapping table.

## 3. The line between deterministic code and LLM reasoning

**Rule: the LLM never produces a number that is used downstream, and never sees the trial balance.**

| Deterministic (code) | LLM |
|---|---|
| Parse, type, dedupe, sum | Judge whether a JE description matches its lines (JE-008 "settlement" that never touches cash) |
| Select FX rate per policy, translate, round, compute translation difference | Explain a rule failure in a finance user's language, citing only the numbers the rule produced |
| All 13 adjustment rules (§5) | Propose candidate fixes as *structured* line sets, which are re-run through the same rules |
| Severity → decision mapping | Propose a COA node for an unmapped account with a confidence score and a one-line reason |
| Posting, lineage, statement aggregation, tie-outs | Write a narrative "what moved and why" over code-computed deltas (reconciliation slice) |
| Idempotent run ids, audit log | Flag an anomaly for a human ("depreciation catch-up is 25% of the period's depreciation") — the number comes from code |

Where the AI actually earns its keep in this domain: (a) *mapping* — a new ERP's "Sundry
Operating Expenses" → our `6900 Other Operating Expenses` with a confidence and a reason,
across thousands of accounts; (b) *intent review* — catching entries whose arithmetic is
fine but whose meaning is wrong; (c) *explanation* — turning `R001 BLOCK Δ 3,500.00` into
something a controller acts on in ten seconds; (d) *narrative reconciliation* — "why did
accrued expenses move 925,000" answered from lineage, in prose.

## 4. Failure modes that kill you in production

| Failure mode | Detection (code) | Handling | Prototype evidence |
|---|---|---|---|
| **Hallucinated account mapping** | Every LLM output passes a *whitelist check*: proposed codes must exist in the COA or be explicitly marked `NEW_ACCOUNT_REQUEST`; confidence < 0.85 → human queue | Mapping is a proposal, stored with reason + confidence; posting uses only approved mappings; an approved mapping is versioned in the COA history | H-PP-02 (`6905` → `6900`, fuzzy 0.9x, routed for approval); JE-005 `6315` candidates shown, auto-mapping rejected as it would create a no-op |
| **Debits ≠ credits after adjustments** | R001 per entry (Decimal exact); batch-level invariant; post-adjustment TB imbalance must equal pre-adjustment imbalance | Entry REJECTED, cannot be approved; fix candidates proposed; batch posting is atomic per entry | JE-002 Δ 3,500.00 |
| **Account that fits no COA node** | Orphan check on TB (`9999`) and on every JE line (R002); fuzzy candidates with scores | TB orphan → `UNMAPPED` bucket excluded from subtotals and shown on every statement as a reconciling line until resolved; JE orphan → QUARANTINE with "add to COA" or "remap" actions | H-TB-03, JE-005 |
| **FX gaps** | H-FX-01: rate matrix check before translation | Policy from config: `block` (hard stop, statements not produced), `fallback_average`, `fallback_opening`, `carry_forward_last_known`; the chosen fallback is stamped on every affected line's lineage and surfaced in the UI and the statement notes | GBP period-end missing → 521,147.20 at average, flagged |
| **Double-counted FX revaluation** (the one they did not list) | R007: entry touches an FX gain/loss account *and* an account with non-functional-currency TB rows while `fx.translation_mode=system` | QUARANTINE with the recomputed expected reval on both rate bases | JE-003: booked 11,200.00 vs 10,730.20 / 19,809.60 |
| **Circular intercompany entries** | R005: same account on both sides / entry nets to zero on every account; R011: IC account without counterparty entity reference | REJECT; Intent Reviewer asked whether the description implies a different counter-account; fix proposal re-validated | JE-008 |
| **Unbalanced source TB** | H-TB-01 under every FX policy | Difference posted to a system-generated translation-difference line with its own lineage tag, blocked above materiality; never silently plugged | Δ +182,460.20 at default policy |
| **Prompt injection via memos** | Memo/description wrapped as `<untrusted_data>`; output schema has no free-form "action" field | LLM cannot trigger any action; it only fills a schema | tested with an adversarial memo in `tests/llm/test_guardrails.py` |
| **Model unavailable / rate limited** | provider error | cassette replay in demo; deterministic template explanation in prod with `guardrail_fallback=true` — the pipeline never blocks on the LLM | cassette mode is the default |

## 5. Validation and self-correction loop

```
for each entry:
  findings = run_all_rules(entry, ctx)                     # 13 deterministic rules
  findings += intent_reviewer(entry, findings)             # LLM, may only ADD an ESCALATE/WARN finding
  decision  = max_severity(findings) → ACCEPTED | QUARANTINED | REJECTED
  if decision != ACCEPTED:
      explanation = explainer(entry, findings)             # LLM → prose, number/code-whitelisted
      candidates  = fix_proposer(entry, findings)          # LLM → structured line sets
      for c in candidates: c.revalidation = run_all_rules(c, ctx)   # code decides if a fix would work
      (max 2 proposer iterations; failing candidates are still shown, marked "does not resolve")
  record(entry, findings, decision, explanation, candidates, trace)
post(ACCEPTED ∪ human_approved) atomically; recompute invariants; export lineage
```

What the agent checks before returning output (batch-level): all entries have a decision;
∑ posted debits = ∑ posted credits; post-adjustment imbalance = pre-adjustment imbalance;
every posted line has lineage; no `UNMAPPED` line silently inside a COA subtotal; every LLM
output passed guardrails or is marked fallback. If any batch check fails, the run is marked
`FAILED_INVARIANT` and nothing is written to the "posted" output — the partial state is kept
for debugging under `output/runs/<id>/failed/`.

For the full product the same loop wraps statement generation: build → tie-outs → on
failure, *diagnose deterministically* (which invariant, which accounts) → Narrative Verifier
writes the diagnosis for a human → human resolves (policy change, mapping, adjustment) →
rebuild. The LLM never "fixes the balance sheet".

## 6. Production properties

- **Traceability** — every posted line carries `lineage: [{kind: TB_ROW, row: 3, currency: GBP, rate_id: GBP/period_average(fallback)}, {kind: JE, id: JE-001, line: 2}]`. Statement cells carry the list of posted lines they aggregate. Clicking a cell → lines → source rows is a pure join. The auditor path is: *cell → COA node → posted lines → (TB rows, FX rate rows, JE lines, human decisions)*; each hop is a stored id, not a recomputation.
- **Idempotency** — `run_id = sha256(canonical(inputs) + canonical(config) + code_version)[:12]`. Same inputs → byte-identical outputs (cassette mode). Human decisions are stored outside the run and applied as an overlay, so re-running does not lose approvals.
- **Human override** — quarantine queue with approve/reject + mandatory reason; rejected entries are immutable and require a new version; every action appended to `audit_log.jsonl` with actor, timestamp, before/after.
- **Observability** — one JSONL trace per run: node enter/exit, rule results, LLM request/response (prompt hash, model, latency, tokens), guardrail verdicts. Optional Langfuse export for a shareable trace. Metrics surfaced: % entries auto-accepted, % quarantined, guardrail failure rate, LLM fallback rate.
- **Evaluation** — golden decisions for the 10 entries + synthetic variants; defect-detection precision/recall; explanation faithfulness (every number and account code in the prose must appear in the findings); schema validity; optional LLM-as-judge rubric for clarity. Evals run in CI.
- **Materiality & policy as config, not code** — `config/default.yaml` holds FX policy, imbalance tolerance, magnitude thresholds, confidence threshold. Policy changes are reviewable diffs.

## 7. How an auditor traces a balance-sheet cell

Example: *Accrued Expenses, closing balance 2,075,000.00 Cr*.
1. Cell → COA node `2120` → posted lines for `2120` in run `a1b2c3d4e5f6`.
2. Posted line shows components: TB row 18 (`2120, USD, credit 1,150,000.00`, rate `USD/period_end=1.0`), `JE-001` line 2 (credit 850,000.00, decision ACCEPTED by system, rule results all pass), `JE-009` line 2 (credit 75,000.00, ACCEPTED).
3. Each JE id → entry record: original JSON as submitted, findings, LLM explanation (if any), human decisions with actor/time/reason, trace id.
4. Each TB row → the raw CSV line (file hash recorded in the run manifest).
Sum of the components reproduces the cell exactly; the test suite asserts this for every
posted line (`tests/adjustments/test_lineage.py`).

## 8. Clarifying questions asked

See `07_CLARIFYING_QUESTIONS.md`. The build proceeds on documented fallback assumptions
(`08_ASSUMPTIONS.md`), each flagged in the UI with "assumption" badges so a finance reviewer
sees exactly where we guessed.

## 9. What this prototype does *not* do (honest scope)

Statement assembly for the four statements, intercompany elimination, prior-period
restatement and the full mapper agent are designed above but not built. The prototype proves
the pattern — kernel + bounded roles + guardrails + human gates + lineage — on the slice
where the data is messiest.
