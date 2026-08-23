#!/usr/bin/env python3
"""Aggregate-only conceptual diagnosis of the private Mapping A v2 pilot.

The script validates a manually coded cause file against the already frozen
development/calibration diagnostic sample.  It never accepts locked-test rows,
changes labels, or fits a mapping model.  Row-level causes and task text remain
private; only counts and length diagnostics are release-safe.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import statistics
from collections.abc import Mapping

import pandas as pd


CAUSE_FLAGS = (
    "granularity_mismatch",
    "end_to_end_deliverable_vs_narrow_activity",
    "work_modality_mismatch",
    "wording_or_domain_false_friend",
    "occupation_context_mismatch",
    "one_to_many_decomposition_required",
    "many_to_one_aggregation_in_measurement",
    "capability_family_without_task_substitutability",
    "pair_level_retrieval_failure",
    "taxonomy_definition_too_strict",
    "other_structural_cause",
)
PRIMARY_CAUSES = frozenset({
    "capability_family_without_task_substitutability",
    "work_modality_mismatch",
    "wording_or_domain_false_friend",
    "other_structural_cause",
})
ALLOWED_SPLITS = frozenset({"development", "calibration"})
ALLOWED_LABELS = frozenset({"D", "F", "N", "U"})


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _words(value: object) -> int:
    return len(str(value or "").split())


def _quantiles(values: list[int]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty length diagnostic")
    return {
        "minimum": ordered[0],
        "median": statistics.median(ordered),
        "maximum": ordered[-1],
    }


def _read_packets(path: pathlib.Path) -> dict[int, Mapping[str, object]]:
    result: dict[int, Mapping[str, object]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            index = int(row["diagnostic_index"])
            if index in result:
                raise ValueError("duplicate diagnostic packet index")
            result[index] = row
    return result


def execute(args: argparse.Namespace) -> dict[str, object]:
    sample_path = args.sample.resolve()
    labels_path = args.labels.resolve()
    causes_path = args.causes.resolve()
    packets_path = args.packets.resolve()
    sample = pd.read_csv(sample_path, dtype=str).fillna("")
    labels = pd.read_csv(labels_path, dtype=str).fillna("")
    causes = pd.read_csv(causes_path, dtype=str).fillna("")
    packets = _read_packets(packets_path)

    if len(sample) != len(labels) or len(sample) != len(causes) or len(sample) != 60:
        raise ValueError("conceptual diagnosis requires the exact 60-pair diagnostic sample")
    if not set(sample["split"]) <= ALLOWED_SPLITS:
        raise ValueError("locked or unknown split in conceptual diagnosis")
    if set(sample["diagnostic_index"].astype(int)) != set(range(1, 61)):
        raise ValueError("diagnostic sample indices drifted")
    sample["diagnostic_index"] = sample["diagnostic_index"].astype(int)
    if set(packets) != set(range(1, 61)):
        raise ValueError("diagnostic packet indices drifted")

    required_label = {"diagnostic_index", "relation_label", "concise_rationale"}
    required_cause = {"diagnostic_index", "primary_cause", *CAUSE_FLAGS}
    if not required_label <= set(labels) or not required_cause <= set(causes):
        raise ValueError("label or cause schema incomplete")
    labels["diagnostic_index"] = labels["diagnostic_index"].astype(int)
    causes["diagnostic_index"] = causes["diagnostic_index"].astype(int)
    if labels["diagnostic_index"].duplicated().any() or causes["diagnostic_index"].duplicated().any():
        raise ValueError("diagnostic labels/causes must be one-to-one")
    labels["relation_label"] = labels["relation_label"].str.upper().str.strip()
    if set(labels["relation_label"]) - ALLOWED_LABELS:
        raise ValueError("unknown relation label")

    for field in CAUSE_FLAGS:
        if set(causes[field]) - {"0", "1"}:
            raise ValueError(f"cause flag must be binary: {field}")
        causes[field] = causes[field].astype(int)
    if not set(causes["primary_cause"]) <= PRIMARY_CAUSES:
        raise ValueError("unknown primary cause")
    for row in causes.to_dict("records"):
        if row[row["primary_cause"]] != 1:
            raise ValueError("primary cause must also be flagged")
        if sum(int(row[field]) for field in CAUSE_FLAGS) == 0:
            raise ValueError("every pair requires at least one structural cause")

    merged = sample.merge(labels, on="diagnostic_index", validate="one_to_one").merge(
        causes, on="diagnostic_index", validate="one_to_one"
    )
    if len(merged) != 60:
        raise ValueError("diagnostic join drift")
    # Rarity is never permitted to mutate the private relation labels.
    if collections.Counter(merged["relation_label"]) != {"N": 36, "F": 24}:
        raise ValueError("relation labels differ from the frozen preliminary diagnostic")

    onet_lengths: list[int] = []
    prompt_lengths: list[int] = []
    rubric_lengths: list[int] = []
    for index in range(1, 61):
        packet = packets[index]
        onet_lengths.append(_words(packet["onet_task"]["statement"]))
        prompt_lengths.append(_words(packet["gdpval_task"]["prompt"]))
        rubric_lengths.append(_words(packet["gdpval_task"]["rubric"]))

    flag_counts = {field: int(merged[field].sum()) for field in CAUSE_FLAGS}
    primary_counts = dict(sorted(collections.Counter(merged["primary_cause"]).items()))
    by_relation = {
        relation: {
            "pairs": int((merged["relation_label"] == relation).sum()),
            "flag_counts": {
                field: int(merged.loc[merged["relation_label"] == relation, field].sum())
                for field in CAUSE_FLAGS
            },
        }
        for relation in ("D", "F", "N", "U")
    }
    receipt = {
        "status": "V2_CONCEPTUAL_FAILURE_DIAGNOSED_DEVELOPMENT_MATERIAL_ONLY",
        "scope": "existing_60_pair_development_calibration_diagnostic",
        "pairs": 60,
        "relation_counts_unchanged": {"D": 0, "F": 24, "N": 36, "U": 0},
        "primary_cause_counts": primary_counts,
        "overlapping_structural_cause_counts": flag_counts,
        "cause_counts_by_relation": by_relation,
        "mechanical_unit_diagnostics_words": {
            "onet_task_statement": _quantiles(onet_lengths),
            "gdpval_prompt": _quantiles(prompt_lengths),
            "gdpval_scoring_rubric": _quantiles(rubric_lengths),
            "median_prompt_to_onet_statement_ratio": round(
                statistics.median(p / o for p, o in zip(prompt_lengths, onet_lengths)), 2
            ),
        },
        "interpretation_limits": {
            "counts_are_overlapping_except_primary": True,
            "formal_validation_performance_claimed": False,
            "taxonomy_or_label_changed": False,
            "locked_test_read": False,
            "production_mapping_selected": False,
        },
        "private_input_hashes": {
            "sample_sha256": sha256(sample_path),
            "packets_sha256": sha256(packets_path),
            "labels_sha256": sha256(labels_path),
            "cause_codes_sha256": sha256(causes_path),
        },
        "row_level_data_committed": False,
        "incremental_api_spend_usd": 0,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--sample", type=pathlib.Path, required=True)
    value.add_argument("--packets", type=pathlib.Path, required=True)
    value.add_argument("--labels", type=pathlib.Path, required=True)
    value.add_argument("--causes", type=pathlib.Path, required=True)
    value.add_argument("--output", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    print(json.dumps(execute(parser().parse_args()), indent=2, sort_keys=True))
