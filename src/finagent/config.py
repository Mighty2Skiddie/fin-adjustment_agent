"""Settings: `config/default.yaml` overlaid by environment variables.

Policy (FX fallback, materiality, thresholds) lives in YAML so a change of policy is a
reviewable diff, not a code change. Environment overrides use the `FINAGENT__` prefix with
`__` as the nesting delimiter (`FINAGENT__FX__MISSING_RATE_POLICY=block`). The short
`LLM_MODE` / `LLM_PROVIDER` / `LLM_MODEL` variables from `.env.example` are honoured too.
"""

from __future__ import annotations

import hashlib
import os
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import orjson
import yaml
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


def find_root() -> Path:
    """The repo root holds `config/default.yaml`; prefer cwd so containers work too."""
    env = os.environ.get("FINAGENT_ROOT")
    if env:
        return Path(env)
    for base in (Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents):
        if (base / "config" / "default.yaml").is_file():
            return base
    return Path.cwd()


ROOT = find_root()
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"

_ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return _ENV_REF.sub(lambda m: os.environ.get(m.group(1)) or (m.group(2) or ""), value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, list):
        return [_expand_env(v) for v in value]  # pyright: ignore[reportUnknownVariableType]
    return value


def _decimal_from_str(v: object) -> Decimal:
    if isinstance(v, float):
        raise ValueError("monetary and ratio settings must be strings, not floats")
    return Decimal(str(v))


class PeriodSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    start: str
    end: str


class FxSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    translation_mode: Literal["system", "erp_pretranslated"] = "system"
    balance_sheet_rate: str = "period_end"
    missing_rate_policy: Literal["block", "fallback_average", "fallback_opening"] = (
        "fallback_average"
    )
    translation_difference_account: str = "3310"


class MaterialitySettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    imbalance_tolerance_abs: Decimal
    imbalance_tolerance_pct: Decimal

    _dec = field_validator("imbalance_tolerance_abs", "imbalance_tolerance_pct", mode="before")(
        _decimal_from_str
    )


class ThresholdSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    magnitude_info_pct: Decimal
    magnitude_warn_pct: Decimal
    fuzzy_match_min_score: int = 80
    mapping_confidence_auto: Decimal

    _dec = field_validator(
        "magnitude_info_pct", "magnitude_warn_pct", "mapping_confidence_auto", mode="before"
    )(_decimal_from_str)


class LlmSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    mode: Literal["cassette", "live", "off"] = "cassette"
    provider: str = "google_genai"
    model: str = "gemini-2.5-flash"
    temperature: int = 0
    max_retries: int = 1
    cassette_dir: str = "evals/cassettes"


class ObservabilitySettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    trace_dir: str = "output/traces"
    langfuse_enabled: bool = False


class _YamlSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], path: Path) -> None:
        super().__init__(settings_cls)
        self._path = path

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        raw: Any = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        data: dict[str, Any] = _expand_env(raw)
        llm: dict[str, Any] = dict(data.get("llm") or {})
        for env_name, key in (("LLM_MODE", "mode"), ("LLM_PROVIDER", "provider")):
            if os.environ.get(env_name):
                llm[key] = os.environ[env_name]
        if not llm.get("model"):
            llm.pop("model", None)
        data["llm"] = llm
        return data


_config_path: Path = DEFAULT_CONFIG


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FINAGENT__", env_nested_delimiter="__", frozen=True, extra="ignore"
    )

    period: PeriodSettings
    functional_currency: str = "USD"
    fx: FxSettings = FxSettings()
    materiality: MaterialitySettings
    thresholds: ThresholdSettings
    llm: LlmSettings = LlmSettings()
    observability: ObservabilitySettings = ObservabilitySettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, env_settings, _YamlSource(settings_cls, _config_path))

    def canonical_json(self) -> bytes:
        """Stable serialisation used for the config hash in `run_id`."""
        return orjson.dumps(self.model_dump(mode="json"), option=orjson.OPT_SORT_KEYS)

    def config_hash(self) -> str:
        return hashlib.sha256(self.canonical_json()).hexdigest()


def load_settings(overrides: dict[str, Any] | None = None, path: Path | None = None) -> Settings:
    """Build settings; `overrides` (nested dict) beat env, which beats YAML."""
    global _config_path
    _config_path = path or DEFAULT_CONFIG
    return Settings(**(overrides or {}))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def deep_merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)  # pyright: ignore[reportUnknownArgumentType]
        else:
            out[k] = v
    return out
