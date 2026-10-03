"""Ground truth: docs/02_DATA_SPEC.md §8 (net-presented, credit balances shown as credit)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from finagent.adjustments.posting import (
    PostingInvariantError,
    effective_decision,
    ledger_imbalance,
    post,
    totals,
)
from finagent.config import Settings
from finagent.domain.models import (
    Decision,
    HumanAction,
    HumanDecision,
    LineageKind,
    PostedLine,
)
from finagent.pipeline import Prepared, RunOutcome, prepare

# account -> (side, post-adjustment amount)
EXPECTED = {
    "6100": ("Dr", "6250000.00"),
    "2120": ("Cr", "2075000.00"),
    "6600": ("Dr", "140000.00"),
    "1121": ("Cr", "230000.00"),
    "6500": ("Dr", "1065000.00"),
    "1211": ("Cr", "4415000.00"),
    "8200": ("Dr", "158000.00"),
    "1250": ("Dr", "282000.00"),
    "6400": ("Dr", "595000.00"),
    "2210": ("Cr", "6300000.00"),
    "2140": ("Cr", "1000000.00"),
    "1110": ("Dr", "5674960.20"),
    "6310": ("Dr", "283500.00"),
}


@pytest.fixture(scope="module")
def prep(settings: Settings) -> Prepared:
    return prepare(settings, version="test")


def _by(lines: list[PostedLine]) -> dict[str, PostedLine]:
    return {ln.account_code: ln for ln in lines}


@pytest.mark.parametrize(("account", "expected"), sorted(EXPECTED.items()))
def test_spec_section_8(off_run: RunOutcome, account: str, expected: tuple[str, str]) -> None:
    assert off_run.posted is not None
    line = _by(off_run.posted)[account]
    side, amount = expected
    if side == "Dr":
        assert (line.debit, line.credit) == (Decimal(amount), Decimal("0.00"))
    else:
        assert (line.debit, line.credit) == (Decimal("0.00"), Decimal(amount))


def test_only_accepted_entries_post(off_run: RunOutcome) -> None:
    assert off_run.posted is not None
    je_refs = {
        r.ref.split("#")[0] for ln in off_run.posted for r in ln.lineage if r.kind == LineageKind.JE
    }
    assert je_refs == {"JE-001", "JE-004", "JE-006", "JE-007", "JE-009", "JE-010"}


def test_imbalance_unchanged(off_run: RunOutcome, prep: Prepared) -> None:
    assert off_run.posted is not None and prep.base_ledger is not None
    assert ledger_imbalance(off_run.posted) == ledger_imbalance(prep.base_ledger)
    t = totals(off_run.posted)
    assert t["imbalance"] == Decimal("0.00")


def _human(entry_id: str, action: HumanAction) -> HumanDecision:
    return HumanDecision(
        id="d1",
        entry_id=entry_id,
        action=action,
        actor="Controller",
        reason="Confirmed with treasury",
        ts=datetime(2025, 1, 5, tzinfo=UTC).isoformat(),
        before_decision=Decision.QUARANTINED,
    )


def test_human_approval_overlay_posts_je003(off_run: RunOutcome, prep: Prepared) -> None:
    assert prep.base_ledger is not None
    posted = post(
        prep.base_ledger, off_run.results, [_human("JE-003", HumanAction.APPROVED)], prep.audit.coa
    )
    cash = _by(posted)["1110"]
    assert cash.debit == Decimal("5686160.20")  # 5,674,960.20 + 11,200.00
    kinds = [r.kind for r in cash.lineage]
    assert LineageKind.HUMAN in kinds and LineageKind.JE in kinds


def test_human_cannot_post_rejected(off_run: RunOutcome, prep: Prepared) -> None:
    assert prep.base_ledger is not None and off_run.posted is not None
    posted = post(
        prep.base_ledger, off_run.results, [_human("JE-002", HumanAction.APPROVED)], prep.audit.coa
    )
    assert posted == off_run.posted
    je2 = next(r for r in off_run.results if r.entry.id == "JE-002")
    assert effective_decision(je2, _human("JE-002", HumanAction.APPROVED)) == Decision.REJECTED


def test_human_reject_keeps_quarantined_out(off_run: RunOutcome, prep: Prepared) -> None:
    assert prep.base_ledger is not None and off_run.posted is not None
    posted = post(
        prep.base_ledger, off_run.results, [_human("JE-003", HumanAction.REJECTED)], prep.audit.coa
    )
    assert posted == off_run.posted


def test_unbalanced_accepted_entry_trips_invariant(off_run: RunOutcome, prep: Prepared) -> None:
    assert prep.base_ledger is not None
    je2 = next(r for r in off_run.results if r.entry.id == "JE-002")
    forced = je2.model_copy(update={"decision": Decision.ACCEPTED})
    with pytest.raises(PostingInvariantError):
        post(prep.base_ledger, [forced], [], prep.audit.coa)
