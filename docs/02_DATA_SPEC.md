# 02 — Data specification and ground truth

All numbers below were computed with `Decimal`, quantized to 0.01, `ROUND_HALF_UP`.
Tests in `tests/ingest/test_health_audit.py` and `tests/adjustments/test_golden_decisions.py`
**must assert these exact values**. `inputs/` is never modified.

Conventions from the data bundle README: functional currency **USD**; period **2024-Q4**
(2024-10-01 → 2024-12-31); normal balance: assets/expenses debit, liabilities/equity/revenue
credit; TB rows may repeat an `account_code` across currencies and are summed in USD after
translation; the adjustments JSON is an **unposted batch** — the system decides
accept / reject / quarantine per entry.

---

## 1. `chart_of_accounts.csv` (72 accounts; 73 lines including the header)

| column | type | notes |
|---|---|---|
| `account_code` | str (4 digits) | unique |
| `account_name` | str | |
| `account_type` | enum `Header, Asset, Liability, Equity, Revenue, Expense` | `Header` = non-posting |
| `parent_code` | str or empty | empty for roots `1000 2000 3000 4000 5000 6000 7000 8000` |
| `statement` | `BS` / `PL` | |
| `cf_category` | `Cash, Operating, Investing, Financing, TBD` or empty | cash-flow classification |
| `normal_balance` | `Debit` / `Credit` or empty | |

Tree semantics: a node's balance = sum of its descendants' posted balances. Posting is
allowed only to non-`Header` accounts. **Important:** `8000` (type `Expense`) and `3300`
(type `Equity`) have children even though they are not `Header` — treat "has children" as
the structural header test for aggregation, and additionally emit health finding H-COA-05.

## 2. `trial_balance.csv` (62 rows, 59 unique codes)

Columns: `account_code, account_name, currency, debit, credit` (amounts as strings → Decimal).
Multi-currency rows exist only for `1110` (USD, EUR, GBP). Duplicate same-currency rows
exist for `6310` (245,000.00 and 38,500.00).

## 3. `prior_period_tb.csv` (33 rows)

Same columns. Balance-sheet accounts only, plus one stray P&L account `6905 Sundry Operating
Expenses` (132,000.00) which does not exist in the COA (renamed → `6900 Other Operating
Expenses` in the current period).

## 4. `fx_rates.csv` (7 rows)

Columns: `currency, rate_type, rate, period`. `rate_type ∈ {period_average, period_end, opening}`.
Present: EUR avg 1.082 / end 1.095 / open 1.071; GBP avg 1.264 / open 1.251 / **end MISSING**;
USD avg 1.0 / end 1.0 (no USD opening row — harmless, functional currency).

## 5. `manual_adjustments.json`

```json
{ "period": "2024-Q4", "functional_currency": "USD",
  "entries": [ { "id": "JE-001", "description": "...", "date": "YYYY-MM-DD", "source": "...",
                 "lines": [ { "account": "6100", "debit": 850000.0, "credit": 0.0, "memo": "..." } ] } ] }
```
Note: amounts are JSON numbers (floats). Load with `orjson`/`json` and convert via
`Decimal(str(value))` — never `Decimal(value)` on a float.

---

## 6. Ground truth — Data Health findings

Each health check lives in `src/finagent/ingest/health_checks/<id>.py` and produces
`HealthFinding(id, file, severity, title, detail, evidence, policy_applied)`.
Severity scale: `CRITICAL` (blocks posting unless policy resolves it), `HIGH`, `MEDIUM`, `LOW`, `INFO`.

### 6.1 Trial balance

