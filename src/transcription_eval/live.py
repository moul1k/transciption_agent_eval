"""Run a real transcript through OpenAI and emit linked human-review artifacts."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from .agent import OpenAIProvider
from .meta import ReviewCase, load_bundle
from .review import export_review
from .schemas import BenchmarkInput
from .tracing import client, load_credentials


def extract(
    transcript: Path,
    rubric: Path,
    output_dir: Path,
    model: str,
    credentials: Path | None = None,
    tracing: bool = False,
):
    load_credentials(credentials)
    # Validate config and files before any paid call or output directory creation.
    provider = OpenAIProvider(model, tracing=tracing)
    meeting = BenchmarkInput(transcript=transcript.read_text(encoding="utf-8-sig"))
    from .meta import Rubric

    Rubric.model_validate_json(rubric.read_text(encoding="utf-8"))
    lf = client() if tracing else None
    output_dir.mkdir(parents=True, exist_ok=False)
    run_id = uuid4().hex
    metadata = {
        "run_id": run_id,
        "model": model,
        "prompt_sha256": hashlib.sha256(provider.prompt.encode()).hexdigest(),
        "source": "live-openai",
        "human_labels": "pending",
    }
    trace_url = None
    try:
        if lf:
            with lf.start_as_current_observation(
                name="meeting-transcript-extraction",
                as_type="span",
                input=meeting.model_dump(mode="json"),
                metadata=metadata,
            ) as span:
                actual = provider.generate(meeting)
                span.update(output=actual.model_dump(mode="json"))
                metadata["trace_id"] = lf.get_current_trace_id()
                trace_url = lf.get_trace_url()
        else:
            actual = provider.generate(meeting)
        case = ReviewCase(
            id=run_id,
            meeting_id=hashlib.sha256(meeting.transcript.encode()).hexdigest(),
            split="discovery",
            input=meeting,
            output=actual,
        )
        (output_dir / "cases.jsonl").write_text(case.model_dump_json() + "\n", encoding="utf-8")
        (output_dir / "candidate.json").write_text(
            actual.model_dump_json(indent=2), encoding="utf-8"
        )
        bundle = load_bundle(output_dir / "cases.jsonl", rubric)
        (output_dir / "review.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        export_review(bundle, output_dir / "review.html")
        metadata["trace_url"] = trace_url
        (output_dir / "run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata
    finally:
        if lf:
            lf.flush()
