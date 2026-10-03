# How to deploy fin-adjustments-agent

The app ships as **one Docker image**. Docker is a tool that packs an app and everything it needs into one box (an "image") that runs the same way on any computer.

Key facts:

- One program serves both the API and the web screen.
- It listens on port **7860**.
- It runs in **cassette** mode: it replays saved AI answers, so it needs **no API key and no secrets**.
- The same image runs on your own computer and on Hugging Face Spaces (a free hosting site for demo apps).

## 1. What the Dockerfile does

The `Dockerfile` (in the repo root) builds the image in two stages.

**Stage 1: `frontend` (based on `node:20-alpine`).** It builds the web screen.

1. Copies `frontend/package.json` and `frontend/package-lock.json`.
2. Runs `npm ci --no-audit --no-fund` to install the packages.
3. Copies the rest of `frontend/`.
4. Runs `npm run build`. This makes `frontend/dist`.

**Stage 2: `runtime` (based on `python:3.12-slim`).** It runs the app.

1. Copies the `uv` and `uvx` tools from `ghcr.io/astral-sh/uv:latest`.
2. Sets these settings:
   - `LLM_MODE=cassette` (replay saved AI answers),
   - `FINAGENT_CODE_VERSION=container` (the code version label used in the run id),
   - `UV_PYTHON_DOWNLOADS=never` (use the image's own Python 3.12),
   - plus `UV_COMPILE_BYTECODE=1`, `UV_LINK_MODE=copy`, `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`.
3. Creates a normal (non-admin) user called `app` with user id 1000. Hugging Face Spaces runs apps as user id 1000.
4. Copies `pyproject.toml`, `uv.lock` and `README.md`. Installs the libraries from `uv.lock` first:
   `uv sync --frozen --no-dev --no-install-project --extra llm-google --extra llm-groq`.
   Docker saves this step, so later builds are faster when only code changes.
5. Copies `src/` and installs the app itself (not in editable mode). The Google and Groq extras are included, so the image can also run `live` mode if you give it a key. It does not need one.
6. Copies `config/`, `inputs/`, `evals/` (with the saved AI answers), `docs/`, `output/` and the built `frontend/dist`.
7. Gives the `app` user ownership of `output/`, because human review decisions are written there. Makes `inputs/` read-only.
8. Switches to the `app` user.
9. Opens port 7860 (`EXPOSE 7860`).
10. Adds a health check. Every 30 seconds it calls `http://127.0.0.1:7860/healthz` (timeout 5 seconds, first check after 20 seconds).
11. Starts the app with:
    `/app/.venv/bin/finagent serve --host 0.0.0.0 --port 7860`.

**What is left out of the build.** The file `.dockerignore` keeps these out:

- secrets and local setups: `.env`, `.env.*` (but `.env.example` is kept), `.venv/`, Python caches, test and coverage caches,
- `frontend/node_modules/` and `frontend/dist/` (they are built inside the image),
- `.git/`, `.github/`, `tests/`, `docs/00_ASSIGNMENT_ORIGINAL.pdf` and `output/failed/`.

**At start-up**, `finagent serve` uses the run named in `output/runs/LATEST` (today: `0f6fe063474d`). If the image has no run, the app first makes one in cassette mode, then starts.

## 2. Run with Docker on your own computer

1. Install Docker Desktop and start it.
2. Open a terminal in the repo folder.
3. Build the image:

   ```
   docker build -t fin-adjustments-agent .
   ```

4. Start the app:

   ```
   docker run --rm -p 7860:7860 fin-adjustments-agent
   ```

5. Open <http://localhost:7860> in your browser.
6. Optional: check that the app is healthy.

   ```
   curl http://localhost:7860/healthz
   # {"ok":true}
   ```

**Optional: live AI calls** (not needed for the demo):

```
docker run --rm -p 7860:7860 -e LLM_MODE=live -e GOOGLE_API_KEY=... fin-adjustments-agent
```

**Keeping human decisions.** Approvals and rejections made in the web screen are saved in `output/runs/<run_id>/` inside the container. They are lost when the container is removed. To keep them, mount a folder on `/app/output`. That folder must be writable by user id 1000. It should contain a run; if it does not, the container makes one at start-up.

## 3. Deploy to Hugging Face Spaces

### Step 1. Create the Space

1. Go to <https://huggingface.co/new-space>.
2. Pick an owner and a name, for example `fin-adjustments-agent`.
3. Choose **Docker** as the SDK and the **Blank** template.
4. Choose the free **CPU basic** hardware and the visibility you want.
5. Click create. The Space starts empty. Its git address is `https://huggingface.co/spaces/<user>/<space>`.

### Step 2. Add the settings block to the README

Spaces reads its settings from a block at the very top of `README.md`. Add this block at the top of `README.md` on the branch you push to the Space. The GitHub copy does not need it.

```yaml
---
title: Fin Adjustments Agent
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---
```

- `sdk: docker` tells Spaces to build the Dockerfile.
- `app_port: 7860` is the port the app listens on. 7860 is also the Spaces default, but writing it down keeps the two in step.

### Step 3. Include the saved run in git

Git ignores `output/runs/` and `output/traces/`. Add the run by force, so the Space starts with the same run as the repo:

```
git add -f output/runs/0f6fe063474d output/runs/LATEST output/traces/0f6fe063474d.jsonl
```

If you skip this step, the Space still works. It makes a new cassette-mode run on first start.

### Step 4. Track image and PDF files with Git LFS

Hugging Face refuses pushes with binary files (images, PDFs) unless they are stored with Git LFS (Large File Storage). The repo has PNG files (screenshots, diagram previews) and a PDF under `docs/`. Track them first:

```
git lfs install
git lfs track "*.png" "*.pdf"
git add .gitattributes
git add --renormalize .
git commit -m "chore: track binary files with LFS for Hugging Face"
```

### Step 5. Push

```
git remote add hf https://huggingface.co/spaces/<user>/<space>
git push hf master:main
```

- This repo's branch is `master`. A Space builds from its `main` branch. So you push `master:main`.
- When git asks for a password, use a Hugging Face **access token with write rights** (Settings → Access Tokens), not your account password.
- If the Space already has a starter commit you do not need, use `git push --force hf master:main`.

### Step 6. Set the Space variable

In the Space, open **Settings → Variables and secrets**. Add a **variable** (not a secret):

| Name | Value |
|---|---|
| `LLM_MODE` | `cassette` |

The Dockerfile already uses `cassette`. The variable just makes the mode easy to see in the Space settings.

**Do not add API keys to a public Space.** In cassette mode the app makes no real AI calls, so it needs no secrets.

### Step 7. Check that it works

1. The Space page shows **Building**, then **Running**. The first build takes a few minutes (`npm ci`, `npm run build`, `uv sync`).
2. Open `https://<user>-<space>.hf.space/healthz`. It must return `{"ok":true}`.
3. Open the Space address. The top bar shows the run id, the period `2024-Q4` and the LLM mode `Cassette (recorded)`. The Health, Queue, Ledger, Audit, Evals and About pages all load.
4. Put the public address in `README.md` (replace `<your-space-url>`).

## 4. Common problems

| Problem | Cause and fix |
|---|---|
| `Bind for 0.0.0.0:7860 failed: port is already allocated` | Another program uses port 7860. Use another port on your computer: `docker run -p 8080:7860 …`, then open <http://localhost:8080>. Inside the container the port stays 7860. |
| Space stays on **Starting**, or says "app not responding" | The port does not match. `app_port` in the README block must be `7860`, and the start command must keep `--host 0.0.0.0`. |
| Web page says ``Frontend not built. Run `npm run build` in frontend/.`` | `frontend/dist` is missing. In Docker, the frontend stage failed: look for `npm ci` or `npm run build` errors in the build log. Outside Docker, run `cd frontend && npm ci && npm run build`. |
| Web screen changes do not show after `docker build` | Docker reused an old saved step. Rebuild with `docker build --no-cache -t fin-adjustments-agent .`. |
| `npm ci` fails in the frontend stage | `package-lock.json` does not match `package.json`. Run `npm install` in `frontend/`, commit the new lock file, build again. |
| `uv sync --frozen` fails | `uv.lock` does not match `pyproject.toml`. Run `uv lock`, commit `uv.lock`, build again. |
| Container stops during build or start (exit code 137) | Out of memory. Give Docker Desktop at least 4 GB (Settings → Resources). The web screen build uses the most memory. If it still fails, set `NODE_OPTIONS=--max-old-space-size=2048` in the frontend stage. |
| Approving an entry fails with a permission error | `output/` is not writable by user id 1000. This usually happens after mounting your own folder on `/app/output`. Fix that folder's owner or permissions. |
| Push to the Space is refused because of binary files | Track `*.png` and `*.pdf` with Git LFS (Step 4). |
| Push login fails | Use an access token with write rights as the git password, not your account password. |
