"""Domain models shared by ingest, rules, LLM roles, store and API.

Money fields are `Money` (a Decimal quantized to cents on the way in, serialised as a string
on the way out), so a float can never leak into arithmetic through a model.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    PlainSerializer,
    field_validator,
)

from finagent.domain.money import parse_decimal, parse_money


def _to_money(v: Any) -> Decimal:
    return parse_money(v)


def _to_rate(v: Any) -> Decimal:
    return parse_decimal(v)


Money = Annotated[
    Decimal,
    BeforeValidator(_to_money),
    PlainSerializer(lambda d: str(d), return_type=str, when_used="json"),
]
Rate = Annotated[
    Decimal,
    BeforeValidator(_to_rate),
    PlainSerializer(lambda d: str(d), return_type=str, when_used="json"),
]

Evidence = dict[str, Any]  # JSON-compatible; validated below (no floats, no objects)


def _check_evidence_value(value: object, path: str = "evidence") -> None:
    """Evidence holds the exact values a rule used; floats would make it inexact."""
    if isinstance(value, float):
        raise ValueError(f"{path} contains a float; store amounts as Decimal strings")
    if isinstance(value, dict):
        items: dict[object, object] = value  # pyright: ignore[reportUnknownVariableType]
        for k, v in items.items():
            _check_evidence_value(v, f"{path}.{k}")
    elif isinstance(value, list):
        seq: list[object] = value  # pyright: ignore[reportUnknownVariableType]
        for i, v in enumerate(seq):
            _check_evidence_value(v, f"{path}[{i}]")
    elif value is not None and not isinstance(value, str | int | bool):
        raise ValueError(f"{path} has unsupported type {type(value).__name__}")


class AccountType(StrEnum):
    HEADER = "Header"
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"


class Statement(StrEnum):
    BS = "BS"
    PL = "PL"


class NormalBalance(StrEnum):
    DEBIT = "Debit"
    CREDIT = "Credit"


class CoaAccount(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: str
    name: str
    account_type: AccountType
    parent_code: str | None
    statement: Statement
    cf_category: str | None
    normal_balance: NormalBalance | None


class TbRow(BaseModel):
    """One raw row, exactly as in the file."""

    model_config = ConfigDict(frozen=True)
    source_file: str
    row_index: int  # 0-based data row index (header excluded)
    account_code: str
    account_name: str
    currency: str
    debit: Money
    credit: Money


class FxRate(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str  # f"{currency}/{rate_type}", e.g. "GBP/period_average"
    currency: str
    rate_type: str
    rate: Rate
    period: str
    is_fallback: bool = False  # set when used in place of a missing rate
    requested_rate_type: str | None = None  # the rate type that was missing, when a fallback


class LineageKind(StrEnum):
    TB_ROW = "TB_ROW"
    FX = "FX"
    JE = "JE"
    TRANSLATION_DIFF = "TRANSLATION_DIFF"
    HUMAN = "HUMAN"


class LineageRef(BaseModel):
    kind: LineageKind
    # "trial_balance.csv#3" | "GBP/period_average" | "JE-001#2" | "decision:<id>"
    ref: str
    amount: Money | None = None  # functional-currency contribution, signed, debit positive
    note: str | None = None


class PostedLine(BaseModel):
    """One account after translation / dedupe / posting."""

    account_code: str
    account_name: str
    debit: Money
    credit: Money
    net: Money  # debit - credit
    mapped: bool  # False for the UNMAPPED bucket (e.g. 9999)
    lineage: list[LineageRef]


class Severity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


SEVERITY_RANK: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.WARN: 1,
    Severity.ESCALATE: 2,
    Severity.BLOCK: 3,
}


class HealthSeverity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


HEALTH_SEVERITY_RANK: dict[HealthSeverity, int] = {
    HealthSeverity.CRITICAL: 0,
    HealthSeverity.HIGH: 1,
    HealthSeverity.MEDIUM: 2,
    HealthSeverity.LOW: 3,
    HealthSeverity.INFO: 4,
}


class Decision(StrEnum):
    ACCEPTED = "ACCEPTED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


class _EvidenceBacked(BaseModel):
    title: str  # short, finance-user language
    message: str  # one or two sentences, finance-user language, numbers formatted
    evidence: Evidence  # exact values used; Decimals as strings
    suggested_action: str | None = None
    assumption: str | None = None  # id in docs/08_ASSUMPTIONS.md, shown as a UI chip

    @field_validator("evidence")
    @classmethod
    def _evidence_present(cls, v: Evidence) -> Evidence:
        if not v:
            raise ValueError("every finding must carry evidence")
        _check_evidence_value(v)
        return v


class Finding(_EvidenceBacked):
    rule_id: str  # "R001" | "R013" (LLM intent)
    severity: Severity
    produced_by: str = "rule"  # "rule" | "llm:intent_reviewer"


class HealthFinding(_EvidenceBacked):
    """Same evidence-backed shape as `Finding`; data-health severities and a file."""

    id: str  # "H-TB-01"
    severity: HealthSeverity
    file: str
    policy_applied: str | None = None


class JeLine(BaseModel):
    account: str
    debit: Money
    credit: Money
    memo: str = ""


class JournalEntry(BaseModel):
    id: str
    description: str
    date: str
    source: str
    lines: list[JeLine]
    version: int = 1  # bumps when a human edits and resubmits


class FixCandidate(BaseModel):
    label: str
    rationale: str
    lines: list[JeLine]
    revalidation: list[Finding] = Field(default_factory=list[Finding])  # filled by the rules
    resolves: bool = False  # True only if revalidation has no BLOCK/ESCALATE


class ImpactLine(BaseModel):
    account_code: str
    account_name: str
    delta_net: Money
    depth: int


class Impact(BaseModel):
    lines: list[ImpactLine]
    net_income_delta: Money
    total_assets_delta: Money
    total_liabilities_delta: Money
    total_equity_delta: Money


class EntryResult(BaseModel):
    entry: JournalEntry
    findings: list[Finding]
    decision: Decision
    explanation: str | None
    explanation_source: str  # "llm" | "template" | "none"
    explanation_detail: dict[str, JsonValue] | None = None  # structured summary/details/next_step
    explanation_model: str | None = None  # model that wrote it ("llm" source only)
    fix_candidates: list[FixCandidate]
    needs_human_input: str | None = None
    impact: Impact
    trace_id: str


class RunManifest(BaseModel):
    run_id: str
    created_at: str
    code_version: str
    input_hashes: dict[str, str]  # file -> sha256
    config_hash: str
    llm_mode: str
    counts: dict[str, int]  # accepted / quarantined / rejected
    invariants: dict[str, bool]
    status: str  # "OK" | "FAILED_INVARIANT"
    metrics: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    fx_policy: str | None = None
    period: str | None = None


class HumanAction(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class HumanDecision(BaseModel):
    """A reviewer's decision on a quarantined entry. Stored outside the run (never in run_id)."""

    id: str
    entry_id: str
    entry_version: int = 1
    action: HumanAction
    actor: str
    reason: str
    ts: str
    before_decision: Decision
