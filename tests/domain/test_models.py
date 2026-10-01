from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from finagent.domain.coa_tree import CoaTree
from finagent.domain.ids import run_id, trace_id
from finagent.domain.models import Finding, JeLine, Severity
from finagent.ingest.loaders import load_coa


def test_money_fields_quantize_and_serialise_as_strings() -> None:
    line = JeLine.model_validate({"account": "6100", "debit": "850000", "credit": 0})
    assert line.debit == Decimal("850000.00")
    assert line.model_dump(mode="json")["debit"] == "850000.00"


def test_finding_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        Finding(rule_id="R001", severity=Severity.BLOCK, title="t", message="m", evidence={})


@pytest.mark.parametrize("evidence", [{"x": 0.1}, {"nested": [{"y": 1.5}]}])
def test_finding_rejects_float_evidence(evidence: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Finding(rule_id="R001", severity=Severity.BLOCK, title="t", message="m", evidence=evidence)


def test_coa_tree_shape() -> None:
    coa = CoaTree(load_coa())
    # 72 accounts: the file has 73 lines including the header (spec §1 says "73 rows").
    assert len(coa) == 72
    assert [a.code for a in coa.ancestors("2120")] == ["2100", "2000"]
    assert [a.code for a in coa.ancestors("3310")] == ["3300", "3000"]
    assert sorted(a.code for a in coa.roots()) == [
        "1000", "2000", "3000", "4000", "5000", "6000", "7000", "8000",
    ]  # fmt: skip
    assert coa.is_structural_header("8000") and coa.is_postable("8000")
    assert coa.is_structural_header("3300")
    assert not coa.is_postable("1000") and not coa.is_postable("9999")
    assert coa.is_postable("6310") and not coa.is_structural_header("6310")
    assert coa.leaf_codes_under("8000") == ["8100", "8200"]
    root = coa.root_of("1121")
    assert root is not None and root.code == "1000"


def test_ids_are_deterministic() -> None:
    a = run_id({"f": "1"}, "c", "g")
    assert a == run_id({"f": "1"}, "c", "g") and len(a) == 12
    assert a != run_id({"f": "2"}, "c", "g")
    assert trace_id(a, "JE-001") == trace_id(a, "JE-001") != trace_id(a, "JE-002")
