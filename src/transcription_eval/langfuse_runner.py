from __future__ import annotations

from .graders import grade
from .schemas import BenchmarkCase, BenchmarkInput, MeetingOutput


def _client():
    try:
        from langfuse import get_client
    except ImportError as exc:
        raise RuntimeError('Install the Langfuse extra: pip install -e ".[langfuse]"') from exc
    return get_client()


def run_experiment(cases: list[BenchmarkCase], provider, name: str):
    from langfuse import Evaluation

    client = _client()
    data = [{"input": case.input.model_dump(mode="json"),
             "expected_output": case.expected.model_dump(mode="json"),
             "metadata": {"case_id": case.id, "feature": case.feature, "scenario": case.scenario}}
            for case in cases]

    def task(*, item, **kwargs):
        return provider.generate(BenchmarkInput.model_validate(item["input"])).model_dump(mode="json")

    def evaluator(*, output, expected_output, **kwargs):
        scores = grade(MeetingOutput.model_validate(output), MeetingOutput.model_validate(expected_output))
        return [Evaluation(name=s.name, value=s.value, comment=s.detail) for s in scores]

    result = client.run_experiment(name=name, data=data, task=task, evaluators=[evaluator])
    client.flush()
    return result


def seed_dataset(cases: list[BenchmarkCase], dataset_name: str) -> None:
    client = _client()
    client.create_dataset(name=dataset_name, description="Meeting agent benchmark")
    for case in cases:
        client.create_dataset_item(
            dataset_name=dataset_name, input=case.input.model_dump(mode="json"),
            expected_output=case.expected.model_dump(mode="json"),
            metadata={"case_id": case.id, "feature": case.feature,
                      "scenario": case.scenario, "tags": case.tags},
        )
    client.flush()
