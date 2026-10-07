#!/usr/bin/env python3
"""Validate compact outputs and deterministically add caller metadata and quote offsets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema" / "compact_model_output.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
SCHEMA_VALIDATOR = Draft202012Validator(SCHEMA)
OBJECTS = {"general_work", "occupation_task", "industry_domain"}
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
NUMBER_TOKEN = r"(?:\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
NUMBER_EXPRESSION = rf"{NUMBER_TOKEN}(?:\s+and\s+(?:a\s+)?half)?"
MINIMUM_CUE = re.compile(r"\b(?:at least|minimum(?: of)?|or more|more than|no less than)\b|\+")
MAXIMUM_CUE = re.compile(r"\b(?:up to|at most|maximum(?: of)?|no more than|less than)\b")
EXACT_CUE = re.compile(r"\bexactly\b")
RANGE_CUE = re.compile(
    rf"\bbetween\s+{NUMBER_EXPRESSION}\s+and\s+{NUMBER_EXPRESSION}\b|"
    rf"(?<!\w){NUMBER_EXPRESSION}\s*(?:to|through|[-–—])\s*{NUMBER_EXPRESSION}(?!\w)"
)
BARE_DURATION_QUOTE = re.compile(
    rf"\s*(?:(?:at\s+least|minimum(?:\s+of)?|exactly|more\s+than|no\s+less\s+than)\s+)?"
    rf"{NUMBER_TOKEN}(?:\s+and\s+(?:a\s+)?half)?"
    rf"(?:\s*(?:-|–|—|to|through)\s*{NUMBER_TOKEN}(?:\s+and\s+(?:a\s+)?half)?)?"
    rf"\s*\+?\s*years?\s*(?:or\s+more)?\s*",
    re.IGNORECASE,
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows, errors = [], []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
    return rows, errors


def locate_unique(text: str, quote: str, path: str) -> tuple[dict[str, Any] | None, list[str]]:
    starts = []
    position = text.find(quote)
    while position >= 0:
        starts.append(position)
        position = text.find(quote, position + 1)
    if not starts:
        return None, [f"{path}: quote is not an exact source substring"]
    if len(starts) != 1:
        return None, [f"{path}: quote occurs {len(starts)} times; provide a longer unique exact quote"]
    start = starts[0]
    return {"start": start, "end": start + len(quote), "text": quote}, []


def number_values(text: str) -> set[float]:
    lowered = text.lower()
    values = {float(value) for value in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", lowered)}
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+and\s+(?:a\s+)?half\b", lowered):
            values.add(value + 0.5)
        if re.search(rf"\b{word}\b", lowered):
            values.add(float(value))
    return values


def has_year_amount(quote: str) -> bool:
    return bool(re.search(r"\byears?\b", quote.lower()) and number_values(quote))


def close_enough(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0, abs_tol=1e-9)


def duration_errors(duration: dict[str, Any] | None, quote: str, mode: str, path: str) -> list[str]:
    errors: list[str] = []
    lowered = quote.lower()
    observed = number_values(quote)
    if duration is None:
        return errors
    if mode != "prior_experience":
        errors.append(f"{path}: duration is allowed only for condition_mode=prior_experience")
    if not re.search(r"\byears?\b", lowered):
        errors.append(f"{path}: duration quote has no year unit")
    if MAXIMUM_CUE.search(lowered):
        errors.append(f"{path}: maximum-only duration is unsupported in this compact test")
    kind = duration["kind"]
    expected = [duration["lower"], duration["upper"]] if kind == "range" else [duration["value"]]
    for value in expected:
        if not any(close_enough(value, found) for found in observed):
            errors.append(f"{path}: duration value {value} is not supported by the exact quote")
    if kind == "range":
        if duration["lower"] > duration["upper"]:
            errors.append(f"{path}: range lower exceeds upper")
        if not RANGE_CUE.search(lowered):
            errors.append(f"{path}: range interpretation lacks a range cue")
    elif kind == "minimum" and not MINIMUM_CUE.search(lowered):
        errors.append(f"{path}: minimum interpretation lacks a minimum cue")
    elif kind == "exact" and not EXACT_CUE.search(lowered):
        errors.append(f"{path}: exact interpretation lacks an exact cue")
    elif kind == "stated_unspecified" and (
        MINIMUM_CUE.search(lowered) or RANGE_CUE.search(lowered) or EXACT_CUE.search(lowered) or MAXIMUM_CUE.search(lowered)
    ):
        errors.append(f"{path}: stated_unspecified conflicts with an explicit interpretation cue")
    return errors


def validate_and_expand(prediction: dict[str, Any], source: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors = [
        f"schema:{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(SCHEMA_VALIDATOR.iter_errors(prediction), key=lambda item: str(list(item.absolute_path)))
    ]
    if errors:
        return None, errors
    text = source.get("original_text")
    record_id = source.get("record_id")
    if not isinstance(text, str) or not isinstance(record_id, (str, int)):
        return None, ["source row requires record_id and string original_text"]
    objects = [finding["object"] for finding in prediction["findings"]]
    if set(objects) != OBJECTS or len(set(objects)) != 3:
        errors.append("findings must contain each compact object exactly once")

    expanded_findings = []
    for finding in prediction["findings"]:
        obj, state = finding["object"], finding["state"]
        state_quote, mentions = finding["state_quote"], finding["mentions"]
        base = f"{obj}"
        if state == "positive":
            if state_quote is not None:
                errors.append(f"{base}: positive requires state_quote=null")
            if not mentions:
                errors.append(f"{base}: positive requires at least one mention")
        elif state == "not_mentioned":
            if state_quote is not None or mentions:
                errors.append(f"{base}: not_mentioned requires null state_quote and no mentions")
        else:
            if not isinstance(state_quote, str) or not state_quote:
                errors.append(f"{base}: {state} requires an exact state_quote")
            if mentions:
                errors.append(f"{base}: {state} cannot carry positive mentions")

        state_evidence = None
        if isinstance(state_quote, str) and state_quote:
            state_evidence, found = locate_unique(text, state_quote, f"{base}.state_quote")
            errors.extend(found)
            if state_evidence is not None:
                state_evidence["span_id"] = f"s_{obj}_state"

        expanded_mentions = []
        for index, mention in enumerate(mentions, 1):
            path = f"{base}.mentions[{index - 1}]"
            if BARE_DURATION_QUOTE.fullmatch(mention["quote"]):
                errors.append(f"{path}: quote cannot be a bare duration; include the full phrase that binds it to the experience object")
            evidence, found = locate_unique(text, mention["quote"], f"{path}.quote")
            errors.extend(found)
            errors.extend(duration_errors(mention["duration"], mention["quote"], mention["condition_mode"], f"{path}.duration"))
            if mention["qualification_scope"] in {"education_substitution", "other_conditional"} and len(mention["quote"]) < 8:
                errors.append(f"{path}: conditional scope requires a quote long enough to carry condition evidence")
            expanded = {key: value for key, value in mention.items() if key != "quote"}
            if evidence is not None:
                evidence["span_id"] = f"m_{obj}_{index}"
            expanded["evidence"] = evidence
            expanded_mentions.append(expanded)
        expanded_findings.append({
            "object": obj,
            "state": state,
            "state_evidence": state_evidence,
            "mentions": expanded_mentions,
        })

    if errors:
        return None, errors
    return {
        "schema_version": "linkup_compact_measurement_v1.0.0",
        "prompt_version": "linkup_compact_extraction_v1.0.0",
        "record_id": str(record_id),
        "source_text_sha256": sha256_text(text),
        "findings": expanded_findings,
    }, []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    sources, source_parse_errors = read_jsonl(args.source)
    predictions, prediction_parse_errors = read_jsonl(args.predictions)
    failures: list[dict[str, Any]] = []
    expanded: list[dict[str, Any]] = []
    if len(predictions) != len(sources):
        failures.append({"index": None, "errors": [f"source/prediction count differs: {len(sources)} != {len(predictions)}"]})
    for index, (source, prediction) in enumerate(zip(sources, predictions), 1):
        record, errors = validate_and_expand(prediction, source)
        if errors:
            failures.append({"index": index, "errors": errors})
        elif record is not None:
            expanded.append(record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in expanded),
        encoding="utf-8",
    )
    categories = Counter(error.split(":", 1)[0] for failure in failures for error in failure["errors"])
    receipt = {
        "schema_version": "linkup_compact_validation_receipt_v1",
        "source_records": len(sources),
        "prediction_records": len(predictions),
        "valid_records": len(expanded),
        "failed_records": len(failures),
        "source_parse_errors": source_parse_errors,
        "prediction_parse_errors": prediction_parse_errors,
        "error_category_counts": dict(sorted(categories.items())),
        "failures": failures,
        "repairs_applied": 0,
        "note": "The validator adds caller metadata and unique exact quote offsets only. It never deletes or overwrites a model label.",
    }
    args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if not source_parse_errors and not prediction_parse_errors and not failures and len(expanded) == len(sources) else 1


if __name__ == "__main__":
    raise SystemExit(main())
