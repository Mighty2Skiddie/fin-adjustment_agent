"""Per-entry impact preview: which COA subtotals move, and by how much.

Pure aggregation over the COA tree, not statement generation. Accounts outside the COA
(e.g. `6315`) are shown but not classified: guessing their statement would be a silent mapping.
"""

from __future__ import annotations

from decimal import Decimal

from finagent.adjustments.context import net_by_account
from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import Impact, ImpactLine, JournalEntry, Statement
from finagent.domain.money import ZERO, q

ASSETS_ROOT = "1000"
LIABILITIES_ROOT = "2000"
EQUITY_ROOT = "3000"


def compute_impact(entry: JournalEntry, coa: CoaTree) -> Impact:
    deltas: dict[str, Decimal] = {}
    depth: dict[str, int] = {}
    ni = assets = liabilities = equity = ZERO
    for account, net in net_by_account(entry.lines).items():
        if net == ZERO:
            continue
        chain = coa.ancestors(account)
        deltas[account] = deltas.get(account, ZERO) + net
        depth[account] = len(chain)
        for i, anc in enumerate(chain):
            deltas[anc.code] = deltas.get(anc.code, ZERO) + net
            depth[anc.code] = len(chain) - 1 - i
        root = coa.root_of(account) if account in coa else None
        if root is None:
            continue
        if root.statement == Statement.PL:
            ni -= net  # an expense debit reduces net income
        elif root.code == ASSETS_ROOT:
            assets += net
        elif root.code == LIABILITIES_ROOT:
            liabilities -= net  # liabilities are shown credit-positive
        elif root.code == EQUITY_ROOT:
            equity -= net
    lines = [
        ImpactLine(
            account_code=code,
            account_name=coa.name_of(code) or "(not in chart of accounts)",
            delta_net=q(delta),
            depth=depth[code],
        )
        for code, delta in sorted(deltas.items(), key=lambda kv: (depth[kv[0]], kv[0]))
        if q(delta) != ZERO
    ]
    return Impact(
        lines=lines,
        net_income_delta=q(ni),
        total_assets_delta=q(assets),
        total_liabilities_delta=q(liabilities),
        total_equity_delta=q(equity),
    )
