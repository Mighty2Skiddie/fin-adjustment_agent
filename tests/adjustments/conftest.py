from __future__ import annotations

from pathlib import Path

import pytest

from finagent.config import Settings
from finagent.pipeline import RunOutcome, run_pipeline
from finagent.store.run_store import RunStore


@pytest.fixture(scope="session")
def off_run(settings: Settings, tmp_path_factory: pytest.TempPathFactory) -> RunOutcome:
    """One deterministic (llm off) run in an isolated store."""
    runs: Path = tmp_path_factory.mktemp("runs")
    return run_pipeline(settings, RunStore(runs))