| ID | Severity | Title | Exact evidence the test asserts |
|---|---|---|---|
| H-TB-01 | CRITICAL | TB does not balance; imbalance depends on FX policy | raw: D 71,072,200.00 C 71,077,000.00 Δ −4,800.00 · USD-only: D 69,834,500.00 C 71,077,000.00 Δ −1,242,500.00 · translated @period-end with GBP→average fallback: D 71,259,460.20 C 71,077,000.00 Δ +182,460.20 · with GBP→opening fallback: D 71,254,100.30 Δ +177,100.30. Policy applied: per `config.fx`. The difference is posted to a system-generated **translation difference** line (account `3310` by default, see `08_ASSUMPTIONS.md` A3) with lineage `TRANSLATION_DIFF`, and flagged if `abs(Δ) > materiality`. |
| H-TB-02 | HIGH | Duplicate account rows in the same currency | `6310` USD appears twice: 245,000.00 and 38,500.00 → summed to 283,500.00 per README convention; flagged as possible double-posting. |
| H-TB-03 | HIGH | Account not in COA (orphan) | `9999 Suspense - Unmapped` debit 12,400.00. Carried as `UNMAPPED` bucket; excluded from any COA subtotal; flagged for mapper/human. |
| H-TB-04 | MEDIUM | Credit balance on accounts whose COA normal balance is Debit | `7310` net −42,000.00 (credit) and `7400` net −18,000.00 (credit). Not an error (they are gain/loss accounts typed `Expense`), but proves sign-by-type logic would be wrong. |
| H-TB-05 | INFO | Row count differs from brief | brief says "~80 accounts"; file has 62 rows / 59 unique codes. |
| H-TB-06 | MEDIUM | Intercompany balance without counterparty | `2170` credit 1,240,000.00 in a single-entity TB; cannot be eliminated without the counterparty entity's TB. |

### 6.2 Chart of accounts

| ID | Severity | Title | Evidence |
|---|---|---|---|
| H-COA-01 | HIGH | Ambiguous cash-flow category (`TBD`) | `1150 Other Current Assets`, `2170 Intercompany Payable` |
| H-COA-02 | MEDIUM | Header with no children | `1290 Other Assets` |
| H-COA-03 | MEDIUM | Missing `normal_balance` | `7000 Non-Operating Items` |
| H-COA-04 | LOW | BS posting accounts with no `cf_category` | `3200 Retained Earnings`, `3300 Accumulated OCI`, `3310 FX Translation Reserve` (defensible: derived lines) |
| H-COA-05 | MEDIUM | Non-header accounts that have children | `8000 Income Tax Expense` (children 8100, 8200), `3300 Accumulated OCI` (child 3310) |
| H-COA-06 | INFO | Contra accounts with reversed normal balance (correct, but must be handled) | `1121, 1211, 1221` (Asset/Credit), `4200` (Revenue/Debit), `3400` (Equity/Debit) |

### 6.3 Prior-period TB

| ID | Severity | Title | Evidence |
|---|---|---|---|
| H-PP-01 | HIGH | Prior TB does not balance | raw D 35,177,800.00 C 32,345,000.00 Δ +2,832,800.00 · USD-only Δ +1,737,000.00 · translated @opening rates D 35,325,009.80 Δ +2,980,009.80 → opening balances unreliable for SOCIE / cash-flow walk. |
| H-PP-02 | HIGH | Account not in COA (renamed) | `6905 Sundry Operating Expenses` 132,000.00; fuzzy match → top candidate `6900 Other Operating Expenses` (rapidfuzz token_set_ratio; tests assert the top candidate, not the score). Proposed mapping, requires approval. |
| H-PP-03 | MEDIUM | P&L account present in a balance-sheet-only prior TB | `6905` is the only PL-range account. |
| H-PP-04 | INFO | Retained earnings movement with no dividend/distribution account visible | `3200`: 5,180,000.00 → 7,240,000.00 (Δ 2,060,000.00); `3310`: 95,000.00 → 180,000.00 (Δ 85,000.00). Needs clarification Q2. |

### 6.4 FX rates

| ID | Severity | Title | Evidence |
|---|---|---|---|
| H-FX-01 | CRITICAL | Missing period-end rate | `GBP period_end` absent; affects `1110 GBP 412,300.00`. Policy `config.fx.missing_rate_policy` ∈ {`block`, `fallback_average` (→ 521,147.20), `fallback_opening` (→ 515,787.30)}. Default `fallback_average`, flagged on every affected line. |
| H-FX-02 | INFO | Opening rates present | EUR 1.071, GBP 1.251 — usable for a CTA (translation reserve) walk; not used by the prototype beyond H-PP-01. |

