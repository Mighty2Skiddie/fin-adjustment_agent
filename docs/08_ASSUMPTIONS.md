# 08 — Assumptions register

This page lists every accounting or data assumption the system makes. Each one has an ID.
The code uses the ID on findings (for example `assumption="A3"`). The UI shows it as an
amber "assumption" chip. A finance reviewer can disagree with any line here and see exactly
what would change.

Short terms used below:

- **TB** = trial balance (the list of every account and its total).
- **COA** = chart of accounts (the tree of all accounts).
- **JE** = journal entry (one manual adjustment).
- **FX** = foreign exchange (currency rates).
- **CTA** = cumulative translation adjustment (the equity account for currency differences).

## Assumptions

| ID | Assumption | Why we had to assume | What changes if wrong | Confidence |
|---|---|---|---|---|
| A1 | Functional currency is USD. The period is 2024-10-01 → 2024-12-31. | Stated in the data bundle README. | — | High |
| A2 | Every TB row is translated at the **period-end** rate (a point-in-time TB). We do not use average rates for P&L rows in this slice. | The slice is adjustments, not statements. One rate keeps the TB consistent. In the full product, P&L rows use the period-average rate and the difference goes to CTA. | P&L lines in other currencies would differ. There are none in this data (only `1110` has several currencies), so the numbers do not change here. | Medium |
| A3 | The imbalance left after translation is posted to `3310 FX Translation Reserve` as a system line tagged `TRANSLATION_DIFF`. It is flagged CRITICAL when above materiality. | A TB that does not balance cannot be posted. Under the current-rate method, translation differences belong in CTA. The difference here (182,460.20) is far bigger than rounding, so it is flagged, not quietly accepted. | Finance may prefer a separate suspense account, or a hard block. | Medium |
| A4 | GBP has no period-end rate. We fall back to the period-average rate and flag every affected line. | No rate means no translation. Blocking the whole run for one rate does not help in review mode. | The `block` policy stops posting. `fallback_opening` changes 1110 by −5,359.90. | Medium |
| A5 | Repeated TB rows for one account in the same currency are **added together**, with a HIGH flag. | The README says repeated codes are summed. Repeats in the same currency are still suspicious. | If the 38,500.00 row is a double posting, 6310 is overstated by 38,500.00. | Medium |
| A6 | TB account `9999`, which is not in the COA, stays in an `UNMAPPED` bucket. It is left out of COA subtotals and shown as a reconciling line. | We must not guess a mapping for a suspense account. | Mapping it changes one subtotal by 12,400.00. | High |
| A7 | The sign is always debit − credit. `account_type` and `normal_balance` only drive warnings. | Gain/loss accounts are typed Expense but carry credit balances. Contra accounts have reversed normal balances. | — (this is the safer choice in every case) | High |
| A8 | An account that has children is structural (it only sums its children), whatever its `account_type`. | `8000` and `3300` have children but are not typed Header. | Posting straight to 8000 or 3300 would be unclear. It does not happen in this data. | High |
| A9 | A JE date must fall inside the period. Otherwise the entry is REJECTED. | Mid-period adjustments are in scope. Postings outside the period need a different workflow. | It could be QUARANTINE if finance allows backdated entries. | Medium |
| A10 | An entry whose per-account totals are all zero is REJECTED as a no-op, not quarantined. | It cannot change any balance, so approving it means nothing. | — | High |
| A11 | Unbalanced entries are REJECTED and cannot be approved by a human. They must be edited and sent again as a new version. | Approving an unbalanced entry breaks the rule that the ledger balances. | — | High |
| A12 | Fix candidates are only proposals. Nothing is applied automatically. | The judgment belongs to the person who prepared the entry. The system cannot know which of two conflicting values is right. | — | High |
| A13 | Size thresholds: INFO at ≥ 20%, WARN at ≥ 50% of the account's existing absolute balance. These never block. | Sensible defaults for a review aid. | Tune them in `config/default.yaml`. | Low |
| A14 | Intercompany balances are not eliminated (this is a single-entity TB). They are flagged. | No TB was provided for the other company. | Consolidation would net 2170 against a receivable we do not have. | High |
| A15 | The prior-period TB is used for comparatives only. Opening-balance walks are flagged as unreliable. | It does not balance, and it contains a P&L account. | If it is post-close and balanced, the SOCIE opening walk can be computed. | Medium |
| A16 | `6905` (prior) → `6900` (current) is a *proposed* mapping. It needs approval. | Similar name, same number range. | Approving it changes prior comparatives for 6900 by 132,000.00. | Medium |
| A17 | The Intent Reviewer (an AI role) can only add findings (escalate). It can never remove or soften one. | A probabilistic judgment must not override fixed rule checks. | — | High |
| A18 | Cassette mode is the default, so the prototype runs without an API key. A cassette is a saved recording of a real AI answer, replayed later. Recordings are labelled. | A free and repeatable demo. | Live mode changes the wording, never the decisions (decisions come from rules). | High |

