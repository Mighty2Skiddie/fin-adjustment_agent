"""Optional Langfuse export. A no-op unless the `observability` extra is installed, the
config enables it and LANGFUSE_* keys are present — the app never depends on it.

The JSONL trace stays the system of record; Langfuse is a shareable view of the same LLM calls.
"""

from __future__ import annotations

import importlib
import os
from functools import lru_cache
from typing import Any

from finagent.config import Settings

REQUIRED_ENV = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")


def langfuse_status(settings: Settings) -> tuple[bool, str]:
    """(enabled, reason) — the reason is shown by the CLI/API so a disabled export is explicit."""
    if not settings.observability.langfuse_enabled:
        return False, "disabled in config (observability.langfuse_enabled=false)"
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        return False, f"missing environment variables: {', '.join(missing)}"
    try:
        importlib.import_module("langfuse")
    except ImportError:
        return False, "langfuse not installed (uv sync --extra observability)"
    return True, "enabled"


@lru_cache(maxsize=1)
def _handler_factory() -> Any:
    module = importlib.import_module("langfuse.langchain")
    return module.CallbackHandler


def callbacks(settings: Settings) -> list[Any]:
    """LangChain callbacks to attach to model / graph invocations ([] when disabled)."""
    enabled, _ = langfuse_status(settings)
    if not enabled:
        return []
    try:
        return [_handler_factory()()]
    except Exception:  # noqa: BLE001 - observability must never break a run
        return []


def flush(settings: Settings) -> None:
    enabled, _ = langfuse_status(settings)
    if not enabled:
        return
    try:
        client = importlib.import_module("langfuse").get_client()
        client.flush()
    except Exception:  # noqa: BLE001
        return
