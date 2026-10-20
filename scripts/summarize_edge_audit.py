"""Per-scenario report for the frozen edge suite, with reviewable expectation mismatches."""

import argparse
import html
import json
from pathlib import Path

from transcription_eval.audit import score_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    folder = args.run_dir
    rows = json.loads((folder / "rows.json").read_text())
    report = json.loads((folder / "report.json").read_text())
    categories = score_rows([dict(r, condition=r["category"]) for r in rows])
    criteria = score_rows([dict(r, condition=r["criterion_id"]) for r in rows])
    for name, value in [("by-category.json", categories), ("by-criterion.json", criteria)]:
        with (folder / name).open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
    overall = report["groups"]["edge"]
    usage = report["usage"]
    lines = [
        "# Niche evaluator test results",
        "",
        (f"{usage['successes']}/{usage['calls']} valid judgments with GPT-6 Luna at low reasoning. "
        f"Estimated Standard API cost: ${usage['estimated_usd']:.5f}."),
        "",
        (f"Contract matches: {overall['correct_contract_verdicts']}/{overall['cells']} "
        f"({overall['contract_match_rate']:.1%}). Repeated-cell agreement: "
        f"{overall['complete_repeat_agreement']:.1%}. False acceptances: "
        f"{overall['false_acceptances']}; false rejections: {overall['false_rejections']}."),
        "",
        ("36 candidates in 18 matched pairs, two repeats each. This is a synthetic challenge "
        "set scored against authored contracts, not an estimate of human agreement or "
        "production failure rates. The rubric and expected labels were frozen before calls. "
        "Expected labels were not sent to the model."),
        "",
        "| Scenario | Contract matches | Repeat agreement | False acceptances |",
        "|---|---:|---:|---:|",
    ]
    for name, g in categories["groups"].items():
        lines.append(
            f"| {name} | {g['correct_contract_verdicts']}/{g['cells']} "
            f"| {g['complete_repeat_agreement']:.1%} | {g['false_acceptances']} |"
        )
    lines.extend(
        [
            "",
            "## Cases for independent review",
            "",
            ("A mismatch can indicate a judge error, an ambiguous rubric, or an incorrect authored "
            "expectation. Preserve the original judgment and expectation while adjudicating."),
        ]
    )
    contracts = json.loads((folder / "contracts.json").read_text())
    reasons = {(c["case_id"], c["criterion_id"]): c["rationale"] for c in contracts}
    for row in report["review_queue"]:
        lines.extend(
            [
                "",
                f"### {row['category']} — repeat {row['repeat']}",
                f"Case: {row['case_id']}; criterion: {row['criterion_id']}.",
                f"Authored expectation: {row['expected']}; judge: {row.get('verdict')}.",
                f"Contract rationale: {reasons[(row['case_id'], row['criterion_id'])]}",
                f"Judge rationale: {row.get('rationale', row.get('error_type', 'Missing judgment'))}",
                f"Trace: {row.get('trace_url', 'unavailable')}",
            ]
        )
    if not report["review_queue"]:
        lines.append("No mismatches in this run; broader validity is still unmeasured.")
    lines.extend(
        [
            "",
            "## Artifacts and limitations",
            "",
            ("human-review.html contains the blind source/candidate review packet. contracts.json "
            "contains the separate proposed expectations. rows.json contains every rationale, "
            "usage record and trace link. junit.xml preserves contract failures for regression "
            "testing. No external calendar or workspace was modified."),
            "",
            ("Only the targeted criterion is scored for each candidate. Correctness on that "
            "criterion does not imply the whole output is acceptable. Matched variants and "
            "repeats are correlated. Human references remain pending."),
        ]
    )
    markdown = "\n".join(lines) + "\n"
    with (folder / "RESULTS.md").open("x", encoding="utf-8") as handle:
        handle.write(markdown)
    with (folder / "results.html").open("x", encoding="utf-8") as handle:
        handle.write(
            '<!doctype html><html lang="en"><meta charset="utf-8"><title>Niche evaluation results</title>'
            "<style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:20px}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}</style><pre>"
            + html.escape(markdown)
            + "</pre></html>"
        )
    print(markdown[:2400])


if __name__ == "__main__":
    main()
