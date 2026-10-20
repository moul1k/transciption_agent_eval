import json
from xml.etree import ElementTree

from typer.testing import CliRunner

from transcription_eval.audit import export_junit, gate, score_rows, wilson
from transcription_eval.cli import app
from transcription_eval.contracts import build_suite, state_verdict
from transcription_eval.meta import load_bundle


def test_authored_contracts_are_separate_and_final_state_oracle_is_exact():
    bundle, contracts = build_suite()
    assert len(bundle["cases"]) == len(contracts) == 34
    assert len({c["meeting_id"] for c in bundle["cases"]}) == 14
    assert all("expected" not in c for c in bundle["cases"])
    by_id = {c["id"]: c for c in bundle["cases"]}
    tool = [c for c in contracts if c.oracle == "final_state"]
    assert len(tool) == 8
    assert all(state_verdict(by_id[c.case_id]) == c.expected for c in tool)
    case = next(by_id[c.case_id] for c in tool if c.expected == "pass")
    case["final_state"] = {}
    assert state_verdict(case) == "insufficient_context"


def test_generic_bundle_roundtrips_into_human_workflow(tmp_path):
    result = CliRunner().invoke(app, ["meta", "contract-suite", str(tmp_path / "suite")])
    assert result.exit_code == 0, result.output
    bundle = load_bundle(tmp_path / "suite/cases.jsonl", tmp_path / "suite/rubric.json")
    assert len(bundle["cases"]) == 34
    assert (tmp_path / "suite/review.html").exists()


def test_missing_predictions_do_not_pass_gate_and_junit_escapes(tmp_path):
    rows = [
        {
            "condition": "example",
            "case_id": "<case>",
            "criterion_id": "grounding",
            "repeat": 1,
            "expected": "fail",
            "verdict": None,
            "rationale": "<invalid>",
        }
    ]
    report = score_rows(rows)
    assert report["groups"]["example"]["contract_match_rate"] == 0
    assert report["groups"]["example"]["failure_detection_rate"] == 0
    assert gate(report)
    assert gate({"groups": {}})
    path = tmp_path / "junit.xml"
    export_junit(rows, path)
    xml = ElementTree.parse(path).getroot()
    assert xml.attrib["failures"] == "1"
    assert xml.find("testcase").attrib["name"].startswith("<case>")


def test_abstention_expected_for_missing_evidence_is_not_failure_accuracy():
    rows = [
        {
            "condition": "no-state",
            "case_id": "c",
            "criterion_id": "execution",
            "repeat": i,
            "expected": "insufficient_context",
            "verdict": "insufficient_context",
        }
        for i in (1, 2)
    ]
    metrics = score_rows(rows)["groups"]["no-state"]
    assert metrics["contract_match_rate"] == 1
    assert metrics["failure_precision"] is None
    assert metrics["binary_coverage"] == 0
    assert metrics["complete_repeat_agreement"] == 1


def test_regression_gate_has_nonzero_exit(tmp_path):
    report = score_rows(
        [
            {
                "condition": "c",
                "case_id": "id",
                "criterion_id": "k",
                "repeat": 1,
                "expected": "fail",
                "verdict": "pass",
            }
        ]
    )
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert CliRunner().invoke(app, ["meta", "gate", str(path)]).exit_code == 1


def test_gate_can_exclude_a_deliberately_bad_control(tmp_path):
    rows = [
        {
            "condition": name,
            "case_id": "id",
            "criterion_id": "c",
            "repeat": 1,
            "expected": "fail",
            "verdict": verdict,
        }
        for name, verdict in [("legacy", "pass"), ("candidate", "fail")]
    ]
    path = tmp_path / "report.json"
    path.write_text(json.dumps(score_rows(rows)), encoding="utf-8")
    runner = CliRunner()
    assert (
        runner.invoke(app, ["meta", "gate", str(path), "--condition", "candidate"]).exit_code == 0
    )
    assert runner.invoke(app, ["meta", "gate", str(path), "--condition", "unknown"]).exit_code != 0
    assert gate({"groups": {"fake": {"contract_match_rate": 1, "false_acceptances": 0}}})


def test_wilson_zero_success_is_not_zero_uncertainty():
    assert wilson(0, 4)["upper"] > 0
    assert wilson(4, 4)["lower"] < 1
    assert wilson(0, 0) is None
