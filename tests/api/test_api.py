from __future__ import annotations

import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from typing import Any

import orjson
import pytest
from fastapi.testclient import TestClient

from finagent.api.app import create_app
from finagent.api.deps import set_store
from finagent.config import load_settings
from finagent.pipeline import run_pipeline
from finagent.store.run_store import RunStore


@pytest.fixture()
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, str]]:
    for key in ("GOOGLE_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    store = RunStore(tmp_path / "runs")
    rid = run_pipeline(load_settings({"llm": {"mode": "cassette"}}), store).manifest.run_id
    set_store(store)
    with TestClient(create_app()) as client:
        yield client, rid
    set_store(None)


def _approve(client: TestClient, rid: str, je: str, action: str = "APPROVED") -> Any:
    return client.post(
        f"/api/runs/{rid}/entries/{je}/decision",
        json={"action": action, "actor": "A. Controller", "reason": "Confirmed with treasury."},
    )


def test_healthz(api: tuple[TestClient, str]) -> None:
    client, _ = api
    assert client.get("/healthz").json() == {"ok": True}


def test_runs_list_and_latest_alias(api: tuple[TestClient, str]) -> None:
    client, rid = api
    runs = client.get("/api/runs").json()
    assert [r["run_id"] for r in runs] == [rid] and runs[0]["latest"] is True
    assert runs[0]["counts"] == {"accepted": 6, "quarantined": 2, "rejected": 2}
    m = client.get("/api/runs/latest").json()
    assert m["run_id"] == rid and m["status"] == "OK" and m["metrics"]["llm_calls"] == 18


def test_create_run_is_idempotent(api: tuple[TestClient, str]) -> None:
    client, rid = api
    res = client.post("/api/runs", json={"config_overrides": {"llm": {"mode": "cassette"}}})
    assert res.status_code == 409 and res.json() == {"run_id": rid, "existing": True}


def test_create_run_new_config(api: tuple[TestClient, str]) -> None:
    client, rid = api
    res = client.post("/api/runs", json={"config_overrides": {"llm": {"mode": "off"}}})
    assert res.status_code == 200 and res.json()["run_id"] != rid
    assert client.get("/api/runs/latest").json()["llm_mode"] == "off"


def test_unknown_run_uses_error_envelope(api: tuple[TestClient, str]) -> None:
    client, _ = api
    res = client.get("/api/runs/nope/entries")
    assert res.status_code == 404
    err = res.json()["error"]
    assert err["code"] == "run_not_found" and "not found" in err["message_for_user"]


def test_health(api: tuple[TestClient, str]) -> None:
    client, rid = api
    h = client.get(f"/api/runs/{rid}/health").json()
    assert len(h["findings"]) == 20 and h["brief_listed_total"] == 10
    assert h["by_severity"]["CRITICAL"] == 2
    active = [v for v in h["fx_variants"] if v["active"]]
    assert [v["key"] for v in active] == ["pe_gbp_avg"] and active[0]["delta"] == "182460.20"


def test_entries_money_as_strings(api: tuple[TestClient, str]) -> None:
    client, rid = api
    entries = client.get(f"/api/runs/{rid}/entries").json()
    assert len(entries) == 10
    je2 = next(e for e in entries if e["entry"]["id"] == "JE-002")
    assert je2["entry"]["lines"][0]["debit"] == "28500.00"
    assert je2["effective_decision"] == "REJECTED" and je2["effective_state"] == "system"
    je8 = next(e for e in entries if e["entry"]["id"] == "JE-008")
    assert "R013" in [f["rule_id"] for f in je8["findings"]]


def test_entry_detail(api: tuple[TestClient, str]) -> None:
    client, rid = api
    d = client.get(f"/api/runs/{rid}/entries/JE-001").json()
    assert d["decision"] == "ACCEPTED" and d["human_decisions"] == []
    assert all(p["posted"] for p in d["lineage_preview"])
    assert client.get(f"/api/runs/{rid}/entries/JE-999").status_code == 404


def test_cannot_approve_rejected(api: tuple[TestClient, str]) -> None:
    client, rid = api
    res = _approve(client, rid, "JE-002")
    assert res.status_code == 400
    msg = res.json()["error"]["message_for_user"]
    assert "can't be approved" in msg and "new version" in msg


def test_cannot_decide_accepted(api: tuple[TestClient, str]) -> None:
    client, rid = api
    assert _approve(client, rid, "JE-001").status_code == 400


def test_reason_required(api: tuple[TestClient, str]) -> None:
    client, rid = api
    res = client.post(
        f"/api/runs/{rid}/entries/JE-003/decision",
        json={"action": "APPROVED", "actor": "A", "reason": "ok"},
    )
    assert res.status_code == 400 and res.json()["error"]["code"] == "reason_too_short"
    bad = client.post(f"/api/runs/{rid}/entries/JE-003/decision", json={"action": "APPROVED"})
    assert bad.status_code == 422 and "error" in bad.json()


def test_approve_quarantined_posts_with_human_lineage(api: tuple[TestClient, str]) -> None:
    client, rid = api
    before = client.get(f"/api/runs/{rid}/posted-tb").json()
    cash_before = next(ln for ln in before["lines"] if ln["account_code"] == "1110")
    res = _approve(client, rid, "JE-003")
    assert res.status_code == 200
    body = res.json()
    assert body["effective_decision"] == "ACCEPTED" and body["decision"] == "QUARANTINED"
    after = client.get(f"/api/runs/{rid}/posted-tb").json()
    cash = next(ln for ln in after["lines"] if ln["account_code"] == "1110")
    assert Decimal(cash["debit"]) - Decimal(cash_before["debit"]) == Decimal("11200.00")
    kinds = [r["kind"] for r in cash["lineage"]]
    assert "HUMAN" in kinds and "JE" in kinds
    assert all(after["invariants"].values())
    assert after["totals"]["imbalance"] == "0.00"
    events = client.get(f"/api/runs/{rid}/audit-log").json()
    human = [e for e in events if e["event"] == "decision.human"]
    assert len(human) == 1 and human[0]["before"] == "QUARANTINED"
    assert human[0]["after"] == "ACCEPTED" and human[0]["actor"] == "A. Controller"
    lineage = client.get(f"/api/runs/{rid}/lineage/1110").json()
    assert lineage["reconciles"] is True
    assert any(c["kind"] == "HUMAN" and c["source"]["decision"] for c in lineage["components"])
    trace = client.get(f"/api/runs/{rid}/trace/JE-003").json()
    assert trace[-1]["event"] == "decision.human"


def test_decisions_are_final(api: tuple[TestClient, str]) -> None:
    client, rid = api
    assert _approve(client, rid, "JE-005", "REJECTED").status_code == 200
    again = _approve(client, rid, "JE-005")
    assert again.status_code == 409
    entries = client.get(f"/api/runs/{rid}/entries").json()
    je5 = next(e for e in entries if e["entry"]["id"] == "JE-005")
    assert je5["effective_decision"] == "REJECTED"
    assert je5["effective_state"] == "rejected by A. Controller"


def test_concurrent_decisions_have_one_winner(api: tuple[TestClient, str]) -> None:
    client, rid = api
    barrier = threading.Barrier(8)

    def go(i: int) -> int:
        barrier.wait()
        return client.post(
            f"/api/runs/{rid}/entries/JE-003/decision",
            json={"action": "APPROVED", "actor": f"user{i}", "reason": "concurrent decision test"},
        ).status_code

    with ThreadPoolExecutor(8) as pool:
        codes = sorted(pool.map(go, range(8)))
    assert codes == [200] + [409] * 7
    audit = client.get(f"/api/runs/{rid}/audit-log").json()
    assert sum(e["event"] == "decision.human" for e in audit) == 1
    entries = client.get(f"/api/runs/{rid}/entries").json()
    assert sum(e["human_decision"] is not None for e in entries) == 1


@pytest.mark.parametrize(
    ("actor", "reason", "code"),
    [
        ("A" * 201, "Confirmed with treasury.", "actor_too_long"),
        ("Ann", "r" * 2001, "reason_too_long"),
    ],
    ids=["actor", "reason"],
)
def test_decision_field_length_caps(
    api: tuple[TestClient, str], actor: str, reason: str, code: str
) -> None:
    client, rid = api
    res = client.post(
        f"/api/runs/{rid}/entries/JE-003/decision",
        json={"action": "APPROVED", "actor": actor, "reason": reason},
    )
    assert res.status_code == 400 and res.json()["error"]["code"] == code


def test_lineage_accrued_expenses(api: tuple[TestClient, str]) -> None:
    client, rid = api
    out = client.get(f"/api/runs/{rid}/lineage/2120").json()
    assert out["reconciles"] is True and out["line"]["credit"] == "2075000.00"
    assert [c["ref"] for c in out["components"] if c["kind"] == "JE"] == ["JE-001#2", "JE-009#2"]
    assert client.get(f"/api/runs/{rid}/lineage/0000").status_code == 404


def test_trace_for_je008(api: tuple[TestClient, str]) -> None:
    client, rid = api
    events = client.get(f"/api/runs/{rid}/trace/JE-008").json()
    kinds = {e["event"] for e in events}
    assert {"rule.result", "llm.call", "guardrail.result", "decision"} <= kinds


def test_evals_missing_then_present(api: tuple[TestClient, str], tmp_path: Path) -> None:
    client, rid = api
    res = client.get(f"/api/runs/{rid}/evals")
    assert res.status_code == 404 and "finagent eval" in res.json()["error"]["message_for_user"]
    (tmp_path / "evals").mkdir()
    (tmp_path / "evals" / "report.json").write_bytes(orjson.dumps({"passed": True}))
    assert client.get(f"/api/runs/{rid}/evals").json() == {"passed": True}


def test_config_redacts_secrets(
    api: tuple[TestClient, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = api
    monkeypatch.setenv("GROQ_API_KEY", "gsk_secret_value")
    cfg = client.get("/api/config").json()
    assert cfg["secrets"]["GROQ_API_KEY"] == "set"
    assert "gsk_secret_value" not in orjson.dumps(cfg).decode()


def test_architecture_doc(api: tuple[TestClient, str]) -> None:
    client, _ = api
    res = client.get("/api/docs/architecture")
    assert res.status_code == 200 and "Architecture" in res.text


def test_api_404_is_json_not_spa(api: tuple[TestClient, str]) -> None:
    client, _ = api
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404 and res.json()["error"]["code"] == "http_error"
