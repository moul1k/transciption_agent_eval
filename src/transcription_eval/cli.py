from __future__ import annotations

import os
from pathlib import Path

import typer

from .agent import FixtureProvider, OpenAIProvider, load_cases
from .meta_cli import app as meta_app
from .runner import run_local

app = typer.Typer(no_args_is_help=True)
app.add_typer(meta_app, name='meta')
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "data" / "benchmark.jsonl"


@app.command('extract')
def extract_transcript(transcript: Path, output_dir: Path,
                       rubric: Path = typer.Option(ROOT / 'data/meta/rubric.json'),
                       model: str = 'gpt-4.1-mini',
                       credentials: Path | None = None, langfuse: bool = False):
    """Generate a real candidate and human-review packet; optionally trace it to Langfuse."""
    from .live import extract
    try:
        metadata = extract(transcript, rubric, output_dir, model, credentials, langfuse)
    except Exception as exc:
        # Provider exception bodies may contain request data: no rich locals or secrets.
        typer.echo(f'Extraction failed ({type(exc).__name__}). Check credentials, paths and service access.', err=True)
        raise typer.Exit(1) from None
    typer.echo(f'Review: {output_dir / "review.html"}')
    if metadata['trace_url']:
        typer.echo(f'Trace: {metadata["trace_url"]}')


def _provider(name: str, model: str, tracing: bool = False):
    if name == "fixture":
        return FixtureProvider()
    if name == "openai":
        return OpenAIProvider(model, tracing=tracing)
    raise typer.BadParameter("provider must be 'fixture' or 'openai'")


@app.command()
def benchmark(
    provider: str = typer.Option("fixture"),
    model: str = typer.Option(os.getenv("MEETING_AGENT_MODEL", "gpt-4.1-mini")),
    dataset: Path = typer.Option(DEFAULT_DATASET, exists=True, readable=True),
    output_dir: Path = typer.Option(ROOT / "artifacts" / "runs"),
    langfuse: bool = typer.Option(False, help="Run as a traced Langfuse experiment."),
    run_name: str = typer.Option("meeting-agent-eval"),
) -> None:
    """Run the benchmark locally or as a Langfuse experiment."""
    cases = load_cases(dataset)
    selected = _provider(provider, model, tracing=langfuse)
    if langfuse:
        if provider == "fixture":
            raise typer.BadParameter("Langfuse experiments require a real provider")
        from .langfuse_runner import run_experiment
        typer.echo(run_experiment(cases, selected, run_name).format())
        return
    path, report = run_local(cases, selected, model, output_dir)
    typer.echo('Legacy ID-matching baseline: these scores do not establish semantic correctness.')
    typer.echo(f"report: {path}")
    typer.echo(f"errors: {report['run']['error_count']}")
    for metric, value in sorted(report["aggregate"].items()):
        typer.echo(f"{metric}: {value:.4f}")
    if report['run']['error_count']:
        raise typer.Exit(1)


@app.command("seed-langfuse")
def seed_langfuse(
    dataset_name: str = typer.Option("meeting-agent-v1", "--dataset"),
    source: Path = typer.Option(DEFAULT_DATASET, exists=True, readable=True),
) -> None:
    """Upload local cases to a Langfuse dataset."""
    from .langfuse_runner import seed_dataset
    cases = load_cases(source)
    seed_dataset(cases, dataset_name)
    typer.echo(f"seeded {len(cases)} cases into {dataset_name}")


if __name__ == "__main__":
    app()