### 6.5 Adjustments batch (batch-level, before per-entry rules)

| ID | Severity | Title | Evidence |
|---|---|---|---|
| H-ADJ-01 | INFO | Batch summary | 10 entries, 20 lines, batch total debits 1,801,200.00 vs credits 1,797,700.00 (Δ 3,500.00 → entirely JE-002). |
| H-ADJ-02 | MEDIUM | Batch references account not in COA | `6315` (JE-005). |

---

## 7. Ground truth — per-entry decisions

Decision = highest severity among findings: `BLOCK → REJECTED`, `ESCALATE → QUARANTINED`,
`WARN/INFO only → ACCEPTED`. R009 magnitude thresholds: INFO at ≥ 20% of the account's existing
absolute balance, WARN at ≥ 50%, never blocks (config `thresholds.magnitude_info_pct=0.20`,
`magnitude_warn_pct=0.50`). Rule IDs are defined in `04_BACKEND_SPEC.md` §3.

| JE | Decision | Findings (rule → severity) | Why, in finance-user language (the Explainer must say this, not more) |
|---|---|---|---|
| JE-001 Accrue Q4 bonus pool | **ACCEPTED** | R009 WARN (per account, D4: 2120 850,000 / 1,150,000 = 73.9% ≥ 50%; 6100 850,000 / 5,400,000 = 15.7% below threshold) | Balanced, both accounts exist, within period. |
| JE-002 Reclassify marketing spend | **REJECTED** | R001 BLOCK (debits 28,500.00 ≠ credits 25,000.00, Δ 3,500.00) | Entry is out of balance by 3,500.00. We cannot tell which side is right. Fix candidates: (a) credit 6310 28,500.00, (b) debit 6300 25,000.00 — the preparer must confirm. |
| JE-003 FX reval of EUR cash | **QUARANTINED** | R007 ESCALATE (system already translates `1110 EUR` at period-end 1.095 → manual reval would double-count); R007b WARN (booked 11,200.00 ≠ 10,730.20 expected = 825,400 × (1.095 − 1.082); ≠ 19,809.60 on opening basis); R009 INFO (7310 11,200 / 42,000 = 26.7%) | If the system revalues EUR cash itself, this entry counts the same gain twice. Also the amount does not match either rate basis. Needs finance to confirm who owns FX revaluation (Clarifying Q1). |
| JE-004 Bad debt top-up | **ACCEPTED** | R009 INFO ×2 (6600 45,000 / 95,000 = 47.4%; 1121 45,000 / 185,000 = 24.3% of existing allowance) | Balanced, valid, contra-asset direction consistent; magnitude noted for awareness. |
| JE-005 Reclass conference travel | **QUARANTINED** | R002 ESCALATE (`6315` not in COA); R002b INFO (fuzzy candidates — tests assert only that `6310 Travel and Entertainment` is the top candidate and carries `would_create_noop=true`; exact scores are not asserted); R005-derived note: mapping 6315→6310 would make both lines hit 6310 and the entry a no-op (circular) | The destination account doesn't exist. The closest existing account is the one the money is being moved *out of*, so remapping would cancel the entry. Either add `6315` to the COA (under 6000) or reject. |
| JE-006 Depreciation catch-up | **ACCEPTED** | R009 INFO (215,000 / 850,000 existing depreciation = 25.3%) | Balanced and valid; sizeable relative to the period's existing depreciation, shown for awareness. |
| JE-007 Deferred tax true-up | **ACCEPTED** | R009 INFO (8200 38,000 / 120,000 = 31.7%) | Balanced, valid. |
| JE-008 Intercompany settlement | **REJECTED** | R005 BLOCK (same account `2170` on both sides; entry nets to 0.00 on every account); R011 WARN (intercompany account with no counterparty reference) | Entry debits and credits the same account, so it changes nothing. The description says "settlement", which should reduce the payable against cash. Fix candidate: Dr 2170 320,000.00 / Cr 1110 320,000.00 — requires preparer confirmation of the paying bank account. |
| JE-009 Legal fee accrual | **ACCEPTED** | none | Balanced, valid. |
| JE-010 Reclass current portion of LTD | **ACCEPTED** | R009 INFO (2140 200,000 / 800,000 = 25.0%) | Balanced, valid; classification move within liabilities. |

