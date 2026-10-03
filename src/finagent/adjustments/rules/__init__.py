"""Registry of deterministic adjustment rules, in ID order (R013 is the LLM finding)."""

from __future__ import annotations

from finagent.adjustments.rules import (
    r001_balance,
    r002_account_exists,
    r003_postable_account,
    r004_period,
    r005_circular,
    r006_line_shape,
    r007_fx_double_count,
    r008_normal_balance_flip,
    r009_magnitude,
    r010_duplicate_entry,
    r011_intercompany,
    r012_suspense,
)
from finagent.adjustments.rules.base import Rule

ALL_RULES: list[Rule] = [
    r001_balance,
    r002_account_exists,
    r003_postable_account,
    r004_period,
    r005_circular,
    r006_line_shape,
    r007_fx_double_count,
    r008_normal_balance_flip,
    r009_magnitude,
    r010_duplicate_entry,
    r011_intercompany,
    r012_suspense,
]  # pyright: ignore[reportAssignmentType]
