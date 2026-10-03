"""Shared dependencies. The store root is overridable so tests run against a temp directory."""

from __future__ import annotations

from finagent.store.run_store import RunStore

_store: RunStore | None = None


def get_store() -> RunStore:
    global _store
    if _store is None:
        _store = RunStore()
    return _store


def set_store(store: RunStore | None) -> None:
    global _store
    _store = store
