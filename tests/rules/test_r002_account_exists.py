from __future__ import annotations

from finagent.adjustments.context import RuleContext
from finagent.adjustments.rules import r002_account_exists
from finagent.domain.models import Finding, JournalEntry, Severity
from tests.conftest import make_entry


def _candidates(f: Finding) -> list[dict[str, object]]:
    cands = f.evidence["candidates"]
    assert isinstance(cands, list)
    return [c for c in cands if isinstance(c, dict)]  # pyright: ignore[reportUnknownVariableType]


def test_je005_missing_6315(entries: dict[str, JournalEntry], rule_ctx: RuleContext) -> None:
    main, cand = r002_account_exists.check(entries["JE-005"], rule_ctx)
    assert main.rule_id == "R002" and main.severity == Severity.ESCALATE
    assert main.evidence == {"missing_accounts": ["6315"], "lines": [1]}
    assert "6315" in main.message

    assert cand.rule_id == "R002b" and cand.severity == Severity.INFO
    assert cand.evidence["missing_account"] == "6315"
    top = _candidates(cand)[0]
    assert top["code"] == "6310"
    assert top["name"] == "Travel and Entertainment"
    assert top["would_create_noop"] is True
    assert "cancel the entry" in cand.message
    assert cand.suggested_action is not None and "do not remap" in cand.suggested_action


def test_je005_candidates_are_bounded_and_scored(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    _, cand = r002_account_exists.check(entries["JE-005"], rule_ctx)
    cands = _candidates(cand)
    assert 1 <= len(cands) <= 3
    for c in cands:
        score = c["score"]
        assert isinstance(score, str) and len(score.split(".")[1]) == 2
        assert c["code"] != "6000"  # headers are never proposed (D7)
    assert [c["would_create_noop"] for c in cands[1:]] == [False] * (len(cands) - 1)


def test_only_je005_fires_on_real_data(
    entries: dict[str, JournalEntry], rule_ctx: RuleContext
) -> None:
    fired = {je for je, e in entries.items() if r002_account_exists.check(e, rule_ctx)}
    assert fired == {"JE-005"}


def test_known_accounts_pass(rule_ctx: RuleContext) -> None:
    e = make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"))
    assert r002_account_exists.check(e, rule_ctx) == []


def test_missing_account_without_noop(rule_ctx: RuleContext) -> None:
    # Split offset: no single remap of 6315 can net every account to zero.
    e = make_entry(
        ("6315", "100.00", "0"),
        ("2120", "0", "60.00"),
        ("6100", "0", "40.00"),
        description="Conference travel accrual",
        memo="Conference travel",
    )
    main, cand = r002_account_exists.check(e, rule_ctx)
    assert main.evidence == {"missing_accounts": ["6315"], "lines": [1]}
    assert cand.evidence["missing_account"] == "6315"
    assert all(c["would_create_noop"] is False for c in _candidates(cand))
    assert "cancel" not in cand.message


def test_offset_account_candidate_is_noop(rule_ctx: RuleContext) -> None:
    e = make_entry(("6315", "100.00", "0"), ("2120", "0", "100.00"))
    assert r002_account_exists._would_create_noop(e, "6315", "2120") is True  # pyright: ignore[reportPrivateUsage]
    assert r002_account_exists._would_create_noop(e, "6315", "6100") is False  # pyright: ignore[reportPrivateUsage]


def test_noop_requires_full_cancellation(rule_ctx: RuleContext) -> None:
    # 6310 is on another line but the amounts differ, so remapping would not net to zero.
    e = make_entry(
        ("6315", "100.00", "0"),
        ("6310", "0", "60.00"),
        ("2120", "0", "40.00"),
        description="Conference travel",
        memo="Conference travel",
    )
    _, cand = r002_account_exists.check(e, rule_ctx)
    assert all(c["would_create_noop"] is False for c in _candidates(cand))


def test_two_missing_accounts_emit_one_candidate_list_each(rule_ctx: RuleContext) -> None:
    e = make_entry(("6315", "100.00", "0"), ("6316", "0", "50.00"), ("6315", "0", "50.00"))
    findings = r002_account_exists.check(e, rule_ctx)
    assert [f.rule_id for f in findings] == ["R002", "R002b", "R002b"]
    assert findings[0].evidence == {"missing_accounts": ["6315", "6316"], "lines": [1, 2, 3]}
    assert [f.evidence["missing_account"] for f in findings[1:]] == ["6315", "6316"]
