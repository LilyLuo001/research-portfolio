#!/usr/bin/env python3
"""Compare blind model labels with the frozen V5 candidate parser.

This is a diagnostic comparison against model-generated reference labels, not
an accuracy evaluation against human annotations.  Row-level output is private;
the JSON and Markdown reports contain aggregate counts only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


MODULES = ("education", "experience")
PRESENCE_VALUES = {
    "explicit_positive", "explicit_negative", "not_mentioned",
    "insufficient_text", "unresolved",
}
PRIMARY_MODEL = "gpt-5.6-terra"
SECONDARY_MODEL = "gpt-5.6-sol"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value: Any) -> None:
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    temp = Path(str(path) + ".tmp")
    with temp.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(temp, path)


def load_parser(path: Path):
    spec = importlib.util.spec_from_file_location("frozen_requirement_candidates_v5", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen parser: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def index_unique(rows: list[dict[str, Any]], source: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        diagnostic_id = row.get("diagnostic_id")
        if not isinstance(diagnostic_id, str) or diagnostic_id in result:
            raise ValueError(f"{source}: missing or duplicate diagnostic_id")
        result[diagnostic_id] = row
    return result


def validate_labels(rows: list[dict[str, Any]], texts: dict[str, str], source: str) -> None:
    errors: list[str] = []
    for row in rows:
        diagnostic_id = row.get("diagnostic_id")
        if diagnostic_id not in texts:
            errors.append(f"{diagnostic_id}: ID absent from texts")
            continue
        for module in MODULES:
            value = row.get(f"{module}_presence")
            if value not in PRESENCE_VALUES:
                errors.append(f"{diagnostic_id}: invalid {module}_presence={value!r}")
        for field in ("education_evidence", "experience_evidence", "technology_evidence"):
            evidence = row.get(field)
            if not isinstance(evidence, list):
                errors.append(f"{diagnostic_id}: {field} is not a list")
                continue
            for position, item in enumerate(evidence):
                quote = item.get("quote") if isinstance(item, dict) else None
                if not isinstance(quote, str) or not quote or quote not in texts[diagnostic_id]:
                    errors.append(f"{diagnostic_id}: {field}[{position}] is not an exact source substring")
    if errors:
        raise ValueError(source + " label validation failed:\n" + "\n".join(errors))


def confusion(rows: list[dict[str, Any]], module: str) -> dict[str, Any]:
    # explicit_positive is the reference-positive class. not_mentioned is the
    # only reference-negative class. Explicit absence and unknown states are
    # reported separately and never silently counted as true negatives.
    counts = Counter()
    for row in rows:
        reference = row[f"{module}_reference"]
        predicted = row[f"{module}_v5_candidate"]
        if reference == "explicit_positive":
            counts["tp" if predicted else "fn"] += 1
        elif reference == "not_mentioned":
            counts["fp" if predicted else "tn"] += 1
        elif reference == "explicit_negative":
            counts["explicit_absence_v5_candidate" if predicted else "explicit_absence_v5_no_candidate"] += 1
        else:
            counts[f"excluded_{reference}"] += 1
    support = counts["tp"] + counts["fn"] + counts["fp"] + counts["tn"]
    explicit_absence_predictions = [
        row for row in rows if row.get(f"{module}_v5_explicit_absence") is True
    ]
    return {
        "binary_support": support,
        "tp": counts["tp"], "fn": counts["fn"],
        "fp": counts["fp"], "tn": counts["tn"],
        "reference_explicit_absence": {
            "support": counts["explicit_absence_v5_candidate"] + counts["explicit_absence_v5_no_candidate"],
            "v5_candidate": counts["explicit_absence_v5_candidate"],
            "v5_no_candidate": counts["explicit_absence_v5_no_candidate"],
        },
        "v5_predicted_explicit_absence": {
            "available": any(f"{module}_v5_explicit_absence" in row for row in rows),
            "count": len(explicit_absence_predictions),
            "reference_presence_counts": dict(sorted(Counter(
                row[f"{module}_reference"] for row in explicit_absence_predictions
            ).items())),
        },
        "excluded_unknown_or_conflict": {
            key.removeprefix("excluded_"): value
            for key, value in sorted(counts.items()) if key.startswith("excluded_")
        },
    }


def categorical_counts(rows: list[dict[str, Any]], evidence_field: str, category: str) -> dict[str, int]:
    return dict(sorted(Counter(
        item.get(category, "missing")
        for row in rows for item in row.get(evidence_field, [])
    ).items()))


def label_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "presence_counts": {
            module: dict(sorted(Counter(row[f"{module}_presence"] for row in rows).items()))
            for module in MODULES
        },
        "experience_object_evidence_counts": categorical_counts(rows, "experience_evidence", "object"),
        "technology_role_evidence_counts": categorical_counts(rows, "technology_evidence", "technology_role"),
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Model diagnostic aggregate",
        "",
        "This compares frozen V5 applicant-qualification candidates with blind model labels. "
        "The labels are model references, not human ground truth, so the counts are diagnostic and are not accuracy estimates.",
        "",
        f"Primary: `{report['design']['primary_model']}` on 32 rows. Secondary: "
        f"`{report['design']['secondary_model']}` on a fixed 8-row subset.",
        "",
        "## Primary comparison",
        "",
        "| Module | Binary support | TP | FN | FP | TN | Reference explicit absence | V5 predicted explicit absence | Excluded unknown/conflict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for module in MODULES:
        c = report["primary32"]["confusion"][module]
        excluded = sum(c["excluded_unknown_or_conflict"].values())
        predicted_absence = c["v5_predicted_explicit_absence"]
        predicted_absence_text = str(predicted_absence["count"]) if predicted_absence["available"] else "not available"
        lines.append(f"| {module.title()} | {c['binary_support']} | {c['tp']} | {c['fn']} | {c['fp']} | {c['tn']} | {c['reference_explicit_absence']['support']} | {predicted_absence_text} | {excluded} |")
    lines.extend(["", "## Independent subset", ""])
    for module in MODULES:
        disagreement = report["secondary8"]["primary_secondary_disagreement"][module]
        c = report["secondary8"]["agreed_only_confusion"][module]
        lines.append(f"- {module.title()}: {disagreement['disagreements']} primary/secondary disagreements out of {disagreement['support']}; agreed-only V5 comparison support {c['binary_support']} (TP {c['tp']}, FN {c['fn']}, FP {c['fp']}, TN {c['tn']}).")
    lines.extend([
        "", "## Protocol-only label composition", "",
        "Experience-object and technology-role counts below count evidence objects, including multiple objects per ad. They diagnose labeling protocol use and do not measure V5 accuracy.", "",
        "```json", json.dumps(report["protocol_diagnosis"], indent=2, sort_keys=True), "```", "",
        "The sample is a calibration diagnostic. With only 32 rows, it supports no full-corpus or per-period inference.", "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    default_artifact = here / "artifacts/model_diagnostic32_v1"
    parser.add_argument("--artifact-dir", type=Path, default=default_artifact)
    parser.add_argument("--parser", type=Path, default=here.parent / "stage_c_v5/requirement_candidates.py")
    parser.add_argument("--primary-model", default=PRIMARY_MODEL)
    parser.add_argument("--secondary-model", default=SECONDARY_MODEL)
    args = parser.parse_args()

    artifact = args.artifact_dir.resolve()
    texts_rows = read_jsonl(artifact / "texts.jsonl")
    primary_rows = read_jsonl(artifact / "model_primary.jsonl")
    secondary_rows = read_jsonl(artifact / "model_check.jsonl")
    if len(texts_rows) != 32 or len(primary_rows) != 32 or len(secondary_rows) != 8:
        raise ValueError("expected texts=32, primary=32, secondary=8")
    texts = {row["diagnostic_id"]: row["raw_text"] for row in texts_rows}
    primary = index_unique(primary_rows, "primary")
    secondary = index_unique(secondary_rows, "secondary")
    if set(primary) != set(texts) or not set(secondary).issubset(primary):
        raise ValueError("label ID coverage does not match the 32-row frame / 8-row subset")
    validate_labels(primary_rows, texts, "primary")
    validate_labels(secondary_rows, texts, "secondary")

    frozen = load_parser(args.parser.resolve())
    comparisons: list[dict[str, Any]] = []
    for diagnostic_id in sorted(texts):
        result = frozen.extract(texts[diagnostic_id])
        row: dict[str, Any] = {"diagnostic_id": diagnostic_id}
        for module in MODULES:
            row[f"{module}_reference"] = primary[diagnostic_id][f"{module}_presence"]
            row[f"{module}_v5_candidate"] = any(
                item.get("module") == module and item.get("is_applicant_qualification_candidate") is True
                for item in result["evidence"]
            )
            if module == "experience":
                row[f"{module}_v5_explicit_absence"] = bool(
                    result["summary"][module].get("no_experience_explicit")
                )
            if diagnostic_id in secondary:
                row[f"{module}_secondary_reference"] = secondary[diagnostic_id][f"{module}_presence"]
        comparisons.append(row)

    subset = [row for row in comparisons if row["diagnostic_id"] in secondary]
    disagreements: dict[str, Any] = {}
    agreed_rows: dict[str, list[dict[str, Any]]] = {}
    for module in MODULES:
        agree = [row for row in subset if row[f"{module}_reference"] == row[f"{module}_secondary_reference"]]
        agreed_rows[module] = agree
        disagreements[module] = {"support": len(subset), "disagreements": len(subset) - len(agree), "agreements": len(agree)}

    report = {
        "status": "complete",
        "design": {
            "primary_model": args.primary_model, "primary_rows": len(primary_rows),
            "secondary_model": args.secondary_model, "secondary_rows": len(secondary_rows),
            "reference_type": "blind_model_labels", "human_annotations": False,
            "model_identity_note": "Requested model-family identities; exact runtime build identifiers were not emitted with the label artifacts.",
            "parser": "frozen stage_c_v5/requirement_candidates.py",
            "target": "is_applicant_qualification_candidate",
            "positive_reference": "explicit_positive", "negative_reference": "not_mentioned",
            "explicit_negative_reported_separately": True,
            "unknown_or_conflict_excluded_from_binary_confusion": True,
            "sealed_test_accessed": False,
            "inference_limit": "No full-corpus or per-period inference; n=32 is insufficient.",
        },
        "quote_validation": {"method": "nonempty literal substring of source raw_text", "errors": 0},
        "primary32": {"confusion": {module: confusion(comparisons, module) for module in MODULES}},
        "secondary8": {
            "primary_secondary_disagreement": disagreements,
            "agreed_only_confusion": {module: confusion(agreed_rows[module], module) for module in MODULES},
        },
        "protocol_diagnosis": {
            "unit": "labeled evidence objects (multiple per ad possible)",
            "not_v5_accuracy": True,
            "primary32": label_summary(primary_rows),
            "secondary8": label_summary(secondary_rows),
        },
    }
    write_jsonl(artifact / "row_comparisons_private.jsonl", comparisons)
    write_json(artifact / "model_diagnostic_aggregate.json", report)
    md_path = artifact / "model_diagnostic_aggregate.md"
    temp_md = Path(str(md_path) + ".tmp")
    temp_md.write_text(markdown(report))
    os.replace(temp_md, md_path)
    print(json.dumps({"status": "complete", "json": str(artifact / "model_diagnostic_aggregate.json"), "markdown": str(md_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
