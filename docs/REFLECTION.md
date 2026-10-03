<!-- Drafted from the build session log; the candidate should review and add personal notes before submitting. -->

# Reflection

## With 3 months instead of 8 hours

- **Tests on many made-up data sets**, not only this bundle, checking that Assets = Liabilities + Equity always holds.
- **Better account matching.** Today a fuzzy text match suggests three accounts. I would learn from past approved mappings and measure accuracy.
- **A ledger where records are only added, never changed**, so restatements and "as of" views are easy.
- **Policies with versions and approval.** Today FX and materiality rules sit in one YAML file.
- **Live AI tests**, not only answers recorded on 2026-10-01, with alerts when answers drift.

## Where this prototype breaks at scale

- **Thousands of accounts and entries.** The matcher compares each unknown account with every postable account. The review screen fits tens of entries, not thousands.
- **More than one company.** There is no entity field. JE-008 and the 1,240,000.00 credit on 2170 Intercompany Payable can be flagged, but never eliminated. The other company's books are not in scope.
- **Storage.** Runs and human decisions are JSON files under `output/runs/`. Many reviewers at once need a real database.
- **One entry at a time.** The 10 entries are checked one after another. They could run in parallel.

## How I used AI tools

I used Claude Code as my coding assistant. It also ran separate AI helpers. Some wrote parts of the code. Others tried to find mistakes in that code. Details are in `docs/AI_USAGE.md`. What mattered most:

- **Check the expected answers first.** Before any code, every expected number in the spec was recomputed with exact decimals. This found a spec conflict. One rule (R009) gave 73.9% (a warning) on JE-001's 2120 line, where the expected results showed nothing. The tool asked me. I chose to measure per account (decision D4).
- **The tool's own safety check was wrong.** It treated account codes like "6100" as invented amounts. On the first live recording, 33% of AI answers were thrown away. Reading the trace (the step-by-step run log) showed why. The eval report (the automatic test report) now shows a fallback rate of 0.0000.
- **Attacking the code beat writing more tests.** A separate AI helper found five holes in finished code. One: a memo could break out of the `<untrusted_data>` wrapper. Another: a 5.00 "fix" for JE-002 used an amount that was not in the entry.
- **Evals found what review missed.** "SYN-11" was read as the number −11. I fixed it narrowly, so "USD-3600" did not become a way around the check.
- **Browser testing found real bugs.** The page overflowed at 420 px wide, totals were cut off, and the main code file the browser downloads was 767 kB. Splitting it brought it to 468 kB.
- **What the checks cannot catch.** Gemini's JE-003 explanation says GBP is translated at the period-end rate. In fact GBP has no period-end rate, so the average rate is used. Every number in it is correct, so the checks pass it. I left it visible.

## One thing I think you are underestimating

**The product is policy, not arithmetic.** The trial balance (the list of every account and its total) does not balance under any FX policy:

| FX policy | Out of balance by |
|---|---:|
| Raw numbers, no translation | −4,800.00 |
| Keep USD rows only | −1,242,500.00 |
| GBP uses the average rate | +182,460.20 |
| GBP uses the opening rate | +177,100.30 |

Arithmetic cannot pick between these. A person must own the choice. The run records the policy in use (`fallback_average`). It posts the 182,460.20 difference to account 3310 as a flagged line. It does not hide it.

JE-003 shows the same thing for one entry. The booked 11,200.00 matches neither 10,730.20 nor 19,809.60. Whether the entry should exist depends on who owns FX revaluation. The AI is a small part of this system. Most of the value is making these choices clear and visible on every number they change.
