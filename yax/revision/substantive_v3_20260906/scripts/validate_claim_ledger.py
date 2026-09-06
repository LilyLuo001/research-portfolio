#!/usr/bin/env python3
"""Validate the canonical YAX V3 numerical-result and prose-claim ledgers."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any

from spec_contract import compute_result_id, sha256_file


class LedgerError(ValueError):
    pass


def _contained_file(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or ".." in rel.parts:
        raise LedgerError(f"unsafe source path: {relative!r}")
    path = (root / rel).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise LedgerError(f"source is not a regular contained file: {relative}")
    return path


def _json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise LedgerError("JSON pointer must be empty or begin with /")
    value = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise LedgerError(f"JSON pointer descends through scalar at {pointer}")
    return value


def _read_value(path: Path, selector: dict[str, Any]) -> Any:
    kind = selector.get("kind")
    if kind == "json_pointer":
        with path.open("r", encoding="utf-8") as stream:
            return _json_pointer(json.load(stream), selector.get("pointer", ""))
    if kind == "csv_key":
        keys = selector.get("keys")
        column = selector.get("column")
        if not isinstance(keys, dict) or not column:
            raise LedgerError("csv_key selector needs keys and column")
        with path.open("r", encoding="utf-8", newline="") as stream:
            matched = [row for row in csv.DictReader(stream)
                       if all(row.get(key) == str(value) for key, value in keys.items())]
        if len(matched) != 1:
            raise LedgerError(f"csv selector matched {len(matched)} rows, expected one")
        return matched[0][column]
    raise LedgerError(f"unsupported selector kind: {kind!r}")


def _equal_numeric(left: Any, right: Any, tolerance: float) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return left == right


def validate(results_doc: Any, claims_doc: Any, root: Path) -> tuple[int, int]:
    root = root.resolve(strict=True)
    if not isinstance(results_doc, dict) or results_doc.get("schema_version") != "yax-result-ledger-v1":
        raise LedgerError("invalid results ledger schema")
    if not isinstance(claims_doc, dict) or claims_doc.get("schema_version") != "yax-claim-ledger-v1":
        raise LedgerError("invalid claims ledger schema")
    results: dict[str, dict[str, Any]] = {}
    canonical_targets: dict[str, str] = {}
    for row in results_doc.get("results", []):
        path = _contained_file(root, row.get("source_path", ""))
        digest = sha256_file(path)
        if digest != row.get("source_sha256"):
            raise LedgerError(f"source hash mismatch: {row.get('source_path')}")
        selector = row.get("selector")
        selector_text = json.dumps(selector, sort_keys=True, separators=(",", ":"))
        expected = compute_result_id(row.get("spec_id", ""), row.get("logical_key", ""), digest, selector_text)
        if row.get("result_id") != expected:
            raise LedgerError(f"result_id mismatch for {row.get('logical_key')}")
        if row["result_id"] in results:
            raise LedgerError(f"duplicate result_id: {row['result_id']}")
        observed = _read_value(path, selector)
        if not _equal_numeric(observed, row.get("value"), float(row.get("tolerance", 0.0))):
            raise LedgerError(f"ledger value differs from source for {row['result_id']}")
        if row.get("canonical"):
            target = row.get("target_key")
            if not target:
                raise LedgerError("canonical result needs target_key")
            if target in canonical_targets:
                raise LedgerError(f"multiple canonical results for target {target}")
            canonical_targets[target] = row["result_id"]
        results[row["result_id"]] = row
    claim_ids: set[str] = set()
    for claim in claims_doc.get("claims", []):
        claim_id = claim.get("claim_id")
        if not claim_id or claim_id in claim_ids:
            raise LedgerError(f"missing or duplicate claim_id: {claim_id!r}")
        claim_ids.add(claim_id)
        result = results.get(claim.get("result_id"))
        if result is None:
            raise LedgerError(f"claim {claim_id} references unknown result")
        if not _equal_numeric(claim.get("value"), result.get("value"), float(result.get("tolerance", 0.0))):
            raise LedgerError(f"claim {claim_id} is a manuscript-only numerical patch")
        if not claim.get("locations"):
            raise LedgerError(f"claim {claim_id} has no output location")
        if claim.get("target_key") != result.get("target_key"):
            raise LedgerError(f"claim {claim_id} target_key differs from result")
        canonical_id = canonical_targets.get(claim.get("target_key"))
        if claim.get("canonical_target") and canonical_id != result["result_id"]:
            raise LedgerError(f"claim {claim_id} does not use declared canonical result")
    return len(results), len(claim_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.results.open("r", encoding="utf-8") as stream:
            results = json.load(stream)
        with args.claims.open("r", encoding="utf-8") as stream:
            claims = json.load(stream)
        n_results, n_claims = validate(results, claims, args.root.resolve(strict=True))
        print(json.dumps({"status": "PASS", "results": n_results, "claims": n_claims}, indent=2))
        return 0
    except (OSError, KeyError, IndexError, json.JSONDecodeError, LedgerError) as exc:
        print(f"LEDGER ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
