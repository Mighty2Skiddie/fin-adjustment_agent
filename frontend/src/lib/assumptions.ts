/**
 * Assumption texts from docs/08_ASSUMPTIONS.md (the "Assumption" column for A-ids, and the
 * build decisions findings reference). Findings carry only the id; the UI shows this text in
 * the amber assumption chip and on /about#assumptions. Keep in sync with the register.
 */
export const ASSUMPTIONS: Readonly<Record<string, string>> = {
  A1: "Functional currency USD; period 2024-10-01 → 2024-12-31",
  A2: "Every TB row is translated at the period-end rate (point-in-time TB). We do not apply average rates to P&L rows in this slice.",
  A3: "The post-translation imbalance is posted to 3310 FX Translation Reserve as a system line tagged TRANSLATION_DIFF, flagged CRITICAL when above materiality",
  A4: "Missing GBP period-end rate → fall back to period-average, flag every affected line",
  A5: "Duplicate same-currency TB rows for one account are summed, with a HIGH flag",
  A6: "Orphan TB account 9999 stays in an UNMAPPED bucket, excluded from COA subtotals, shown as a reconciling line",
  A7: "Sign is always debit − credit; account_type and normal_balance only drive warnings",
  A8: "\"Has children\" makes an account structural (aggregates), regardless of account_type",
  A9: "JE dates must fall inside the period; otherwise REJECT",
  A10: "An entry whose per-account nets are all zero is REJECTED as a no-op, not quarantined",
  A11: "Unbalanced entries are REJECTED and cannot be human-approved; they must be edited and resubmitted as a new version",
  A12: "Fix candidates are proposals only; nothing is auto-applied",
  A13: "Magnitude thresholds: INFO ≥ 20%, WARN ≥ 50% of the account's existing absolute balance; never blocking",
  A14: "Intercompany balances are not eliminated (single-entity TB) and are flagged",
  A15: "Prior-period TB is used for comparatives only; opening-balance walks are flagged unreliable",
  A16: "6905 (prior) → 6900 (current) is a *proposed* mapping requiring approval",
  A17: "The Intent Reviewer LLM can only add findings (escalate), never remove or soften one",
  A18: "Cassette mode is the default so the prototype runs with no API key; recordings/hand-authored responses are labelled",
  D6: "R007b computes the expected revaluation only for currencies that have a period-end rate; GBP is excluded with a note, so the expected values are EUR-only (10,730.20 / 19,809.60).",
  D7: "Fuzzy candidate matching (H-PP-02, R002b) only considers postable, non-structural accounts; otherwise header 6000 Operating Expenses outranks 6900.",
}

export const ASSUMPTIONS_SOURCE = 'docs/08_ASSUMPTIONS.md'

export function assumptionText(id: string): string | undefined {
  return ASSUMPTIONS[id]
}

/** DOM id used for anchors on /about, e.g. "assumption-A3". */
export function assumptionAnchor(id: string): string {
  return `assumption-${id}`
}
