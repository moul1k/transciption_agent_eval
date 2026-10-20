"""Controlled output transformations, with proposed expectations kept outside blind cases.

Mutation intent is not a human label. Consumers must review challenge validity before
using these expectations as evidence about semantic quality.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Literal

from pydantic import Field

from .meta import Submission, digest, validate_submission
from .schemas import StrictModel


class Relation(StrictModel):
    base_id: str
    variant_id: str
    criterion_id: str
    behavior: Literal["invariant", "detect_failure"]
    transformation: str
    review_note: str


class ChallengeManifest(StrictModel):
    schema_version: Literal["1"] = "1"
    dataset_hash: str
    rubric_hash: str
    expectations_status: Literal["proposed_not_human_validated"] = "proposed_not_human_validated"
    relations: list[Relation] = Field(min_length=1)


def generate(bundle: dict, case_id: str) -> tuple[dict, ChallengeManifest]:
    seeds = [c for c in bundle["cases"] if c["id"] == case_id]
    if not seeds:
        raise ValueError("unknown seed case")
    base = deepcopy(seeds[0])
    cases, relations = [base], []
    criteria = {r["id"] for r in bundle["rubric"]["criteria"]}

    def add(variant, transformation, criterion_ids, behavior, note):
        # Opaque stable IDs keep transformation names out of blind review material.
        variant["id"] = digest({"base": base["id"], "transformation": transformation})[:24]
        cases.append(variant)
        for criterion_id in sorted(set(criterion_ids) & criteria):
            relations.append(
                Relation(
                    base_id=base["id"],
                    variant_id=variant["id"],
                    criterion_id=criterion_id,
                    behavior=behavior,
                    transformation=transformation,
                    review_note=note,
                )
            )

    fields = ("action_items", "calendar_events", "decisions", "follow_ups")
    if any(base["output"][field] for field in fields):
        variant = deepcopy(base)
        for field in fields:
            for i, item in enumerate(variant["output"][field]):
                item["id"] = f"opaque-{field}-{i}"
        add(
            variant,
            "rename_object_ids",
            criteria,
            "invariant",
            "Assumes the rubric does not prescribe object identifiers.",
        )
    if any(len(base["output"][field]) > 1 for field in fields):
        variant = deepcopy(base)
        for field in fields:
            variant["output"][field].reverse()
        add(
            variant,
            "reverse_object_order",
            criteria,
            "invariant",
            "Review whether ordering carries meaning for this rubric.",
        )
    actions = base["output"]["action_items"]
    if actions:
        # An arbitrary replacement is intentionally only a candidate negative;
        # it must be inspected against the complete transcript.
        if "grounded_action" in criteria:
            variant = deepcopy(base)
            variant["output"]["action_items"][0]["task"] = "Delete all customer records"
            if variant["output"] != base["output"]:
                add(
                    variant,
                    "replace_task_preserve_id",
                    ["grounded_action"],
                    "detect_failure",
                    "Confirm replacement is unsupported and the base task is valid.",
                )
        if "coverage" in criteria:
            variant = deepcopy(base)
            variant["output"]["action_items"].pop(0)
            add(
                variant,
                "omit_first_action",
                ["coverage"],
                "detect_failure",
                "Confirm omitted task is required and not duplicated elsewhere.",
            )
        if "preserve_uncertainty" in criteria and actions[0]["owner"] is None:
            variant = deepcopy(base)
            variant["output"]["action_items"][0]["owner"] = "Unmentioned Assignee"
            add(
                variant,
                "invent_owner",
                ["preserve_uncertainty"],
                "detect_failure",
                "Confirm no evidence assigns this owner, and base preserves uncertainty.",
            )
    if not relations:
        raise ValueError("seed has no applicable transformations for this rubric")
    result = dict(bundle, cases=cases, dataset_hash=digest(cases))
    manifest = ChallengeManifest(
        dataset_hash=result["dataset_hash"], rubric_hash=result["rubric_hash"], relations=relations
    )
    return result, manifest


def analyze(bundle: dict, manifest: ChallengeManifest, submission: Submission) -> dict:
    validate_submission(submission, bundle)
    if submission.kind != "judge":
        raise ValueError("robustness analysis requires a judge submission")
    if (
        manifest.dataset_hash != bundle["dataset_hash"]
        or manifest.rubric_hash != bundle["rubric_hash"]
    ):
        raise ValueError("challenge manifest provenance mismatch")
    cases = {c["id"]: c for c in bundle["cases"]}
    criteria = {r["id"] for r in bundle["rubric"]["criteria"]}
    predictions = {(j.case_id, j.criterion_id): j.verdict for j in submission.judgments}
    details = []
    for relation in manifest.relations:
        if (
            relation.base_id not in cases
            or relation.variant_id not in cases
            or relation.criterion_id not in criteria
        ):
            raise ValueError("challenge relation refers to an unknown case or criterion")
        if cases[relation.base_id]["meeting_id"] != cases[relation.variant_id]["meeting_id"]:
            raise ValueError("challenge pair must belong to the same meeting")
        left = predictions.get((relation.base_id, relation.criterion_id))
        right = predictions.get((relation.variant_id, relation.criterion_id))
        if left not in ("pass", "fail") or right not in ("pass", "fail"):
            status = "unanswered"
        elif relation.behavior == "invariant":
            status = "satisfied" if left == right else "violated"
        elif left != "pass":
            status = "base_not_passed"
        else:
            status = "satisfied" if right == "fail" else "violated"
        details.append(
            {
                **relation.model_dump(),
                "base_verdict": left,
                "variant_verdict": right,
                "status": status,
            }
        )
    groups = {}
    for behavior in ("invariant", "detect_failure"):
        rows = [r for r in details if r["behavior"] == behavior]
        counts = {
            s: sum(r["status"] == s for r in rows)
            for s in ("satisfied", "violated", "unanswered", "base_not_passed")
        }
        evaluated = counts["satisfied"] + counts["violated"]
        groups[behavior] = dict(
            **counts,
            total=len(rows),
            answered_relation_rate=evaluated / len(rows) if rows else None,
            satisfaction_rate=counts["satisfied"] / evaluated if evaluated else None,
        )
    return {
        "schema_version": "1",
        "evaluator_id": submission.evaluator_id,
        "dataset_hash": bundle["dataset_hash"],
        "rubric_hash": bundle["rubric_hash"],
        "expectations_status": manifest.expectations_status,
        "limitation": "Proposed synthetic relations, not human-validated evaluator accuracy. "
        "Invariance alone does not establish correctness.",
        "summary": groups,
        "relations": details,
    }
