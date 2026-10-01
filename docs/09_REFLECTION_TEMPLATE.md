# 09 — One-page reflection (template; finalise in Phase 7, keep to one page)

## With 3 months instead of 8 hours

- Build the ledger kernel as a library with property-based tests (Hypothesis) over
  randomly generated COA trees and journals: A = L + E and NI → RE must hold for every
  generated input, not just this bundle.
- Make the COA mapper a real retrieval problem: embeddings over account names + descriptions
  + historical mappings per ERP, with a human-approved mapping memory that becomes training
  data for the confidence model. Measure mapper precision on held-out ERP exports.
- Event-sourced ledger (append-only journal of posted lines) instead of recomputed JSON
  snapshots, so re-runs, restatements and "as-of" views are first-class.
- Policy engine with versioned policies (FX fallback, materiality, cut-off) and an approval
  workflow around policy changes — today it is a YAML file.
- Multi-entity model from day one: entity id on every row, counterparty id on every IC line,
  elimination as a deterministic pass with its own lineage kind.
- Replace cassettes with a proper eval harness in CI against live models, with drift
  alarms on faithfulness and decision agreement.

## Where this prototype breaks at scale

- **1000s of accounts:** rules are O(lines), fine; the fuzzy mapper (`rapidfuzz` over every
  COA name per orphan) becomes O(orphans × accounts) and the "COA excerpt" in prompts stops
  fitting — needs retrieval. The expanded-row UI assumes tens of entries, not thousands;
  needs server-side pagination and a "needs review" inbox.
- **Multi-entity consolidation:** the kernel has no entity dimension. Lineage would need
  `entity` and `elimination` kinds; the single translation-difference line becomes per-entity
  CTA; intercompany matching needs both sides' TBs and a tolerance for timing differences.
- **State:** JSON files per run are fine for a prototype and for audit, but concurrent human
  decisions need a real store with optimistic locking.
- **Sequential graph execution:** 10 entries run in series; at scale, entries are independent
  and should fan out, with the batch-level invariants as the join.

## How I used AI tools

*(Pull 4–6 concrete items from `AI_USAGE.md`. Suggested seeds, replace with what actually happened:)*
- Claude Code scaffolded the rule engine and tests from the spec in one pass; the spec's
  ground-truth tables made this reliable.
- It tried to parse CSV amounts as float twice; the "no `float(`" grep test caught it.
- It proposed auto-mapping `6315 → 6310` for JE-005 — plausible, and wrong (makes the entry
  a no-op). This is exactly the hallucinated-mapping failure mode; the code-level
  "would create no-op" check came from catching this.
- When asked to write the explanation prompt it initially let the model restate amounts in
  its own words; the number-whitelist guardrail exists because of that.
- Useful for: boilerplate, tests, the frontend data layer. Not useful for: deciding accounting
  policy — every time I let it decide, it picked the convenient option.

## One thing I think you are underestimating

*(Pick one and argue it in 4–5 sentences. Candidates:)*
- **Policy, not arithmetic, is the product.** The TB in the bundle does not balance under
  *any* FX policy, and which Δ you get (−4,800 / −1,242,500 / +182,460) depends on a choice a
  human must own. Most of the system's value is making those choices explicit, versioned
  and visible on every affected number — the LLM is a small part of that.
- **The adjustments batch is where fraud and error enter.** Validation that is "balanced and
  accounts exist" passes JE-008, which changes nothing, and would pass a settlement booked
  to the wrong bank account. Intent review against the description is the real control, and
  it is the hardest part to make reliable.
- **Traceability has a UX cost nobody budgets for.** Lineage is cheap to store and expensive
  to *show*; the lineage drawer took as long as the rule engine.
