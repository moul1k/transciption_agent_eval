import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from transcription_eval.challenges import analyze, generate
from transcription_eval.cli import app
from transcription_eval.demo import run
from transcription_eval.meta import load_bundle
from transcription_eval.reporting import write_html

ROOT = Path(__file__).parents[1]


def seed():
    return load_bundle(ROOT / "data/meta/cases.jsonl", ROOT / "data/meta/rubric.json")


def test_variants_keep_inputs_split_and_hide_mutation_names():
    bundle, manifest = generate(seed(), "sample-correct")
    assert len(bundle["cases"]) == 4
    assert len(manifest.relations) == 5
    assert manifest.expectations_status == "proposed_not_human_validated"
    for case in bundle["cases"]:
        assert case["input"] == bundle["cases"][0]["input"]
        assert case["split"] == "discovery"
        assert case["meeting_id"] == "sample-budget"
    assert all(r.transformation not in r.variant_id for r in manifest.relations)
    replacement = next(
        r for r in manifest.relations if r.transformation == "replace_task_preserve_id"
    )
    variant = next(c for c in bundle["cases"] if c["id"] == replacement.variant_id)
    assert variant["output"]["action_items"][0]["id"] == "a1"


def test_demo_exposes_always_pass_failure_and_escapes_html(tmp_path):
    report = run(tmp_path / "demo", ROOT / "data/meta/cases.jsonl", ROOT / "data/meta/rubric.json")
    assert report["synthetic_demo"]
    assert report["evaluators"]["always-pass-baseline"]["all"]["failure_detection_rate"] == 0
    robustness = json.loads((tmp_path / "demo/robustness.json").read_text())
    assert robustness["summary"]["invariant"]["satisfaction_rate"] == 1
    assert robustness["summary"]["detect_failure"]["satisfaction_rate"] == 0
    assert len(report["review_queue"]) == 2
    report["review_queue"][0]["annotations"][0]["rationale"] = "<script>alert(1)</script>"
    write_html(report, tmp_path / "escape.html")
    text = (tmp_path / "escape.html").read_text()
    assert "<script>alert(1)</script>" not in text and "&lt;script&gt;" in text
    with pytest.raises(FileExistsError):
        run(tmp_path / "demo", ROOT / "data/meta/cases.jsonl", ROOT / "data/meta/rubric.json")


def test_abstentions_and_bad_base_never_count_as_robustness_success(tmp_path):
    from transcription_eval.meta import Submission

    run(tmp_path / "demo", ROOT / "data/meta/cases.jsonl", ROOT / "data/meta/rubric.json")
    bundle, manifest = generate(seed(), "sample-correct")
    submission = Submission.model_validate_json(
        (tmp_path / "demo/submissions/always-pass-baseline.json").read_text()
    )
    for j in submission.judgments:
        j.verdict = "insufficient_context"
    result = analyze(bundle, manifest, submission)
    assert result["summary"]["invariant"]["satisfaction_rate"] is None
    assert result["summary"]["detect_failure"]["unanswered"] == 2
    for j in submission.judgments:
        j.verdict = "fail"
    result = analyze(bundle, manifest, submission)
    assert result["summary"]["detect_failure"]["base_not_passed"] == 2
    assert result["summary"]["detect_failure"]["satisfaction_rate"] is None


def test_cli_challenge_io_and_provenance(tmp_path):
    runner = CliRunner()
    folder = tmp_path / "challenge"
    result = runner.invoke(
        app,
        [
            "meta",
            "challenges",
            str(ROOT / "data/meta/cases.jsonl"),
            str(ROOT / "data/meta/rubric.json"),
            str(folder),
            "sample-correct",
        ],
    )
    assert result.exit_code == 0, result.output
    bundle = load_bundle(folder / "cases.jsonl", ROOT / "data/meta/rubric.json")
    assert (
        bundle["dataset_hash"] == json.loads((folder / "manifest.json").read_text())["dataset_hash"]
    )


def test_input_cannot_leak_by_changing_meeting_id(tmp_path):
    cases = seed()["cases"]
    cases[1]["meeting_id"] = "different"
    cases[1]["split"] = "test"
    path = tmp_path / "cases.jsonl"
    path.write_text("\n".join(json.dumps(c) for c in cases), encoding="utf-8")
    with pytest.raises(ValueError, match="identical meeting input"):
        load_bundle(path, ROOT / "data/meta/rubric.json")


def test_owner_and_order_challenges_are_conditional():
    bundle = seed()
    first = bundle["cases"][0]
    first["output"]["action_items"][0]["owner"] = None
    second = dict(first["output"]["action_items"][0], id="a2", task="Another task")
    first["output"]["action_items"].append(second)
    generated, manifest = generate(bundle, first["id"])
    names = {r.transformation for r in manifest.relations}
    assert "invent_owner" in names and "reverse_object_order" in names
    assert first["output"]["action_items"][0]["owner"] is None
    assert len(generated["cases"]) == 6


def test_expanded_rubric_does_not_mix_with_old_submissions(tmp_path):
    from transcription_eval.meta import Submission, validate_submission

    run(tmp_path / "demo", ROOT / "data/meta/cases.jsonl", ROOT / "data/meta/rubric.json")
    old = Submission.model_validate_json(
        (tmp_path / "demo/submissions/always-pass-baseline.json").read_text()
    )
    expanded = load_bundle(tmp_path / "demo/cases.jsonl", ROOT / "data/meta/rubric_v2.json")
    assert len(expanded["rubric"]["criteria"]) == 7
    with pytest.raises(ValueError, match="provenance"):
        validate_submission(old, expanded)
