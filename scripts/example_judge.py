"""Protocol smoke test only. Deliberately abstains; not a quality evaluator."""

import json
import sys

request = json.load(sys.stdin)
json.dump(
    {
        "case_id": request["case"]["id"],
        "criterion_id": request["criterion"]["id"],
        "verdict": "insufficient_context",
        "rationale": "Smoke-test adapter; human review required.",
        "evidence": [],
    },
    sys.stdout,
)
