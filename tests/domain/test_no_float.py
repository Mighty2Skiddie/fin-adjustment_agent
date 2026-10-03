"""Repo hygiene: money code must never go through binary floats (engineering rule 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "finagent"
NEEDLE = "float" + "("


@pytest.mark.parametrize("package", ["domain", "ingest", "adjustments"])
def test_no_float_calls(package: str) -> None:
    offenders = [
        f"{p.relative_to(SRC)}:{i}"
        for p in sorted((SRC / package).rglob("*.py"))
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1)
        if NEEDLE in line
    ]
    assert offenders == []
