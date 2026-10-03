"""Shared context for data-health checks. Each check is one module exposing `CHECK_ID` and
`check(ctx) -> list[HealthFinding]`; checks are pure functions of the loaded inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finagent.config import Settings
from finagent.domain.coa_tree import CoaTree
from finagent.domain.models import CoaAccount, FxRate, JournalEntry, TbRow
from finagent.ingest.fx import RateBook


@dataclass(frozen=True)
class AuditContext:
    settings: Settings
    coa_accounts: list[CoaAccount]
    coa: CoaTree
    tb_rows: list[TbRow]
    prior_rows: list[TbRow]
    fx_rates: list[FxRate]
    ratebook: RateBook
    entries: list[JournalEntry]
    adjustments_raw: dict[str, Any] = field(default_factory=dict[str, Any])
