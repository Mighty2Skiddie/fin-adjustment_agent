"""Recorded LLM responses, committed to the repo so the app runs with no API key.

Key = sha256(role + prompt_version + canonical(input_payload)). The model name is deliberately
*not* in the key: a recording made with the fallback provider replays exactly like one made
with the primary, and the file records which model actually answered.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson

JSON_OPTS = orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS


def cassette_key(role: str, prompt_version: str, payload: dict[str, Any]) -> str:
    body = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(
        role.encode() + b"\x00" + prompt_version.encode() + b"\x00" + body
    ).hexdigest()


@dataclass(frozen=True)
class Recording:
    response: dict[str, Any]
    model: str
    provider: str
    recorded_at: str


class CassetteStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, role: str, key: str) -> Path:
        return self.root / role / f"{key[:24]}.json"

    def get(self, role: str, key: str) -> Recording | None:
        """A missing, unreadable or malformed recording is a miss, never an exception: a bad
        cassette file must not stop a run (the role falls back to its template)."""
        p = self.path(role, key)
        if not p.is_file():
            return None
        try:
            raw: Any = orjson.loads(p.read_bytes())
        except (OSError, orjson.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        data: dict[str, Any] = raw  # pyright: ignore[reportUnknownVariableType]
        response: Any = data.get("response")
        if data.get("key") != key or not isinstance(response, dict):
            return None
        return Recording(
            response=response,  # pyright: ignore[reportUnknownArgumentType]
            model=str(data.get("model", "unknown")),
            provider=str(data.get("provider", "unknown")),
            recorded_at=str(data.get("recorded_at", "unknown")),
        )

    def put(
        self,
        role: str,
        key: str,
        request: dict[str, Any],
        response: dict[str, Any],
        model: str,
        provider: str,
        recorded_at: str,
    ) -> Path:
        p = self.path(role, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "key": key,
            "role": role,
            "request": request,
            "response": response,
            "model": model,
            "provider": provider,
            "recorded_at": recorded_at,
        }
        p.write_bytes(orjson.dumps(record, option=JSON_OPTS) + b"\n")
        return p
