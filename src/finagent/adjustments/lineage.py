"""Resolve a posted line's lineage refs to their sources, for the auditor's drill-down.

Each hop is a stored id, never a recomputation: cell -> posted line -> TB row (raw CSV text),
FX rate row, JE line (as submitted), human decision record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finagent.domain.models import (
    FxRate,
    HumanDecision,
    JournalEntry,
    LineageKind,
    PostedLine,
    TbRow,
)
from finagent.domain.money import ZERO, q


@dataclass(frozen=True)
class LineageSources:
    tb_rows: dict[str, TbRow] = field(default_factory=dict[str, TbRow])  # "file#idx" -> row
    raw_lines: dict[str, str] = field(default_factory=dict[str, str])  # "file#idx" -> csv text
    rates: dict[str, FxRate] = field(default_factory=dict[str, FxRate])
    entries: dict[str, JournalEntry] = field(default_factory=dict[str, JournalEntry])
    human: dict[str, HumanDecision] = field(default_factory=dict[str, HumanDecision])


def _source_for(kind: LineageKind, ref: str, src: LineageSources) -> dict[str, Any]:
    if kind == LineageKind.TB_ROW:
        row = src.tb_rows.get(ref)
        return {
            "file": ref.split("#", 1)[0],
            "row_index": row.row_index if row else None,
            "raw": src.raw_lines.get(ref),
            "row": row.model_dump(mode="json") if row else None,
        }
    if kind == LineageKind.FX:
        rate = src.rates.get(ref)
        return {"rate": rate.model_dump(mode="json") if rate else None}
    if kind == LineageKind.JE:
        entry_id, _, line_no = ref.partition("#")
        entry = src.entries.get(entry_id)
        line = None
        if entry is not None and line_no.isdigit() and 1 <= int(line_no) <= len(entry.lines):
            line = entry.lines[int(line_no) - 1].model_dump(mode="json")
        return {
            "entry_id": entry_id,
            "line_number": int(line_no) if line_no.isdigit() else None,
            "description": entry.description if entry else None,
            "line": line,
        }
    if kind == LineageKind.HUMAN:
        decision = src.human.get(ref.removeprefix("decision:"))
        return {"decision": decision.model_dump(mode="json") if decision else None}
    return {"note": "System-generated line; see ASSUMPTIONS A3."}


def explain_line(line: PostedLine, sources: LineageSources) -> dict[str, Any]:
    components = [
        {
            "kind": str(r.kind),
            "ref": r.ref,
            "amount": str(r.amount) if r.amount is not None else None,
            "note": r.note,
            "source": _source_for(r.kind, r.ref, sources),
        }
        for r in line.lineage
    ]
    total = q(sum((r.amount for r in line.lineage if r.amount is not None), ZERO))
    return {
        "line": line.model_dump(mode="json"),
        "components": components,
        "components_total": str(total),
        "reconciles": total == line.net,
    }
