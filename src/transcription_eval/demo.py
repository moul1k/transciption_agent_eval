"""Runnable demo with conspicuous synthetic labels; never a research result."""

import json
from datetime import UTC, datetime
from pathlib import Path

from .challenges import analyze, generate
from .meta import Judgment, Submission, compare, load_bundle
from .reporting import write_html
from .review import export_review


def run(output_dir: Path, cases: Path, rubric: Path):
    bundle, plan = generate(load_bundle(cases, rubric), "sample-correct")
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "cases.jsonl").write_text(
        "".join(json.dumps(c) + "\n" for c in bundle["cases"]), encoding="utf-8"
    )
    (output_dir / "manifest.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    export_review(bundle, output_dir / "review.html")
    proposed_failures = {
        (r.variant_id, r.criterion_id) for r in plan.relations if r.behavior == "detect_failure"
    }
    # These references demonstrate I/O. They are scripted, not adjudicated human truth.
    judgments = [
        Judgment(
            case_id=c["id"],
            criterion_id=r["id"],
            verdict="fail" if (c["id"], r["id"]) in proposed_failures else "pass",
            rationale="SYNTHETIC DEMO: scripted for the known teaching example.",
        )
        for c in bundle["cases"]
        for r in bundle["rubric"]["criteria"]
    ]
    common = {
        "dataset_hash": bundle["dataset_hash"],
        "rubric_hash": bundle["rubric_hash"],
        "rubric_id": bundle["rubric"]["id"],
        "rubric_version": bundle["rubric"]["version"],
        "created_at": datetime.now(UTC),
        "metadata": {"synthetic_demo": True},
    }
    refs = [
        Submission(
            **common, evaluator_id=f"synthetic-reviewer-{i}", kind="human", judgments=judgments
        )
        for i in (1, 2)
    ]
    always_pass = Submission(
        **common,
        evaluator_id="always-pass-baseline",
        kind="judge",
        judgments=[
            j.model_copy(
                update={"verdict": "pass", "rationale": "SYNTHETIC DEMO: always-pass control."}
            )
            for j in judgments
        ],
    )
    folder = output_dir / "submissions"
    folder.mkdir()
    for submission in [*refs, always_pass]:
        (folder / f"{submission.evaluator_id}.json").write_text(
            submission.model_dump_json(indent=2), encoding="utf-8"
        )
    report = compare(bundle, [*refs, always_pass], "discovery")
    (output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_html(report, output_dir / "report.html")
    (output_dir / "robustness.json").write_text(
        json.dumps(analyze(bundle, plan, always_pass), indent=2), encoding="utf-8"
    )
    return report
