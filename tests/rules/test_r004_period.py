from __future__ import annotations

import pytest

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r004_period
from finagent.domain.models import JournalEntry, Severity
from tests.conftest import make_entry


def _entry(date: str) -> JournalEntry:
    return make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"), date=date)


def test_real_entries_are_in_period(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    for je in entries.values():
        assert r004_period.check(je, rule_ctx) == []


@pytest.mark.parametrize("date", ["2025-01-02", "2024-09-30"])
def test_out_of_period_blocks(date: str, rule_ctx: RuleContext) -> None:
    [f] = r004_period.check(_entry(date), rule_ctx)
    assert f.rule_id == "R004" and f.severity == Severity.BLOCK
    assert f.title == "Entry dated outside the period"
    assert f.evidence == {"date": date, "period_start": "2024-10-01", "period_end": "2024-12-31"}
    assert f.assumption == "A9"
    assert date in f.message


@pytest.mark.parametrize("date", ["2024-10-01", "2024-12-31"])
def test_period_boundaries_pass(date: str, rule_ctx: RuleContext) -> None:
    assert r004_period.check(_entry(date), rule_ctx) == []


def test_unparsable_date_warns(rule_ctx: RuleContext) -> None:
    [f] = r004_period.check(_entry("31/12/2024"), rule_ctx)
    assert f.rule_id == "R004" and f.severity == Severity.WARN
    assert f.title == "Entry date could not be read"
    assert f.evidence == {
        "date": "31/12/2024",
        "period_start": "2024-10-01",
        "period_end": "2024-12-31",
    }
