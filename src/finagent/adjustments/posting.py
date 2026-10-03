"""Post accepted (and human-approved) entries onto the base ledger, with lineage.

`posted = base + system-ACCEPTED + human-APPROVED quarantined`. Human decisions are an overlay
recomputed on every read, so re-running the pipeline never loses an approval. A REJECTED entry
never posts, whatever a human decision says (engineering rule 4).
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import (
    Decision,
    EntryResult,
    HumanAction,
    HumanDecision,
    LineageKind,
    LineageRef,
    PostedLine,
)
from finagent.domain.money import ZERO, q


class PostingInvariantError(RuntimeError):
    """Posting changed the ledger's imbalance: an unbalanced entry slipped through."""


def latest_human_decisions(decisions: Iterable[HumanDecision]) -> dict[str, HumanDecision]:
    """The last decision per entry wins (the audit log keeps the full history)."""
    out: dict[str, HumanDecision] = {}
    for d in decisions:
        out[d.entry_id] = d
    return out


def effective_decision(result: EntryResult, human: HumanDecision | None) -> Decision:
    if result.decision != Decision.QUARANTINED or human is None:
        return result.decision
    return Decision.ACCEPTED if human.action == HumanAction.APPROVED else Decision.REJECTED


def entries_to_post(
    results: Iterable[EntryResult], human_decisions: Iterable[HumanDecision]
) -> list[tuple[EntryResult, HumanDecision | None]]:
    human = latest_human_decisions(human_decisions)
    out: list[tuple[EntryResult, HumanDecision | None]] = []
    for r in results:
        h = human.get(r.entry.id)
        if r.decision == Decision.ACCEPTED:
            out.append((r, None))
        elif (
            r.decision == Decision.QUARANTINED
            and h is not None
            and h.action == HumanAction.APPROVED
        ):
            out.append((r, h))
    return out


def ledger_imbalance(lines: Iterable[PostedLine]) -> Decimal:
    return q(sum((ln.net for ln in lines), ZERO))


def _present(net: Decimal) -> tuple[Decimal, Decimal]:
    """Net-presented debit/credit columns, as a TB shows them."""
    return (net, ZERO) if net >= ZERO else (ZERO, -net)


def post(
    base_ledger: list[PostedLine],
    results: list[EntryResult],
    human_decisions: Iterable[HumanDecision],
    coa: CoaTree,
) -> list[PostedLine]:
    lines: dict[str, PostedLine] = {ln.account_code: ln for ln in base_ledger}
    for result, human in entries_to_post(results, human_decisions):
        entry = result.entry
        for idx, je_line in enumerate(entry.lines, start=1):
            amount = je_line.debit - je_line.credit
            refs = [
                LineageRef(
                    kind=LineageKind.JE,
                    ref=f"{entry.id}#{idx}",
                    amount=amount,
                    note=je_line.memo or None,
                )
            ]
            if human is not None:
                refs.append(
                    LineageRef(
                        kind=LineageKind.HUMAN,
                        ref=f"decision:{human.id}",
                        note=f"Approved by {human.actor}: {human.reason}",
                    )
                )
            existing = lines.get(je_line.account)
            if existing is None:
                existing = PostedLine(
                    account_code=je_line.account,
                    account_name=coa.name_of(je_line.account) or "(not in chart of accounts)",
                    debit=ZERO,
                    credit=ZERO,
                    net=ZERO,
                    mapped=je_line.account in coa,
                    lineage=[],
                )
            new_net = existing.net + amount
            lines[je_line.account] = existing.model_copy(
                update={"net": new_net, "lineage": [*existing.lineage, *refs]}
            )
    posted: list[PostedLine] = []
    for code in sorted(lines):
        ln = lines[code]
        debit, credit = _present(ln.net)
        posted.append(ln.model_copy(update={"debit": debit, "credit": credit}))
    before, after = ledger_imbalance(base_ledger), ledger_imbalance(posted)
    if before != after:
        raise PostingInvariantError(
            f"Posting changed the ledger imbalance from {before} to {after}."
        )
    return posted


def totals(lines: Iterable[PostedLine]) -> dict[str, Decimal]:
    ls = list(lines)
    d = q(sum((ln.debit for ln in ls), ZERO))
    c = q(sum((ln.credit for ln in ls), ZERO))
    return {"debit": d, "credit": c, "imbalance": d - c}


def lineage_sums_ok(lines: Iterable[PostedLine]) -> bool:
    """Every posted line is exactly the sum of its lineage components."""
    return all(
        q(sum((r.amount for r in ln.lineage if r.amount is not None), ZERO)) == ln.net
        for ln in lines
    )


def all_lines_have_lineage(lines: Iterable[PostedLine]) -> bool:
    return all(ln.lineage for ln in lines)
