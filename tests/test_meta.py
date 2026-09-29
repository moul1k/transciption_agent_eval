import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from transcription_eval.cli import app
from transcription_eval.judges import run_judge
from transcription_eval.meta import Judgment, Submission, compare, load_bundle, validate_submission
from transcription_eval.review import export_review

ROOT = Path(__file__).parents[1]


@pytest.fixture
def bundle():
    return load_bundle(ROOT / "data/meta/cases.jsonl", ROOT / "data/meta/rubric.json")


def submission(bundle, who, kind, verdict):
    return Submission(
        dataset_hash=bundle["dataset_hash"],
        rubric_hash=bundle["rubric_hash"],
        rubric_id=bundle["rubric"]["id"],
        rubric_version=bundle["rubric"]["version"],
        evaluator_id=who,
        kind=kind,
        created_at=datetime.now(UTC),
        judgments=[
            Judgment(
                case_id=c["id"], criterion_id=r["id"], verdict=verdict, rationale="Test rationale"
            )
            for c in bundle["cases"]
            for r in bundle["rubric"]["criteria"]
        ],
    )


def test_consensus_and_false_acceptance(bundle):
    data = [
        submission(bundle, "h1", "human", "fail"),
        submission(bundle, "h2", "human", "fail"),
        submission(bundle, "j1", "judge", "pass"),
    ]
    report = compare(bundle, data, "discovery")
    assert report["reference_count"] == 9
    assert report["evaluators"]["j1"]["all"]["false_acceptance_rate_answered"] == 1
    assert report["human_pair_agreement"] == 1


def test_disagreement_is_not_silently_majority_voted(bundle):
    data = [submission(bundle, "h1", "human", "fail"), submission(bundle, "h2", "human", "pass")]
    assert compare(bundle, data, "discovery")["reference_count"] == 0
    data.append(submission(bundle, "arbiter", "adjudication", "fail"))
    assert compare(bundle, data, "discovery")["reference_count"] == 9


def test_missing_and_abstention_count_against_detection(bundle):
    judge = submission(bundle, "j", "judge", "insufficient_context")
    judge.judgments.pop()
    report = compare(
        bundle,
        [
            submission(bundle, "h1", "human", "fail"),
            submission(bundle, "h2", "human", "fail"),
            judge,
        ],
        "discovery",
    )
    metrics = report["evaluators"]["j"]["all"]
    assert metrics["missing"] == 1 and metrics["abstained"] == 8
    assert metrics["coverage"] == 0 and metrics["failure_detection_rate"] == 0
    assert metrics["failure_precision"] is None


def test_reject_duplicate_and_wrong_provenance(bundle):
    human = submission(bundle, "h", "human", "pass")
    with pytest.raises(ValueError, match="duplicate evaluator"):
        compare(bundle, [human, human], "discovery")
    human.rubric_hash = "wrong"
    with pytest.raises(ValueError, match="provenance"):
        validate_submission(human, bundle)


def test_reject_split_leakage(tmp_path, bundle):
    bundle["cases"][1]["split"] = "test"
    cases = tmp_path / "cases.jsonl"
    cases.write_text("\n".join(json.dumps(c) for c in bundle["cases"]), encoding="utf-8")
    with pytest.raises(ValueError, match="variants"):
        load_bundle(cases, ROOT / "data/meta/rubric.json")


def test_offline_page_escapes_untrusted_script(tmp_path, bundle):
    bundle["cases"][0]["input"]["transcript"] = "</script><script>alert(1)</script>"
    page = tmp_path / "review.html"
    export_review(bundle, page)
    assert "</script><script>alert(1)</script>" not in page.read_text(encoding="utf-8")


def test_adapter_and_cli_roundtrip(tmp_path, bundle):
    result = run_judge(
        bundle, [sys.executable, str(ROOT / "scripts/example_judge.py")], "smoke", "discovery"
    )
    assert len(result.judgments) == 9 and not result.metadata["errors"]
    folder = tmp_path / "submissions"
    folder.mkdir()
    for s in [
        result,
        submission(bundle, "h1", "human", "pass"),
        submission(bundle, "h2", "human", "pass"),
    ]:
        (folder / f"{s.evaluator_id}.json").write_text(s.model_dump_json(), encoding="utf-8")
    report = tmp_path / "report.json"
    invocation = CliRunner().invoke(
        app,
        [
            "meta",
            "compare",
            str(ROOT / "data/meta/cases.jsonl"),
            str(ROOT / "data/meta/rubric.json"),
            str(folder),
            str(report),
            "--split",
            "discovery",
        ],
    )
    assert invocation.exit_code == 0, invocation.output
    assert json.loads(report.read_text())["evaluators"]["smoke"]["all"]["abstained"] == 9


def test_adapter_errors_are_recorded(bundle):
    result = run_judge(bundle, [sys.executable, "-c", 'print("not json")'], "bad", "discovery")
    assert not result.judgments and len(result.metadata["errors"]) == 9
