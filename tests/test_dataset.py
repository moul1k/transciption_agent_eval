from pathlib import Path

from transcription_eval.agent import load_cases


def test_benchmark_is_valid_and_unique() -> None:
    path = Path(__file__).parents[1] / "data" / "benchmark.jsonl"
    cases = load_cases(path)
    assert len(cases) >= 5
    assert len({case.id for case in cases}) == len(cases)
    assert {case.feature for case in cases} >= {"action_items", "calendar_events", "decisions", "safety"}
