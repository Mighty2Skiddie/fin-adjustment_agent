"""Cassette keys, the cassette store, and LlmClient replay behaviour (no network, no key)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import orjson
import pytest

from finagent.adjustments.context import RuleContext
from finagent.adjustments.decisions import decide
from finagent.adjustments.validator import run_rules
from finagent.config import Settings, load_settings
from finagent.domain.models import Decision, JournalEntry
from finagent.llm.cassette import CassetteStore, cassette_key
from finagent.llm.providers import LlmClient, load_prompt
from finagent.llm.roles import explainer
from finagent.llm.schemas import Explanation
from finagent.llm.templates import template_explanation
from finagent.observability.tracer import Tracer

PAYLOAD: dict[str, Any] = {"role": "explainer", "entry": {"id": "JE-X", "lines": [1, 2]}}


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)


def cassette_settings(cassette_dir: Path) -> Settings:
    return load_settings({"llm": {"mode": "cassette", "cassette_dir": str(cassette_dir)}})


def llm_calls(tracer: Tracer) -> list[dict[str, Any]]:
    return [e for e in tracer.events if e["event"] == "llm.call"]


# ---- cassette_key ----------------------------------------------------------------------------
def test_key_is_deterministic_and_hex() -> None:
    k1 = cassette_key("explainer", "abc123", PAYLOAD)
    k2 = cassette_key("explainer", "abc123", dict(PAYLOAD))
    assert k1 == k2
    assert len(k1) == 64 and all(c in "0123456789abcdef" for c in k1)


def test_key_ignores_dict_insertion_order() -> None:
    reordered = {"entry": {"lines": [1, 2], "id": "JE-X"}, "role": "explainer"}
    assert cassette_key("explainer", "v", PAYLOAD) == cassette_key("explainer", "v", reordered)


@pytest.mark.parametrize(
    ("role", "version", "payload"),
    [
        ("fix_proposer", "abc123", PAYLOAD),
        ("explainer", "abc124", PAYLOAD),
        ("explainer", "abc123", {**PAYLOAD, "role": "other"}),
        ("explainer", "abc123", {"role": "explainer", "entry": {"id": "JE-X", "lines": [2, 1]}}),
        ("explainer", "abc123", {**PAYLOAD, "previous_violations": ["x"]}),
    ],
)
def test_key_sensitive_to_role_version_and_payload(
    role: str, version: str, payload: dict[str, Any]
) -> None:
    assert cassette_key(role, version, payload) != cassette_key("explainer", "abc123", PAYLOAD)


def test_role_and_version_are_separated() -> None:
    """The NUL separator stops ("ab", "c") colliding with ("a", "bc")."""
    assert cassette_key("ab", "c", PAYLOAD) != cassette_key("a", "bc", PAYLOAD)


# ---- CassetteStore ---------------------------------------------------------------------------
def test_store_roundtrip(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path)
    key = cassette_key("explainer", "v1", PAYLOAD)
    path = store.put(
        "explainer", key, {"payload": PAYLOAD}, {"a": "b"}, "model-x", "prov-y", "2024-01-01"
    )
    assert path == tmp_path / "explainer" / f"{key[:24]}.json"
    assert path.is_file()
    rec = store.get("explainer", key)
    assert rec is not None
    assert rec.response == {"a": "b"}
    assert (rec.model, rec.provider, rec.recorded_at) == ("model-x", "prov-y", "2024-01-01")
    on_disk = orjson.loads(path.read_bytes())
    assert on_disk["key"] == key and on_disk["role"] == "explainer"


def test_store_missing_file_is_none(tmp_path: Path) -> None:
    assert CassetteStore(tmp_path).get("explainer", "0" * 64) is None


def test_store_full_key_mismatch_is_none(tmp_path: Path) -> None:
    """Files are named by a key prefix; the full key inside must still match."""
    store = CassetteStore(tmp_path)
    key = "a" * 64
    other = "a" * 24 + "b" * 40
    store.put("explainer", key, {}, {"x": 1}, "m", "p", "t")
    assert store.path("explainer", other) == store.path("explainer", key)
    assert store.get("explainer", other) is None
    assert store.get("explainer", key) is not None


def test_store_role_is_part_of_the_path(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path)
    key = "c" * 64
    store.put("explainer", key, {}, {"x": 1}, "m", "p", "t")
    assert store.get("fix_proposer", key) is None


# ---- LlmClient -------------------------------------------------------------------------------
def test_cassette_dir_absolute_path_is_used(tmp_path: Path) -> None:
    client = LlmClient(cassette_settings(tmp_path))
    assert client.cassettes.root == tmp_path
    assert client.mode == "cassette" and client.enabled


def test_cassette_miss_returns_none_and_traces(tmp_path: Path) -> None:
    tracer = Tracer("t")
    client = LlmClient(cassette_settings(tmp_path), tracer)
    obj, meta = client.structured("explainer", Explanation, PAYLOAD, "msg", entry_id="JE-X")
    assert obj is None
    assert meta.cassette_miss is True
    assert meta.cassette_hit is False
    assert meta.model is None
    calls = llm_calls(tracer)
    assert len(calls) == 1
    assert calls[0]["cassette_miss"] is True
    assert calls[0]["entry_id"] == "JE-X"
    assert calls[0]["mode"] == "cassette"
    assert (
        calls[0]["cassette_key"]
        == cassette_key("explainer", meta.prompt_version or "", PAYLOAD)[:24]
    )


def test_cassette_hit_returns_recorded_object(tmp_path: Path) -> None:
    _, version = load_prompt("explainer")
    key = cassette_key("explainer", version, PAYLOAD)
    recorded = Explanation(summary="Recorded.", details=["one"], next_step="Do it.")
    CassetteStore(tmp_path).put(
        "explainer",
        key,
        {"payload": PAYLOAD},
        recorded.model_dump(mode="json"),
        "gemini-test",
        "google_genai",
        "2024-01-01T00:00:00Z",
    )
    tracer = Tracer("t")
    client = LlmClient(cassette_settings(tmp_path), tracer)
    obj, meta = client.structured("explainer", Explanation, PAYLOAD, "msg")
    assert obj == recorded
    assert meta.cassette_hit is True and meta.cassette_miss is False
    assert (meta.model, meta.provider) == ("gemini-test", "google_genai")
    assert meta.recorded_at == "2024-01-01T00:00:00Z"
    call = llm_calls(tracer)[0]
    assert call["cassette_hit"] is True
    assert "cassette_miss" not in call  # emitted as None -> dropped


def test_cassette_invalid_recording_is_a_miss(tmp_path: Path) -> None:
    _, version = load_prompt("explainer")
    key = cassette_key("explainer", version, PAYLOAD)
    CassetteStore(tmp_path).put("explainer", key, {}, {"nope": True}, "m", "p", "t")
    client = LlmClient(cassette_settings(tmp_path))
    obj, meta = client.structured("explainer", Explanation, PAYLOAD, "msg")
    assert obj is None
    assert meta.cassette_miss is True


def test_off_mode_makes_no_call(tmp_path: Path, settings: Settings) -> None:
    tracer = Tracer("t")
    client = LlmClient(settings, tracer)
    assert not client.enabled
    obj, meta = client.structured("explainer", Explanation, PAYLOAD, "msg")
    assert obj is None
    assert meta.mode == "off"
    assert meta.cassette_hit is None and meta.cassette_miss is False
    assert llm_calls(tracer) == []


# ---- roles on a miss -------------------------------------------------------------------------
def test_explainer_on_miss_falls_back_to_template(
    tmp_path: Path, entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    entry = entries["JE-002"]
    findings = run_rules(entry, rule_ctx)
    decision = decide(findings)
    assert decision == Decision.REJECTED
    tracer = Tracer("t")
    client = LlmClient(cassette_settings(tmp_path), tracer)
    exp, meta = explainer.run(entry, findings, decision, rule_ctx, client, tracer)
    assert exp == template_explanation(entry, findings, decision)
    assert meta["source"] == "template"
    assert meta["model"] is None
    assert meta["cassette_miss"] is True
    assert meta["guardrail_fallback"] is False
    assert meta["attempts"] == 1  # a miss is not retried
    assert [e["cassette_miss"] for e in llm_calls(tracer)] == [True]


def test_explainer_off_mode_uses_template(
    settings: Settings, entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    entry = entries["JE-005"]
    findings = run_rules(entry, rule_ctx)
    decision = decide(findings)
    tracer = Tracer("t")
    exp, meta = explainer.run(entry, findings, decision, rule_ctx, LlmClient(settings), tracer)
    assert exp == template_explanation(entry, findings, decision)
    assert meta["source"] == "template"
    assert meta["cassette_miss"] is False
    assert llm_calls(tracer) == []


def test_explainer_on_hit_uses_recording(
    tmp_path: Path, entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    entry = entries["JE-002"]
    findings = run_rules(entry, rule_ctx)
    decision = decide(findings)
    payload = explainer.build_payload(entry, findings, decision, rule_ctx)
    _, version = load_prompt(explainer.ROLE)
    recorded = Explanation(
        summary="The entry does not balance.",
        details=["R001: debits and credits differ."],
        next_step="Correct the amounts and resubmit.",
    )
    CassetteStore(tmp_path).put(
        explainer.ROLE,
        cassette_key(explainer.ROLE, version, payload),
        {"payload": payload},
        recorded.model_dump(mode="json"),
        "gemini-test",
        "google_genai",
        "t",
    )
    tracer = Tracer("t")
    client = LlmClient(cassette_settings(tmp_path), tracer)
    exp, meta = explainer.run(entry, findings, decision, rule_ctx, client, tracer)
    assert exp == recorded
    assert meta["source"] == "llm"
    assert meta["model"] == "gemini-test"
    assert meta["cassette_miss"] is False
    guard = [e for e in tracer.events if e["event"] == "guardrail.result"]
    assert [g["passed"] for g in guard] == [True]
