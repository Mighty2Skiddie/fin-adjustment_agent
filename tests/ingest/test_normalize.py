from __future__ import annotations

from decimal import Decimal

import pytest

from finagent.config import Settings, load_settings
from finagent.domain.models import HealthFinding, LineageKind, PostedLine
from finagent.ingest.fx import MissingRateError, RateBook
from finagent.ingest.health_checks.base import AuditContext
from finagent.ingest.normalize import build_base_ledger


def _ledger(ctx: AuditContext, settings: Settings) -> tuple[list[PostedLine], list[HealthFinding]]:
    rb = RateBook(ctx.fx_rates, settings.fx.missing_rate_policy)
    return build_base_ledger(ctx.tb_rows, ctx.coa, rb, settings)


def test_base_ledger_values(audit_ctx: AuditContext, settings: Settings) -> None:
    lines, findings = _ledger(audit_ctx, settings)
    by = {ln.account_code: ln for ln in lines}
    assert len(lines) == 59
    assert by["1110"].debit == Decimal("5674960.20")
    assert by["6310"].debit == Decimal("283500.00")
    assert by["9999"].mapped is False and by["9999"].net == Decimal("12400.00")
    assert by["3310"].credit == Decimal("362460.20")  # translation difference merged (D5)
    assert sum(ln.net for ln in lines) == Decimal("0.00")
    assert [f.id for f in findings] == ["H-TB-01"]


def test_lineage_sums_to_line(audit_ctx: AuditContext, settings: Settings) -> None:
    lines, _ = _ledger(audit_ctx, settings)
    for ln in lines:
        assert sum(r.amount for r in ln.lineage if r.amount is not None) == ln.net


def test_gbp_fallback_stamped_on_lineage(audit_ctx: AuditContext, settings: Settings) -> None:
    lines, _ = _ledger(audit_ctx, settings)
    cash = next(ln for ln in lines if ln.account_code == "1110")
    fx = [r for r in cash.lineage if r.kind == LineageKind.FX]
    assert [r.ref for r in fx] == ["USD/period_end", "EUR/period_end", "GBP/period_average"]
    assert "fallback" in (fx[2].note or "")
    tb = [r.ref for r in cash.lineage if r.kind == LineageKind.TB_ROW]
    assert tb == ["trial_balance.csv#0", "trial_balance.csv#1", "trial_balance.csv#2"]


def test_plug_lineage(audit_ctx: AuditContext, settings: Settings) -> None:
    lines, _ = _ledger(audit_ctx, settings)
    plug = next(ln for ln in lines if ln.account_code == "3310")
    diff = [r for r in plug.lineage if r.kind == LineageKind.TRANSLATION_DIFF]
    assert len(diff) == 1 and diff[0].amount == Decimal("-182460.20")


def test_opening_policy_changes_cash(audit_ctx: AuditContext) -> None:
    s = load_settings({"fx": {"missing_rate_policy": "fallback_opening"}})
    lines, findings = _ledger(audit_ctx, s)
    cash = next(ln for ln in lines if ln.account_code == "1110")
    assert cash.debit == Decimal("5669600.30")  # A4: -5,359.90 vs average
    assert findings[0].evidence["active_delta"] == "177100.30"


def test_block_policy_stops(audit_ctx: AuditContext) -> None:
    s = load_settings({"fx": {"missing_rate_policy": "block"}})
    with pytest.raises(MissingRateError):
        _ledger(audit_ctx, s)
