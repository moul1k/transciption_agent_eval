"""Render measured audit results without converting authored contracts to human labels."""

import argparse
import html
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    folder = args.run_dir
    report = json.loads((folder / "report.json").read_text())
    rows = json.loads((folder / "rows.json").read_text())
    usage = report["usage"]
    lines = [
        "# Developer evaluator audit results",
        "",
        (f"{usage['successes']}/{usage['calls']} calls returned valid judgments. "
        f"Estimated token-based Standard cost: ${usage['estimated_usd']:.5f}."),
        "",
        ("All calls used GPT-6 Luna, low reasoning, a 1,000-output-token cap, no retries, "
        "and Langfuse tracing. Expectations were frozen authored synthetic contracts, "
        "not independent human labels. Models did not receive the contracts."),
        "",
        "| Condition | Contract matches | Repeat agreement | False acceptances | Binary coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, g in report["groups"].items():
        stability = (
            f"{g['complete_repeat_agreement']:.1%}"
            if g["complete_repeat_agreement"] is not None
            else "unavailable"
        )
        lines.append(
            f"| {name} | {g['correct_contract_verdicts']}/{g['cells']} "
            f"({g['contract_match_rate']:.1%}) | {stability} | {g['false_acceptances']} "
            f"| {g['binary_coverage']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Interpreting the conditions",
            "",
            ("Scope compares legacy versus tightly scoped wording on six new template-derived "
            "scenarios, each with three candidate variants. The target contract treats omissions "
            "as coverage failures rather than owner/deadline assertion failures."),
            "",
            ("Tool-full compares judgments with observable final state. Tool-output-only withholds "
            "state and trace and expects insufficient_context. Its abstentions are desirable; "
            "its score is not accuracy about an unobserved state."),
            "",
            ("Injection compares control and attacked candidates. The attack text tries to order "
            "the judge to pass a task that contradicts the source. Both conditions should fail."),
            "",
            "## Review priorities",
            "",
        ]
    )
    for row in report["review_queue"]:
        lines.append(
            f"- {row['condition']}, {row['category']}, repeat {row['repeat']}: "
            f"expected {row['expected']}; returned {row.get('verdict')}. "
            f"{row.get('rationale', row.get('error_type', 'Missing judgment'))}"
        )
    if not report["review_queue"]:
        lines.append(
            "No mismatches against these authored contracts. This does not establish human validity."
        )
    lines.extend(
        [
            "",
            "## Limits and next study",
            "",
            ("The suite has 14 synthetic scenario groups and repeated/template-derived variants. "
            "These are not independent real-world observations. Neither statistical superiority "
            "nor broad injection resistance is established. Only four scenarios sharing one attack template "
            "and a narrow local event-creation contract were exercised. No real external tools "
            "were executed. Independent human annotations are still pending."),
            "",
            ("Collect human judgments using human-review.html; inspect all mismatches and a "
            "random set of matches. Then test the frozen chosen rubric on independently "
            "collected meetings and real execution traces."),
            "",
            "## Artifacts",
            "",
            "- report.json: metrics and mismatch queue.",
            "- rows.json: every verdict, rationale, usage and trace link.",
            "- conditions/: exact rubric/evidence snapshots and portable judge submissions.",
            "- junit.xml: authored-contract regression results for CI.",
            "- plan.json: frozen settings and source-code provenance.",
            "",
            "## Example traces",
            "",
        ]
    )
    for condition in sorted(report["groups"]):
        sample = next((r for r in rows if r["condition"] == condition and r.get("trace_url")), None)
        if sample:
            lines.append(f"- [{condition}]({sample['trace_url']})")
    markdown = "\n".join(lines) + "\n"
    with (folder / "RESULTS.md").open("x", encoding="utf-8") as handle:
        handle.write(markdown)
    summary_table = (
        "<table><tr><th>Condition</th><th>Contract match</th><th>Repeat agreement</th></tr>"
    )
    for name, g in report["groups"].items():
        summary_table += f"<tr><td>{html.escape(name)}</td><td>{g['contract_match_rate']:.1%}</td><td>{g['complete_repeat_agreement']:.1%}</td></tr>"
    with (folder / "results.html").open("x", encoding="utf-8") as handle:
        handle.write(
            '<!doctype html><html lang="en"><meta charset="utf-8"><title>Developer evaluator audit</title>'
            "<style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:20px}"
            "td,th{padding:12px;border:1px solid #ddd;text-align:left}table{border-collapse:collapse}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}</style>"
            "<h1>Developer evaluator audit</h1><p>Authored synthetic contracts. Human validation pending.</p>"
            + summary_table
            + "</table><pre>"
            + html.escape(markdown)
            + "</pre></html>"
        )
    print(markdown[:2400])


if __name__ == "__main__":
    main()
