#!/usr/bin/env python3
"""Freeze and evaluate the private DAX v3 S1 construct-validity pilot.

The runner never calls a model or reads DAX outcomes. Row-level O*NET task IDs,
text, constructed instances, and judgments stay in the private directory. Git
receives only aggregate receipts and code.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import pathlib
import re
from collections.abc import Iterable, Mapping

import pandas as pd


RECOMMENDATIONS = {
    "PROCEED_TO_S3_DESIGN",
    "REVISE_V3_PROTOCOL",
    "PARTIAL_IDENTIFICATION_ONLY",
    "NOT_YET_EVALUABLE",
}
FIDELITY = {"pass", "revise", "fail", "not_applicable"}
RISK = {"low", "medium", "high", "not_applicable"}
INSTANCE_FIELDS = (
    "occupational_activity",
    "minimum_context",
    "required_inputs",
    "input_provenance_method",
    "allowed_tools",
    "expected_work_product",
    "completion_criterion",
    "scoring_method",
    "failure_criterion",
    "human_review_requirement",
    "construction_assumptions",
)
AUDIT_FIELDS = (
    "task_boundary_fidelity",
    "work_product_fidelity",
    "domain_context_fidelity",
    "tool_input_fidelity",
    "difficulty_distortion",
    "added_task_content_risk",
    "omitted_essential_content_risk",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable(seed: str, purpose: str, value: str) -> str:
    return hashlib.sha256(f"{seed}|{purpose}|{value}".encode()).hexdigest()


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z]+", value.casefold()))


def prestratum(statement: str, spec: Mapping[str, object]) -> str:
    tokens = _tokens(statement)
    rules = spec["mechanical_prestrata"]
    for name, key in (
        ("physical_manual", "physical_tokens"),
        ("interpersonal_service", "interpersonal_tokens"),
        ("document_data", "document_data_tokens"),
    ):
        if tokens.intersection(rules[key]):
            return name
    return "other"


def _write_csv(path: pathlib.Path, rows: list[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError("refuse empty private CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def _frame(args: argparse.Namespace, spec: Mapping[str, object]) -> pd.DataFrame:
    onet = pd.read_csv(args.onet_timeshares, dtype=str).fillna("")
    wage = pd.read_csv(args.task_wage_allocations, dtype=str).fillna("")
    onet = onet[onet["primary_usable"].str.casefold().eq("true")].copy()
    wage = wage[
        wage["vintage"].eq("2021")
        & wage["allocation_usable"].str.casefold().eq("true")
    ].copy()
    wage = wage[["onet_soc", "task_id", "task_annual_wage_bill_allocation"]]
    frame = onet.merge(wage, on=["onet_soc", "task_id"], validate="one_to_one")
    if len(frame) != spec["sample_provenance"]["frame_expected_unique_tasks"]:
        raise ValueError("authorized S1 frame count drift")
    if frame["task_id"].duplicated().any():
        raise ValueError("S1 frame task IDs must be unique")
    frame["major_family"] = frame["onet_soc"].str[:2]
    if frame["major_family"].nunique() != spec["sample_provenance"]["major_family_expected_count"]:
        raise ValueError("major-family count drift")
    frame["task_mass"] = pd.to_numeric(
        frame["task_annual_wage_bill_allocation"], errors="raise"
    )
    if (~frame["task_mass"].map(math.isfinite) | (frame["task_mass"] < 0)).any():
        raise ValueError("invalid task mass")
    frame["mechanical_modality"] = [
        prestratum(value, spec) for value in frame["task_statement"]
    ]
    frame["sampling_stratum"] = (
        frame["task_type"].str.casefold() + "|" + frame["mechanical_modality"]
    )
    return frame


def _family_draw(pool: pd.DataFrame, quota: int, seed: str) -> pd.DataFrame:
    groups: dict[str, list[int]] = {}
    for stratum, rows in pool.groupby("sampling_stratum", sort=True):
        groups[stratum] = sorted(
            rows.index,
            key=lambda index: _stable(seed, "task", str(pool.loc[index, "task_id"])),
        )
    stratum_order = sorted(groups, key=lambda value: _stable(seed, "stratum", value))
    selected: list[int] = []
    cursor = 0
    while len(selected) < quota:
        available = [value for value in stratum_order if groups[value]]
        if not available:
            raise ValueError("family pool exhausted before quota")
        stratum = available[cursor % len(available)]
        selected.append(groups[stratum].pop(0))
        cursor += 1
    return pool.loc[selected].copy()


def draw(args: argparse.Namespace) -> dict[str, object]:
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if spec["status"] != "FROZEN_BEFORE_S1_TASK_TEXT_INSPECTION":
        raise ValueError("S1 protocol is not frozen")
    seed = spec["sample_provenance"]["seed"]
    frame = _frame(args, spec)
    families = sorted(frame["major_family"].unique())
    extra_n = spec["sample_provenance"]["extra_task_family_count"]
    extra_families = set(
        sorted(families, key=lambda value: _stable(seed, "extra-family", value))[:extra_n]
    )
    pieces = []
    for family in families:
        quota = spec["sample_provenance"]["base_tasks_per_family"] + (
            1 if family in extra_families else 0
        )
        pieces.append(_family_draw(frame[frame["major_family"].eq(family)], quota, seed))
    selected = pd.concat(pieces, ignore_index=True)
    if len(selected) != spec["sample_provenance"]["sample_size"]:
        raise ValueError("S1 sample-size drift")
    selected = selected.sort_values(
        "task_id", key=lambda values: values.map(lambda value: _stable(seed, "packet", value))
    ).reset_index(drop=True)
    selected["pilot_index"] = selected.index + 1
    pool_counts = frame.groupby(["major_family", "sampling_stratum"]).size().to_dict()
    selected_counts = selected.groupby(["major_family", "sampling_stratum"]).size().to_dict()

    rows: list[dict[str, object]] = []
    for row in selected.to_dict("records"):
        key = (row["major_family"], row["sampling_stratum"])
        rows.append({
            "pilot_index": int(row["pilot_index"]),
            "onet_task_id": row["task_id"],
            "onet_soc": row["onet_soc"],
            "major_family": row["major_family"],
            "task_type": row["task_type"],
            "mechanical_modality": row["mechanical_modality"],
            "sampling_stratum": row["sampling_stratum"],
            "stratum_selected": selected_counts[key],
            "stratum_pool": pool_counts[key],
            "stratum_sampling_fraction": selected_counts[key] / pool_counts[key],
            "task_statement": row["task_statement"],
            "task_mass": float(row["task_mass"]),
        })

    private_dir = args.private_dir.resolve()
    private_dir.mkdir(parents=True, exist_ok=True)
    private_dir.chmod(0o700)
    sample_path = private_dir / "s1_sample_120.csv"
    template_path = private_dir / "s1_construct_annotations_template.csv"
    _write_csv(sample_path, rows)
    template_fields = [
        "pilot_index", "evaluable_class", *INSTANCE_FIELDS, "scoring_class",
        *AUDIT_FIELDS, "construct_status", "main_failure_mode",
        "required_environment", "historical_snapshot_compatibility",
        "expert_review_family", "concise_rationale",
    ]
    _write_csv(template_path, [
        {key: (row["pilot_index"] if key == "pilot_index" else "") for key in template_fields}
        for row in rows
    ])
    receipt = {
        "status": "S1_FIRST_DETERMINISTIC_DRAW_FROZEN_ANNOTATION_PENDING",
        "provenance_disclosure": "NO_PRIOR_PERSISTED_120_TASK_DRAW_FOUND_FIRST_REALIZATION_NOT_REDRAW",
        "seed": seed,
        "frame_tasks": len(frame),
        "sample_tasks": len(rows),
        "major_families": len(families),
        "family_sample_counts": dict(sorted(collections.Counter(row["major_family"] for row in rows).items())),
        "task_type_counts": dict(sorted(collections.Counter(row["task_type"] for row in rows).items())),
        "mechanical_prestratum_counts": dict(sorted(collections.Counter(row["mechanical_modality"] for row in rows).items())),
        "private_input_hashes": {
            "onet_timeshares_sha256": sha256(args.onet_timeshares),
            "task_wage_allocations_sha256": sha256(args.task_wage_allocations),
            "spec_sha256": sha256(args.spec),
        },
        "private_output_hashes": {
            sample_path.name: sha256(sample_path),
            template_path.name: sha256(template_path),
        },
        "selected_task_text_inspected_before_draw": False,
        "task_replacement_count": 0,
        "row_level_data_committed": False,
        "model_or_api_calls": 0,
        "realized_spend_usd": 0,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _weighted_share(rows: pd.DataFrame, column: str, value: str, weight: str) -> float:
    total = rows[weight].sum()
    return 0.0 if not total else float(rows.loc[rows[column].eq(value), weight].sum() / total)


def _family_share(rows: pd.DataFrame, column: str, value: str) -> float:
    shares = rows.groupby("major_family")[column].apply(
        lambda values: float(values.eq(value).mean())
    )
    return float(shares.mean())


def evaluate(args: argparse.Namespace) -> dict[str, object]:
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    sample = pd.read_csv(args.private_dir / "s1_sample_120.csv", dtype=str).fillna("")
    annotations = pd.read_csv(args.annotations, dtype=str).fillna("")
    if len(sample) != 120 or len(annotations) != 120:
        raise ValueError("S1 evaluation requires exactly 120 rows")
    if annotations["pilot_index"].duplicated().any():
        raise ValueError("duplicate S1 annotation")
    merged = sample.merge(annotations, on="pilot_index", validate="one_to_one")
    if len(merged) != 120:
        raise ValueError("S1 annotations do not cover frozen sample")
    classes = set(spec["evaluable_classes"])
    scores = set(spec["scoring_classes"])
    statuses = set(spec["construct_statuses"])
    if set(merged["evaluable_class"]) - classes:
        raise ValueError("unknown evaluability class")
    if set(merged["scoring_class"]) - scores:
        raise ValueError("unknown scoring class")
    if set(merged["construct_status"]) - statuses:
        raise ValueError("unknown construct status")
    evaluable = set(spec["evaluable_classes"][:3])
    for row in merged.to_dict("records"):
        is_evaluable = row["evaluable_class"] in evaluable
        if is_evaluable and any(not str(row[key]).strip() for key in INSTANCE_FIELDS):
            raise ValueError("benchmarkable row missing constructed instance field")
        if not is_evaluable:
            if row["construct_status"] != "NON_EVALUABLE":
                raise ValueError("non-evaluable class must remain NON_EVALUABLE")
            if row["scoring_class"] != "not_currently_scoreable":
                raise ValueError("non-evaluable class cannot claim scoring")
            if any(str(row[key]).strip() for key in INSTANCE_FIELDS):
                raise ValueError("non-evaluable row cannot contain substitute instance")
        if is_evaluable and row["construct_status"] == "NON_EVALUABLE":
            raise ValueError("evaluable class/status contradiction")
        if row["task_boundary_fidelity"] not in FIDELITY or row["work_product_fidelity"] not in FIDELITY:
            raise ValueError("invalid fidelity audit")
        if row["domain_context_fidelity"] not in FIDELITY or row["tool_input_fidelity"] not in FIDELITY:
            raise ValueError("invalid fidelity audit")
        for key in AUDIT_FIELDS[4:]:
            if row[key] not in RISK:
                raise ValueError("invalid risk audit")
        if row["construct_status"] == "PASS":
            if any(row[key] != "pass" for key in AUDIT_FIELDS[:4]):
                raise ValueError("PASS violates fidelity rule")
            if any(row[key] != "low" for key in AUDIT_FIELDS[4:]):
                raise ValueError("PASS violates risk rule")
        if not row["concise_rationale"].strip() or not row["main_failure_mode"].strip():
            raise ValueError("every audit needs rationale and failure-mode field")

    merged["task_mass"] = pd.to_numeric(merged["task_mass"], errors="raise")
    class_counts = collections.Counter(merged["evaluable_class"])
    status_counts = collections.Counter(merged["construct_status"])
    scoring_counts = collections.Counter(merged["scoring_class"])
    class_mass = {
        value: _weighted_share(merged, "evaluable_class", value, "task_mass")
        for value in spec["evaluable_classes"]
    }
    status_mass = {
        value: _weighted_share(merged, "construct_status", value, "task_mass")
        for value in spec["construct_statuses"]
    }
    status_family = {
        value: _family_share(merged, "construct_status", value)
        for value in spec["construct_statuses"]
    }
    pass_rows = merged[merged["construct_status"].eq("PASS")]
    no_human_mass_conditional = _weighted_share(
        pass_rows, "scoring_class", "fully_objective_mechanical", "task_mass"
    ) if len(pass_rows) else 0.0
    no_human_mass_unconditional = float(
        merged.loc[
            merged["construct_status"].eq("PASS")
            & merged["scoring_class"].eq("fully_objective_mechanical"),
            "task_mass",
        ].sum() / merged["task_mass"].sum()
    ) if merged["task_mass"].sum() else 0.0
    calls_per_model = len(pass_rows) * 2 * 3
    initial_rows = 16
    total_calls = calls_per_model * initial_rows
    private_result = args.private_dir / "s1_constructed_items_and_audit.csv"
    # Opening with newline="" pins the line ending to "\n" on every platform
    # without the `lineterminator` keyword, which pandas only gained in 1.5
    # (it was `line_terminator` before). The SCC carries an older pandas than
    # CI installs, and this call is on the path the S1 second-annotator run
    # has to take -- a crash here would block the replication rather than a
    # test. Behaviour is unchanged on the version CI uses.
    with open(private_result, "w", newline="", encoding="utf-8") as handle:
        merged.to_csv(handle, index=False)
    private_result.chmod(0o600)
    receipt = {
        "status": "S1_CONSTRUCT_VALIDITY_PILOT_COMPLETE_THRESHOLD_UNSIGNED",
        "sample_tasks": 120,
        "evaluable_class_counts": {value: class_counts[value] for value in spec["evaluable_classes"]},
        "non_evaluable_total": sum(class_counts[value] for value in spec["evaluable_classes"][3:]),
        "construct_status_counts": {value: status_counts[value] for value in spec["construct_statuses"]},
        "scoring_class_counts": {value: scoring_counts[value] for value in spec["scoring_classes"]},
        "task_mass_weighted_evaluable_class_shares_within_pilot": class_mass,
        "task_mass_weighted_construct_status_shares_within_pilot": status_mass,
        "equal_family_weighted_construct_status_shares": status_family,
        "families_with_at_least_one_pass": int(pass_rows["major_family"].nunique()),
        "major_families": int(merged["major_family"].nunique()),
        "pilot_task_mass_share_pass_and_without_human_judging": no_human_mass_unconditional,
        "pass_task_mass_share_without_human_judging_conditional_on_pass_mass": no_human_mass_conditional,
        "main_failure_mode_counts": dict(sorted(collections.Counter(merged["main_failure_mode"]).items())),
        "expert_review_family_counts": dict(sorted(collections.Counter(
            value for value in merged["expert_review_family"] if value.strip()
        ).items())),
        "historical_capture_readiness": {
            "passing_items": len(pass_rows),
            "planning_calls_per_model_vintage": calls_per_model,
            "planning_calls_across_16_conditional_registry_rows": total_calls,
            "illustrative_direct_api_cost_sensitivity_usd": [
                round(total_calls * 0.00135, 2), round(total_calls * 0.21, 2)
            ],
            "required_environment_counts": dict(sorted(collections.Counter(
                pass_rows["required_environment"]
            ).items())),
            "snapshot_compatibility_counts": dict(sorted(collections.Counter(
                pass_rows["historical_snapshot_compatibility"]
            ).items())),
            "paid_calls_made": 0,
        },
        "threshold": None,
        "threshold_status": "NEED_PROSPECTIVE_PI_THRESHOLD_SIGNATURE",
        "formal_s1_gate_result": "UNRESOLVED",
        "recommendation": args.recommendation,
        "recommendation_is_not_threshold_signature": True,
        "audit_limit": "PRELIMINARY_SINGLE_CODEX_NOT_INDEPENDENT_DOMAIN_EXPERT_VALIDATION",
        "weight_limit": "PILOT_DESCRIPTIVE_NOT_DESIGN_WEIGHTED_POPULATION_ESTIMATE",
        "private_lineage": {
            "sample_sha256": sha256(args.private_dir / "s1_sample_120.csv"),
            "annotations_sha256": sha256(args.annotations),
            "constructed_audit_sha256": sha256(private_result),
        },
        "row_level_data_committed": False,
        "model_or_api_calls": 0,
        "outcomes_opened": False,
        "realized_spend_usd": 0,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)
    draw_parser = commands.add_parser("draw")
    draw_parser.add_argument("--spec", type=pathlib.Path, required=True)
    draw_parser.add_argument("--onet-timeshares", type=pathlib.Path, required=True)
    draw_parser.add_argument("--task-wage-allocations", type=pathlib.Path, required=True)
    draw_parser.add_argument("--private-dir", type=pathlib.Path, required=True)
    draw_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    evaluate_parser = commands.add_parser("evaluate")
    evaluate_parser.add_argument("--spec", type=pathlib.Path, required=True)
    evaluate_parser.add_argument("--private-dir", type=pathlib.Path, required=True)
    evaluate_parser.add_argument("--annotations", type=pathlib.Path, required=True)
    evaluate_parser.add_argument("--recommendation", choices=sorted(RECOMMENDATIONS), required=True)
    evaluate_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    return result


if __name__ == "__main__":
    args = parser().parse_args()
    output = draw(args) if args.command == "draw" else evaluate(args)
    print(json.dumps(output, indent=2, sort_keys=True))
