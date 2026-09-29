"""Explicit file I/O for annotation and external judge integrations."""

import json
from pathlib import Path

import typer

from .meta import Submission, compare, load_bundle, validate_submission
from .review import export_review

app = typer.Typer(help="Human-calibrated evaluator experiments. JSON/JSONL in, JSON/HTML out.")


@app.command("import-transcript")
def import_transcript(
    transcript: Path,
    candidate: Path,
    output: Path,
    case_id: str = "review-001",
    meeting_id: str = "meeting-001",
):
    """Import TXT + candidate MeetingOutput JSON as a discovery case; unknown time stays null."""
    from .meta import ReviewCase
    from .schemas import BenchmarkInput, MeetingOutput

    case = ReviewCase(
        id=case_id,
        meeting_id=meeting_id,
        split="discovery",
        input=BenchmarkInput(transcript=transcript.read_text(encoding="utf-8-sig")),
        output=MeetingOutput.model_validate_json(candidate.read_text(encoding="utf-8")),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(case.model_dump_json() + "\n")
    typer.echo(f"Imported {len(case.input.transcript)} characters to {output}")


@app.command("judge")
def judge(
    cases: Path,
    rubric: Path,
    config: Path,
    output: Path,
    split: str = "test",
    credentials: Path | None = None,
    langfuse: bool = False,
):
    """Run an adapter configured as {evaluator_id, command: [executable, args], timeout}."""
    import os

    from .judges import run_judge
    from .tracing import client, load_credentials

    load_credentials(credentials)
    if langfuse:
        client()
        os.environ["MEETING_TRACE"] = "1"

    if output.exists():
        raise typer.BadParameter("output exists; choose a new path")
    settings = json.loads(config.read_text(encoding="utf-8"))
    if not isinstance(settings.get("command"), list) or not all(
        isinstance(v, str) for v in settings["command"]
    ):
        raise typer.BadParameter("command must be an argv array of strings")
    bundle = load_bundle(cases, rubric)
    if not any(c["split"] == split for c in bundle["cases"]):
        raise typer.BadParameter("no cases in selected split")
    submission = run_judge(
        bundle, settings["command"], settings["evaluator_id"], split, settings.get("timeout", 60)
    )
    write_new(output, submission.model_dump(mode="json"))
    typer.echo(
        f"{len(submission.judgments)} judgments; {len(submission.metadata['errors'])} errors"
    )
    if submission.metadata["errors"]:
        raise typer.Exit(1)


def write_new(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


@app.command("prepare")
def prepare(cases: Path, rubric: Path, output: Path):
    """Export a validated blind review bundle and offline HTML review page."""
    bundle = load_bundle(cases, rubric)
    page = output.with_suffix(".html")
    if page.exists() or output.exists():
        raise typer.BadParameter("output exists; choose a new path")
    write_new(output, bundle)
    export_review(bundle, page)
    typer.echo(f"Review: {page}\nBundle: {output}")


@app.command("validate")
def validate(cases: Path, rubric: Path, submission: Path):
    """Validate human, adjudicator, or judge output and its provenance."""
    bundle = load_bundle(cases, rubric)
    data = Submission.model_validate_json(submission.read_text(encoding="utf-8"))
    validate_submission(data, bundle)
    typer.echo(f"Valid: {len(data.judgments)} judgments by {data.evaluator_id}")


@app.command("compare")
def report(cases: Path, rubric: Path, submissions: Path, output: Path, split: str = "test"):
    """Read *.json submissions in a directory; write evaluator metrics and disagreements."""
    bundle = load_bundle(cases, rubric)
    data = [
        Submission.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(submissions.glob("*.json"))
    ]
    if not data:
        raise typer.BadParameter("no submissions found")
    write_new(output, compare(bundle, data, split))
    typer.echo(str(output))


@app.command("schema")
def schema(output: Path):
    """Export the strict JSON Schema used by human and model adapters."""
    write_new(output, Submission.model_json_schema())
