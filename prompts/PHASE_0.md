# PHASE 0 — Scaffold & tooling

Read `README_START_HERE.md`, `CLAUDE.md`, and `docs/06_BUILD_PLAN.md` (Phase 0 section). Then:

1. Create `pyproject.toml` for package `finagent` (src layout), Python 3.12, with dependencies
   from `CLAUDE.md` "Stack" and optional extras `llm-google`, `llm-groq`, `llm-anthropic`,
   `observability`. Script entry `finagent = "finagent.cli:app"`. Configure `ruff` (line length
   100, rules E,F,I,B,UP,SIM), `pyright` strict on `src`, `pytest` (`testpaths = ["tests"]`,
   `addopts = "-q"`).
2. `uv sync` and commit `uv.lock`.
3. Create the full folder tree from `CLAUDE.md` with `__init__.py` files and a `cli.py` exposing
   typer commands `audit`, `run`, `eval`, `serve`, `record-cassettes`, `show` as stubs that print
   "not implemented (phase N)".
4. `config/default.yaml` and `.env.example` exactly as in `docs/04_BACKEND_SPEC.md` §1, plus
   `src/finagent/config.py` with a pydantic-settings `Settings` that loads YAML and env overrides
   (`FINAGENT__` nested delimiter `__`). Decimal fields from strings. Add `tests/test_config.py`.
5. `.pre-commit-config.yaml` (ruff, ruff-format, pyright), `.github/workflows/ci.yml` (uv sync →
   ruff → pyright → pytest), `.gitignore` (Python, Node, `.env`, `output/runs/*` except a
   `.gitkeep`; note: we WILL commit one completed run later by force-adding it).
6. Frontend: `npm create vite@latest frontend -- --template react-ts`, add Tailwind, shadcn/ui
   (init with default style, CSS variables), TanStack Query, react-router-dom, lucide-react.
   Add `vite.config.ts` proxy `/api` → `http://localhost:8000`. Replace the template App with an
   empty `AppShell` that renders "fin-adjustments-agent" so the build is meaningful.
7. `README.md` skeleton with the sections: What this is · Scope (in/out) · Run in 3 commands ·
   Screenshots (placeholders) · Architecture summary · Deliverables index.
8. Run the Phase 0 acceptance commands from `docs/06_BUILD_PLAN.md`. Commit
   `chore: scaffold project`. Print the phase summary.
