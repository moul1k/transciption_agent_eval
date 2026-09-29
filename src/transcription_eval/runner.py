from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean

from .agent import Provider
from .graders import grade
from .schemas import BenchmarkCase


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_local(cases: list[BenchmarkCase], provider: Provider, model: str, output_dir: Path) -> tuple[Path, dict]:
    rows = []
    for case in cases:
        started = time.perf_counter()
        try:
            actual = provider.generate(case.input, expected=case.expected)
            scores = grade(actual, case.expected)
            error = None
        except Exception as exc:
            actual, scores, error = None, [], f"{type(exc).__name__}: {exc}"
        rows.append({
            "case_id": case.id, "feature": case.feature, "scenario": case.scenario,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "actual": actual.model_dump(mode="json") if actual else None,
            "scores": [score.to_dict() for score in scores], "error": error,
        })

    values: dict[str, list[float]] = {}
    for row in rows:
        for score in row["scores"]:
            values.setdefault(str(score["name"]), []).append(float(score["value"]))
    report = {
        "metric_limitations": "Legacy ID matching only; averages exclude provider errors. See error_count. Not semantic quality.",
        "run": {"created_at": datetime.now(UTC).isoformat(), "git_sha": _git_sha(),
                "provider": provider.name, "model": model, "prompt_version": "agent_v1",
                "case_count": len(cases), "error_count": sum(row["error"] is not None for row in rows)},
        "aggregate": {name: round(fmean(v), 4) for name, v in values.items()}, "cases": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path, report
