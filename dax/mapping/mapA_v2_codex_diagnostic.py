#!/usr/bin/env python3
"""Development/calibration-only preliminary Mapping A v2 diagnostic.

This utility is deliberately separate from the independent-label and locked-test
validation runners.  It freezes a small stratified diagnostic sample, prepares
private task packets for one Codex annotator, and emits an aggregate-only
receipt.  It refuses locked-test rows and never fits or changes the frozen
prediction rule or thresholds.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
from collections.abc import Iterable, Mapping

import pandas as pd


DIAGNOSTIC_SEED = "DAX-MAPA-V2-CODEX-DIAGNOSTIC-20260821"
ALLOWED_SPLITS = frozenset({"development", "calibration"})
CATEGORIES = (
    "agree_high",
    "dense_only_high",
    "lexical_only_high",
    "medium_uncertain",
    "apparent_negative",
    "rrf_best",
)
QUOTA_BY_SPLIT = {"development": 6, "calibration": 4}
SAMPLE_SIZE = len(CATEGORIES) * sum(QUOTA_BY_SPLIT.values())
LABELS = frozenset({"D", "F", "N", "U"})


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable(value: str) -> str:
    return hashlib.sha256(f"{DIAGNOSTIC_SEED}|{value}".encode()).hexdigest()


def _clean(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def select_diagnostic_rows(rows: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    """Select exactly ten rows per retrieval category without locked rows."""
    eligible: list[dict[str, object]] = []
    for original in rows:
        row = dict(original)
        split = _clean(row.get("split"))
        if split not in ALLOWED_SPLITS:
            continue
        if _clean(row.get("relation_label")):
            raise ValueError("refusing to inspect an already labeled development/calibration row")
        category = _clean(row.get("candidate_category"))
        if category not in CATEGORIES:
            raise ValueError(f"unknown candidate category: {category}")
        eligible.append(row)

    selected: list[dict[str, object]] = []
    represented_families: collections.Counter[str] = collections.Counter()
    seen_pairs: set[tuple[str, str]] = set()
    for category in CATEGORIES:
        category_families: collections.Counter[str] = collections.Counter()
        for split, quota in QUOTA_BY_SPLIT.items():
            pool = [
                row for row in eligible
                if _clean(row["candidate_category"]) == category and _clean(row["split"]) == split
            ]
            for _ in range(quota):
                available = [
                    row for row in pool
                    if (_clean(row["onet_task_id"]), _clean(row["gdpval_task_id"])) not in seen_pairs
                ]
                if not available:
                    raise ValueError(f"insufficient rows for {category}/{split}")
                winner = min(
                    available,
                    key=lambda row: (
                        represented_families[_clean(row["major_soc_family"])],
                        category_families[_clean(row["major_soc_family"])],
                        _stable(
                            f'{category}|{split}|{_clean(row["onet_task_id"])}|'
                            f'{_clean(row["gdpval_task_id"])}'
                        ),
                    ),
                )
                pair = (_clean(winner["onet_task_id"]), _clean(winner["gdpval_task_id"]))
                seen_pairs.add(pair)
                family = _clean(winner["major_soc_family"])
                represented_families[family] += 1
                category_families[family] += 1
                selected.append(winner)

    if len(selected) != SAMPLE_SIZE:
        raise AssertionError(f"diagnostic sample drift: {len(selected)}")
    if any(_clean(row["split"]) not in ALLOWED_SPLITS for row in selected):
        raise AssertionError("locked or unknown split entered diagnostic sample")
    # Annotation packets must not reveal the category blocks through row order.
    return sorted(
        selected,
        key=lambda row: _stable(
            f'diagnostic-order|{_clean(row["onet_task_id"])}|{_clean(row["gdpval_task_id"])}'
        ),
    )


def _write_csv(path: pathlib.Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def freeze(args: argparse.Namespace) -> dict[str, object]:
    private_dir = args.private_dir.resolve()
    receipt_path = args.receipt.resolve()
    if private_dir == receipt_path.parent or private_dir in receipt_path.parents:
        raise SystemExit("REFUSED: aggregate receipt must be outside private directory")
    private_dir.mkdir(parents=True, exist_ok=True)
    private_dir.chmod(0o700)

    pairs = pd.read_csv(args.validation_pairs, dtype=str).fillna("")
    selected = select_diagnostic_rows(pairs.to_dict("records"))
    onet = pd.read_csv(args.onet_csv, dtype={"task_id": str}).fillna("")
    gdpval = pd.read_parquet(args.gdpval_parquet).fillna("")
    onet_by_id = {str(row["task_id"]): row for _, row in onet.iterrows()}
    gdpval_by_id = {str(row["task_id"]): row for _, row in gdpval.iterrows()}

    sample_rows: list[dict[str, object]] = []
    packets: list[dict[str, object]] = []
    for index, row in enumerate(selected, start=1):
        onet_id = _clean(row["onet_task_id"])
        gdpval_id = _clean(row["gdpval_task_id"])
        if onet_id not in onet_by_id or gdpval_id not in gdpval_by_id:
            raise ValueError("diagnostic pair absent from source task universe")
        o = onet_by_id[onet_id]
        g = gdpval_by_id[gdpval_id]
        sample_rows.append({
            "diagnostic_index": index,
            "onet_task_id": onet_id,
            "gdpval_task_id": gdpval_id,
            "major_soc_family": _clean(row["major_soc_family"]),
            "candidate_category": _clean(row["candidate_category"]),
            "dense_rank": _clean(row["dense_rank"]),
            "lexical_rank": _clean(row["lexical_rank"]),
            "split": _clean(row["split"]),
        })
        packets.append({
            "diagnostic_index": index,
            "onet_task": {
                "statement": _clean(o.get("task_statement")),
                "type": _clean(o.get("task_type")),
            },
            "gdpval_task": {
                "sector": _clean(g.get("sector")),
                "occupation": _clean(g.get("occupation")),
                "prompt": _clean(g.get("prompt")),
                "rubric": _clean(g.get("rubric_pretty")),
            },
            "rubric": {
                "D": "Same work product, core operations, domain constraints, and quality criterion.",
                "F": "Material shared capability/workflow, but not sufficient for end-to-end substitution.",
                "N": "No material task-output or capability transfer.",
                "U": "Insufficient task information to distinguish D/F/N.",
            },
        })

    sample_path = private_dir / "mapA_v2_codex_diagnostic_sample.csv"
    packet_path = private_dir / "mapA_v2_codex_diagnostic_packets.jsonl"
    template_path = private_dir / "mapA_v2_codex_diagnostic_labels_template.csv"
    _write_csv(sample_path, sample_rows)
    packet_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in packets), encoding="utf-8")
    packet_path.chmod(0o600)
    _write_csv(template_path, [{"diagnostic_index": i, "relation_label": "", "concise_rationale": ""} for i in range(1, SAMPLE_SIZE + 1)])

    counts_category = collections.Counter(row["candidate_category"] for row in sample_rows)
    counts_split = collections.Counter(row["split"] for row in sample_rows)
    counts_family = collections.Counter(row["major_soc_family"] for row in sample_rows)
    receipt = {
        "status": "PRELIMINARY_CODEX_DIAGNOSTIC_SAMPLE_FROZEN_LABELS_PENDING",
        "scope": "development_calibration_only",
        "seed": DIAGNOSTIC_SEED,
        "sample_pairs": SAMPLE_SIZE,
        "counts_by_category": dict(sorted(counts_category.items())),
        "counts_by_split": dict(sorted(counts_split.items())),
        "major_soc_families_covered": len(counts_family),
        "locked_test_rows_read_for_annotation": 0,
        "locked_test_labels_opened": False,
        "formal_independent_validation": False,
        "thresholds_or_methods_changed": False,
        "incremental_api_spend_usd": 0,
        "private_artifact_hashes": {
            sample_path.name: sha256(sample_path),
            packet_path.name: sha256(packet_path),
            template_path.name: sha256(template_path),
        },
        "row_level_data_committed": False,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _wilson(successes: int, total: int) -> list[float]:
    if total == 0:
        return [0.0, 1.0]
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [round(max(0.0, center - radius), 4), round(min(1.0, center + radius), 4)]


def _summary(rows: list[dict[str, str]]) -> dict[str, object]:
    total = len(rows)
    counts = collections.Counter(row["relation_label"] for row in rows)
    direct = counts["D"]
    related = counts["D"] + counts["F"]
    return {
        "pairs": total,
        "label_counts": {label: counts[label] for label in sorted(LABELS)},
        "direct_rate": round(direct / total, 4),
        "direct_rate_wilson_95": _wilson(direct, total),
        "direct_or_family_rate": round(related / total, 4),
        "direct_or_family_rate_wilson_95": _wilson(related, total),
    }


def evaluate(args: argparse.Namespace) -> dict[str, object]:
    private_dir = args.private_dir.resolve()
    sample_path = private_dir / "mapA_v2_codex_diagnostic_sample.csv"
    sample = pd.read_csv(sample_path, dtype=str).fillna("")
    labels = pd.read_csv(args.labels, dtype=str).fillna("")
    required = {"diagnostic_index", "relation_label", "concise_rationale"}
    if not required <= set(labels.columns):
        raise ValueError(f"diagnostic labels missing {sorted(required - set(labels.columns))}")
    if len(labels) != SAMPLE_SIZE or labels["diagnostic_index"].duplicated().any():
        raise ValueError("diagnostic labels must contain each of the 60 indices exactly once")
    labels["relation_label"] = labels["relation_label"].str.strip().str.upper()
    if set(labels["relation_label"]) - LABELS:
        raise ValueError("diagnostic label outside D/F/N/U")
    if labels["concise_rationale"].str.strip().eq("").any():
        raise ValueError("every diagnostic label requires a rationale")
    merged = sample.merge(labels, on="diagnostic_index", validate="one_to_one")
    if len(merged) != SAMPLE_SIZE or not set(merged["split"]) <= ALLOWED_SPLITS:
        raise ValueError("sample/label mismatch or locked split exposure")

    records = merged.to_dict("records")
    by_category = {
        category: _summary([row for row in records if row["candidate_category"] == category])
        for category in CATEGORIES
    }
    high = [row for row in records if row["candidate_category"] in {"agree_high", "rrf_best"}]
    negative = [row for row in records if row["candidate_category"] == "apparent_negative"]
    receipt = {
        "status": "PRELIMINARY_SINGLE_CODEX_DIAGNOSTIC_COMPLETE_NOT_FORMAL_VALIDATION",
        "completed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "development_calibration_only",
        "annotator": "single_current_codex_session_included_usage",
        "independent_multi_vendor_validation": False,
        "sample": {
            "pairs": SAMPLE_SIZE,
            "splits": dict(sorted(collections.Counter(merged["split"]).items())),
            "major_soc_families": int(merged["major_soc_family"].nunique()),
        },
        "overall": _summary(records),
        "by_candidate_category": by_category,
        "retrieval_contrast": {
            "agree_high_plus_rrf_best": _summary(high),
            "apparent_negative": _summary(negative),
            "direct_or_family_rate_difference": round(
                _summary(high)["direct_or_family_rate"] - _summary(negative)["direct_or_family_rate"], 4
            ),
        },
        "formal_metrics_not_claimed": [
            "binding_PPV", "binding_false_positive_rate", "candidate_recall",
            "inter_vendor_agreement", "adjudication_rate", "production_coverage",
            "transport_sensitivity", "locked_test_pass_fail",
        ],
        "locked_test_rows_read_for_annotation": 0,
        "locked_test_labels_opened": False,
        "frozen_thresholds_or_methods_changed": False,
        "incremental_api_spend_usd": 0,
        "input_hashes": {
            "private_sample_sha256": sha256(sample_path),
            "private_labels_sha256": sha256(args.labels.resolve()),
        },
        "row_level_data_committed": False,
    }
    output = args.receipt.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    sub = value.add_subparsers(dest="command", required=True)
    freeze_parser = sub.add_parser("freeze")
    freeze_parser.add_argument("--validation-pairs", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--onet-csv", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--gdpval-parquet", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--private-dir", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--private-dir", type=pathlib.Path, required=True)
    evaluate_parser.add_argument("--labels", type=pathlib.Path, required=True)
    evaluate_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    arguments = parser().parse_args()
    result = freeze(arguments) if arguments.command == "freeze" else evaluate(arguments)
    print(json.dumps(result, indent=2, sort_keys=True))
