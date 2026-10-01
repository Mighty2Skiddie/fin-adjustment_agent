# fin-adjustments-agent

## What this is

A prototype **Manual Adjustments Agent** for an AI-native financial reporting platform. It
validates each manual journal entry with deterministic rules, decides
ACCEPT / REJECT / QUARANTINE, uses an LLM only to review intent, explain findings and propose
fixes, routes quarantined items to a human review queue, and posts accepted entries onto the
trial balance with line-level lineage.

## Scope

- **In:** TB ingest + FX translation, COA tree, data-health audit, adjustment
  validation / decisions / explanations / fix proposals, human review, posting with lineage,
  post-adjustment TB export, observability, evals, UI.
- **Out (architecture doc only):** four-statement assembly, IC eliminations, prior-period
  restatement, full COA mapper agent.

## Run in 3 commands

```
uv sync
uv run finagent run
uv run finagent serve
```

## Screenshots

*(Phase 7)*

## Architecture summary

See `docs/ARCHITECTURE.md` (Phase 7).

## Deliverables index

*(Phase 7)*
