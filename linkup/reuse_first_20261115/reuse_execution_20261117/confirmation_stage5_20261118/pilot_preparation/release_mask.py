"""Offline necessary-condition masks; no queue, payload, model, or runtime access."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping


PROTOCOL_SHA256 = "d43e2a065cc516772ae0c31d4fff2c7dc2860c41257002f247fa21748e2b8598"
BUNDLE_SHA256 = "fdf07cec40eef5ce3ed1ac4e2cb7bcf435403ccbaa7aa240f6625b9d27792f11"
SCORER_SHA256 = "2c37e739154296ea969da4126fe92bc922a8d1e5c07c4a42bcca505e9caa5ae0"


class MaskError(ValueError):
    """Fixed codes only; no source values or identities in errors."""


def require(condition, code):
    if not condition:
        raise MaskError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha_pin(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "invalid_sha_pin")
    return value


def parse(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def invalid_number(_):
        raise MaskError("nonfinite_json_number")

    def decimal(value):
        number = float(value)
        require(math.isfinite(number), "nonfinite_json_number")
        return number

    try:
        result = json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_number,
                            parse_float=decimal)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MaskError("invalid_json") from exc
    require(isinstance(result, dict), "json_object_required")
    return result


def pinned_json(path, expected):
    data = Path(path).read_bytes()
    require(digest(data) == sha_pin(expected), "artifact_sha_mismatch")
    return parse(data)


def exact_ids(values, allowed, code):
    require(isinstance(values, (list, tuple, set, frozenset)), code)
    require(all(isinstance(value, str) for value in values), code)
    require(len(values) == len(set(values)) and set(values) <= set(allowed), code)
    return frozenset(values)


@dataclass(frozen=True)
class PinnedGate:
    protocol_version: str
    score_sha256: str
    frame_sha256: str
    measure_fields: Mapping[str, str]
    eligible_measure_dependencies: frozenset[str]


def load_gate(protocol_directory, scores_path, *, expected_score_sha256, expected_frame_sha256):
    """Read the original frozen protocol and original scorer aggregate only.

    Score/frame pins MUST come from trusted existing scoring/freeze receipts,
    not by hashing an untrusted aggregate and passing that hash back as approval.
    This verifies bytes and internal consistency, not independent-model lineage.
    """
    directory = Path(protocol_directory)
    bundle = pinned_json(directory / "PROTOCOL_FREEZE.json", BUNDLE_SHA256)
    require(bundle["files"].get("CONFIRMATION_PROTOCOL.json") == PROTOCOL_SHA256
            and bundle["files"].get("field_score.py") == SCORER_SHA256, "frozen_bundle_mismatch")
    for name, expected in bundle["files"].items():
        require(Path(name).name == name, "unexpected_bundle_path")
        require(digest((directory / name).read_bytes()) == expected, "frozen_member_sha_mismatch")
    protocol = pinned_json(directory / "CONFIRMATION_PROTOCOL.json", PROTOCOL_SHA256)
    scores = pinned_json(scores_path, expected_score_sha256)
    frame_sha = sha_pin(expected_frame_sha256)
    require(isinstance(scores.get("freeze_binding"), dict)
            and scores["freeze_binding"].get("frozen_before_first_request") is True,
            "score_freeze_binding_mismatch")
    require(scores.get("freeze_binding") == {
        "frame_sha256": frame_sha,
        "protocol_bundle_sha256": BUNDLE_SHA256,
        "frozen_before_first_request": True,
    }, "score_freeze_binding_mismatch")
    require(scores.get("protocol_version") == protocol["version"], "score_protocol_mismatch")
    require(scores.get("production_admission") is False
            and scores.get("production_requires_qualified_dependency_subset_and_external_runtime_controls") is True
            and scores.get("machine_reference_agreement_is_not_gold_accuracy") is True
            and scores.get("population_generalization_certified") is False,
            "score_boundary_flags_mismatch")
    fields = {spec["id"]: spec["field"] for spec in protocol["measures"]}
    results = scores.get("measure_results", {})
    require(isinstance(results, dict) and set(results) == {"confirmation", "challenge"},
            "original_measure_results_required")
    passed = set()
    partition_sizes = []
    for partition in ("confirmation", "challenge"):
        rows = results[partition]
        require(isinstance(rows, dict) and set(rows) == set(fields), "measure_roster_mismatch")
        sizes = set()
        for measure, row in rows.items():
            require(isinstance(row, dict), "invalid_measure_result")
            flag, reasons = row.get("machine_reference_measure_gate_pass"), row.get("blocking_reasons")
            require(type(flag) is bool and isinstance(reasons, list)
                    and all(isinstance(reason, str) for reason in reasons)
                    and flag == (len(reasons) == 0), "inconsistent_measure_gate")
            cases = row.get("cases")
            require(type(cases) is int and 0 <= cases <= protocol["authorization"]["fresh_input_cap"],
                    "invalid_partition_count")
            sizes.add(cases)
            if partition == "challenge":
                require(not flag and "challenge_diagnostic_only" in reasons, "challenge_cannot_qualify")
            elif flag:
                passed.add(measure)
        require(len(sizes) == 1, "inconsistent_partition_counts")
        partition_sizes.extend(sizes)
    accounting = scores.get("accounting", {})
    require(isinstance(accounting, dict) and type(accounting.get("frame_cases")) is int
            and 0 < accounting["frame_cases"] <= protocol["authorization"]["fresh_input_cap"]
            and sum(partition_sizes) == accounting["frame_cases"], "frame_accounting_mismatch")
    declared = exact_ids(scores.get("eligible_measure_dependencies"), fields, "invalid_eligible_measure_ids")
    require(declared == passed, "eligible_list_gate_mismatch")
    require(bool(passed), "no_independently_eligible_measure")
    return PinnedGate(protocol["version"], expected_score_sha256, frame_sha,
                      MappingProxyType(fields), frozenset(passed))


def row_mask(gate, *, declared_missing_measures, validation, observations, derived_dependencies=None):
    """Intersect exact qualified IDs, declared missing IDs, and valid known row measures.

    ``validation`` is the unchanged FieldValidator.validate result.
    ``observations`` maps exact IDs to unchanged field_score.observe results.
    Caller binds both to the same output/source before calling; this helper never
    inspects source bodies and cannot establish genuine missingness or freshness.
    Derived declarations are explicit complete dependency lists, never inferred.
    Their closure result is necessary only and grants no new construct qualification.
    """
    require(isinstance(gate, PinnedGate) and bool(gate.eligible_measure_dependencies), "pinned_gate_required")
    missing = exact_ids(declared_missing_measures, gate.measure_fields, "invalid_missing_measure_ids")
    require(isinstance(validation, dict) and isinstance(observations, dict), "row_metadata_required")
    exact_ids(list(observations), gate.measure_fields, "invalid_observation_measure_ids")
    local_fields = validation.get("fields", {})
    require(isinstance(local_fields, dict) and set(local_fields) <= set(gate.measure_fields.values()),
            "invalid_validation_field_ids")
    released, denied = [], {}
    for measure in sorted(missing):
        local = local_fields.get(gate.measure_fields[measure], {})
        observation = observations.get(measure, {})
        require(isinstance(local, dict) and isinstance(observation, dict), "invalid_row_state")
        if measure not in gate.eligible_measure_dependencies:
            reason = "not_independently_eligible"
        elif validation.get("status") != "field_checks_completed" or validation.get("production_admission") is not False:
            reason = "shared_or_unvalidated_row"
        elif not (local.get("status") == "engineering_valid" and local.get("errors") == []
                  and local.get("inventory_scope") == "full" and local.get("field_review_complete") is True):
            reason = "field_not_complete_engineering_valid"
        elif not (observation.get("status") == "known"
                  and observation.get("outcome") in ("present", "not_mentioned")
                  and isinstance(observation.get("atoms"), list)):
            reason = "measure_unknown_invalid_or_unobserved"
        else:
            released.append(measure)
            continue
        denied[measure] = reason
    derived = {} if derived_dependencies is None else derived_dependencies
    require(isinstance(derived, dict), "explicit_derived_dependency_map_required")
    closures = {}
    for quantity, dependencies in derived.items():
        require(isinstance(quantity, str) and bool(quantity) and quantity not in gate.measure_fields,
                "invalid_derived_quantity_id")
        dependency_ids = exact_ids(dependencies, gate.measure_fields, "invalid_derived_dependency_ids")
        require(bool(dependency_ids), "empty_derived_dependency_list")
        closures[quantity] = dependency_ids <= set(released)
    return {
        "status": "offline_release_mask_only",
        "protocol_version": gate.protocol_version,
        "protocol_sha256": PROTOCOL_SHA256,
        "protocol_bundle_sha256": BUNDLE_SHA256,
        "scores_sha256": gate.score_sha256,
        "frame_sha256": gate.frame_sha256,
        "eligible_measure_dependencies": sorted(gate.eligible_measure_dependencies),
        "release_measure_dependencies": released,
        "denied_missing_measures": denied,
        "derived_all_declared_dependencies_released": closures,
        "derived_qualification_granted": False,
        "production_admission": False,
        "freshness_budget_claim_and_row_binding_verified_by_helper": False,
    }
