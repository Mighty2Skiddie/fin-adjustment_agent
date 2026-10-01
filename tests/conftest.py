from __future__ import annotations

import pytest

from finagent.adjustments.context import RuleContext, build_rule_context
from finagent.config import Settings, load_settings
from finagent.domain.models import JeLine, JournalEntry
from finagent.ingest.health_audit import build_context
from finagent.ingest.health_checks.base import AuditContext
from finagent.ingest.normalize import build_base_ledger


@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings({"llm": {"mode": "off"}})


@pytest.fixture(scope="session")
def audit_ctx(settings: Settings) -> AuditContext:
    return build_context(settings)


@pytest.fixture(scope="session")
def rule_ctx(audit_ctx: AuditContext, settings: Settings) -> RuleContext:
    ledger, _ = build_base_ledger(audit_ctx.tb_rows, audit_ctx.coa, audit_ctx.ratebook, settings)
    return build_rule_context(
        settings, audit_ctx.coa, audit_ctx.tb_rows, audit_ctx.ratebook, audit_ctx.entries, ledger
    )


@pytest.fixture(scope="session")
def entries(audit_ctx: AuditContext) -> dict[str, JournalEntry]:
    return {e.id: e for e in audit_ctx.entries}


def make_entry(
    *lines: tuple[str, str, str],
    id: str = "T-001",  # noqa: A002
    description: str = "Test entry",
    date: str = "2024-12-31",
    source: str = "test",
    memo: str = "",
) -> JournalEntry:
    """`make_entry(("6100", "100.00", "0"), ("2120", "0", "100.00"))`."""
    return JournalEntry(
        id=id,
        description=description,
        date=date,
        source=source,
        lines=[
            JeLine.model_validate({"account": a, "debit": d, "credit": c, "memo": memo})
            for a, d, c in lines
        ],
    )
