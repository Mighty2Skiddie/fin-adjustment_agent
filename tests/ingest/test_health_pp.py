from __future__ import annotations

import dataclasses
from decimal import Decimal

from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import (
    AccountType,
    CoaAccount,
    HealthSeverity,
    NormalBalance,
    Statement,
    TbRow,
)
from finagent.ingest.fx import RateBook
from finagent.ingest.health_checks import h_pp_01, h_pp_02, h_pp_03, h_pp_04
from finagent.ingest.health_checks.base import AuditContext

FILE = "prior_period_tb.csv"


def _without(ctx: AuditContext, code: str) -> AuditContext:
    return dataclasses.replace(
        ctx, prior_rows=[r for r in ctx.prior_rows if r.account_code != code]
    )


def _row(code: str, name: str, debit: str, credit: str, currency: str = "USD") -> TbRow:
    return TbRow(
        source_file=FILE,
        row_index=999,
        account_code=code,
        account_name=name,
        currency=currency,
        debit=Decimal(debit),
        credit=Decimal(credit),
    )


def test_pp_01_prior_tb_imbalance(audit_ctx: AuditContext) -> None:
    (f,) = h_pp_01.check(audit_ctx)
    assert f.id == "H-PP-01"
    assert f.severity == HealthSeverity.HIGH
    assert f.file == FILE
    assert f.assumption == "A15"
    assert f.evidence == {
        "raw": {"debit": "35177800.00", "credit": "32345000.00", "delta": "2832800.00"},
        "usd_only": {"debit": "34082000.00", "credit": "32345000.00", "delta": "1737000.00"},
        "opening": {"debit": "35325009.80", "credit": "32345000.00", "delta": "2980009.80"},
    }
    assert "35,177,800.00" in f.message


def test_pp_01_balanced_prior_tb_is_clean(audit_ctx: AuditContext) -> None:
    rows = [
        _row("1110", "Cash", "100.00", "0.00"),
        _row("2110", "AP", "0.00", "100.00"),
    ]
    assert h_pp_01.check(dataclasses.replace(audit_ctx, prior_rows=rows)) == []
    assert h_pp_01.check(dataclasses.replace(audit_ctx, prior_rows=[])) == []


def test_pp_01_missing_opening_rate_omits_opening_variant(audit_ctx: AuditContext) -> None:
    rates = [r for r in audit_ctx.fx_rates if r.rate_type != "opening"]
    book = RateBook(rates, "block", audit_ctx.settings.functional_currency)
    ctx = dataclasses.replace(audit_ctx, fx_rates=rates, ratebook=book)
    (f,) = h_pp_01.check(ctx)
    assert "opening" not in f.evidence
    assert f.evidence["raw"]["delta"] == "2832800.00"
    assert f.evidence["usd_only"]["delta"] == "1737000.00"


def test_pp_02_orphan_with_fuzzy_candidates(audit_ctx: AuditContext) -> None:
    (f,) = h_pp_02.check(audit_ctx)
    assert f.id == "H-PP-02"
    assert f.severity == HealthSeverity.HIGH
    assert f.file == FILE
    assert f.assumption == "A16"
    (orphan,) = f.evidence["orphans"]
    assert orphan["account_code"] == "6905"
    assert orphan["account_name"] == "Sundry Operating Expenses"
    assert orphan["amount"] == "132000.00"
    assert orphan["candidates"][0]["code"] == "6900"
    assert orphan["candidates"][0]["name"] == "Other Operating Expenses"
    assert 1 <= len(orphan["candidates"]) <= 3
    assert "approval" in (f.suggested_action or "")


def test_pp_02_clean_when_all_mapped(audit_ctx: AuditContext) -> None:
    assert h_pp_02.check(_without(audit_ctx, "6905")) == []


def test_pp_03_pl_account_in_prior_tb(audit_ctx: AuditContext) -> None:
    (f,) = h_pp_03.check(audit_ctx)
    assert f.id == "H-PP-03"
    assert f.severity == HealthSeverity.MEDIUM
    assert f.file == FILE
    assert f.evidence == {"accounts": ["6905"]}


def test_pp_03_detects_mapped_pl_account(audit_ctx: AuditContext) -> None:
    ctx = _without(audit_ctx, "6905")
    assert h_pp_03.check(ctx) == []
    ctx = dataclasses.replace(
        ctx, prior_rows=[*ctx.prior_rows, _row("4100", "Product Revenue", "0.00", "5.00")]
    )
    (f,) = h_pp_03.check(ctx)
    assert f.evidence == {"accounts": ["4100"]}


def test_pp_04_reserve_movements(audit_ctx: AuditContext) -> None:
    (f,) = h_pp_04.check(audit_ctx)
    assert f.id == "H-PP-04"
    assert f.severity == HealthSeverity.INFO
    assert f.file == FILE
    assert f.evidence == {
        "movements": [
            {
                "account_code": "3200",
                "prior": "5180000.00",
                "current": "7240000.00",
                "delta": "2060000.00",
            },
            {
                "account_code": "3310",
                "prior": "95000.00",
                "current": "180000.00",
                "delta": "85000.00",
            },
        ],
        "distribution_accounts_found": [],
    }
    assert "Q2" in f.message


def test_pp_04_reports_distribution_account(audit_ctx: AuditContext) -> None:
    extra = CoaAccount(
        code="3250",
        name="Dividends Declared",
        account_type=AccountType.EQUITY,
        parent_code="3000",
        statement=Statement.BS,
        cf_category="Financing",
        normal_balance=NormalBalance.DEBIT,
    )
    accounts = [*audit_ctx.coa_accounts, extra]
    ctx = dataclasses.replace(audit_ctx, coa_accounts=accounts, coa=CoaTree(accounts))
    (f,) = h_pp_04.check(ctx)
    assert f.evidence["distribution_accounts_found"] == ["3250"]


def test_pp_04_clean_when_no_movement(audit_ctx: AuditContext) -> None:
    rows = [r for r in audit_ctx.prior_rows if r.account_code not in {"3200", "3310"}]
    assert h_pp_04.check(dataclasses.replace(audit_ctx, prior_rows=rows)) == []
