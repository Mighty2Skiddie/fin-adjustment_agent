from __future__ import annotations

from decimal import Decimal

from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import AccountType, CoaAccount, NormalBalance, Statement
from finagent.ingest.fuzzy import rank_candidates, score_str
from finagent.ingest.health_checks.base import AuditContext


def _acc(code: str, name: str, parent: str | None, typ: AccountType) -> CoaAccount:
    return CoaAccount(
        code=code,
        name=name,
        account_type=typ,
        parent_code=parent,
        statement=Statement.PL,
        cf_category=None,
        normal_balance=NormalBalance.DEBIT,
    )


def test_top_candidate_for_renamed_account(audit_ctx: AuditContext) -> None:
    ranked = rank_candidates("Sundry Operating Expenses", audit_ctx.coa, code_hint="6905")
    assert ranked[0][0].code == "6900"
    assert len(ranked) == 3
    for _, score in ranked:
        assert Decimal("0") <= score <= Decimal("1")
        assert score == score.quantize(Decimal("0.01"))


def test_headers_and_structural_accounts_excluded(audit_ctx: AuditContext) -> None:
    ranked = rank_candidates("Operating Expenses", audit_ctx.coa, limit=50)
    codes = {a.code for a, _ in ranked}
    assert "6000" not in codes  # Header (decision D7)
    assert "8000" not in codes  # typed Expense but has children
    assert "3300" not in codes


def test_tie_break_prefers_code_hint_range() -> None:
    coa = CoaTree(
        [
            _acc("5000", "Group A", None, AccountType.HEADER),
            _acc("5100", "Widget Costs", "5000", AccountType.EXPENSE),
            _acc("6000", "Group B", None, AccountType.HEADER),
            _acc("6100", "Widget Costs", "6000", AccountType.EXPENSE),
            _acc("6150", "Widget Costs", "6000", AccountType.EXPENSE),
        ]
    )
    ranked = rank_candidates("widget costs", coa, code_hint="6140")
    assert [a.code for a, _ in ranked] == ["6150", "6100", "5100"]
    assert all(s == Decimal("1.00") for _, s in ranked)


def test_score_str() -> None:
    assert score_str(Decimal("0.86")) == "0.86"
    assert score_str(Decimal("1")) == "1.00"
