# 08 — Assumptions register

Every accounting or data assumption the system makes. Each has an ID referenced from code
(`assumption="A3"` on findings) and from the UI (amber "assumption" chip). A finance reviewer
should be able to disagree with any line here and know exactly what changes.

| ID | Assumption | Why we had to assume | What changes if wrong | Confidence |
|---|---|---|---|---|
| A1 | Functional currency USD; period 2024-10-01 → 2024-12-31 | Stated in bundle README | — | High |
| A2 | Every TB row is translated at the **period-end** rate (point-in-time TB). We do not apply average rates to P&L rows in this slice. | The brief's slice is adjustments, not statements; a single rate keeps the TB internally consistent. In the full product P&L rows use period-average and the difference flows to CTA. | P&L lines for non-USD rows would differ; there are none in this data (only `1110` is multi-currency), so no numeric impact here | Medium |
| A3 | The post-translation imbalance is posted to `3310 FX Translation Reserve` as a system line tagged `TRANSLATION_DIFF`, flagged CRITICAL when above materiality | A TB that does not balance cannot be posted; translation differences belong in CTA under the current-rate method. The Δ here (182,460.20) is far larger than a rounding difference, so it is flagged rather than accepted | Finance may prefer a dedicated suspense account or a hard block | Medium |
| A4 | Missing GBP period-end rate → fall back to period-average, flag every affected line | No rate = no translation; blocking the whole run for one rate is unhelpful in review mode | `block` policy stops posting; `fallback_opening` changes 1110 by −5,359.90 | Medium |
| A5 | Duplicate same-currency TB rows for one account are **summed**, with a HIGH flag | README states repeated codes should be summed; same-currency repetition is still suspicious | If the 38,500.00 row is a double-post, 6310 is overstated by 38,500.00 | Medium |
| A6 | Orphan TB account `9999` stays in an `UNMAPPED` bucket, excluded from COA subtotals, shown as a reconciling line | We must not guess a mapping for a suspense account | Mapping it changes one subtotal by 12,400.00 | High |
| A7 | Sign is always debit − credit; `account_type` and `normal_balance` only drive warnings | Gain/loss accounts are typed Expense with credit balances; contra accounts have reversed normal balances | — (this is the safer choice in all cases) | High |
| A8 | "Has children" makes an account structural (aggregates), regardless of `account_type` | `8000` and `3300` have children but are not typed Header | Posting directly to 8000/3300 would be ambiguous; none occurs in the data | High |
| A9 | JE dates must fall inside the period; otherwise REJECT | Mid-period adjustments are in scope; out-of-period postings need a different workflow | Could be QUARANTINE if finance allows backdated entries | Medium |
| A10 | An entry whose per-account nets are all zero is REJECTED as a no-op, not quarantined | It cannot change any balance, so approving it is meaningless | — | High |
| A11 | Unbalanced entries are REJECTED and cannot be human-approved; they must be edited and resubmitted as a new version | Approving an unbalanced entry breaks the ledger invariant | — | High |
| A12 | Fix candidates are proposals only; nothing is auto-applied | Judgment belongs to the preparer; the system cannot know which of two conflicting values is right | — | High |
| A13 | Magnitude thresholds: INFO ≥ 20%, WARN ≥ 50% of the account's existing absolute balance; never blocking | Reasonable defaults for a review aid | Tune in `config/default.yaml` | Low |
| A14 | Intercompany balances are not eliminated (single-entity TB) and are flagged | No counterparty TB provided | Consolidation would net 2170 against a receivable we do not have | High |
| A15 | Prior-period TB is used for comparatives only; opening-balance walks are flagged unreliable | It does not balance and contains a P&L account | If post-close and balanced, SOCIE opening walk becomes computable | Medium |
| A16 | `6905` (prior) → `6900` (current) is a *proposed* mapping requiring approval | Name similarity, same range | Approving changes prior comparatives for 6900 by 132,000.00 | Medium |
| A17 | The Intent Reviewer LLM can only add findings (escalate), never remove or soften one | Probabilistic judgment must not override deterministic checks | — | High |
| A18 | Cassette mode is the default so the prototype runs with no API key; recordings/hand-authored responses are labelled | Zero-cost, reproducible demo | Live mode changes wording, never decisions (decisions are rule-driven) | High |

## Decisions made during build

*(Claude Code appends here whenever a spec ambiguity is resolved during implementation.)*

- D1 (Phase 0): Frontend uses React 19 (what `npm create vite` and current shadcn/ui resolve to) instead of the spec's React 18 — current shadcn components rely on ref-as-prop, which React 18 does not support.
- D2 (Phase 0): Added an optional `llm-openai` extra / `openai` provider alongside google_genai / groq / anthropic; the default stays google_genai + cassette mode.
- D3 (Phase 0): `.gitattributes` marks `inputs/**` as `-text` so git never rewrites line endings in the raw data (input file hashes feed `run_id`).
- D4 (pre-build, approved): R009 applies per account using the entry's net movement on that account (so JE-008's 2170 lines cancel). §7 `rule_ids` are corrected to what that rule produces; decisions are unchanged.
- D5 (pre-build): The translation difference line is part of the base ledger, so 3310 base = 180,000.00 + 182,460.20 = 362,460.20 Cr and the base and posted TB both net to 0.00.
- D6 (pre-build): R007b computes the expected revaluation only for currencies that have a period-end rate; GBP is excluded with a note, so the expected values are EUR-only (10,730.20 / 19,809.60).
- D7 (pre-build): Fuzzy candidate matching (H-PP-02, R002b) only considers postable, non-structural accounts; otherwise header `6000 Operating Expenses` outranks `6900`.
