"""Build a local mentor-readable results document from measured pilot artifacts."""

import argparse
import html
import json
import statistics
from pathlib import Path

from transcription_eval.meta import Submission, compare, load_bundle
from transcription_eval.reporting import write_html


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def usage_summary(records):
    usages = [r["usage"] for r in records if r.get("usage")]
    inputs = sum(u["input_tokens"] for u in usages)
    outputs = sum(u["output_tokens"] for u in usages)
    cached = sum(u.get("input_tokens_details", {}).get("cached_tokens", 0) or 0 for u in usages)
    writes = sum(
        u.get("input_tokens_details", {}).get("cache_write_tokens", 0) or 0 for u in usages
    )
    return {
        "attempts": len(records),
        "successes": sum(r["status"] == "success" for r in records),
        "input_tokens": inputs,
        "output_tokens": outputs,
        "cached_tokens": cached,
        "cache_write_tokens": writes,
        "estimated_usd": (
            (inputs - cached - writes) * 0.1 + cached * 0.01 + writes * 0.125 + outputs * 0.5
        )
        / 1e6,
        "median_latency_ms": statistics.median(r["latency_ms"] for r in records),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pilot", type=Path)
    parser.add_argument("ablation", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    records = read(args.pilot / "calls.json")
    ablation_records = read(args.ablation / "calls.json")
    total = usage_summary(records + ablation_records)
    candidate = read(args.pilot / "transcript/candidate.json")
    judgment = Submission.model_validate_json(
        (args.pilot / "transcript-judgments/low-1.json").read_text()
    )
    bundle = load_bundle(args.pilot / "transcript/cases.jsonl", root / "data/meta/rubric_v2.json")
    # No human labels are invented. The report explicitly has no binary references.
    report = compare(bundle, [judgment], "discovery")
    with (args.pilot / "human-comparison-pending.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    write_html(report, args.pilot / "human-comparison-pending.html")
    lines = [
        "# GPT-6 Luna evaluator pilot results",
        "",
        (
            "Date: October 20, 2026. All calls used `gpt-6-luna`, Standard processing, "
            "no retries, and explicit output limits. These are discovery experiments."
        ),
        "",
        (
            f"**{total['successes']}/{total['attempts']} calls succeeded. Estimated total cost: "
            f"${total['estimated_usd']:.5f}.** This is calculated from returned token usage and "
            "published Standard rates including cache writes; it is not an invoice."
        ),
        "",
        f"Total input tokens: {total['input_tokens']:,}; output tokens: {total['output_tokens']:,}.",
        "",
        "## Real transcript extraction",
        "",
        ", ".join(f"{len(v)} {k.replace('_', ' ')}" for k, v in candidate.items()) + ".",
        "",
        (
            "The proposed seven-criterion judge marked coverage as fail and the other six "
            "criteria as pass. It identified omitted deliverables including the private GitHub "
            "repo, experiment log, learnings field guide, final blog and video demo. These "
            "are model judgments requiring human validation, not accepted ground truth."
        ),
        "",
        (
            "The Monday reschedule was withdrawn in the source meeting; the candidate retained "
            "the regular meeting and left unknown calendar timestamps null."
        ),
        "",
        "## Controlled challenges and repeats",
        "",
        (
            "One synthetic meeting, four outputs, three criteria, two repeats per reasoning setting. "
            "Tested unchanged IDs with changed task meaning, ID-only changes, and omitted tasks. "
            "Mutation expectations are proposed and have not been independently human validated."
        ),
        "",
        "| Reasoning | Binary judgments | Repeated-cell agreement | ID invariance | Targeted failure detection | Median judge latency |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for effort in ("none", "low"):
        stability = read(args.pilot / "analysis" / f"stability-{effort}.json")
        runs = [read(args.pilot / "analysis" / f"robustness-{effort}-{i}.json") for i in (1, 2)]
        inv = sum(r["summary"]["invariant"]["satisfied"] for r in runs)
        inv_n = sum(r["summary"]["invariant"]["total"] for r in runs)
        detected = sum(r["summary"]["detect_failure"]["satisfied"] for r in runs)
        detect_n = sum(r["summary"]["detect_failure"]["total"] for r in runs)
        calls = [
            r
            for r in records
            if r["label"].startswith("challenge-judgments/") and r["effort"] == effort
        ]
        lines.append(
            f"| {effort} | {len(calls)} | {stability['stable_cell_rate']:.1%} "
            f"| {inv}/{inv_n} | {detected}/{detect_n} "
            f"| {statistics.median(r['latency_ms'] for r in calls) / 1000:.2f}s |"
        )
    lines.extend(
        [
            "",
            (
                "The unstable cells concern `preserve_uncertainty`. On identical repeats, "
                "the judge sometimes penalized missing tasks or incorrect task meaning under "
                "this criterion, and sometimes treated those as coverage or grounding errors. "
                "This suggests a criterion-boundary problem worth human review."
            ),
            "",
            "## Post-hoc rubric scope ablation",
            "",
            (
                "A separate discovery rubric explicitly limits uncertainty grading to owner "
                "and deadline assertions that are present, permits empty outputs on this "
                "criterion alone, and assigns omissions to coverage. This is a post-hoc change "
                "on the same examples; it is not held-out validation. The ablation also uses "
                "a single-criterion rubric, so context changed along with wording."
            ),
            "",
        ]
    )
    for effort in ("none", "low"):
        s = read(args.ablation / "analysis" / f"stability-{effort}.json")
        lines.append(
            f"- {effort}: {s['stable_cell_rate']:.1%} stable cells; "
            f"{s['binary_pair_coverage']:.1%} binary pair coverage across four repeated cells."
        )
    lines.extend(
        [
            "",
            (
                "These sample sizes do not establish that one reasoning setting is generally "
                "better. Repeats and variants are correlated; there is only one synthetic "
                "challenge meeting and one real meeting."
            ),
            "",
            "## Human evaluation status",
            "",
            (
                "No human reference submissions have been collected. Human-agreement precision, "
                "recall and evaluator accuracy remain unavailable. Review the candidate using "
                "`transcript/review.html`, save independent exports under a submissions directory, "
                "and use `meeting-eval meta compare` after collecting references. Do not promote "
                "the judge labels to human labels."
            ),
            "",
            "## Traces",
            "",
        ]
    )
    for label in ("extract/transcript",):
        row = next(r for r in records if r["label"] == label)
        lines.append(f"- [Real transcript extraction]({row['trace_url']})")
    for title, rs in [("Transcript judge", records), ("Scope ablation", ablation_records)]:
        row = next(r for r in rs if not r["label"].startswith("extract/"))
        lines.append(f"- [{title} example]({row['trace_url']})")
    lines.extend(
        [
            "",
            (
                "All per-call trace links, latencies, model settings and usage are retained "
                "in each run folder’s `calls.json`. Input transcripts and annotations remain "
                "in ignored local artifacts. Langfuse receives the traced input/output."
            ),
            "",
            "Pricing reference: https://developers.openai.com/api/docs/models/gpt-6-luna",
            "",
        ]
    )
    markdown = "\n".join(lines)
    with (args.pilot / "RESULTS.md").open("x", encoding="utf-8") as handle:
        handle.write(markdown)
    with (args.pilot / "results.html").open("x", encoding="utf-8") as handle:
        handle.write(
            '<!doctype html><html lang="en"><meta charset="utf-8"><title>Luna pilot results</title>'
            "<style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:20px}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65}</style><pre>"
            + html.escape(markdown)
            + "</pre></html>"
        )
    with (args.pilot / "combined-usage.json").open("x", encoding="utf-8") as handle:
        json.dump(total, handle, indent=2)
    print(json.dumps(total))


if __name__ == "__main__":
    main()
