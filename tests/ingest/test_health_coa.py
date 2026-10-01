from __future__ import annotations

import dataclasses

from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import AccountType, CoaAccount, HealthSeverity, NormalBalance
from finagent.ingest.health_checks import (
    h_coa_01,
    h_coa_02,
    h_coa_03,
    h_coa_04,
    h_coa_05,
    h_coa_06,
)
from finagent.ingest.health_checks.base import AuditContext

FILE = "chart_of_accounts.csv"


def _with_accounts(ctx: AuditContext, accounts: list[CoaAccount]) -> AuditContext:
    return dataclasses.replace(ctx, coa_accounts=accounts, coa=CoaTree(accounts))


def _edit(ctx: AuditContext, code: str, **changes: object) -> AuditContext:
    accounts = [a.model_copy(update=changes) if a.code == code else a for a in ctx.coa_accounts]
    return _with_accounts(ctx, accounts)


def test_coa_01_tbd_cf_category(audit_ctx: AuditContext) -> None:
    (f,) = h_coa_01.check(audit_ctx)
    assert f.id == "H-COA-01"
    assert f.severity == HealthSeverity.HIGH
    assert f.file == FILE
    assert f.evidence == {
        "accounts": ["1150", "2170"],
        "names": ["Other Current Assets", "Intercompany Payable"],
    }


def test_coa_01_negative(audit_ctx: AuditContext) -> None:
    ctx = _edit(audit_ctx, "1150", cf_category="Operating")
    ctx = _edit(ctx, "2170", cf_category="Financing")
    assert h_coa_01.check(ctx) == []
    ctx = _edit(audit_ctx, "1150", cf_category="Operating")
    (f,) = h_coa_01.check(ctx)
    assert f.evidence["accounts"] == ["2170"]


def test_coa_02_header_without_children(audit_ctx: AuditContext) -> None:
    (f,) = h_coa_02.check(audit_ctx)
    assert f.id == "H-COA-02"
    assert f.severity == HealthSeverity.MEDIUM
    assert f.file == FILE
    assert f.evidence == {"accounts": ["1290"]}


def test_coa_02_negative(audit_ctx: AuditContext) -> None:
    child = CoaAccount(
        code="1291",
        name="Sundry Other Assets",
        account_type=AccountType.ASSET,
        parent_code="1290",
        statement=audit_ctx.coa_accounts[0].statement,
        cf_category="Investing",
        normal_balance=NormalBalance.DEBIT,
    )
    ctx = _with_accounts(audit_ctx, [*audit_ctx.coa_accounts, child])
    assert h_coa_02.check(ctx) == []


def test_coa_03_missing_normal_balance(audit_ctx: AuditContext) -> None:
    (f,) = h_coa_03.check(audit_ctx)
    assert f.id == "H-COA-03"
    assert f.severity == HealthSeverity.MEDIUM
    assert f.file == FILE
    assert f.evidence == {"accounts": ["7000"]}


def test_coa_03_negative(audit_ctx: AuditContext) -> None:
    ctx = _edit(audit_ctx, "7000", normal_balance=NormalBalance.DEBIT)
    assert h_coa_03.check(ctx) == []


def test_coa_04_bs_without_cf_category(audit_ctx: AuditContext) -> None:
    (f,) = h_coa_04.check(audit_ctx)
    assert f.id == "H-COA-04"
    assert f.severity == HealthSeverity.LOW
    assert f.file == FILE
    assert f.evidence == {"accounts": ["3200", "3300", "3310"]}


def test_coa_04_negative(audit_ctx: AuditContext) -> None:
    ctx = audit_ctx
    for code in ("3200", "3300", "3310"):
        ctx = _edit(ctx, code, cf_category="Financing")
    assert h_coa_04.check(ctx) == []


def test_coa_05_non_header_with_children(audit_ctx: AuditContext) -> None:
    (f,) = h_coa_05.check(audit_ctx)
    assert f.id == "H-COA-05"
    assert f.severity == HealthSeverity.MEDIUM
    assert f.file == FILE
    assert f.assumption == "A8"
    assert f.evidence == {
        "accounts": ["3300", "8000"],
        "children": {"3300": ["3310"], "8000": ["8100", "8200"]},
    }


def test_coa_05_negative(audit_ctx: AuditContext) -> None:
    ctx = _edit(audit_ctx, "3300", account_type=AccountType.HEADER)
    ctx = _edit(ctx, "8000", account_type=AccountType.HEADER)
    assert h_coa_05.check(ctx) == []


def test_coa_06_contra_accounts(audit_ctx: AuditContext) -> None:
    (f,) = h_coa_06.check(audit_ctx)
    assert f.id == "H-COA-06"
    assert f.severity == HealthSeverity.INFO
    assert f.file == FILE
    assert f.assumption == "A7"
    assert f.evidence["accounts"] == ["1121", "1211", "1221", "3400", "4200"]
    assert f.evidence["details"] == [
        {"code": "1121", "account_type": "Asset", "normal_balance": "Credit"},
        {"code": "1211", "account_type": "Asset", "normal_balance": "Credit"},
        {"code": "1221", "account_type": "Asset", "normal_balance": "Credit"},
        {"code": "3400", "account_type": "Equity", "normal_balance": "Debit"},
        {"code": "4200", "account_type": "Revenue", "normal_balance": "Debit"},
    ]


def test_coa_06_negative(audit_ctx: AuditContext) -> None:
    ctx = audit_ctx
    for code in ("1121", "1211", "1221"):
        ctx = _edit(ctx, code, normal_balance=NormalBalance.DEBIT)
    for code in ("3400", "4200"):
        ctx = _edit(ctx, code, normal_balance=NormalBalance.CREDIT)
    assert h_coa_06.check(ctx) == []
    # Headers and missing normal balances are never reported as contra accounts.
    ctx = _edit(ctx, "4100", normal_balance=None)
    assert h_coa_06.check(ctx) == []
