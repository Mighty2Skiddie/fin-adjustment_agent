# PHASE 4 — Observability & run store

Read `docs/04_BACKEND_SPEC.md` §7–§8.

1. `observability/tracer.py` emitting every event type listed, one JSONL per run; `summary()`
   metrics into `manifest.json`. Instrument rules, LLM roles, guardrails, graph nodes, decisions,
   invariants, posting.
2. `observability/langfuse_hooks.py` behind the `observability` extra and `LANGFUSE_*` env; no-op
   otherwise. Document in README how to get a public trace link.
3. Complete `store/run_store.py` (manifest with input hashes, config hash, code version from
   `git rev-parse --short HEAD` or "nogit", metrics, invariants, status), append-only
   `audit_log.jsonl` events `run.created`, `decision.system`, `post.completed`.
4. Tests: trace contains required events for a run; manifest metrics present; `FAILED_INVARIANT`
   path writes to `failed/` and not to `posted_tb.*` (simulate by injecting an unbalanced accepted entry).
5. Commit `feat(observability): jsonl tracer, run manifest, audit log`.
