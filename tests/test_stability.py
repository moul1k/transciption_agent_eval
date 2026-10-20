import json
from pathlib import Path

import pytest
from test_meta import submission
from typer.testing import CliRunner

from transcription_eval.cli import app
from transcription_eval.meta import load_bundle
from transcription_eval.stability import analyze_repeats

ROOT = Path(__file__).parents[1]


def test_stable_wrong_and_abstaining_are_distinguishable():
    bundle = load_bundle(ROOT / "data/meta/cases.jsonl", ROOT / "data/meta/rubric.json")
    first = submission(bundle, "j1", "judge", "pass")
    second = submission(bundle, "j2", "judge", "pass")
    for s in (first, second):
        s.metadata["configuration_hash"] = "same"
    result = analyze_repeats(bundle, [first, second], "discovery")
    assert result["stable_cell_rate"] == 1
    assert result["binary_pair_agreement"] == 1
    second.judgments[0].verdict = "insufficient_context"
    result = analyze_repeats(bundle, [first, second], "discovery")
    assert result["complete_cell_rate"] == 8 / 9
    assert result["binary_pair_coverage"] == 8 / 9
    assert result["stable_cell_rate"] == 8 / 9
    second.metadata["configuration_hash"] = "different"
    with pytest.raises(ValueError, match="shared configuration"):
        analyze_repeats(bundle, [first, second], "discovery")


def test_repeat_command_keeps_abstentions_visible(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "meta",
            "repeat-judge",
            str(ROOT / "data/meta/cases.jsonl"),
            str(ROOT / "data/meta/rubric.json"),
            str(ROOT / "data/meta/example_judge.json"),
            str(tmp_path / "repeats"),
            "--repeats",
            "2",
            "--split",
            "discovery",
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "repeats/stability.json").read_text())
    assert report["binary_pair_coverage"] == 0
    assert report["binary_pair_agreement"] is None
    assert report["stable_cell_rate"] == 0
