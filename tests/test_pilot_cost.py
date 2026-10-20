import runpy
from pathlib import Path

import pytest


def test_cost_summary_includes_cache_write_premium_and_cache_discount():
    script = Path(__file__).parents[1] / "scripts/summarize_luna_pilot.py"
    summarize = runpy.run_path(str(script))["usage_summary"]
    rows = [
        {
            "status": "success",
            "latency_ms": 100,
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 100,
                "input_tokens_details": {"cached_tokens": 200, "cache_write_tokens": 300},
            },
        }
    ]
    summary = summarize(rows)
    assert summary["estimated_usd"] == pytest.approx(
        (500 * 0.1 + 200 * 0.01 + 300 * 0.125 + 100 * 0.5) / 1e6
    )
    assert summary["successes"] == 1
