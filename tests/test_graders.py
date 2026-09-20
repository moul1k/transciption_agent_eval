from datetime import datetime

from transcription_eval.graders import grade
from transcription_eval.schemas import ActionItem, CalendarEvent, MeetingOutput


def values(scores):
    return {score.name: score.value for score in scores}


def test_exact_empty_output_passes() -> None:
    result = values(grade(MeetingOutput(), MeetingOutput()))
    assert all(value == 1.0 for value in result.values())


def test_extra_action_is_a_hallucination() -> None:
    actual = MeetingOutput(action_items=[ActionItem(id="invented", task="Do it", evidence="none")])
    result = values(grade(actual, MeetingOutput()))
    assert result["action_items_precision"] == 0.0
    assert result["no_hallucinations"] == 0.0


def test_missing_action_reduces_recall() -> None:
    expected = MeetingOutput(action_items=[ActionItem(id="a", task="Do it", evidence="Do it")])
    result = values(grade(MeetingOutput(), expected))
    assert result["action_items_recall"] == 0.0


def test_event_time_is_scored_separately() -> None:
    expected = MeetingOutput(calendar_events=[CalendarEvent(
        id="event", title="Review", start_at=datetime.fromisoformat("2026-09-22T14:00:00-06:00"), evidence="review"
    )])
    actual = MeetingOutput(calendar_events=[CalendarEvent(
        id="event", title="Review", start_at=datetime.fromisoformat("2026-09-22T15:00:00-06:00"), evidence="review"
    )])
    result = values(grade(actual, expected))
    assert result["calendar_events_recall"] == 1.0
    assert result["event_start_at_accuracy"] == 0.0
