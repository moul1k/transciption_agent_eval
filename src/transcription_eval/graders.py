from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime

from .schemas import MeetingOutput


@dataclass(frozen=True)
class Score:
    name: str
    value: float
    detail: str = ""

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)


def _ids(items: Iterable[object]) -> set[str]:
    return {str(item.id) for item in items}  # type: ignore[attr-defined]


def _pr(feature: str, actual: Iterable[object], expected: Iterable[object]) -> list[Score]:
    actual_ids, expected_ids = _ids(actual), _ids(expected)
    true_positive = len(actual_ids & expected_ids)
    precision = true_positive / len(actual_ids) if actual_ids else float(not expected_ids)
    recall = true_positive / len(expected_ids) if expected_ids else float(not actual_ids)
    return [
        Score(f"{feature}_precision", precision, f"extra={sorted(actual_ids - expected_ids)}"),
        Score(f"{feature}_recall", recall, f"missing={sorted(expected_ids - actual_ids)}"),
    ]


def _same_time(left: datetime | None, right: datetime | None) -> bool:
    return left == right


def grade(actual: MeetingOutput, expected: MeetingOutput) -> list[Score]:
    scores: list[Score] = []
    for name in ("action_items", "calendar_events", "decisions", "follow_ups"):
        scores.extend(_pr(name, getattr(actual, name), getattr(expected, name)))

    expected_actions = {item.id: item for item in expected.action_items}
    actual_actions = {item.id: item for item in actual.action_items}
    shared_actions = expected_actions.keys() & actual_actions.keys()
    scores.append(Score(
        "action_owner_accuracy",
        sum(actual_actions[key].owner == expected_actions[key].owner for key in shared_actions) / len(shared_actions)
        if shared_actions else float(not expected_actions),
    ))
    scores.append(Score(
        "action_due_at_accuracy",
        sum(_same_time(actual_actions[key].due_at, expected_actions[key].due_at) for key in shared_actions)
        / len(shared_actions) if shared_actions else float(not expected_actions),
    ))

    expected_events = {item.id: item for item in expected.calendar_events}
    actual_events = {item.id: item for item in actual.calendar_events}
    shared_events = expected_events.keys() & actual_events.keys()
    scores.append(Score(
        "event_start_at_accuracy",
        sum(_same_time(actual_events[key].start_at, expected_events[key].start_at) for key in shared_events)
        / len(shared_events) if shared_events else float(not expected_events),
    ))

    expected_all = set().union(
        _ids(expected.action_items), _ids(expected.calendar_events),
        _ids(expected.decisions), _ids(expected.follow_ups),
    )
    actual_all = set().union(
        _ids(actual.action_items), _ids(actual.calendar_events),
        _ids(actual.decisions), _ids(actual.follow_ups),
    )
    unsupported = actual_all - expected_all
    scores.append(Score("no_hallucinations", float(not unsupported), f"unsupported={sorted(unsupported)}"))
    return scores
