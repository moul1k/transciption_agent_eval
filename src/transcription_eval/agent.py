from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .schemas import BenchmarkCase, BenchmarkInput, MeetingOutput

ROOT = Path(__file__).resolve().parents[2]


class Provider(Protocol):
    name: str

    def generate(self, meeting: BenchmarkInput, *, expected: MeetingOutput | None = None) -> MeetingOutput: ...


class FixtureProvider:
    """Harness smoke-test provider; never use its score as a model result."""

    name = "fixture"

    def generate(self, meeting: BenchmarkInput, *, expected: MeetingOutput | None = None) -> MeetingOutput:
        if expected is None:
            raise ValueError("fixture provider requires an expected output")
        return expected.model_copy(deep=True)


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str, prompt_path: Path | None = None, tracing: bool = False) -> None:
        try:
            if tracing:
                from langfuse.openai import OpenAI
            else:
                from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError('Install the OpenAI extra: pip install -e ".[openai]"') from exc
        self.model = model
        self.client = OpenAI(timeout=120, max_retries=0)
        self.prompt = (prompt_path or ROOT / "prompts" / "agent_v1.txt").read_text(encoding="utf-8")

    def generate(self, meeting: BenchmarkInput, *, expected: MeetingOutput | None = None) -> MeetingOutput:
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": json.dumps(meeting.model_dump(mode="json"))},
            ],
            text_format=MeetingOutput,
        )
        if response.output_parsed is None:
            raise RuntimeError("model returned no parsed output")
        return response.output_parsed


def load_cases(path: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                cases.append(BenchmarkCase.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"invalid benchmark case at {path}:{line_number}: {exc}") from exc
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("benchmark case IDs must be unique")
    return cases
