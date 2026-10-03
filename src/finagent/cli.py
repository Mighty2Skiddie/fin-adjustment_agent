"""Command-line entry point (`uv run finagent ...`)."""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING, Any

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from finagent.config import Settings
    from finagent.domain.models import EntryResult

load_dotenv()

# Windows consoles default to a legacy code page; entry descriptions contain em dashes.
for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper) and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8")

app = typer.Typer(
    help="Manual Adjustments Agent: audit, validate, explain and post journal adjustments.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


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


def _run_evals(settings: Settings) -> bool:
    """`evals/` lives at the repo root (not in the package), so put the root on sys.path."""
    from finagent.config import ROOT

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from evals.run_evals import OUT_DIR, run_evals

    result = run_evals(settings)
    table = Table(title=f"Evaluation ({'PASSED' if result.passed else 'FAILED'})")
    table.add_column("Metric")
    table.add_column("Value")
    for k, v in result.report["summary"].items():
        table.add_row(k, str(v))
    console.print(table)
    misses = [e["id"] for e in result.report["entries"] if not e["match"]]
    if misses:
        console.print(f"[red]Entries not matching expectations: {', '.join(misses)}[/]")
    console.print(f"Wrote {OUT_DIR / 'report.md'} and {OUT_DIR / 'report.json'}")
    return result.passed


@app.command(name="eval")
def eval_(llm_mode: str | None = typer.Option(None, help="cassette | live | off")) -> None:
    """Golden + synthetic evals -> output/evals/report.md (exit 1 if the CI gate fails)."""
    from finagent.config import load_settings

    if not _run_evals(load_settings(_overrides(None, llm_mode))):
        raise typer.Exit(code=1)


@app.command()
def serve(
    port: int = typer.Option(8000, help="Port (the container uses 7860)."),
    host: str = typer.Option("127.0.0.1", help="Use 0.0.0.0 inside a container."),
) -> None:
    """FastAPI + static frontend. Creates the first run if none exists yet."""
    import uvicorn

    from finagent.config import load_settings
    from finagent.pipeline import run_pipeline
    from finagent.store.run_store import RunStore

    store = RunStore()
    if store.latest() is None:
        console.print("No run found; running the pipeline once (cassette mode) ...")
        run_pipeline(load_settings(), store)
    from finagent.api.static import DIST

    if not (DIST / "index.html").is_file():
        console.print(
            "[yellow]The UI is not built yet: the API works, but pages will say 'Frontend not "
            "built'. Run: cd frontend && npm ci && npm run build[/]"
        )
    console.print(f"Serving on http://{host}:{port}")
    uvicorn.run("finagent.api.app:app", host=host, port=port, log_level="info")


@app.command(name="record-cassettes")
def record_cassettes(
    clean: bool = typer.Option(False, help="Delete existing cassettes before recording."),
) -> None:
    """Live LLM calls -> evals/cassettes/<role>/*.json (needs an API key)."""
    import shutil

    from finagent.config import ROOT, load_settings
    from finagent.pipeline import run_pipeline
    from finagent.store.run_store import RunStore

    settings = load_settings({"llm": {"mode": "record"}})
    cassette_dir = ROOT / settings.llm.cassette_dir
    if clean and cassette_dir.is_dir():
        for role_dir in cassette_dir.iterdir():
            if role_dir.is_dir():
                shutil.rmtree(role_dir)
    llm = settings.llm
    console.print(
        f"Recording with {llm.provider}/{llm.model} (fallback {llm.fallback_provider}/"
        f"{llm.fallback_model}) into {cassette_dir}"
    )
    outcome = run_pipeline(settings, RunStore())
    print_decisions(outcome.results)
    m = outcome.manifest.metrics
    console.print(
        f"LLM calls {m.get('llm_calls')}, provider fallbacks {m.get('provider_fallbacks')}, "
        f"guardrail fallback rate {m.get('guardrail_fallback_rate')}"
    )
    console.print("Recording the evaluation set (golden + synthetic) ...")
    _run_evals(settings)
    console.print("Now replay with: uv run finagent run --llm-mode cassette")


@app.command()
def show(run_id: str = typer.Argument("latest", help="Run id, or 'latest'.")) -> None:
    """Print a stored run's manifest, metrics, invariants and decision table."""
    from finagent.store.run_store import RunStore

    store = RunStore()
    rid = store.latest() if run_id == "latest" else run_id
    if rid is None or not store.exists(rid):
        console.print(f"[red]No run '{run_id}' found under {store.runs_dir}.[/]")
        raise typer.Exit(code=1)
    m = store.manifest(rid)
    console.print(
        f"Run [bold]{m.run_id}[/] · {m.status} · created {m.created_at} · code {m.code_version}"
        f" · llm {m.llm_mode} · fx {m.fx_policy}"
    )
    meta = Table(title="Metrics and invariants")
    meta.add_column("Name")
    meta.add_column("Value")
    for k, v in m.metrics.items():
        meta.add_row(k, str(v))
    for k, ok in m.invariants.items():
        meta.add_row(k, "[green]pass[/]" if ok else "[red]FAIL[/]")
    console.print(meta)
    print_decisions(store.results(rid))
    human = store.human_decisions(rid)
    if human:
        for h in human:
            console.print(f"Human: {h.entry_id} {h.action.value} by {h.actor} ({h.ts}): {h.reason}")


if __name__ == "__main__":
    app()
