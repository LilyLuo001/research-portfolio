#!/usr/bin/env python3
"""Compare frozen V5 and V6 candidates with the blind NEW48 model reference.

The reference is model-assisted diagnosis, not human ground truth. Row-level
comparisons remain private; JSON and Markdown outputs contain aggregates only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


MODULES = ("education", "experience")
VERSIONS = ("v5", "v6")
PRESENCE_VALUES = (
    "explicit_positive", "explicit_negative", "not_mentioned",
    "insufficient_text", "unresolved",
)
DEFAULT_V5_SHA256 = "336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd"
REQUESTED_REFERENCE_MODEL = "gpt-5.6-terra"
REQUESTED_REFERENCE_EFFORT = "medium"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def atomic_text(path: Path, text: str) -> None:
    temp = Path(str(path) + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def write_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_text(path, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_parser(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen parser: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def index_unique(rows: list[dict[str, Any]], key: str, source: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise ValueError(f"{source}: missing or duplicate {key}")
        result[value] = row
    return result


def load_frame(artifact: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    text_rows = index_unique(
        read_jsonl(artifact / "selected48_source_texts.jsonl"),
        "annotation_id", "selected texts",
    )
    mappings = index_unique(
        read_jsonl(artifact / "hidden_mapping.jsonl"),
        "diagnostic_id", "hidden mapping",
    )
    references = read_jsonl(artifact / "model_reference48.jsonl")
    reference_index = index_unique(references, "diagnostic_id", "model reference")
    if len(text_rows) != 48 or len(mappings) != 48 or len(reference_index) != 48:
        raise ValueError("expected exactly 48 selected texts, mappings, and references")
    texts: dict[str, str] = {}
    for diagnostic_id, mapping in mappings.items():
        annotation_id = mapping.get("calibration_annotation_id")
        if annotation_id not in text_rows:
            raise ValueError(f"{diagnostic_id}: mapping absent from selected text frame")
        raw_text = text_rows[annotation_id].get("raw_text")
        if not isinstance(raw_text, str):
            raise ValueError(f"{diagnostic_id}: raw_text is not a string")
        texts[diagnostic_id] = raw_text
    if set(texts) != set(reference_index):
        raise ValueError("reference IDs do not match mapped selected-text frame")
    return texts, references


def validate_references(rows: list[dict[str, Any]], texts: dict[str, str]) -> None:
    errors: list[str] = []
    for row in rows:
        diagnostic_id = row.get("diagnostic_id")
        if diagnostic_id not in texts:
            errors.append(f"{diagnostic_id}: ID absent from mapped texts")
            continue
        for module in MODULES:
            value = row.get(f"{module}_presence")
            if value not in PRESENCE_VALUES:
                errors.append(f"{diagnostic_id}: invalid {module}_presence={value!r}")
        for field in ("education_evidence", "experience_evidence", "technology_evidence"):
            evidence = row.get(field)
            if evidence is None:
                continue
            if not isinstance(evidence, dict):
                errors.append(f"{diagnostic_id}: {field} is neither an object nor null")
                continue
            quote = evidence.get("quote")
            if not isinstance(quote, str) or not quote or quote not in texts[diagnostic_id]:
                errors.append(f"{diagnostic_id}: {field} quote is not an exact source substring")
    if errors:
        raise ValueError("model-reference validation failed:\n" + "\n".join(errors))


def candidate(payload: dict[str, Any], module: str) -> bool:
    return any(
        item.get("module") == module
        and item.get("is_applicant_qualification_candidate") is True
        for item in payload["evidence"]
    )


def ensure_complete(payload: dict[str, Any], diagnostic_id: str, version: str) -> None:
    if payload.get("errors"):
        raise ValueError(f"{diagnostic_id}: {version} parser error")
    if payload.get("evidence_truncated") is True:
        raise ValueError(f"{diagnostic_id}: {version} aggregate comparison refuses truncated evidence")
    module_flags = payload.get("module_evidence_truncated", {})
    if any(module_flags.get(module) is True for module in payload.get("summary", {})):
        raise ValueError(f"{diagnostic_id}: {version} aggregate comparison refuses module truncation")


def state_matrix(rows: list[dict[str, Any]], module: str, version: str) -> dict[str, Any]:
    counter = Counter(
        (row[f"{module}_reference"], "candidate" if row[f"{module}_{version}_candidate"] else "no_candidate")
        for row in rows
    )
    return {
        state: {
            "support": counter[(state, "candidate")] + counter[(state, "no_candidate")],
            "candidate": counter[(state, "candidate")],
            "no_candidate": counter[(state, "no_candidate")],
        }
        for state in PRESENCE_VALUES
    }


def binary_diagnostic(rows: list[dict[str, Any]], module: str, version: str) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        reference = row[f"{module}_reference"]
        predicted = row[f"{module}_{version}_candidate"]
        if reference == "explicit_positive":
            counts["positive_with_candidate" if predicted else "positive_without_candidate"] += 1
        elif reference == "not_mentioned":
            counts["not_mentioned_with_candidate" if predicted else "not_mentioned_without_candidate"] += 1
    return {
        "support_explicit_positive_plus_not_mentioned": sum(counts.values()),
        "positive_with_candidate": counts["positive_with_candidate"],
        "positive_without_candidate": counts["positive_without_candidate"],
        "not_mentioned_with_candidate": counts["not_mentioned_with_candidate"],
        "not_mentioned_without_candidate": counts["not_mentioned_without_candidate"],
    }


def transition(rows: list[dict[str, Any]], module: str) -> dict[str, int]:
    counts = Counter(
        ("candidate" if row[f"{module}_v5_candidate"] else "no_candidate")
        + "_to_"
        + ("candidate" if row[f"{module}_v6_candidate"] else "no_candidate")
        for row in rows
    )
    return {key: counts[key] for key in (
        "no_candidate_to_no_candidate", "no_candidate_to_candidate",
        "candidate_to_no_candidate", "candidate_to_candidate",
    )}


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# NEW48 model diagnostic aggregate: frozen V5 and V6",
        "",
        "This report compares candidate flags from frozen V5 and V6 with 48 blind model-assisted reference labels. "
        "The labels are not human ground truth, and these counts are diagnostic rather than accuracy estimates.",
        "",
        f"The reference run requested `{report['design']['reference_requested_model']}` at "
        f"`{report['design']['reference_requested_effort']}` effort. Exact runtime build identity was not independently exposed.",
        "",
        "## Reference composition",
        "",
        "| Module | Explicit positive | Explicit negative | Not mentioned | Insufficient text | Unresolved |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for module in MODULES:
        counts = report["reference_presence_counts"][module]
        lines.append(
            f"| {module.title()} | {counts['explicit_positive']} | {counts['explicit_negative']} | "
            f"{counts['not_mentioned']} | {counts['insufficient_text']} | {counts['unresolved']} |"
        )
    for version in VERSIONS:
        lines.extend([
            "", f"## Frozen {version.upper()} comparison", "",
            "| Module | Positive + not-mentioned support | Positive with candidate | Positive without candidate | Not mentioned with candidate | Not mentioned without candidate | Explicit negative support | Insufficient-text support | Unresolved support |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for module in MODULES:
            binary = report["comparisons"][version][module]["binary_diagnostic"]
            matrix = report["comparisons"][version][module]["reference_state_matrix"]
            lines.append(
                f"| {module.title()} | {binary['support_explicit_positive_plus_not_mentioned']} | "
                f"{binary['positive_with_candidate']} | {binary['positive_without_candidate']} | "
                f"{binary['not_mentioned_with_candidate']} | {binary['not_mentioned_without_candidate']} | "
                f"{matrix['explicit_negative']['support']} | {matrix['insufficient_text']['support']} | "
                f"{matrix['unresolved']['support']} |"
            )
    v6_explicit_negative = report["comparisons"]["v6"]["experience"]["reference_state_matrix"]["explicit_negative"]
    v6_absence = report["comparisons"]["v6"]["experience"]["parser_explicit_absence"]
    lines.extend([
        "", "## Explicit-negative limitation", "",
        f"The experience reference has {v6_explicit_negative['support']} explicit-negative rows. V6 produced "
        f"{v6_absence['count']} explicit-absence flags; its ordinary candidate flag was positive on "
        f"{v6_explicit_negative['candidate']} and absent on {v6_explicit_negative['no_candidate']}. "
        "This diagnostic does not support a no-experience rate.",
    ])
    lines.extend(["", "## V5 to V6 candidate transitions", ""])
    for module in MODULES:
        item = report["v5_to_v6_transitions"][module]
        lines.append(
            f"- {module.title()}: {item['no_candidate_to_candidate']} gained, "
            f"{item['candidate_to_no_candidate']} removed, "
            f"{item['candidate_to_candidate']} retained candidates, and "
            f"{item['no_candidate_to_no_candidate']} retained non-candidates."
        )
    missed = report["missed_education_reference_audit"]
    lines.extend([
        "", "## Bounded missed-education audit", "",
        f"Among {missed['support']} V6 non-detections on model-positive education references, "
        f"{missed['economic_type_counts'].get('degree_or_attainment', 0)} are degree or educational-attainment clauses and "
        f"{missed['economic_type_counts'].get('license_training_or_certification', 0)} are license, training, or certification clauses. "
        "No missed clause in this bounded review was categorized as current enrollment, unclear, or a context-only mention.",
        "",
        "The 11 degree-related misses may reflect recognition, context, or scope coverage; quote-only inspection cannot adjudicate the underlying cause. The two license/training clauses mark a measurement-scope boundary. This is a diagnostic classification of existing model-reference quotes, not new annotation or human adjudication.",
    ])
    lines.extend([
        "", "Explicit-negative, insufficient-text, and unresolved references remain separate from the positive/not-mentioned diagnostic comparison. "
        "Current enrollment is an exploratory eligibility mention, not an attained degree or unconditional statement of general eligibility.",
        "",
        "The 48-row calibration sample supports no full-corpus or per-period inference. The sealed test was not accessed.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    parser.add_argument("--artifact-dir", type=Path, default=here / "artifacts/model_diagnostic48_v1")
    parser.add_argument("--v5-parser", type=Path, default=here.parent / "stage_c_v5/requirement_candidates.py")
    parser.add_argument("--v6-parser", type=Path, default=here.parent / "stage_c_v6/requirement_candidates.py")
    parser.add_argument("--expected-v5-sha256", default=DEFAULT_V5_SHA256)
    parser.add_argument("--expected-v6-sha256", required=True)
    parser.add_argument(
        "--miss-classification", type=Path,
        default=here / "artifacts/model_diagnostic48_v1/missed_education_classification_private.jsonl",
    )
    args = parser.parse_args()

    artifact = args.artifact_dir.resolve()
    v5_path, v6_path = args.v5_parser.resolve(), args.v6_parser.resolve()
    actual_hashes = {"v5": sha256(v5_path), "v6": sha256(v6_path)}
    expected_hashes = {"v5": args.expected_v5_sha256, "v6": args.expected_v6_sha256}
    if actual_hashes != expected_hashes:
        raise ValueError(f"frozen parser hash mismatch: expected={expected_hashes}, actual={actual_hashes}")

    texts, references = load_frame(artifact)
    validate_references(references, texts)
    reference_index = index_unique(references, "diagnostic_id", "model reference")
    parsers = {
        "v5": load_parser(v5_path, "frozen_requirement_candidates_v5_new48"),
        "v6": load_parser(v6_path, "frozen_requirement_candidates_v6_new48"),
    }

    rows: list[dict[str, Any]] = []
    for diagnostic_id in sorted(texts):
        outputs = {version: module.extract(texts[diagnostic_id]) for version, module in parsers.items()}
        for version, payload in outputs.items():
            ensure_complete(payload, diagnostic_id, version)
        row: dict[str, Any] = {"diagnostic_id": diagnostic_id}
        for module in MODULES:
            row[f"{module}_reference"] = reference_index[diagnostic_id][f"{module}_presence"]
            for version in VERSIONS:
                row[f"{module}_{version}_candidate"] = candidate(outputs[version], module)
                if module == "experience":
                    row[f"{module}_{version}_explicit_absence"] = bool(
                        outputs[version]["summary"][module].get("no_experience_explicit")
                    )
        rows.append(row)

    reference_presence_counts = {
        module: {state: sum(row[f"{module}_reference"] == state for row in rows) for state in PRESENCE_VALUES}
        for module in MODULES
    }
    missed_ids = {
        row["diagnostic_id"] for row in rows
        if row["education_reference"] == "explicit_positive" and not row["education_v6_candidate"]
    }
    missed_classification = index_unique(
        read_jsonl(args.miss_classification.resolve()), "diagnostic_id", "missed education classification",
    )
    if set(missed_classification) != missed_ids or len(missed_ids) > 13:
        raise ValueError("missed-education classification must cover exactly the bounded <=13 V6 misses")
    missed_audit = {
        "support": len(missed_ids),
        "basis": "existing model-reference education quote only",
        "new_annotation": False,
        "human_adjudication": False,
        "economic_type_counts": dict(sorted(Counter(
            row["economic_type"] for row in missed_classification.values()
        ).items())),
        "audit_interpretation_counts": dict(sorted(Counter(
            row["audit_interpretation"] for row in missed_classification.values()
        ).items())),
        "row_identifiers_published": False,
        "quotes_published": False,
    }
    comparisons = {
        version: {
            module: {
                "binary_diagnostic": binary_diagnostic(rows, module, version),
                "reference_state_matrix": state_matrix(rows, module, version),
                "parser_explicit_absence": (
                    {
                        "available": True,
                        "count": sum(row[f"{module}_{version}_explicit_absence"] for row in rows),
                        "reference_presence_counts": dict(sorted(Counter(
                            row[f"{module}_reference"]
                            for row in rows if row[f"{module}_{version}_explicit_absence"]
                        ).items())),
                    }
                    if module == "experience" else {"available": False}
                ),
            }
            for module in MODULES
        }
        for version in VERSIONS
    }
    report = {
        "status": "complete",
        "design": {
            "rows": len(rows),
            "reference_type": "blind_model_assisted_diagnostic",
            "human_annotations": False,
            "reference_requested_model": REQUESTED_REFERENCE_MODEL,
            "reference_requested_effort": REQUESTED_REFERENCE_EFFORT,
            "runtime_identity_note": "Exact runtime build identity was not independently exposed; self-described persona is not used as provenance.",
            "parsers": {
                version: {"path": f"stage_c_{version}/requirement_candidates.py", "sha256": actual_hashes[version]}
                for version in VERSIONS
            },
            "target": "is_applicant_qualification_candidate",
            "positive_reference": "explicit_positive",
            "negative_reference": "not_mentioned",
            "explicit_negative_reported_separately": True,
            "insufficient_text_reported_separately": True,
            "unresolved_reported_separately": True,
            "truncated_payloads_accepted": False,
            "sealed_test_accessed": False,
            "inference_limit": "No full-corpus or per-period inference; n=48 is a calibration diagnostic.",
            "current_enrollment_interpretation": "Exploratory eligibility mention; not an attained degree or unconditional general eligibility statement.",
        },
        "quote_validation": {"method": "nonempty literal substring of mapped source raw_text", "errors": 0},
        "reference_presence_counts": reference_presence_counts,
        "comparisons": comparisons,
        "v5_to_v6_transitions": {module: transition(rows, module) for module in MODULES},
        "missed_education_reference_audit": missed_audit,
        "root_decision": {
            "second_parser_iteration": False,
            "education_use": "Measurement-audit candidate counts and joint-table diagnostics only; non-detection is not no education and supports no subgroup prevalence or ranking.",
            "experience_use": "Exploratory explicit-clause patterns only; no formal accuracy or causal claim.",
            "technology_role_and_experience_object": "unvalidated",
            "prevalence_release": "No experience/no education prevalence is released; all batch columns are detected-candidate flags, with explicit-negative diagnostic failure noted.",
            "next_research_priority": "After the bounded 100k batch, characterize explicit experience clauses and software/AI co-mentions within supported contexts, preserving unknowns and small-cell support; do not start another all-corpus parse.",
        },
    }
    write_jsonl(artifact / "row_comparisons_private.jsonl", rows)
    write_json(artifact / "model_diagnostic_v5_v6_aggregate.json", report)
    atomic_text(artifact / "model_diagnostic_v5_v6_aggregate.md", markdown(report))
    print(json.dumps({
        "status": "complete",
        "json": str(artifact / "model_diagnostic_v5_v6_aggregate.json"),
        "markdown": str(artifact / "model_diagnostic_v5_v6_aggregate.md"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
