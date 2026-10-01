"""Batch-level context shared by every rule: built once, read-only."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from finagent.config import Settings
from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import JeLine, JournalEntry, PostedLine, TbRow
from finagent.domain.money import ZERO, q
from finagent.ingest.fx import RateBook


class RuleContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    coa: CoaTree
    base_ledger: dict[str, PostedLine]
    ratebook: RateBook
    settings: Settings
    tb_rows: list[TbRow]
    batch: list[JournalEntry]

    def base_net(self, account: str) -> Decimal:
        line = self.base_ledger.get(account)
        return line.net if line is not None else ZERO

    def currencies_of(self, account: str) -> list[str]:
        """Currencies the account is held in on the source TB (sorted, deduplicated)."""
        return sorted({r.currency for r in self.tb_rows if r.account_code == account})


def total_debit(lines: Iterable[JeLine]) -> Decimal:
    return q(sum((ln.debit for ln in lines), ZERO))


def total_credit(lines: Iterable[JeLine]) -> Decimal:
    return q(sum((ln.credit for ln in lines), ZERO))


def net_by_account(lines: Iterable[JeLine]) -> dict[str, Decimal]:
    """Per-account movement of an entry (debit − credit), in first-seen account order."""
    out: dict[str, Decimal] = {}
    for ln in lines:
        out[ln.account] = q(out.get(ln.account, ZERO) + ln.debit - ln.credit)
    return out


def entry_text(entry: JournalEntry) -> str:
    """Description, source and memos: the user-supplied free text of an entry."""
    return " ".join([entry.description, entry.source, *(ln.memo for ln in entry.lines)])


def build_rule_context(
    settings: Settings,
    coa: CoaTree,
    tb_rows: list[TbRow],
    ratebook: RateBook,
    batch: list[JournalEntry],
    base_ledger: list[PostedLine],
) -> RuleContext:
    return RuleContext(
        coa=coa,
        base_ledger={ln.account_code: ln for ln in base_ledger},
        ratebook=ratebook,
        settings=settings,
        tb_rows=tb_rows,
        batch=batch,
    )
