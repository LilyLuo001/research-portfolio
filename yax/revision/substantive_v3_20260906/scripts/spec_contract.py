#!/usr/bin/env python3
"""Create and verify immutable YAX V3 analysis specification identifiers.

The identifier is a SHA-256 digest of canonical JSON after removing only the
top-level ``spec_id`` field.  A change to an analysis-defining field therefore
creates a different identifier.  This module does not infer missing choices or
recompute exposure assignments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable


SCHEMA_VERSION = "yax-canonical-spec-v1"
SPEC_PREFIX = "yaxspec_v1_"
RESULT_PREFIX = "yaxresult_v1_"
SHA256 = re.compile(r"^[0-9a-f]{64}$")

# These paths implement EXECUTION_PROMPT_V3.md section 4.2.  Values may be
# explicit null only where the specification explains why the item does not
# apply; omission is never allowed.
REQUIRED_PATHS = (
    "schema_version",
    "analysis.name",
    "analysis.status",
    "data.sources",
    "data.microdata_eligibility",
    "data.variable_universe",
    "occupation.taxonomy",
    "occupation.family_assignment",
    "occupation.crosswalk",
    "occupation.universe",
    "occupation.analysis_subset",
    "occupation.subgroup_eligibility",
    "outcome.units",
    "outcome.cell_construction",
    "outcome.age_groups",
    "calendar.observed_window",
    "calendar.estimation_window",
    "calendar.transition_handling",
    "calendar.missing_handling",
    "exposure.version",
    "exposure.raw_scale",
    "exposure.construction_weights",
    "exposure.construction_age_universe",
    "exposure.training_dates",
    "exposure.cutoffs",
    "exposure.tie_rule",
    "exposure.fixed_membership",
    "exposure.webb_normalization",
    "estimator.objective",
    "estimator.nuisance_column_space",
    "estimator.identifying_normalizations",
    "estimator.separation_treatment",
    "estimator.boundary_handling",
    "estimator.solver",
    "target.contrast",
    "target.temporal_weights",
    "uncertainty.source",
    "uncertainty.resampling_unit",
    "uncertainty.multiplier_matrix",
    "uncertainty.generated_objects",
    "dependencies",
    "execution.command",
    "execution.code_sha256",
    "execution.environment_sha256",
    "outputs.locations",
)


class ContractError(ValueError):
    """Raised when a specification or compatibility assertion is invalid."""


def _reject_nonfinite(value: Any, path: str = "$") -> None:
    if value is None:
        raise ContractError(
            f"null at {path}; encode inapplicability as a documented object rather than an unexplained null"
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError(f"non-finite number at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_nonfinite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_nonfinite(child, f"{path}[{index}]")


def canonical_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON, rejecting NaN and infinities."""
    _reject_nonfinite(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _without_spec_id(spec: dict[str, Any]) -> dict[str, Any]:
    clean = dict(spec)
    clean.pop("spec_id", None)
    return clean


def compute_spec_id(spec: dict[str, Any]) -> str:
    return SPEC_PREFIX + hashlib.sha256(canonical_bytes(_without_spec_id(spec))).hexdigest()


def get_path(document: Any, dotted_path: str) -> Any:
    value = document
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ContractError(f"missing required field: {dotted_path}")
        value = value[part]
    return value


def _require_hash(value: Any, label: str) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ContractError(f"{label} must be a lowercase SHA-256 digest")


def validate_spec(spec: Any, require_id: bool = True) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ContractError("specification must be a JSON object")
    for path in REQUIRED_PATHS:
        get_path(spec, path)
    if spec["schema_version"] != SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {SCHEMA_VERSION!r}")
    sources = get_path(spec, "data.sources")
    if not isinstance(sources, list) or not sources:
        raise ContractError("data.sources must be a nonempty list")
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ContractError(f"data.sources[{index}] must be an object")
        for field in ("source_id", "vintage", "sha256", "access_class"):
            if field not in source:
                raise ContractError(f"data.sources[{index}] missing {field}")
        _require_hash(source["sha256"], f"data.sources[{index}].sha256")
        if source["source_id"] in source_ids:
            raise ContractError(f"duplicate source_id: {source['source_id']}")
        source_ids.add(source["source_id"])
    for path in (
        "occupation.crosswalk.sha256",
        "occupation.universe.membership_sha256",
        "exposure.fixed_membership.sha256",
        "execution.code_sha256",
        "execution.environment_sha256",
    ):
        _require_hash(get_path(spec, path), path)
    dependencies = get_path(spec, "dependencies")
    if not isinstance(dependencies, list):
        raise ContractError("dependencies must be a list")
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise ContractError(f"dependencies[{index}] must be an object")
        if not dependency.get("role") or not dependency.get("artifact_sha256"):
            raise ContractError(f"dependencies[{index}] needs role and artifact_sha256")
        _require_hash(dependency["artifact_sha256"], f"dependencies[{index}].artifact_sha256")
    locations = get_path(spec, "outputs.locations")
    if not isinstance(locations, list) or not locations:
        raise ContractError("outputs.locations must be a nonempty list")
    _reject_nonfinite(spec)
    if require_id:
        expected = compute_spec_id(spec)
        if spec.get("spec_id") != expected:
            raise ContractError(f"spec_id mismatch: expected {expected}")
    return spec


def stamp_spec(spec: dict[str, Any]) -> dict[str, Any]:
    validate_spec(spec, require_id=False)
    stamped = dict(spec)
    stamped["spec_id"] = compute_spec_id(stamped)
    validate_spec(stamped, require_id=True)
    return stamped


def assert_compatible(left: dict[str, Any], right: dict[str, Any], paths: Iterable[str]) -> None:
    validate_spec(left)
    validate_spec(right)
    differences = []
    for path in paths:
        lvalue = get_path(left, path)
        rvalue = get_path(right, path)
        if canonical_bytes(lvalue) != canonical_bytes(rvalue):
            differences.append(path)
    if differences:
        raise ContractError("incompatible specification fields: " + ", ".join(differences))


def compute_result_id(
    spec_id: str, logical_key: str, artifact_sha256: str, selector: str,
) -> str:
    if not spec_id.startswith(SPEC_PREFIX) or len(spec_id) != len(SPEC_PREFIX) + 64:
        raise ContractError("invalid spec_id")
    _require_hash(artifact_sha256, "artifact_sha256")
    if not logical_key or not selector:
        raise ContractError("logical_key and selector must be nonempty")
    payload = {
        "artifact_sha256": artifact_sha256,
        "logical_key": logical_key,
        "selector": selector,
        "spec_id": spec_id,
    }
    return RESULT_PREFIX + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=_unique_pairs,
                         parse_constant=lambda value: (_ for _ in ()).throw(
                             ContractError(f"invalid JSON numeric constant: {value}")))


