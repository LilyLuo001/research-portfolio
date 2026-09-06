#!/usr/bin/env python3
"""Validate YAX V3 run dependencies and cache fingerprints.

A successful cached run is usable only when its specification, code,
environment, command, upstream result IDs, upstream artifact hashes, and output
hashes match the manifest.  Failed branches remain recorded and block only
their descendants.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from spec_contract import SPEC_PREFIX, canonical_bytes, sha256_file


SHA256 = re.compile(r"^[0-9a-f]{64}$")
RUN_STATUSES = {"PLANNED", "RUNNING", "SUCCESS", "FAILED", "BLOCKED"}


class DependencyError(ValueError):
    pass


def compute_run_fingerprint(run: dict[str, Any]) -> str:
    dependencies = sorted(
        ({k: dep[k] for k in ("run_id", "result_id", "artifact_sha256")}
         for dep in run.get("dependencies", [])),
        key=lambda row: (row["run_id"], row["result_id"]),
    )
    payload = {
        "spec_id": run.get("spec_id"),
        "code_sha256": run.get("code_sha256"),
        "environment_sha256": run.get("environment_sha256"),
        "command": run.get("command"),
        "dependencies": dependencies,
    }
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _contained_file(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise DependencyError(f"unsafe artifact path: {relative!r}")
    path = (root / rel).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise DependencyError(f"artifact must be a regular contained file: {relative}")
    return path


def validate_manifest(document: Any, root: Path) -> dict[str, dict[str, Any]]:
    root = root.resolve(strict=True)
    if not isinstance(document, dict) or document.get("schema_version") != "yax-run-dag-v1":
        raise DependencyError("manifest schema_version must be yax-run-dag-v1")
    rows = document.get("runs")
    if not isinstance(rows, list):
        raise DependencyError("manifest runs must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("run_id"):
            raise DependencyError("each run needs run_id")
        if row["run_id"] in indexed:
            raise DependencyError(f"duplicate run_id: {row['run_id']}")
        if row.get("status") not in RUN_STATUSES:
            raise DependencyError(f"invalid run status for {row['run_id']}")
        indexed[row["run_id"]] = row

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(run_id: str) -> None:
        if run_id in visiting:
            raise DependencyError(f"dependency cycle includes {run_id}")
        if run_id in visited:
            return
        visiting.add(run_id)
        for dependency in indexed[run_id].get("dependencies", []):
            upstream = dependency.get("run_id")
            if upstream not in indexed:
                raise DependencyError(f"{run_id} has unknown dependency {upstream}")
            visit(upstream)
        visiting.remove(run_id)
        visited.add(run_id)

    for run_id in indexed:
        visit(run_id)

    for run_id, row in indexed.items():
        spec_id = row.get("spec_id", "")
        if not isinstance(spec_id, str) or not spec_id.startswith(SPEC_PREFIX):
            raise DependencyError(f"{run_id} has invalid spec_id")
        for field in ("code_sha256", "environment_sha256"):
            if not SHA256.fullmatch(str(row.get(field, ""))):
                raise DependencyError(f"{run_id} has invalid {field}")
        expected = compute_run_fingerprint(row)
        if row.get("run_fingerprint") != expected:
            raise DependencyError(f"{run_id} cache fingerprint mismatch")
        if row["status"] == "SUCCESS":
            for dependency in row.get("dependencies", []):
                upstream = indexed[dependency["run_id"]]
                if upstream["status"] != "SUCCESS":
                    raise DependencyError(
                        f"{run_id} cannot succeed after {upstream['run_id']} status {upstream['status']}"
                    )
                exported = {item["result_id"]: item for item in upstream.get("outputs", [])}
                actual = exported.get(dependency.get("result_id"))
                if not actual or actual.get("sha256") != dependency.get("artifact_sha256"):
                    raise DependencyError(f"{run_id} dependency fingerprint is stale for {upstream['run_id']}")
            outputs = row.get("outputs")
            if not isinstance(outputs, list) or not outputs:
                raise DependencyError(f"successful run {run_id} has no outputs")
            for output in outputs:
                path = _contained_file(root, output.get("path", ""))
                if sha256_file(path) != output.get("sha256"):
                    raise DependencyError(f"output hash mismatch for {run_id}: {output.get('path')}")
        elif row["status"] == "FAILED":
            failure = row.get("failure")
            if not isinstance(failure, dict) or not failure.get("message") or not failure.get("log_path"):
                raise DependencyError(f"failed run {run_id} lacks retained failure evidence")
            log = _contained_file(root, failure["log_path"])
            if sha256_file(log) != failure.get("log_sha256"):
                raise DependencyError(f"failure-log hash mismatch for {run_id}")
    return indexed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--require-success", nargs="*", default=[])
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        with args.manifest.open("r", encoding="utf-8") as stream:
            indexed = validate_manifest(json.load(stream), root)
        missing = [run_id for run_id in args.require_success
                   if run_id not in indexed or indexed[run_id]["status"] != "SUCCESS"]
        if missing:
            raise DependencyError("gate requirements are not successful: " + ", ".join(missing))
        counts: dict[str, int] = {}
        for row in indexed.values():
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        print(json.dumps({"status": "PASS", "runs": len(indexed), "status_counts": counts}, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, DependencyError) as exc:
        print(f"DEPENDENCY ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
