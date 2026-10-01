"""Ground truth for the trial-balance health checks: docs/02_DATA_SPEC.md §6.1."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import HealthSeverity, NormalBalance, TbRow
from finagent.ingest.health_checks import h_tb_01, h_tb_02, h_tb_03, h_tb_04, h_tb_05, h_tb_06
from finagent.ingest.health_checks.base import AuditContext

TB = "trial_balance.csv"


def _with_rows(ctx: AuditContext, rows: list[TbRow]) -> AuditContext:
    return dataclasses.replace(ctx, tb_rows=rows)


# H-TB-01 -------------------------------------------------------------------------------------


def test_tb01_imbalance_variants(audit_ctx: AuditContext) -> None:
    [f] = h_tb_01.check(audit_ctx)
    assert f.id == "H-TB-01"
    assert f.severity == HealthSeverity.CRITICAL
    assert f.file == TB
    ev = f.evidence
    assert ev["raw"]["delta"] == "-4800.00"
    assert ev["usd_only"]["delta"] == "-1242500.00"
    assert ev["pe_gbp_avg"]["delta"] == "182460.20"
    assert ev["pe_gbp_open"]["delta"] == "177100.30"
    assert ev["raw"]["debit"] == "71072200.00"
    assert ev["usd_only"]["debit"] == "69834500.00"
    assert ev["pe_gbp_avg"]["debit"] == "71259460.20"
    assert ev["pe_gbp_open"]["debit"] == "71254100.30"
    for key in ("raw", "usd_only", "pe_gbp_avg", "pe_gbp_open"):
        assert ev[key]["credit"] == "71077000.00"


def test_tb01_balanced_tb_has_no_finding(audit_ctx: AuditContext) -> None:
    rows = [
        TbRow(
            source_file=TB,
            row_index=0,
            account_code="1110",
            account_name="Cash",
            currency="USD",
            debit=Decimal("100.00"),
            credit=Decimal("0.00"),
        ),
        TbRow(
            source_file=TB,
            row_index=1,
            account_code="2170",
            account_name="Intercompany Payable",
            currency="USD",
            debit=Decimal("0.00"),
            credit=Decimal("100.00"),
        ),
    ]
    assert h_tb_01.check(_with_rows(audit_ctx, rows)) == []


# H-TB-02 -------------------------------------------------------------------------------------


def test_tb02_duplicate_same_currency(audit_ctx: AuditContext) -> None:
    [f] = h_tb_02.check(audit_ctx)
    assert f.id == "H-TB-02"
    assert f.severity == HealthSeverity.HIGH
    assert f.file == TB
    assert f.assumption == "A5"
    assert f.evidence == {
        "duplicates": [
            {
                "account_code": "6310",
                "currency": "USD",
                "rows": [46, 47],
                "amounts": ["245000.00", "38500.00"],
                "summed": "283500.00",
            }
        ]
    }
    assert "283,500.00" in f.message


def test_tb02_multi_currency_rows_are_not_duplicates(audit_ctx: AuditContext) -> None:
    """1110 appears in USD, EUR and GBP; only a repeat within one currency counts."""
    rows = [r for r in audit_ctx.tb_rows if r.row_index != 47]
    assert h_tb_02.check(_with_rows(audit_ctx, rows)) == []


# H-TB-03 -------------------------------------------------------------------------------------


def test_tb03_orphan_account(audit_ctx: AuditContext) -> None:
    [f] = h_tb_03.check(audit_ctx)
    assert f.id == "H-TB-03"
    assert f.severity == HealthSeverity.HIGH
    assert f.file == TB
    assert f.assumption == "A6"
    assert f.evidence == {
        "orphans": [
            {
                "account_code": "9999",
                "account_name": "Suspense - Unmapped",
                "debit": "12400.00",
                "credit": "0.00",
                "rows": [61],
            }
        ]
    }
    assert "12,400.00" in f.message


def test_tb03_no_orphans_when_code_added_to_coa(audit_ctx: AuditContext) -> None:
    template = audit_ctx.coa.get("6310")
    assert template is not None
    extra = template.model_copy(update={"code": "9999", "name": "Suspense - Unmapped"})
    accounts = [*audit_ctx.coa_accounts, extra]
    ctx = dataclasses.replace(audit_ctx, coa_accounts=accounts, coa=CoaTree(accounts))
    assert h_tb_03.check(ctx) == []


# H-TB-04 -------------------------------------------------------------------------------------


def test_tb04_credit_balance_on_debit_normal(audit_ctx: AuditContext) -> None:
    [f] = h_tb_04.check(audit_ctx)
    assert f.id == "H-TB-04"
    assert f.severity == HealthSeverity.MEDIUM
    assert f.file == TB
    assert f.assumption == "A7"
    assert f.evidence == {
        "accounts": [
            {"account_code": "7310", "net": "-42000.00", "normal_balance": "Debit"},
            {"account_code": "7400", "net": "-18000.00", "normal_balance": "Debit"},
        ]
    }
    assert "credit balance 42,000.00" in f.message


def test_tb04_credit_normal_accounts_are_not_flagged(audit_ctx: AuditContext) -> None:
    accounts = [
        a.model_copy(update={"normal_balance": NormalBalance.CREDIT})
        if a.code in {"7310", "7400"}
        else a
        for a in audit_ctx.coa_accounts
    ]
    ctx = dataclasses.replace(audit_ctx, coa_accounts=accounts, coa=CoaTree(accounts))
    assert h_tb_04.check(ctx) == []


# H-TB-05 -------------------------------------------------------------------------------------


def test_tb05_row_count_vs_brief(audit_ctx: AuditContext) -> None:
    [f] = h_tb_05.check(audit_ctx)
    assert f.id == "H-TB-05"
    assert f.severity == HealthSeverity.INFO
    assert f.file == TB
    assert f.evidence == {"rows": 62, "unique_codes": 59, "brief_says": "~80 accounts"}


def test_tb05_close_to_brief_is_silent(audit_ctx: AuditContext) -> None:
    template = audit_ctx.tb_rows[0]
    rows = [
        template.model_copy(update={"row_index": i, "account_code": f"X{i:03d}"}) for i in range(80)
    ]
    assert h_tb_05.check(_with_rows(audit_ctx, rows)) == []


# H-TB-06 -------------------------------------------------------------------------------------


def test_tb06_intercompany_without_counterparty(audit_ctx: AuditContext) -> None:
    [f] = h_tb_06.check(audit_ctx)
    assert f.id == "H-TB-06"
    assert f.severity == HealthSeverity.MEDIUM
    assert f.file == TB
    assert f.assumption == "A14"
    assert f.evidence == {
        "accounts": [
            {
                "account_code": "2170",
                "account_name": "Intercompany Payable",
                "debit": "0.00",
                "credit": "1240000.00",
            }
        ]
    }
    assert "1,240,000.00" in f.message


def test_tb06_zero_intercompany_balance_is_silent(audit_ctx: AuditContext) -> None:
    rows = [
        r.model_copy(update={"credit": Decimal("0.00")}) if r.account_code == "2170" else r
        for r in audit_ctx.tb_rows
    ]
    assert h_tb_06.check(_with_rows(audit_ctx, rows)) == []