## Decisions made during build

Each decision notes the build phase where it was made.

- **D1 (Phase 0):** The web app uses React 19, not the planned React 18. `npm create vite`
  and current shadcn/ui install React 19, and current shadcn components need a React 19
  feature (ref passed as a normal prop).
- **D2 (Phase 0):** An optional `llm-openai` extra and `openai` provider were added next to
  google_genai, groq and anthropic. The default is still google_genai in cassette mode.
- **D3 (Phase 0):** `.gitattributes` marks `inputs/**` as `-text`, so git never changes line
  endings in the raw data. This matters because input file hashes feed the `run_id`.
- **D4 (before build, approved):** R009 checks each account using the entry's net change on
  that account, so JE-008's two 2170 lines cancel out. The rule IDs in §7 of
  `02_DATA_SPEC.md` were corrected (JE-001: R009 WARN on 2120; JE-003/004/006/007/010:
  R009 INFO). No decision changed.
- **D5 (before build):** The translation difference line is part of the base ledger. So 3310
  base = 180,000.00 + 182,460.20 = 362,460.20 Cr, and both the base TB and the posted TB net
  to 0.00.
- **D6 (before build):** R007b computes the expected revaluation only for currencies that
  have a period-end rate. GBP is left out, with a note. So the expected values are EUR only
  (10,730.20 / 19,809.60).
- **D7 (before build):** Fuzzy name matching (H-PP-02, R002b) only looks at accounts that can
  take postings and are not structural. Otherwise the header `6000 Operating Expenses`
  would rank above `6900`.
- **D8 (Phase 1):** `HealthFinding` has the same evidence-backed shape as `Finding` (title,
  message, evidence, suggested_action) but its own severity scale (CRITICAL … INFO). So it
  is a sibling class, not a subclass. Evidence can be any JSON value except floats
  (Decimals are stored as strings). A validator enforces this.
- **D9 (Phase 1):** The materiality tolerance is the *stricter* of `imbalance_tolerance_abs`
  and `imbalance_tolerance_pct × total debits`. Here that is 1.00.
- **D10 (Phase 1):** With `missing_rate_policy=block`, the base ledger is not built
  (`MissingRateError`) and the run is marked `BLOCKED`. The health audit still reports every
  finding.
- **D11 (Phase 1):** TB lineage row references count data rows from 0
  (`trial_balance.csv#2` = the GBP cash row), as `TbRow.row_index` says. JE line references
  count from 1 (`JE-001#2` = the second line), to match the auditor example in the
  architecture doc.
- **D12 (Phase 1):** H-TB-05 fires when the number of unique account codes differs from the
  brief's "~80 accounts" by more than 10%.
- **D13 (Phase 1):** H-PP-04 finds reserve accounts from the data, not from code numbers:
  type Equity, not a header, cash-flow category not `Financing` (→ 3200, 3310). It compares
  USD rows only.
- **D14 (Phase 1):** H-FX-01 always computes both fallback translations, whatever the policy.
  It leaves out `fallback_rate_id` under `block`.
- **D15 (Phase 1, confirmed):** `chart_of_accounts.csv` holds **72** accounts (73 lines with
  the header). `02_DATA_SPEC.md` §1 said "73 rows" and was corrected to 72.
- **D16 (Phase 1):** Fuzzy scores are rapidfuzz `token_set_ratio`, rounded to a whole number
  and stored as a 2-decimal string (`"0.86"`). No floats in evidence.
- **D17 (Phase 3, approved by the user):** Cassettes are **real recordings**. The main model
  is `google_genai/gemini-2.5-flash`. The fallback is `groq/openai/gpt-oss-120b` (set with
  `llm.fallback_*`). The fallback is used only when the main model fails or hits a rate
  limit. API keys live in the `.env` file, which git ignores. Replaying needs no key.
- **D18 (Phase 3):** The cassette key does not include the model name (it is a sha256 of role
  + prompt hash + canonical payload). So a recording made by the fallback model replays the
  same way. Each file records which provider and model answered.
