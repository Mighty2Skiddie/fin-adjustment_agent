"""Serve the built frontend (`frontend/dist`) with an SPA fallback to index.html."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from finagent.config import ROOT

DIST = ROOT / "frontend" / "dist"


def mount_frontend(app: FastAPI, dist: Path = DIST) -> None:
    index = dist / "index.html"
    root = dist.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:  # pyright: ignore[reportUnusedFunction]
        if full_path.startswith(("api/", "healthz")):
            raise HTTPException(status_code=404)
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and root in candidate.parents:
            # Vite content-hashes everything under assets/, so it can be cached forever.
            immutable = full_path.startswith("assets/")
            headers = (
                {"Cache-Control": "public, max-age=31536000, immutable"} if immutable else None
            )
            return FileResponse(candidate, headers=headers)
        if not index.is_file():
            raise HTTPException(
                status_code=404, detail="Frontend not built. Run `npm run build` in frontend/."
            )
        return FileResponse(index)
