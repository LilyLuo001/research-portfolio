#!/usr/bin/env python3
"""Build a deterministic blind human-review pack from a canonical frame.

Raw text, key mappings, and model predictions are written only to the caller's
private output directory. The public receipt contains aggregate counts only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path


SEED = "20261003"
FRAME_FIELDS = {
    "private_key", "original_text", "sampling_stratum",
    "first_observation_stratum", "occupation_availability_stratum",
    "challenge_eligible", "challenge_stratum",
}
PREDICTION_PROHIBITED_IN_FRAME = {
    "extractor_prediction", "extractor_evidence_span", "model_judgment",
    "aggregate_result",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_rank(phase: str, private_key: str) -> str:
    return hashlib.sha256(f"{SEED}|{phase}|{private_key}".encode()).hexdigest()


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def allocate_proportional(sizes: dict[str, int], total: int) -> dict[str, int]:
    active = {key: value for key, value in sizes.items() if value > 0}
    if not active or total <= 0:
        return {key: 0 for key in active}
    total = min(total, sum(active.values()))
    if len(active) > total:
        raise ValueError(
            f"{len(active)} nonempty strata exceed sample slots {total}; "
            "freeze a coarser sampling_stratum before running"
        )
    allocation = {key: 1 for key in active}
    remaining = total - len(active)
    capacity_weight = sum(active.values())
    quotas = {key: remaining * active[key] / capacity_weight for key in active}
    for key in active:
        allocation[key] += min(active[key] - 1, math.floor(quotas[key]))
    left = total - sum(allocation.values())
    order = sorted(
        active,
        key=lambda key: (-(quotas[key] - math.floor(quotas[key])), stable_rank("allocation", key)),
    )
    while left:
        progressed = False
        for key in order:
            if allocation[key] < active[key] and left:
                allocation[key] += 1
                left -= 1
                progressed = True
        if not progressed:
            raise RuntimeError("allocation capacity exhausted")
    return allocation


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or ())


def read_metadata(path: Path, label: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} metadata must be a JSON object")
    for field in ("key_namespace", "stable_key_type", "source_provenance"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"{label} metadata requires nonblank string {field}")
    if payload["stable_key_type"] != "string":
        raise ValueError(f"{label} stable_key_type must be string")
    return payload


def read_exclusion_keys(path: Path) -> tuple[set[str], dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("private_keys"), list):
        raise ValueError("heldout manifest must be a JSON object containing private_keys")
    metadata = read_metadata(path, "heldout")
    values = payload["private_keys"]
    if not values or any(not isinstance(value, str) or not value for value in values):
        raise ValueError("heldout private_keys must be a nonempty list of nonblank strings")
    if len(set(values)) != len(values):
        raise ValueError("heldout private_keys must be unique")
    return set(values), metadata


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", type=Path, required=True)
    parser.add_argument("--frame-metadata", type=Path, required=True)
    parser.add_argument("--heldout-key-manifest", type=Path, required=True)
    parser.add_argument("--reviewer-schema", type=Path, required=True)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--core-n", type=int, default=32)
    parser.add_argument("--challenge-n", type=int, default=8)
    args = parser.parse_args()
    if args.core_n != 32 or not (0 <= args.challenge_n <= 8):
        raise ValueError("frozen design requires 32 core and at most 8 challenge ads")

    repo = args.repo_root.resolve()
    private_dir = args.private_output_dir.resolve()
    if private_dir == repo or repo in private_dir.parents:
        raise ValueError("private output directory must be outside the repository")
    private_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(private_dir, 0o700)
    except OSError:
        pass

    schema = json.loads(args.reviewer_schema.read_text(encoding="utf-8"))
    visible = list(schema["initially_visible_columns"])
    hidden = set(schema["hidden_until_human_lock"])
    if set(visible) & hidden:
        raise ValueError("reviewer schema exposes a hidden field")

    rows, fields = read_csv(args.frame)
    frame_metadata = read_metadata(args.frame_metadata, "frame")
    missing = FRAME_FIELDS - set(fields)
    if missing:
        raise ValueError(f"canonical frame missing fields: {sorted(missing)}")
    contamination = PREDICTION_PROHIBITED_IN_FRAME & set(fields)
    if contamination:
        raise ValueError(f"predictions must be separate from canonical frame: {sorted(contamination)}")
    keys = [row["private_key"] for row in rows]
    if any(not key for key in keys) or len(set(keys)) != len(keys):
        raise ValueError("canonical frame private_key must be nonblank and unique")
    if any(not row["original_text"].strip() for row in rows):
        raise ValueError("canonical frame contains blank original_text")

    exclusions, heldout_metadata = read_exclusion_keys(args.heldout_key_manifest)
    if frame_metadata["key_namespace"] != heldout_metadata["key_namespace"]:
        raise ValueError("frame and heldout key_namespace differ")
    eligible = [row for row in rows if row["private_key"] not in exclusions]
    excluded_matches = len(rows) - len(eligible)

    by_core = defaultdict(list)
    for row in eligible:
        if not row["sampling_stratum"].strip():
            raise ValueError("blank sampling_stratum")
        by_core[row["sampling_stratum"]].append(row)
    core_sizes = {key: len(value) for key, value in by_core.items()}
    core_alloc = allocate_proportional(core_sizes, args.core_n)
    core = []
    for stratum, candidates in by_core.items():
        ordered = sorted(candidates, key=lambda row: stable_rank("core", row["private_key"]))
        for row in ordered[:core_alloc[stratum]]:
            chosen = dict(row)
            chosen["selection_stratum"] = stratum
            chosen["sampling_probability"] = core_alloc[stratum] / core_sizes[stratum]
            chosen["core_or_challenge"] = "core"
            core.append(chosen)
    if len(core) != args.core_n:
        raise RuntimeError(f"expected {args.core_n} core rows, got {len(core)}")

    core_keys = {row["private_key"] for row in core}
    by_challenge = defaultdict(list)
    for row in eligible:
        if row["private_key"] not in core_keys and truthy(row["challenge_eligible"]):
            stratum = row["challenge_stratum"].strip()
            if not stratum:
                raise ValueError("challenge-eligible row has blank challenge_stratum")
            by_challenge[stratum].append(row)
    challenge_sizes = {key: len(value) for key, value in by_challenge.items()}
    challenge_total = min(args.challenge_n, sum(challenge_sizes.values()))
    challenge_alloc = allocate_proportional(challenge_sizes, challenge_total)
    challenge = []
    for stratum, candidates in by_challenge.items():
        ordered = sorted(candidates, key=lambda row: stable_rank("challenge", row["private_key"]))
        for row in ordered[:challenge_alloc[stratum]]:
            chosen = dict(row)
            chosen["selection_stratum"] = stratum
            chosen["sampling_probability"] = challenge_alloc[stratum] / challenge_sizes[stratum]
            chosen["core_or_challenge"] = "challenge"
            challenge.append(chosen)

    dual_keys = {
        row["private_key"] for row in sorted(
            core, key=lambda row: stable_rank("dual_review", row["private_key"])
        )[:8]
    }
    selected = sorted(core + challenge, key=lambda row: stable_rank("pack_order", row["private_key"]))
    anonymous_ids = {}
    for row in selected:
        anon = "R" + stable_rank("anonymous", row["private_key"])[:12].upper()
        if anon in anonymous_ids:
            raise RuntimeError("anonymous ID collision")
        anonymous_ids[anon] = row["private_key"]

    reviewer_rows, key_rows, assignment_rows = [], [], []
    blank_human = {field: "" for field in visible if field.startswith("human_")}
    predictions = {}
    prediction_fields = []
    if args.predictions:
        pred_rows, prediction_fields = read_csv(args.predictions)
        if "private_key" not in prediction_fields:
            raise ValueError("prediction file requires private_key")
        for row in pred_rows:
            key = row["private_key"]
            if key in predictions:
                raise ValueError(f"duplicate prediction private_key: {key}")
            predictions[key] = {name: row[name] for name in prediction_fields if name != "private_key"}

    for row, anon in zip(selected, anonymous_ids):
        reviewer = {field: "" for field in visible}
        reviewer.update(blank_human)
        reviewer.update({
            "anonymous_review_id": anon,
            "original_text": row["original_text"],
            "first_observation_stratum": row["first_observation_stratum"],
            "occupation_availability_stratum": row["occupation_availability_stratum"],
            "core_or_challenge": row["core_or_challenge"],
            "sampling_probability": row["sampling_probability"],
            "review_round": "initial_blind",
        })
        reviewer_rows.append(reviewer)
        key_rows.append({
            "anonymous_review_id": anon,
            "private_key": row["private_key"],
            "core_or_challenge": row["core_or_challenge"],
            "selection_stratum": row["selection_stratum"],
            "model_predictions_json": json.dumps(predictions.get(row["private_key"], {}), sort_keys=True),
        })
        slots = ("A", "B") if row["private_key"] in dual_keys else ("A",)
        for slot in slots:
            assignment_rows.append({
                "anonymous_review_id": anon,
                "reviewer_slot": slot,
                "dual_review_required": str(len(slots) == 2).lower(),
            })

    pack_path = private_dir / "reviewer_pack.csv"
    key_path = private_dir / "private_answer_key.csv"
    assignment_path = private_dir / "review_assignments.csv"
    write_csv(pack_path, reviewer_rows, visible)
    write_csv(key_path, key_rows, list(key_rows[0]))
    write_csv(assignment_path, assignment_rows, list(assignment_rows[0]))
    for path in (pack_path, key_path, assignment_path):
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    receipt = {
        "status": "blind_pack_built",
        "seed": SEED,
        "inputs": {
            "canonical_frame_sha256": sha256(args.frame),
            "frame_metadata_sha256": sha256(args.frame_metadata),
            "heldout_key_manifest_sha256": sha256(args.heldout_key_manifest),
            "reviewer_schema_sha256": sha256(args.reviewer_schema),
            "predictions_sha256": sha256(args.predictions) if args.predictions else None,
        },
        "key_contract": {
            "key_namespace": frame_metadata["key_namespace"],
            "stable_key_type": "string",
            "frame_source_provenance": frame_metadata["source_provenance"],
            "heldout_source_provenance": heldout_metadata["source_provenance"],
            "heldout_intersection_may_be_zero_if_frame_was_preexcluded": True,
        },
        "counts": {
            "frame_rows": len(rows),
            "heldout_key_count": len(exclusions),
            "heldout_matches_excluded": excluded_matches,
            "eligible_after_exclusion": len(eligible),
            "core_selected": len(core),
            "challenge_selected": len(challenge),
            "unique_ads": len(selected),
            "core_dual_review": len(dual_keys),
        },
        "core_strata": {
            key: {"frame_size": core_sizes[key], "selected": core_alloc[key],
                  "sampling_probability": core_alloc[key] / core_sizes[key]}
            for key in sorted(core_sizes)
        },
        "challenge_strata": {
            key: {"eligible_size_after_core": challenge_sizes[key], "selected": challenge_alloc[key],
                  "sampling_probability": challenge_alloc[key] / challenge_sizes[key]}
            for key in sorted(challenge_sizes)
        },
        "blinding": {
            "reviewer_columns": visible,
            "model_predictions_in_reviewer_pack": False,
            "private_key_in_reviewer_pack": False,
            "raw_text_written_to_public_receipt": False,
            "challenge_excluded_from_prevalence_estimates": True,
        },
        "private_outputs": [path.name for path in (pack_path, key_path, assignment_path)],
    }
    args.public_receipt.parent.mkdir(parents=True, exist_ok=True)
    args.public_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
