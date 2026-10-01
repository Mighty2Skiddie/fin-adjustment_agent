# PHASE 6 — API + frontend

Read `docs/04_BACKEND_SPEC.md` §9 and ALL of `docs/05_FRONTEND_SPEC.md`.

1. FastAPI app with every endpoint in §9, Pydantic response models, money as strings, error
   envelope, `GET /api/docs/architecture` serving `docs/ARCHITECTURE.md` text, static SPA mount.
   `tests/api/test_api.py` with TestClient covering: create run (and 409 idempotent), entries,
   decision 400 on REJECTED, decision success on QUARANTINED → posted-tb overlay shows HUMAN
   lineage, audit log event present.
2. Frontend per spec: tokens, fonts (IBM Plex Sans/Mono via @fontsource), AppShell + rail +
   RunTopBar, data layer, and the six pages in this order: Health → Queue (with expandable row,
   findings, explanation, fix candidates, impact, decision form) → Ledger (lineage drawer) →
   Entry detail with TraceTimeline → Audit → Evals → About. Keyboard shortcuts, reduced-motion,
   focus rings, loading skeletons, error and empty states.
3. `finagent serve` runs the app on :8000 serving `frontend/dist`. Verify in a browser; take the
   four screenshots listed in `docs/05_FRONTEND_SPEC.md` §7 into `docs/screenshots/`.
4. Commit in two parts: `feat(api): run, entries, decisions, lineage endpoints` and
   `feat(frontend): working-paper review UI`. Print the URL and the manual checks to perform.
