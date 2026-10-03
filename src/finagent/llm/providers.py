"""Provider-agnostic structured LLM calls, with cassette replay and a provider fallback.

Modes (`config.llm.mode`):
- `off`: no model at all; roles use deterministic templates.
- `cassette` (default): replay recorded responses; a miss is reported, never fatal.
- `live`: call the primary provider, fall back to the secondary on any provider error.
- `record`: `live`, and write every response to the cassette store.

Every call returns a validated Pydantic object or `None`; the caller decides what a `None`
means (template fallback). Nothing here can raise into the pipeline.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from finagent.config import ROOT, Settings
from finagent.llm.cassette import CassetteStore, cassette_key
from finagent.observability.langfuse_hooks import callbacks
from finagent.observability.tracer import Tracer
from finagent.store.run_store import now_iso

T = TypeVar("T", bound=BaseModel)
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(role: str) -> tuple[str, str]:
    """(system prompt, version). The version is a hash of the text, recorded in the trace and
    part of every cassette key, so it must not depend on how the file was checked out:
    `read_text` already folds CRLF to LF, and `utf-8-sig` drops a BOM an editor may add."""
    preamble = (PROMPTS_DIR / "_preamble.md").read_text(encoding="utf-8-sig")
    body = (PROMPTS_DIR / f"{role}.md").read_text(encoding="utf-8-sig")
    text = f"{preamble.strip()}\n\n{body.strip()}\n"
    return text, hashlib.sha256(text.encode()).hexdigest()[:12]


@dataclass
class CallMeta:
    role: str
    mode: str
    model: str | None = None
    provider: str | None = None
    prompt_version: str | None = None
    cassette_hit: bool | None = None
    cassette_miss: bool = False
    provider_fallback: bool = False
    error: str | None = None
    latency_ms: float = 0.0
    input_chars: int = 0
    output_chars: int = 0
    recorded_at: str | None = None


def get_chat_model(provider: str, model: str, settings: Settings) -> Any:
    """LangChain chat model via `init_chat_model` (provider packages are optional extras)."""
    from langchain.chat_models import init_chat_model

    return init_chat_model(
        model,
        model_provider=provider,
        temperature=settings.llm.temperature,
        timeout=settings.llm.timeout_s,
        max_retries=1,
    )


@dataclass
class CassetteChatModel:
    """Replays recorded structured responses by cassette key (no network, no key)."""

    store: CassetteStore

    def invoke_structured(
        self, role: str, key: str, schema: type[T]
    ) -> tuple[T | None, str | None, str | None, str | None]:
        rec = self.store.get(role, key)
        if rec is None:
            return None, None, None, None
        try:
            return schema.model_validate(rec.response), rec.model, rec.provider, rec.recorded_at
        except ValidationError:
            return None, rec.model, rec.provider, rec.recorded_at


@dataclass
class LlmClient:
    settings: Settings
    tracer: Tracer | None = None
    cassettes: CassetteStore = field(init=False)
    _models: dict[tuple[str, str], Any] = field(default_factory=dict[tuple[str, str], Any])

    def __post_init__(self) -> None:
        self.cassettes = CassetteStore(ROOT / self.settings.llm.cassette_dir)

    @property
    def mode(self) -> str:
        return self.settings.llm.mode

    @property
    def enabled(self) -> bool:
        return self.mode != "off"

    def _providers(self) -> list[tuple[str, str]]:
        llm = self.settings.llm
        out = [(llm.provider, llm.model)]
        if llm.fallback_provider and llm.fallback_model:
            out.append((llm.fallback_provider, llm.fallback_model))
        return out

    def _live(self, schema: type[T], system: str, user: str, meta: CallMeta) -> T | None:
        for i, (provider, model) in enumerate(self._providers()):
            try:
                chat = self._models.get((provider, model))
                if chat is None:
                    chat = get_chat_model(provider, model, self.settings)
                    self._models[(provider, model)] = chat
                structured = chat.with_structured_output(schema)
                result = structured.invoke(
                    [("system", system), ("human", user)],
                    config={
                        "callbacks": callbacks(self.settings),
                        "run_name": meta.role,
                        "metadata": {"prompt_version": meta.prompt_version},
                    },
                )
                obj = result if isinstance(result, schema) else schema.model_validate(result)
                meta.provider, meta.model, meta.provider_fallback = provider, model, i > 0
                return obj
            except Exception as exc:  # noqa: BLE001 - any provider failure -> next provider
                meta.error = f"{provider}/{model}: {type(exc).__name__}: {str(exc)[:200]}"
        return None

    def structured(
        self,
        role: str,
        schema: type[T],
        payload: dict[str, Any],
        user_message: str,
        entry_id: str | None = None,
    ) -> tuple[T | None, CallMeta]:
        system, version = load_prompt(role)
        meta = CallMeta(role=role, mode=self.mode, prompt_version=version)
        meta.input_chars = len(system) + len(user_message)
        if not self.enabled:
            return None, meta
        key = cassette_key(role, version, payload)
        start = time.perf_counter()
        obj: T | None = None
        if self.mode in {"cassette", "record"}:
            # `record` fills gaps only: an existing recording is replayed, never overwritten
            # (re-record everything with `finagent record-cassettes --clean`).
            replay = CassetteChatModel(self.cassettes)
            obj, meta.model, meta.provider, meta.recorded_at = replay.invoke_structured(
                role, key, schema
            )
            meta.cassette_hit = obj is not None
            meta.cassette_miss = obj is None and self.mode == "cassette"
        if obj is None and self.mode in {"live", "record"}:
            obj = self._live(schema, system, user_message, meta)
            if obj is not None and self.mode == "record":
                meta.recorded_at = now_iso()
                try:
                    self.cassettes.put(
                        role,
                        key,
                        {"system_prompt_version": version, "payload": payload},
                        obj.model_dump(mode="json"),
                        meta.model or "",
                        meta.provider or "",
                        meta.recorded_at,
                    )
                except OSError as exc:  # the answer is still usable; only the recording failed
                    meta.error = f"cassette write failed: {type(exc).__name__}: {exc}"[:240]
        meta.latency_ms = round((time.perf_counter() - start) * 1000, 3)
        meta.output_chars = len(obj.model_dump_json()) if obj is not None else 0
        if self.tracer is not None:
            self.tracer.emit(
                "llm.call",
                entry_id=entry_id,
                role=role,
                mode=self.mode,
                model=meta.model,
                provider=meta.provider,
                prompt_hash=version,
                cassette_key=key[:24],
                cassette_hit=meta.cassette_hit,
                cassette_miss=meta.cassette_miss or None,
                provider_fallback=meta.provider_fallback or None,
                error=meta.error,
                latency_ms=meta.latency_ms,
                input_tokens=meta.input_chars // 4,  # estimate: providers differ in reporting
                output_tokens=meta.output_chars // 4,
                recorded_at=meta.recorded_at,
            )
        return obj, meta