Expected counts: **6 ACCEPTED, 2 REJECTED, 2 QUARANTINED**. *(R009 rows corrected during build — decision D4 in `08_ASSUMPTIONS.md`: R009 is evaluated per account on the entry's net movement; decisions are unchanged.)* `evals/golden/expected_decisions.json`
encodes this table as `{ "JE-001": {"decision": "ACCEPTED", "rule_ids": []}, ... }`.

Intent Reviewer (LLM) expected behaviour, recorded in cassettes:
- JE-008: `consistent=false` (description implies cash movement; lines do not touch cash) → adds `R013 ESCALATE` (already REJECTED, so decision unchanged; finding still recorded).
- JE-003: `consistent=true` (description matches lines) — the problem is policy, not intent.
- JE-002: `consistent=true`.
- JE-005: `consistent=true`.
- All others: `consistent=true`, no finding.

## 8. Ground truth — posting result

Only ACCEPTED entries post (JE-001, 004, 006, 007, 009, 010). Quarantined entries post only
after a human approves them in the UI (stored as a separate `human_decisions.json`; the
posted TB is recomputed as `base + accepted + human-approved`).

System posting of accepted batch, selected accounts (USD):

| account | base (after FX, dedupe) | Δ from accepted JEs | post-adjustment |
|---|---|---|---|
| 6100 Salaries | 5,400,000.00 Dr | +850,000.00 (JE-001) | 6,250,000.00 Dr |
| 2120 Accrued Expenses | 1,150,000.00 Cr | +850,000.00 (JE-001) +75,000.00 (JE-009) | 2,075,000.00 Cr |
| 6600 Bad Debt | 95,000.00 Dr | +45,000.00 (JE-004) | 140,000.00 Dr |
| 1121 Allowance | 185,000.00 Cr | +45,000.00 (JE-004) | 230,000.00 Cr |
| 6500 Depreciation | 850,000.00 Dr | +215,000.00 (JE-006) | 1,065,000.00 Dr |
| 1211 Accum Dep | 4,200,000.00 Cr | +215,000.00 (JE-006) | 4,415,000.00 Cr |
| 8200 Deferred Tax Exp | 120,000.00 Dr | +38,000.00 (JE-007) | 158,000.00 Dr |
| 1250 DTA | 320,000.00 Dr | −38,000.00 (JE-007) | 282,000.00 Dr |
| 6400 Professional Fees | 520,000.00 Dr | +75,000.00 (JE-009) | 595,000.00 Dr |
| 2210 LTD | 6,500,000.00 Cr | −200,000.00 (JE-010) | 6,300,000.00 Cr |
| 2140 Current LTD | 800,000.00 Cr | +200,000.00 (JE-010) | 1,000,000.00 Cr |
| 1110 Cash (translated, default policy) | 4,250,000.00 + 903,813.00 + 521,147.20 = 5,674,960.20 Dr | 0 | 5,674,960.20 Dr |
| 6310 T&E (deduped sum) | 283,500.00 Dr | 0 | 283,500.00 Dr |

Invariant tests: post-adjustment TB debits − credits == base imbalance (adjustments are
balanced, so the imbalance is unchanged); every posted line's `lineage` lists the TB row
indices, FX rate ids and JE ids that compose it; summing lineage components reproduces the
line amount exactly.

## 9. Impact preview (per entry, arithmetic only)

For each entry, compute the Δ on the COA ancestors of each line's account and report the
top-level roots touched, e.g. JE-001: `6000 Operating Expenses +850,000.00`,
`2100 Current Liabilities +850,000.00`, `2000 Total Liabilities +850,000.00`; net income
effect −850,000.00. Implemented in `adjustments/impact.py`; shown in the UI. This is not
statement generation.
