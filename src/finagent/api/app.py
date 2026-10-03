"""FastAPI app: JSON API under /api, the built SPA everywhere else. Money is always a string."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from finagent.api.routers import entries, evals, health, lineage, runs
from finagent.api.service import ApiError
from finagent.api.static import mount_frontend


def error_body(code: str, message: str, detail: object = None) -> dict[str, object]:
    return {"error": {"code": code, "message_for_user": message, "detail": detail}}


async def _api_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return JSONResponse(
        status_code=exc.status, content=error_body(exc.code, exc.message_for_user, exc.detail)
    )


async def _validation(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return JSONResponse(
        status_code=422,
        content=error_body("invalid_request", "Some fields are missing or invalid.", exc.errors()),
    )


async def _http(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    message = "Not found." if exc.status_code == 404 else "The request could not be completed."
    return JSONResponse(
        status_code=exc.status_code, content=error_body("http_error", message, exc.detail)
    )


def healthz() -> dict[str, bool]:
    return {"ok": True}


def create_app() -> FastAPI:
    app = FastAPI(title="fin-adjustments-agent", version="1.0.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_api_route("/healthz", healthz, methods=["GET"])
    for module in (runs, health, entries, lineage, evals):
        app.include_router(module.router)
    mount_frontend(app)
    return app


app = create_app()
