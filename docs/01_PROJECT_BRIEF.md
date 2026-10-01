# 01 — Project brief (distilled from the assignment PDF)

## 1. Context

The company is building an AI-native financial reporting platform. One feature ingests a
trial balance from an ERP (SAP, NetSuite), combines it with manual adjustments and a
configurable chart of accounts, and produces: Balance Sheet, Profit & Loss, Cash Flow
Statement, Statement of Changes in Equity (SOCIE). The hard part is reliability on messy
inputs: inconsistent COA mappings, mid-period adjustments, intercompany eliminations, FX
revaluation, prior-period restatements, and audit-grade traceability.

Time guidance: 6–8 hours over up to 5 calendar days. Up to 3 clarifying questions may be
emailed before starting (not asking is penalized).

## 2. Deliverables

1. **Architecture document** (PDF/MD) — *the main artifact evaluated*. Must cover:
   agent topology + justification; the line between deterministic code and LLM reasoning;
   handling of five named failure modes (hallucinated mappings, D≠C after adjustments,
   account that fits no COA node, FX gaps, circular intercompany entries); the validation
   and self-correction loop; how an auditor traces any cell back to source rows.
2. **Working prototype of ONE slice** on the messy data, unsanitized. Options:
   TB→COA mapper · **manual adjustments agent** · P&L+BS generator with verifier ·
   reconciliation agent.
3. **One-page reflection**: 3 months vs 8 hours; where it breaks at scale (1000s of
   accounts, multi-entity); how AI tools were used (helped / misled); one thing they are
   underestimating.
4. Repo with README (setup + run), output artifacts under `/output`.

## 3. Scoring rubric (what "good" looks like)

| Signal | Good looks like | How this build hits it |
|---|---|---|
| Problem decomposition | "generate financials" = 6+ sub-problems with different reliability bars | §4 of `03_ARCHITECTURE.md` lists 8 with reliability class each |
| Agentic judgment | Knows when NOT to use an LLM | 3 bounded LLM roles; every number is code; LLM can only escalate |
| Production thinking | Traceability, idempotency, human override from day one | `run_id` hash, lineage on every posted line, review queue with audit log |
| Domain humility | Asks about accounting semantics instead of guessing | `07_CLARIFYING_QUESTIONS.md`, `08_ASSUMPTIONS.md`, flagged assumptions in UI |
| AI tool fluency | Uses AI to move faster without offloading judgment | `10_AI_USAGE_TEMPLATE.md` with concrete "AI was wrong here" entries |

## 4. What hurts (and how we avoid it)

| Hurts | Our guard |
|---|---|
| Polished demo on clean data, no failure handling | We run on the raw data; the first UI page is "Data Health" listing every defect we found, including ones they didn't list |
| "Just prompt a frontier model with the TB" | The TB never enters a prompt |
| Ignoring auditability | Lineage per posted line, append-only audit log, trace per entry |
| Over-engineering (12-agent swarm) | One graph, 6 nodes, 3 LLM roles; a section in the doc explaining *why not* more agents |
| No clarifying questions | Three questions emailed before starting, logged in the repo |

## 5. Why this slice

- **Richest defects**: 4 of 10 entries are defective (JE-002, JE-003, JE-005, JE-008);
  one defect (JE-003 FX double-count) is not listed by them.
- **Cleanest deterministic/LLM boundary**: validation is 100% rules; the LLM reviews
  intent, explains and proposes.
- **Natural human-in-the-loop UX**: a review queue for a finance user is the honest shape
  of this feature. The frontend serves the brief rather than decorating it.
- **Scope control**: the P&L+BS slice secretly requires FX + mapping + adjustments → three
  slices done shallowly. The mapper slice has only ~3 unmapped accounts in this data.

Scope boundary for the prototype (say this explicitly in the README):
- IN: TB ingest + FX translation (needed to post), COA load + tree, data-health audit,
  adjustment validation/decisions/explanations/fix proposals, human review, posting with
  lineage, post-adjustment TB export, observability, evals, UI.
- OUT (described in architecture doc only): statement assembly for all four statements,
  IC eliminations, prior-period restatement logic, full COA mapper agent.
- SMALL BONUS (arithmetic only, cheap): per-entry "impact preview" showing which BS/PL
  subtotals move and by how much. This is aggregation over the COA tree, not statement
  generation, and makes the review UI meaningfully better for a finance user.
