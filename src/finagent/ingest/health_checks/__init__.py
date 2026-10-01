"""Registry of data-health checks, one module per ID in docs/02_DATA_SPEC.md §6."""

from __future__ import annotations

from types import ModuleType

from finagent.ingest.health_checks import (
    h_adj_01,
    h_adj_02,
    h_coa_01,
    h_coa_02,
    h_coa_03,
    h_coa_04,
    h_coa_05,
    h_coa_06,
    h_fx_01,
    h_fx_02,
    h_pp_01,
    h_pp_02,
    h_pp_03,
    h_pp_04,
    h_tb_01,
    h_tb_02,
    h_tb_03,
    h_tb_04,
    h_tb_05,
    h_tb_06,
)

ALL_CHECKS: list[ModuleType] = [
    h_tb_01,
    h_tb_02,
    h_tb_03,
    h_tb_04,
    h_tb_05,
    h_tb_06,
    h_coa_01,
    h_coa_02,
    h_coa_03,
    h_coa_04,
    h_coa_05,
    h_coa_06,
    h_pp_01,
    h_pp_02,
    h_pp_03,
    h_pp_04,
    h_fx_01,
    h_fx_02,
    h_adj_01,
    h_adj_02,
]
