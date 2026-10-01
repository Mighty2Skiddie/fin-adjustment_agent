from __future__ import annotations

from decimal import Decimal

import pytest
from typer.testing import CliRunner

from finagent.cli import app
from finagent.config import load_settings


def test_defaults_from_yaml() -> None:
    s = load_settings()
    assert s.period.id == "2024-Q4"
    assert s.functional_currency == "USD"
    assert s.fx.missing_rate_policy == "fallback_average"
    assert s.fx.translation_difference_account == "3310"
    assert s.materiality.imbalance_tolerance_abs == Decimal("1.00")
    assert s.thresholds.magnitude_info_pct == Decimal("0.20")
    assert isinstance(s.thresholds.magnitude_warn_pct, Decimal)


def test_env_override_nested(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINAGENT__FX__MISSING_RATE_POLICY", "block")
    s = load_settings()
    assert s.fx.missing_rate_policy == "block"
    assert s.fx.translation_difference_account == "3310"


def test_init_override_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINAGENT__FX__MISSING_RATE_POLICY", "block")
    s = load_settings({"fx": {"missing_rate_policy": "fallback_opening"}})
    assert s.fx.missing_rate_policy == "fallback_opening"


def test_llm_mode_short_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODE", "off")
    assert load_settings().llm.mode == "off"


def test_config_hash_stable() -> None:
    assert load_settings().config_hash() == load_settings().config_hash()


def test_cli_help_lists_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("audit", "run", "eval", "serve", "record-cassettes", "show"):
        assert cmd in result.output
