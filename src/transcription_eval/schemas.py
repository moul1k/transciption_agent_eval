from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ActionItem(StrictModel):
    id: str = Field(description="Stable semantic ID, e.g. action-send-recap")
    task: str
    owner: str | None = None
    due_at: datetime | None = None
    evidence: str


class CalendarEvent(StrictModel):
    id: str
    title: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    attendees: list[str] = Field(default_factory=list)
    status: Literal["confirmed", "tentative"] = "confirmed"
    evidence: str


class Decision(StrictModel):
    id: str
    decision: str
    evidence: str


class FollowUp(StrictModel):
    id: str
    question: str
    owner: str | None = None
    evidence: str


class MeetingOutput(StrictModel):
    action_items: list[ActionItem] = Field(default_factory=list)
    calendar_events: list[CalendarEvent] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    follow_ups: list[FollowUp] = Field(default_factory=list)


class BenchmarkInput(StrictModel):
    transcript: str
    meeting_at: datetime | None = None
    timezone: str | None = None


class BenchmarkCase(StrictModel):
    id: str
    feature: str
    scenario: str
    input: BenchmarkInput
    expected: MeetingOutput
    tags: list[str] = Field(default_factory=list)
