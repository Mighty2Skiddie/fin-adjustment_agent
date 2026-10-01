from __future__ import annotations

import dataclasses
from decimal import Decimal

from finagent.config import load_settings
from finagent.domain.models import FxRate, HealthSeverity, JeLine
from finagent.ingest.fx import RateBook
from finagent.ingest.health_checks import h_adj_01, h_adj_02, h_fx_01, h_fx_02
from finagent.ingest.health_checks.base import AuditContext

# --- H-FX-01 -------------------------------------------------------------------------------


def test_fx01_missing_gbp_period_end(audit_ctx: AuditContext) -> None:
    [f] = h_fx_01.check(audit_ctx)
    assert f.id == "H-FX-01"
    assert f.severity == HealthSeverity.CRITICAL
    assert f.file == "fx_rates.csv"
    assert f.title == "Missing period-end rate"
    assert f.evidence == {
        "missing": [
            {
                "currency": "GBP",
                "rate_type": "period_end",
                "affected_rows": [{"account_code": "1110", "row": 2, "local_amount": "412300.00"}],
                "fallback_average": "521147.20",
                "fallback_opening": "515787.30",
            }
        ],
        "policy": "fallback_average",
        "fallback_rate_id": "GBP/period_average",
    }
    assert f.policy_applied == "fx.missing_rate_policy=fallback_average"
    assert f.assumption == "A4"
    assert "412,300.00" in f.message
    assert "521,147.20" in f.message


def test_fx01_block_policy_still_reports(audit_ctx: AuditContext) -> None:
    settings = load_settings({"llm": {"mode": "off"}, "fx": {"missing_rate_policy": "block"}})
    ctx = dataclasses.replace(
        audit_ctx, settings=settings, ratebook=RateBook(audit_ctx.fx_rates, "block")
    )
    [f] = h_fx_01.check(ctx)
    assert f.severity == HealthSeverity.CRITICAL
    assert f.evidence["policy"] == "block"
    assert "fallback_rate_id" not in f.evidence
    assert f.policy_applied == "fx.missing_rate_policy=block"


def test_fx01_opening_policy_names_opening_rate(audit_ctx: AuditContext) -> None:
    settings = load_settings(
        {"llm": {"mode": "off"}, "fx": {"missing_rate_policy": "fallback_opening"}}
    )
    ctx = dataclasses.replace(
        audit_ctx, settings=settings, ratebook=RateBook(audit_ctx.fx_rates, "fallback_opening")
    )
    [f] = h_fx_01.check(ctx)
    assert f.evidence["fallback_rate_id"] == "GBP/opening"


def test_fx01_nothing_missing_when_rate_supplied(audit_ctx: AuditContext) -> None:
    gbp_end = FxRate(
        id="GBP/period_end", currency="GBP", rate_type="period_end", rate=Decimal("1.27"), period=""
    )
    rates = [*audit_ctx.fx_rates, gbp_end]
    ctx = dataclasses.replace(
        audit_ctx, fx_rates=rates, ratebook=RateBook(rates, "fallback_average")
    )
    assert h_fx_01.check(ctx) == []


# --- H-FX-02 -------------------------------------------------------------------------------


def test_fx02_opening_rates(audit_ctx: AuditContext) -> None:
    [f] = h_fx_02.check(audit_ctx)
    assert f.id == "H-FX-02"
    assert f.severity == HealthSeverity.INFO
    assert f.file == "fx_rates.csv"
    assert f.evidence == {"opening_rates": {"EUR": "1.071", "GBP": "1.251"}}


def test_fx02_no_opening_rates(audit_ctx: AuditContext) -> None:
    rates = [r for r in audit_ctx.fx_rates if r.rate_type != "opening"]
    assert h_fx_02.check(dataclasses.replace(audit_ctx, fx_rates=rates)) == []


# --- H-ADJ-01 ------------------------------------------------------------------------------


def test_adj01_batch_summary(audit_ctx: AuditContext) -> None:
    [f] = h_adj_01.check(audit_ctx)
    assert f.id == "H-ADJ-01"
    assert f.severity == HealthSeverity.INFO
    assert f.file == "manual_adjustments.json"
    assert f.evidence == {
        "entries": 10,
        "lines": 20,
        "total_debit": "1801200.00",
        "total_credit": "1797700.00",
        "difference": "3500.00",
        "unbalanced_entries": ["JE-002"],
    }
    assert "3,500.00" in f.message


def test_adj01_balanced_batch(audit_ctx: AuditContext) -> None:
    entries = [e for e in audit_ctx.entries if e.id != "JE-002"]
    [f] = h_adj_01.check(dataclasses.replace(audit_ctx, entries=entries))
    assert f.evidence["entries"] == 9
    assert f.evidence["difference"] == "0.00"
    assert f.evidence["unbalanced_entries"] == []


def test_adj01_empty_batch(audit_ctx: AuditContext) -> None:
    assert h_adj_01.check(dataclasses.replace(audit_ctx, entries=[])) == []


# --- H-ADJ-02 ------------------------------------------------------------------------------


def test_adj02_unknown_account(audit_ctx: AuditContext) -> None:
    [f] = h_adj_02.check(audit_ctx)
    assert f.id == "H-ADJ-02"
    assert f.severity == HealthSeverity.MEDIUM
    assert f.file == "manual_adjustments.json"
    assert f.evidence == {"accounts": ["6315"], "entries": ["JE-005"]}


def test_adj02_all_accounts_known(audit_ctx: AuditContext) -> None:
    entries = [
        e.model_copy(
            update={
                "lines": [
                    ln if ln.account in audit_ctx.coa else ln.model_copy(update={"account": "6310"})
                    for ln in e.lines
                ]
            }
        )
        for e in audit_ctx.entries
    ]
    assert h_adj_02.check(dataclasses.replace(audit_ctx, entries=entries)) == []


def test_adj02_lists_every_unknown_account(audit_ctx: AuditContext) -> None:
    je1 = audit_ctx.entries[0]
    extra = JeLine.model_validate({"account": "9999", "debit": "0", "credit": "0"})
    changed = je1.model_copy(update={"lines": [*je1.lines, extra]})
    ctx = dataclasses.replace(audit_ctx, entries=[changed, *audit_ctx.entries[1:]])
    [f] = h_adj_02.check(ctx)
    assert f.evidence == {"accounts": ["6315", "9999"], "entries": sorted([je1.id, "JE-005"])}
