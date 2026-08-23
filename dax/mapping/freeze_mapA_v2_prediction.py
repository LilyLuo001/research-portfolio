#!/usr/bin/env python3
"""Fit and freeze Mapping A v2 after private dev/cal labels exist.

The runner has no locked-test argument.  It validates independent-vendor
lineage, fits only development, calibrates/selects the cutoff only on
calibration, and writes a release-safe parameter receipt with no pair IDs,
task text, rationales, vendor identities, or row-level labels.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import hashlib
import json
import pathlib
import platform

import numpy as np
import sklearn

from mapA_v2_label_protocol import validate_independent_labels
from mapA_v2_prediction import (
    FEATURE_NAMES,
    RetrievalPair,
    build_feature_rows,
    calibrated_probabilities,
    fit_platt_calibrator,
    frozen_algorithm_specification,
    select_and_fit_development_model,
    select_calibration_cutoff,
)


EXPECTED_COUNTS = {"development": 1513, "calibration": 540}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _parameter_receipt(model: object) -> dict[str, object]:
    return {
        "classes": np.asarray(model.classes_).tolist(),
        "coefficients": np.asarray(model.coef_, dtype=float).tolist(),
        "intercept": np.asarray(model.intercept_, dtype=float).tolist(),
        "iterations": np.asarray(model.n_iter_).tolist(),
    }


def execute(args: argparse.Namespace) -> dict[str, object]:
    labels_path = args.dev_cal_labels.resolve()
    labels = read_csv(labels_path)
    counts = validate_independent_labels(labels, allowed_splits={"development", "calibration"})
    observed_counts = {split: sum(row["split"] == split for row in labels) for split in EXPECTED_COUNTS}
    if observed_counts != EXPECTED_COUNTS:
        raise SystemExit(f"REFUSED: exact dev/cal counts required; observed {observed_counts}")

    sample_rows = read_csv(args.frozen_sample.resolve())
    frozen = {
        (row["onet_task_id"], row["gdpval_task_id"]): row["split"]
        for row in sample_rows
        if row["split"] in EXPECTED_COUNTS
    }
    provided = {(row["onet_task_id"], row["gdpval_task_id"]): row["split"] for row in labels}
    if provided != frozen:
        raise SystemExit("REFUSED: label pairs/splits differ from the frozen dev/cal sample")

    ids = json.loads(args.ordered_ids.read_text(encoding="utf-8"))
    onet_ids = [str(value) for value in ids["onet_task_ids"]]
    gdpval_ids = [str(value) for value in ids["gdpval_task_ids"]]
    if len(onet_ids) != 19259 or len(set(onet_ids)) != len(onet_ids):
        raise SystemExit("REFUSED: O*NET ID universe drift")
    if len(gdpval_ids) != 220 or len(set(gdpval_ids)) != len(gdpval_ids):
        raise SystemExit("REFUSED: GDPval ID universe drift")
    scores = np.load(args.full_scores, allow_pickle=False)
    dense = scores["dense"]
    lexical = scores["lexical"]
    if dense.shape != (19259, 220) or lexical.shape != (19259, 220):
        raise SystemExit("REFUSED: retrieval matrix shape drift")

    onet_index = {task_id: index for index, task_id in enumerate(onet_ids)}
    selected_onet = sorted({row["onet_task_id"] for row in labels})
    retrieval_rows: list[RetrievalPair] = []
    for onet_id in selected_onet:
        if onet_id not in onet_index:
            raise SystemExit("REFUSED: labeled O*NET ID absent from frozen score universe")
        index = onet_index[onet_id]
        retrieval_rows.extend(
            RetrievalPair(onet_id, gdpval_id, float(dense[index, column]), float(lexical[index, column]))
            for column, gdpval_id in enumerate(gdpval_ids)
        )

    by_pair = {(row["onet_task_id"], row["gdpval_task_id"]): row for row in labels}
    development_pairs = [pair for pair, split in frozen.items() if split == "development"]
    calibration_pairs = [pair for pair, split in frozen.items() if split == "calibration"]
    development_x, development_order = build_feature_rows(retrieval_rows, development_pairs)
    calibration_x, calibration_order = build_feature_rows(retrieval_rows, calibration_pairs)
    development_y = [by_pair[pair]["final_label"] for pair in development_order]
    calibration_y = [by_pair[pair]["final_label"] for pair in calibration_order]

    scaler, model, selection = select_and_fit_development_model(development_x, development_y)
    calibrator = fit_platt_calibrator(scaler, model, calibration_x, calibration_y)
    probabilities = calibrated_probabilities(scaler, model, calibrator, calibration_x)
    cutoff = select_calibration_cutoff(probabilities, calibration_y)

    source_files = [
        pathlib.Path(__file__).resolve(),
        pathlib.Path(__file__).with_name("mapA_v2_prediction.py"),
        pathlib.Path(__file__).with_name("mapA_v2_label_protocol.py"),
        pathlib.Path(__file__).with_name("mapA_v2_prediction_spec_20260821.json"),
    ]
    receipt = {
        "status": "IMMUTABLE_PREDICTION_RULE_FROZEN",
        "fitted_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "algorithm": frozen_algorithm_specification(),
        "counts": {**observed_counts, **counts},
        "input_hashes": {
            "development_calibration_labels_sha256": sha256(labels_path),
            "frozen_sample_sha256": sha256(args.frozen_sample.resolve()),
            "full_scores_sha256": sha256(args.full_scores.resolve()),
            "ordered_ids_sha256": sha256(args.ordered_ids.resolve()),
        },
        "source_code_hashes": {path.name: sha256(path) for path in source_files},
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "platform": platform.platform(),
        },
        "feature_names_in_order": list(FEATURE_NAMES),
        "development_selection": selection,
        "scaler": {
            "mean": np.asarray(scaler.mean_, dtype=float).tolist(),
            "scale": np.asarray(scaler.scale_, dtype=float).tolist(),
            "variance": np.asarray(scaler.var_, dtype=float).tolist(),
        },
        "classifier": _parameter_receipt(model),
        "calibrator": _parameter_receipt(calibrator),
        "cutoff": {
            "probability": cutoff.cutoff,
            "selection_constraints": {"PPV_min": 0.95, "FPR_max": 0.05},
            "selection_objective": "maximum_recall",
            "calibration_partition_metrics": dataclasses.asdict(cutoff),
        },
        "locked_test_read": False,
        "outcomes_opened": False,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_hash = sha256(output)
    sidecar = output.with_suffix(output.suffix + ".sha256")
    sidecar.write_text(f"{artifact_hash}  {output.name}\n", encoding="utf-8")
    return {"status": receipt["status"], "artifact_sha256": artifact_hash, "sidecar": str(sidecar)}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--dev-cal-labels", type=pathlib.Path, required=True)
    value.add_argument("--frozen-sample", type=pathlib.Path, required=True)
    value.add_argument("--full-scores", type=pathlib.Path, required=True)
    value.add_argument("--ordered-ids", type=pathlib.Path, required=True)
    value.add_argument("--output", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    print(json.dumps(execute(parser().parse_args()), indent=2, sort_keys=True))
