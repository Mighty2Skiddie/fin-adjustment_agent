# 01 — Project brief (short version of the assignment PDF)

## 1. Context

The company is building a financial reporting platform that uses AI at its core. One feature
takes a trial balance (the list of every account and its total) from an ERP system such as
SAP or NetSuite. It combines it with manual adjustments and a configurable chart of accounts
(COA, the tree of all accounts). It then produces four statements: Balance Sheet, Profit &
Loss, Cash Flow Statement and Statement of Changes in Equity (SOCIE).

The hard part is staying reliable on messy inputs:

- inconsistent COA mappings,
- adjustments in the middle of the period,
- intercompany eliminations,
- FX (foreign exchange) revaluation,
- restatements of prior periods,
- audit-grade traceability.

Time guidance: 6–8 hours, spread over up to 5 calendar days. Up to 3 clarifying questions
may be emailed before starting. Not asking any is penalised.

## 2. Deliverables

1. **Architecture document** (PDF or Markdown). This is *the main artifact that is graded*.
   It must cover:
   - the agent layout and why it was chosen;
   - the line between fixed code and LLM (AI model) reasoning;
   - how five named failures are handled: invented mappings, debits ≠ credits after
     adjustments, an account that fits no COA node, missing FX rates, circular
     intercompany entries;
   - the check-and-correct loop;
   - how an auditor traces any number back to its source rows.
2. **A working prototype of ONE slice**, run on the messy data without cleaning it.
   Options: TB→COA mapper · **manual adjustments agent** · P&L+BS generator with verifier ·
   reconciliation agent.
3. **A one-page reflection**: 3 months vs 8 hours; where it breaks at scale (thousands of
   accounts, many entities); how AI tools were used (where they helped, where they misled);
   one thing the company is underestimating.
4. A repository with a README (setup and run) and output files under `/output`.

## 3. Scoring rubric (what "good" looks like)

| Signal | Good looks like | How this build meets it |
|---|---|---|
| Problem decomposition | "generate financials" = 6+ sub-problems with different reliability needs | §1 of `ARCHITECTURE.md` lists 8 parts, each with its trust level |
| Agentic judgment | Knows when NOT to use an LLM | 3 limited LLM roles; every number comes from code; the LLM can only escalate |
| Production thinking | Traceability, repeatable runs, human override from day one | `run_id` hash, lineage on every posted line, review queue with an audit log |
| Domain humility | Asks about accounting meaning instead of guessing | `07_CLARIFYING_QUESTIONS.md`, `08_ASSUMPTIONS.md`, assumption badges in the UI |
| AI tool fluency | Uses AI to move faster without handing over judgment | `AI_USAGE.md`, with concrete "the AI was wrong here" examples |

## 4. What hurts (and how we avoid it)

| Hurts | Our guard |
|---|---|
| A polished demo on clean data, with no failure handling | We run on the raw data. The first UI page is "Data Health". It lists every defect we found, including ones the brief did not list |
| "Just send the TB to a frontier model" | The TB never goes into a prompt |
| Ignoring auditability | Lineage for each posted line, an append-only audit log, a trace for each entry |
| Over-engineering (a 12-agent swarm) | One graph, 6 steps, 3 LLM roles. The architecture doc has a section on *why not* more agents |
| No clarifying questions | Three questions prepared before starting and kept in the repo |

## 5. Why this slice

- **Most defects**: 4 of 10 entries are defective (JE-002, JE-003, JE-005, JE-008).
  One defect (JE-003 FX double-count) is not listed in the brief.
- **Clearest line between code and LLM**: validation is 100% rules. The LLM only reviews
  intent, explains and proposes fixes.
- **Natural human-in-the-loop screen**: a review queue for a finance user is the honest
  shape of this feature. The web app serves the task; it is not decoration.
- **Scope control**: the P&L+BS slice quietly needs FX + mapping + adjustments, so it would
  be three slices done thinly. The mapper slice has only about 3 unmapped accounts in this data.

Scope of the prototype (also stated in the README):

- IN: TB loading + FX translation (needed to post), COA loading + tree, data health audit,
  adjustment checks / decisions / explanations / fix proposals, human review, posting with
  lineage, export of the TB after adjustments, observability, evals, web app.
- OUT (described in the architecture doc only): building all four statements, intercompany
  eliminations, prior-period restatement logic, a full COA mapper agent.
- SMALL BONUS (only arithmetic, cheap): an "impact preview" for each entry. It shows which
  BS/PL subtotals move and by how much. This is a sum over the COA tree, not statement
  generation. It makes the review screen much more useful for a finance user.
