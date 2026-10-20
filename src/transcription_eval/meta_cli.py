"""Explicit file I/O for annotation and external judge integrations."""

import json
from pathlib import Path

import typer

from .meta import Submission, compare, load_bundle, validate_submission
from .review import export_review

app = typer.Typer(help="Human-calibrated evaluator experiments. JSON/JSONL in, JSON/HTML out.")


@app.command("demo")
def demo(output_dir: Path):
    """Create an end-to-end synthetic teaching run, without keys or paid calls."""
    from .demo import run

    root = Path(__file__).resolve().parents[2]
    run(output_dir, root / "data/meta/cases.jsonl", root / "data/meta/rubric.json")
    typer.echo(f"SYNTHETIC DEMO (not human research): {output_dir / 'report.html'}")


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
    if output.with_suffix(".html").exists() or output.exists():
        raise typer.BadParameter("report output exists; choose a new path")
    result = compare(bundle, data, split)
    write_new(output, result)
    from .reporting import write_html

    write_html(result, output.with_suffix(".html"))
    typer.echo(str(output))


@app.command("challenges")
def challenges(cases: Path, rubric: Path, output_dir: Path, case_id: str):
    """Generate blind output variants and a separate proposed challenge manifest."""
    from .challenges import generate

    bundle, manifest = generate(load_bundle(cases, rubric), case_id)
    output_dir.mkdir(parents=True, exist_ok=False)
    with (output_dir / "cases.jsonl").open("x", encoding="utf-8") as handle:
        for case in bundle["cases"]:
            handle.write(json.dumps(case) + "\n")
    write_new(output_dir / "manifest.json", manifest.model_dump(mode="json"))
    write_new(output_dir / "review.json", bundle)
    export_review(bundle, output_dir / "review.html")
    typer.echo(
        f"{len(bundle['cases'])} cases; {len(manifest.relations)} proposed relations. "
        "Review before treating expectations as valid."
    )


@app.command("robustness")
def robustness(cases: Path, rubric: Path, manifest: Path, submission: Path, output: Path):
    """Analyze invariance and conditional failure detection; no human labels inferred."""
    from .challenges import ChallengeManifest, analyze

    bundle = load_bundle(cases, rubric)
    plan = ChallengeManifest.model_validate_json(manifest.read_text(encoding="utf-8"))
    judge_result = Submission.model_validate_json(submission.read_text(encoding="utf-8"))
    write_new(output, analyze(bundle, plan, judge_result))
    typer.echo(str(output))


@app.command("repeat-judge")
def repeat_judge(
    cases: Path,
    rubric: Path,
    config: Path,
    output_dir: Path,
    repeats: int = typer.Option(3, min=2, max=10),
    split: str = "test",
):
    """Execute identical trusted adapter config repeatedly; report coverage and stability.

    Real model adapters incur repeats times the usual number of API calls.
    """
    from .judges import run_judge
    from .meta import digest
    from .stability import analyze_repeats

    bundle = load_bundle(cases, rubric)
    if not any(c["split"] == split for c in bundle["cases"]):
        raise typer.BadParameter("no cases in selected split")
    settings = json.loads(config.read_text(encoding="utf-8"))
    command = settings.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(v, str) for v in command):
        raise typer.BadParameter("command must be a nonempty argv array")
    output_dir.mkdir(parents=True, exist_ok=False)
    runs = []
    for i in range(repeats):
        result = run_judge(
            bundle,
            command,
            f"{settings['evaluator_id']}:repeat-{i + 1}",
            split,
            settings.get("timeout", 60),
        )
        result.metadata.update(
            configuration_hash=digest(settings),
            judge_family=settings["evaluator_id"],
            repetition=i + 1,
        )
        write_new(output_dir / f"repeat-{i + 1}.json", result.model_dump(mode="json"))
        runs.append(result)
        typer.echo(f"Repeat {i + 1}/{repeats}: {len(result.metadata['errors'])} adapter errors")
    write_new(output_dir / "stability.json", analyze_repeats(bundle, runs, split))
    if any(r.metadata["errors"] for r in runs):
        raise typer.Exit(1)


@app.command("schema")
def schema(output: Path):
    """Export the strict JSON Schema used by human and model adapters."""
    write_new(output, Submission.model_json_schema())
