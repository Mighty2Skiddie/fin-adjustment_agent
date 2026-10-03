# 07 — Clarifying questions (written before starting)

The brief allows up to three questions before starting, and penalises asking none. Each
question below comes from a real gap in the data. Each one also states the fallback we use
if no answer arrives, so the build is never blocked. Until an answer arrives, the app
uses these fallbacks.

---

**Subject:** AI Agentic Engineer take-home — three clarifying questions before I start

Hi [name],

I have read the brief and gone through the data bundle. Three points materially change the
design, so I want to check them before building. I have included the assumption I will
use if you would rather I proceed.

**1. Who owns FX revaluation — the ERP export or our system?**
The TB contains EUR and GBP cash rows in local currency, and `manual_adjustments.json`
also contains JE-003, an FX revaluation of EUR cash. If our system translates foreign rows
at the period-end rate (per the README convention), JE-003 would count the same gain twice.
The booked amount (11,200.00) also does not match either rate basis I can derive from
`fx_rates.csv` (10,730.20 on average→end, 19,809.60 on opening→end).
Separately, GBP has no period-end rate.
*Fallback:* system translates every row at period-end; JE-003 is quarantined for a human
with the double-count and amount mismatch explained; GBP falls back to the period-average
rate with every affected line flagged.

**2. Is `prior_period_tb.csv` pre- or post-close, and is `6905` a rename of `6900`?**
The prior TB contains only balance-sheet accounts plus one P&L account (`6905 Sundry
Operating Expenses`), and it does not balance under any rate policy (USD-only Δ 1,737,000.00).
Retained earnings also move 5,180,000 → 7,240,000 with no distribution account visible.
*Fallback:* treat the prior TB as unreliable for opening balances (flagged), propose
`6905 → 6900` as a human-approved mapping, and use the prior TB only for comparatives.

**3. Materiality and intercompany scope.**
What imbalance tolerance should block posting versus be posted to a translation-difference /
suspense line with a flag (e.g. 1.00 absolute, 0.1% of total debits)? And is this a
single-entity TB in which `2170 Intercompany Payable` should remain as-is because there is no
counterparty TB to eliminate against?
*Fallback:* tolerance 1.00 absolute / 0.1% of debits; differences above tolerance are posted
to `3310 FX Translation Reserve` with lineage and a CRITICAL flag, never silently plugged;
intercompany balances are kept and flagged as non-eliminable.

Thanks — happy to proceed on the fallbacks if that is easier.

Pranav

---

## Why these three (for the architecture doc)

- Q1 decides if R007 (FX double-count) finds a real defect or a false alarm. It also decides
  if our system should do FX translation at all.
- Q2 decides if we can compute opening balances for the SOCIE and the cash-flow statement
  from this data at all.
- Q3 decides where we block and where we only flag. Every statement depends on that line.
  It also settles intercompany treatment, which the brief lists as a core difficulty.

Questions we considered and did not ask (documented as assumptions instead): whether
duplicate same-currency TB rows should be summed (README says yes); whether `TBD`
cash-flow categories should block the cash-flow statement (out of slice); whether gain/loss
accounts typed "Expense" are intentional (handled by sign-from-debit/credit regardless).
