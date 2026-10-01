"""Command-line entry point (`uv run finagent ...`)."""

from __future__ import annotations

import typer
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

app = typer.Typer(
    help="Manual Adjustments Agent: audit, validate, explain and post journal adjustments.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _not_implemented(phase: int) -> None:
    console.print(f"not implemented (phase {phase})")


@app.command()
def audit() -> None:
    """Data health audit -> output/DEFECT_LOG.md + output/health.json."""
    _not_implemented(1)


@app.command()
def run() -> None:
    """Full adjustments pipeline -> output/runs/<run_id>/."""
    _not_implemented(2)


@app.command(name="eval")
def eval_() -> None:
    """Golden + synthetic evals -> output/evals/report.md."""
    _not_implemented(5)


@app.command()
def serve() -> None:
    """FastAPI + static frontend."""
    _not_implemented(6)


@app.command(name="record-cassettes")
def record_cassettes() -> None:
    """Live LLM calls -> evals/cassettes/*.json (needs an API key)."""
    _not_implemented(3)


@app.command()
def show(run_id: str) -> None:
    """Print a stored run's decision table."""
    _not_implemented(4)


if __name__ == "__main__":
    app()