def write_new_json(path: Path, value: Any) -> None:
    if path.exists():
        raise ContractError(f"refusing to overwrite immutable contract: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("spec", type=Path)
    stamp = sub.add_parser("stamp")
    stamp.add_argument("source", type=Path)
    stamp.add_argument("destination", type=Path)
    identify = sub.add_parser("id")
    identify.add_argument("spec", type=Path)
    compatible = sub.add_parser("compatible")
    compatible.add_argument("left", type=Path)
    compatible.add_argument("right", type=Path)
    compatible.add_argument("--paths", nargs="+", required=True)
    result = sub.add_parser("result-id")
    result.add_argument("spec", type=Path)
    result.add_argument("artifact", type=Path)
    result.add_argument("--logical-key", required=True)
    result.add_argument("--selector", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.action == "validate":
            spec = validate_spec(load_json(args.spec))
            print(json.dumps({"status": "PASS", "spec_id": spec["spec_id"]}))
        elif args.action == "stamp":
            stamped = stamp_spec(load_json(args.source))
            write_new_json(args.destination, stamped)
            print(stamped["spec_id"])
        elif args.action == "id":
            spec = validate_spec(load_json(args.spec))
            print(spec["spec_id"])
        elif args.action == "compatible":
            assert_compatible(load_json(args.left), load_json(args.right), args.paths)
            print(json.dumps({"status": "PASS", "paths": args.paths}))
        elif args.action == "result-id":
            spec = validate_spec(load_json(args.spec))
            print(compute_result_id(
                spec["spec_id"], args.logical_key, sha256_file(args.artifact), args.selector,
            ))
        return 0
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"CONTRACT ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
