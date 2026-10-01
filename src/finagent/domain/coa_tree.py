"""Chart-of-accounts tree.

A node's balance is the sum of its descendants' posted balances. "Structural" (aggregating)
is decided by shape as well as type: `8000` and `3300` have children without being typed
Header (ASSUMPTIONS A8), so `is_structural_header` checks both.
"""

from __future__ import annotations

from collections.abc import Iterable

from finagent.domain.models import AccountType, CoaAccount


class CoaTree:
    def __init__(self, accounts: Iterable[CoaAccount]) -> None:
        self._accounts: dict[str, CoaAccount] = {}
        self._children: dict[str, list[str]] = {}
        for acc in accounts:
            self._accounts[acc.code] = acc
        for acc in self._accounts.values():
            if acc.parent_code is not None:
                self._children.setdefault(acc.parent_code, []).append(acc.code)
        for kids in self._children.values():
            kids.sort()

    def __contains__(self, code: object) -> bool:
        return code in self._accounts

    def __len__(self) -> int:
        return len(self._accounts)

    def accounts(self) -> list[CoaAccount]:
        return sorted(self._accounts.values(), key=lambda a: a.code)

    def codes(self) -> set[str]:
        return set(self._accounts)

    def get(self, code: str) -> CoaAccount | None:
        return self._accounts.get(code)

    def children(self, code: str) -> list[CoaAccount]:
        return [self._accounts[c] for c in self._children.get(code, [])]

    def has_children(self, code: str) -> bool:
        return bool(self._children.get(code))

    def ancestors(self, code: str) -> list[CoaAccount]:
        """Parents of `code`, nearest first. Cycles in a malformed COA stop the walk."""
        out: list[CoaAccount] = []
        seen: set[str] = {code}
        acc = self._accounts.get(code)
        while acc is not None and acc.parent_code is not None and acc.parent_code not in seen:
            parent = self._accounts.get(acc.parent_code)
            if parent is None:
                break
            out.append(parent)
            seen.add(parent.code)
            acc = parent
        return out

    def root_of(self, code: str) -> CoaAccount | None:
        chain = self.ancestors(code)
        if chain:
            return chain[-1]
        return self._accounts.get(code)

    def roots(self) -> list[CoaAccount]:
        return [a for a in self.accounts() if a.parent_code is None]

    def is_structural_header(self, code: str) -> bool:
        acc = self._accounts.get(code)
        if acc is None:
            return False
        return acc.account_type == AccountType.HEADER or self.has_children(code)

    def is_postable(self, code: str) -> bool:
        acc = self._accounts.get(code)
        return acc is not None and acc.account_type != AccountType.HEADER

    def leaf_codes_under(self, code: str) -> list[str]:
        kids = self._children.get(code, [])
        if not kids:
            return [code] if code in self._accounts else []
        out: list[str] = []
        for k in kids:
            out.extend(self.leaf_codes_under(k))
        return out

    def descendants(self, code: str) -> list[str]:
        out: list[str] = []
        for k in self._children.get(code, []):
            out.append(k)
            out.extend(self.descendants(k))
        return out

    def name_of(self, code: str) -> str:
        acc = self._accounts.get(code)
        return acc.name if acc is not None else ""
