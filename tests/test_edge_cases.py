from datetime import UTC

from typer.testing import CliRunner

from transcription_eval.cli import app
from transcription_eval.edge_cases import build_edge_suite
from transcription_eval.meta import load_bundle


def test_niche_cases_are_paired_blind_and_valid():
    bundle, contracts = build_edge_suite()
    assert len(bundle["cases"]) == len(contracts) == 36
    assert len({c["meeting_id"] for c in bundle["cases"]}) == 18
    for category in {c.category for c in contracts}:
        assert {c.expected for c in contracts if c.category == category} == {"pass", "fail"}
    assert all("expected" not in c for c in bundle["cases"])
    assert {c.criterion_id for c in contracts} <= {c["id"] for c in bundle["rubric"]["criteria"]}
    assert len({c["id"] for c in bundle["cases"]}) == 36


def test_edge_cli_roundtrip_and_frozen_scope(tmp_path):
    folder = tmp_path / "suite"
    result = CliRunner().invoke(app, ["meta", "contract-suite", str(folder), "--suite", "edge"])
    assert result.exit_code == 0, result.output
    bundle = load_bundle(folder / "cases.jsonl", folder / "rubric.json")
    assert len(bundle["cases"]) == 36
    scope = next(c for c in bundle["rubric"]["criteria"] if c["id"] == "preserve_uncertainty")
    assert "An omitted task or empty output passes" in scope["pass_condition"]
    assert (folder / "review.html").exists()


def test_tool_counterexamples_keep_shared_trace_and_state():
    bundle, contracts = build_edge_suite()
    cases = {c["id"]: c for c in bundle["cases"]}
    timeout = [c for c in contracts if c.category == "timeout-but-committed"]
    good = next(cases[c.case_id] for c in timeout if c.expected == "pass")
    bad = next(cases[c.case_id] for c in timeout if c.expected == "fail")
    assert good["tool_trace"] == bad["tool_trace"]
    assert good["final_state"] == bad["final_state"]
    assert len(good["final_state"]["events"]) == 1


def test_utc_date_rollover_reference_is_independently_checkable():
    from datetime import datetime

    bundle, contracts = build_edge_suite()
    by_id = {c["id"]: c for c in bundle["cases"]}
    source = datetime.fromisoformat("2026-10-20T23:30:00-07:00").astimezone(UTC)
    for contract in contracts:
        if contract.category == "cross-midnight-utc":
            actual = datetime.fromisoformat(
                by_id[contract.case_id]["output"]["events"][0]["start_at"]
            )
            assert (actual == source) == (contract.expected == "pass")
