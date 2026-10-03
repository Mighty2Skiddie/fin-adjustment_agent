# syntax=docker/dockerfile:1
# Multi-stage build: Node builds the static UI, Python serves API + UI on one port.
# Hugging Face Spaces (Docker SDK) expects the app on 7860 and runs as uid 1000.

# ---- Stage 1: frontend ---------------------------------------------------------------------
FROM node:20-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: runtime ----------------------------------------------------------------------
FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    LLM_MODE=cassette \
    FINAGENT_CODE_VERSION=container

RUN useradd --create-home --uid 1000 app
WORKDIR /app

# Dependencies first (cached layer), then the project itself, non-editable.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --extra llm-google --extra llm-groq
COPY src/ ./src/
RUN uv sync --frozen --no-dev --no-editable --extra llm-google --extra llm-groq

# Data and run state: inputs are read-only; output/ must be writable for human decisions.
COPY config/ ./config/
COPY inputs/ ./inputs/
COPY evals/ ./evals/
COPY docs/ ./docs/
COPY output/ ./output/
COPY --from=frontend /build/frontend/dist ./frontend/dist

RUN chown -R app:app /app/output && chmod -R a-w /app/inputs
USER app

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/healthz')"
CMD ["/app/.venv/bin/finagent", "serve", "--host", "0.0.0.0", "--port", "7860"]
