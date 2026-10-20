"""Contract scoring, risk/coverage reporting and CI exports independent of any provider."""

import math
from xml.etree import ElementTree as ET


def wilson(successes: int, total: int):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return {
        "lower": max(0, center - half),
        "upper": min(1, center + half),
        "method": "Wilson 95%; descriptive only when examples/repeats are correlated",
    }


def score_rows(rows: list[dict]) -> dict:
    """Missing judgments count in denominators; abstention is correct only if expected."""
    groups = {}
    for group in sorted({r["condition"] for r in rows}):
        subset = [r for r in rows if r["condition"] == group]
        successes = sum(r.get("verdict") == r["expected"] for r in subset)
        missing = sum(r.get("verdict") is None for r in subset)
        tp = sum(r["expected"] == "fail" and r.get("verdict") == "fail" for r in subset)
        fp = sum(r["expected"] == "pass" and r.get("verdict") == "fail" for r in subset)
        failures = sum(r["expected"] == "fail" for r in subset)
        agreements = {}
        for r in subset:
            agreements.setdefault((r["case_id"], r["criterion_id"]), []).append(r.get("verdict"))
        repeated = [v for v in agreements.values() if len(v) > 1]

        def divide(a, b):
            return a / b if b else None

        groups[group] = {
            "cells": len(subset),
            "correct_contract_verdicts": successes,
            "contract_match_rate": divide(successes, len(subset)),
            "missing": missing,
            "insufficient_context": sum(r.get("verdict") == "insufficient_context" for r in subset),
            "binary_coverage": divide(
                sum(r.get("verdict") in ("pass", "fail") for r in subset), len(subset)
            ),
            "failure_precision": divide(tp, tp + fp),
            "failure_detection_rate": divide(tp, failures),
            "false_acceptances": sum(
                r["expected"] == "fail" and r.get("verdict") == "pass" for r in subset
            ),
            "false_rejections": fp,
            "repeat_cell_count": len(repeated),
            "complete_repeat_agreement": divide(
                sum(all(x is not None for x in v) and len(set(v)) == 1 for v in repeated),
                len(repeated),
            ),
            "contract_match_ci95": wilson(successes, len(subset)),
        }
    return {
        "reference_type": "authored_synthetic_contracts_not_human_consensus",
        "human_reference_status": "pending",
        "groups": groups,
        "review_queue": [r for r in rows if r.get("verdict") != r["expected"]],
    }


def export_junit(rows: list[dict], path):
    suite = ET.Element(
        "testsuite",
        name="authored-evaluator-contracts",
        tests=str(len(rows)),
        failures=str(sum(r.get("verdict") != r["expected"] for r in rows)),
    )
    for row in rows:
        case = ET.SubElement(
            suite,
            "testcase",
            classname=row["condition"],
            name=f"{row['case_id']}/{row['criterion_id']}/repeat-{row['repeat']}",
        )
        if row.get("verdict") != row["expected"]:
            failure = ET.SubElement(
                case, "failure", message=f"expected={row['expected']}; actual={row.get('verdict')}"
            )
            failure.text = row.get("rationale", "Missing judgment")
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def gate(report: dict, minimum_match=0.95, maximum_false_acceptances=0):
    """Return failures explicitly; observed point thresholds aren't statistical guarantees."""
    failures = []
    if report.get("reference_type") != "authored_synthetic_contracts_not_human_consensus":
        return ["Expected an authored-contract audit report; refuse to gate another report type"]
    if not report["groups"]:
        return ["No scored groups"]
    for name, group in report["groups"].items():
        if group["contract_match_rate"] is None or group["contract_match_rate"] < minimum_match:
            failures.append(f"{name}: contract match below {minimum_match}")
        if group["false_acceptances"] > maximum_false_acceptances:
            failures.append(f"{name}: too many false acceptances")
    return failures
