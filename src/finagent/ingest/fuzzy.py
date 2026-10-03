"""Fuzzy account-name matching for proposed (never auto-applied) account mappings.

Only postable, non-structural accounts are candidates (decision D7): a header such as
`6000 Operating Expenses` shares every token with most of its children, so token-set scoring
would rank it at 100 and propose a mapping to an account nobody can post to.
"""

from __future__ import annotations

from decimal import Decimal

from rapidfuzz import fuzz

from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import CoaAccount
from finagent.domain.money import dstr, q


def _score(query: str, name: str) -> Decimal:
    raw = fuzz.token_set_ratio(query.lower(), name.lower())
    pct = Decimal(int(round(raw)))
    return q(pct / 100)


def _distance(code: str, hint: str | None) -> int:
    if hint is None or not code.isdigit() or not hint.isdigit():
        return 0
    return abs(int(code) - int(hint))


def rank_candidates(
    query: str, coa: CoaTree, code_hint: str | None = None, limit: int = 3
) -> list[tuple[CoaAccount, Decimal]]:
    """Best COA matches for `query`. Ties prefer the same code range as `code_hint`, then the
    nearest code, then the lowest code, so the proposal is deterministic."""
    scored: list[tuple[CoaAccount, Decimal]] = [
        (acc, _score(query, acc.name))
        for acc in coa.accounts()
        if coa.is_postable(acc.code) and not coa.is_structural_header(acc.code)
    ]

    def key(item: tuple[CoaAccount, Decimal]) -> tuple[Decimal, int, int, str]:
        acc, score = item
        same_range = code_hint is not None and acc.code[:2] == code_hint[:2]
        return (-score, 0 if same_range else 1, _distance(acc.code, code_hint), acc.code)

    scored.sort(key=key)
    return scored[:limit]


score_str = dstr  # evidence form of a match score: `0.86`