- **D19 (Phase 3):** The Intent Reviewer runs on every entry, because an entry that passes
  every rule can still be described wrongly. The Explainer and Fix Proposer run only on
  entries that are not ACCEPTED.
- **D20 (Phase 3):** The fix loop runs `propose_fix` again only when the model proposed
  candidates and none of them solves the problem (at most 2 rounds). An empty proposal with
  a question for the preparer ends the loop.
- **D21 (Phase 3):** Guardrails (automatic checks on AI output) also check the *amounts* in
  fix candidates. Every non-zero amount must appear in the entry or the findings. Every
  account must be in the COA. Candidates that fail are dropped and logged. After a failed
  retry, the candidates that passed are kept, and the question is replaced by a fixed one.
- **D22 (Phase 3):** A bare 4-digit number is treated as an account code (checked against the
  code list), not as an amount. An invented "3600" is still caught, because it is not a COA
  code.
- **D23 (Phase 3):** If the Intent Reviewer's answer fails the guardrails twice, no R013 is
  added (the rule-based decision stands) and `guardrail_fallback=true` is written to the
  trace.
- **D24 (Phase 3):** `CassetteChatModel` is a small replay class, not a LangChain
  `BaseChatModel` subclass. The roles need checked structured objects, not chat messages.
- **D25 (Phase 3):** Token counts in the trace are estimates (characters ÷ 4). Providers
  report usage unevenly through the structured-output wrappers.
- **D26 (Phase 5):** `llm.mode=record` fills only missing cassettes. Existing recordings are
  replayed, never overwritten, so checked recordings cannot drift.
  `finagent record-cassettes --clean` records everything again.
- **D27 (Phase 5):** Synthetic test cases may list `llm_allowed` findings. These are Intent
  Reviewer escalations that are acceptable but not required (R013 on SYN-05/09/10, all
  already REJECTED by rules). Required AI findings must appear. Any finding outside
  required ∪ allowed fails the case.
- **D28 (Phase 5):** `evals/` stays at the repository root, as specified. The CLI adds the
  root to `sys.path` before importing it.
- **D29 (Phase 5):** The AI-as-judge clarity score runs only in live or record mode (a
  replayed judge measures nothing). Its recordings are kept as evidence of the last live
  score (5.00 average).
- **D30 (Phase 5):** The guardrails treat `JE-`/`SYN-` ids and short codes like `ABC-123`
  (3 digits or fewer) as identifiers, not amounts. The eval found this when "SYN-11" was
  read as −11.
- **D31 (Phase 6):** Only QUARANTINED entries can be decided by a human. ACCEPTED entries
  return 400 ("posted automatically"). REJECTED entries return 400 ("edit and resubmit as
  a new version").
- **D32 (Phase 6):** Human decisions are final. A second decision on the same entry returns
  409. To change one, the entry must be sent again as a new version. So the audit trail
  never holds a silent reversal.
- **D33 (Phase 6):** Every API view (entries, posted TB, lineage) is recomputed from the
  fixed system results plus `human_decisions.json`. After a decision, `posted_tb.*` is
  rewritten, and `decision.human` and `post.completed` events are added to the audit log.
- **D34 (Phase 6):** `GET /api/runs/latest/...` finds the run through `output/runs/LATEST`.
  `finagent serve` creates a cassette-mode run first if none exists, so a fresh copy of the
  repository shows data at once.
- **D35 (Phase 6):** `/api/config` shows secrets only as "set" or "not set", never their
  values.
- **D36 (Phase 7):** `thresholds.fuzzy_match_min_score` (80) stays in the config as specified,
  but no code reads it yet. Fuzzy candidates are only for information (H-PP-02 and R002b
  list the top 3 with scores and never map automatically), so no cut-off is used. A future
  mapper agent would use it as the minimum score for proposals.
- **D37 (Phase 7):** The container sets `FINAGENT_CODE_VERSION=container` because it has no
  `.git` folder. So a run created inside the image has a different `run_id` from one made
  on a developer machine. The image ships the committed run and serves it through `LATEST`.
- **D38 (QA):** The check-and-write for a reviewer decision runs under one lock for the whole
  process. `human_decisions.json` and `posted_tb.*` are written safely in one step (temp file
  + `os.replace`). So when several decisions on one entry arrive at the same time, exactly
  one gets 200 and the rest get 409. This holds for one server process. Several workers
  would need a file lock.
- **D39 (QA):** Reviewer names are limited to 200 characters and reasons to 2,000 (counted
  after trimming spaces; longer input returns 400). Decisions are final and cannot be
  corrected, so oversized input is refused rather than stored.
