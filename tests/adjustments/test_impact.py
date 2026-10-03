"""docs/02_DATA_SPEC.md §9: impact preview is arithmetic over the COA tree."""

from __future__ import annotations

from decimal import Decimal

from finagent.adjustments.context import RuleContext
from finagent.adjustments.impact import compute_impact
from finagent.domain.models import JournalEntry


def test_je001(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    imp = compute_impact(entries["JE-001"], rule_ctx.coa)
    by = {ln.account_code: ln.delta_net for ln in imp.lines}
    assert by["6000"] == Decimal("850000.00")
    assert by["2100"] == Decimal("-850000.00")  # debit-positive: a credit to liabilities
    assert by["2000"] == Decimal("-850000.00")
    assert imp.net_income_delta == Decimal("-850000.00")
    assert imp.total_liabilities_delta == Decimal("850000.00")
    assert imp.total_assets_delta == Decimal("0.00")
    roots = [ln.account_code for ln in imp.lines if ln.depth == 0]
    assert roots == ["2000", "6000"]


def test_je008_noop_has_no_impact(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    imp = compute_impact(entries["JE-008"], rule_ctx.coa)
    assert imp.lines == [] and imp.net_income_delta == Decimal("0.00")


def test_je010_reclass_within_liabilities(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    imp = compute_impact(entries["JE-010"], rule_ctx.coa)
    assert imp.total_liabilities_delta == Decimal("0.00")
    by = {ln.account_code: ln.delta_net for ln in imp.lines}
    assert by["2100"] == Decimal("-200000.00") and by["2200"] == Decimal("200000.00")
    assert "2000" not in by  # nets to zero at the root


def test_je005_unknown_account_not_classified(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    imp = compute_impact(entries["JE-005"], rule_ctx.coa)
    by = {ln.account_code: ln for ln in imp.lines}
    assert by["6315"].account_name == "(not in chart of accounts)"
    assert imp.net_income_delta == Decimal("18500.00")  # only 6310's credit is classified


def test_je006_contra_asset(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    imp = compute_impact(entries["JE-006"], rule_ctx.coa)
    assert imp.total_assets_delta == Decimal("-215000.00")
    assert imp.net_income_delta == Decimal("-215000.00")
