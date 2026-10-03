"""Read `inputs/` exactly as delivered. Nothing here corrects data; defects are reported later."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import orjson

from finagent.config import ROOT
from finagent.domain.models import (
    AccountType,
    CoaAccount,
    FxRate,
    JeLine,
    JournalEntry,
    NormalBalance,
    Statement,
    TbRow,
)
from finagent.domain.money import parse_decimal, parse_money

INPUTS = ROOT / "inputs"
COA_FILE = "chart_of_accounts.csv"
TB_FILE = "trial_balance.csv"
PRIOR_TB_FILE = "prior_period_tb.csv"
FX_FILE = "fx_rates.csv"
ADJ_FILE = "manual_adjustments.json"
INPUT_FILES = (COA_FILE, TB_FILE, PRIOR_TB_FILE, FX_FILE, ADJ_FILE)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def read_raw_lines(path: Path) -> list[str]:
    """Data lines (header excluded) as raw text, for lineage display of a source row."""
    with path.open(encoding="utf-8", newline="") as fh:
        return [line.rstrip("\r\n") for line in fh.readlines()[1:]]


def load_coa(path: Path | None = None) -> list[CoaAccount]:
    rows = _read_csv(path or INPUTS / COA_FILE)
    return [
        CoaAccount(
            code=r["account_code"],
            name=r["account_name"],
            account_type=AccountType(r["account_type"]),
            parent_code=r["parent_code"] or None,
            statement=Statement(r["statement"]),
            cf_category=r["cf_category"] or None,
            normal_balance=NormalBalance(r["normal_balance"]) if r["normal_balance"] else None,
        )
        for r in rows
    ]


def load_tb(path: Path | None = None) -> list[TbRow]:
    p = path or INPUTS / TB_FILE
    return [
        TbRow(
            source_file=p.name,
            row_index=i,
            account_code=r["account_code"],
            account_name=r["account_name"],
            currency=r["currency"],
            debit=parse_money(r["debit"]),
            credit=parse_money(r["credit"]),
        )
        for i, r in enumerate(_read_csv(p))
    ]


def load_prior_tb(path: Path | None = None) -> list[TbRow]:
    return load_tb(path or INPUTS / PRIOR_TB_FILE)


def load_fx(path: Path | None = None) -> list[FxRate]:
    return [
        FxRate(
            id=f"{r['currency']}/{r['rate_type']}",
            currency=r["currency"],
            rate_type=r["rate_type"],
            rate=parse_decimal(r["rate"]),
            period=r["period"],
        )
        for r in _read_csv(path or INPUTS / FX_FILE)
    ]


def load_adjustments_raw(path: Path | None = None) -> dict[str, Any]:
    data: dict[str, Any] = orjson.loads((path or INPUTS / ADJ_FILE).read_bytes())
    return data


def entry_from_dict(e: dict[str, Any]) -> JournalEntry:
    """JSON numbers are floats once parsed; `parse_money` goes through `str()` to stay exact."""
    lines: list[dict[str, Any]] = e.get("lines") or []
    return JournalEntry(
        id=str(e["id"]),
        description=str(e.get("description", "")),
        date=str(e.get("date", "")),
        source=str(e.get("source", "")),
        version=int(e.get("version", 1)),
        lines=[
            JeLine(
                account=str(ln.get("account", "")),
                debit=parse_money(ln.get("debit", 0) or 0),
                credit=parse_money(ln.get("credit", 0) or 0),
                memo=str(ln.get("memo", "")),
            )
            for ln in lines
        ],
    )


def load_adjustments(path: Path | None = None) -> list[JournalEntry]:
    raw = load_adjustments_raw(path)
    entries: list[dict[str, Any]] = raw.get("entries") or []
    return [entry_from_dict(e) for e in entries]
