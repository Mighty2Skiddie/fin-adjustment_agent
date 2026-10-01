"""Command-line entry point (`uv run finagent ...`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from finagent.domain.models import EntryResult

load_dotenv()

app = typer.Typer(
    help="Manual Adjustments Agent: audit, validate, explain and post journal adjustments.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _not_implemented(phase: int) -> None:
    console.print(f"not implemented (phase {phase})")


SEVERITY_STYLE = {
    "CRITICAL": "bold red",
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "cyan",
    "INFO": "dim",
}


@app.command()
def audit(
    fx_policy: str | None = typer.Option(
        None, help="Override fx.missing_rate_policy: block | fallback_average | fallback_opening"
    ),
) -> None:
    """Data health audit -> output/DEFECT_LOG.md + output/health.json."""
    from finagent.config import ROOT, load_settings
    from finagent.ingest.health_audit import run_audit

    overrides = {"fx": {"missing_rate_policy": fx_policy}} if fx_policy else None
    settings = load_settings(overrides)
    findings = run_audit(settings)
    table = Table(title=f"Data health ({len(findings)} findings)", show_lines=False)
    for col in ("ID", "Severity", "File", "Title"):
        table.add_column(col)
    for f in findings:
        sev = str(f.severity)
        table.add_row(f.id, f"[{SEVERITY_STYLE[sev]}]{sev}[/]", f.file, f.title)
    console.print(table)
    out = ROOT / "output"
    console.print(f"Wrote {out / 'DEFECT_LOG.md'} and {out / 'health.json'}")


DECISION_STYLE = {"ACCEPTED": "green", "QUARANTINED": "yellow", "REJECTED": "red"}


def _overrides(fx_policy: str | None, llm_mode: str | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if fx_policy:
        out["fx"] = {"missing_rate_policy": fx_policy}
    if llm_mode:
        out["llm"] = {"mode": llm_mode}
    return out


def print_decisions(results: list[EntryResult]) -> None:
    table = Table(title="Decisions")
    for col in ("JE", "Description", "Decision", "Findings", "Explanation"):
        table.add_column(col)
    for r in results:
        d = r.decision.value
        findings = ", ".join(f"{f.rule_id} {f.severity.value}" for f in r.findings) or "-"
        table.add_row(
            r.entry.id,
            r.entry.description,
            f"[{DECISION_STYLE[d]}]{d}[/]",
            findings,
            r.explanation_source,
        )
    console.print(table)


@app.command()
def run(
    fx_policy: str | None = typer.Option(None, help="block | fallback_average | fallback_opening"),
    llm_mode: str | None = typer.Option(None, help="cassette | live | off"),
) -> None:
    """Full adjustments pipeline -> output/runs/<run_id>/."""
    from finagent.config import load_settings
    from finagent.pipeline import run_pipeline
    from finagent.store.run_store import RunStore

    settings = load_settings(_overrides(fx_policy, llm_mode))
    store = RunStore()
    outcome = run_pipeline(settings, store)
    m = outcome.manifest
    print_decisions(outcome.results)
    counts = " · ".join(f"{v} {k}" for k, v in m.counts.items())
    console.print(f"Run [bold]{m.run_id}[/] status {m.status} ({counts}); llm mode {m.llm_mode}")
    failed = [k for k, ok in m.invariants.items() if not ok]
    if failed:
        console.print(f"[red]Invariants failed: {', '.join(failed)}[/]")
    console.print(f"Outputs: {store.run_dir(m.run_id)}")
    if m.status != "OK":
        raise typer.Exit(code=1)


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
