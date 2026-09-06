from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import errno
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

import pytest


HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / "normalize_public_receipts.py"
LOADER = importlib.util.spec_from_file_location("yax_gate1_transfer", SCRIPT)
assert LOADER is not None and LOADER.loader is not None
TRANSFER = importlib.util.module_from_spec(LOADER)
sys.modules[LOADER.name] = TRANSFER
LOADER.loader.exec_module(TRANSFER)

CELL_ARTIFACT_SHA = "7" * 64
ASSIGNMENT_SHA = "8" * 64
ASSIGNMENT_ARTIFACT_SHA = "9" * 64
RUN_IDS = {
    "cells": "gate1_cells_sge_700001",
    "target": "gate1_target_sge_700002",
    "numerical": "gate1_numerical_sge_700003",
}
JOB_IDS = {"cells": "700001", "target": "700002", "numerical": "700003"}
ARGV = copy.deepcopy(TRANSFER.EXPECTED_SANITIZED_ARGV)
CAPTURE_NORMALIZER_STATE = TRANSFER.capture_normalizer_state
VERIFY_NORMALIZER_STATE = TRANSFER.verify_normalizer_state_unchanged
CAPTURE_AUTHORIZATION_STATE = TRANSFER.capture_committed_authorization_state


@pytest.fixture(autouse=True)
def committed_normalizer_fixture(monkeypatch):
    state = {
        "source_path": "yax/revision/substantive_v3_20260906/gate1_transfer/normalize_public_receipts.py",
        "source_sha256": digest(SCRIPT),
        "committed_source_sha256": digest(SCRIPT),
        "git_commit": "d" * 40,
        "git_tree": "b" * 40,
        "tracked_at_head": True,
        "tracked_worktree_clean": True,
        "untracked_nonignored_files_absent": True,
        "ignored_path_inventory_count": 0,
        "ignored_path_inventory_sha256": hashlib.sha256(b"").hexdigest(),
        "ignored_importable_or_executable_paths_in_v3_scope": 0,
        "tracked_path_inventory_count": 1,
        "tracked_path_inventory_sha256": hashlib.sha256(b"normalizer.py\0").hexdigest(),
    }
    monkeypatch.setattr(TRANSFER, "capture_normalizer_state", lambda: copy.deepcopy(state))
    monkeypatch.setattr(TRANSFER, "verify_normalizer_state_unchanged", lambda expected: None)
    authorization_public = {
        "schema_version": TRANSFER.PRE_EXECUTION_AUTHORIZATION_SCHEMA,
        "status": TRANSFER.PRE_EXECUTION_AUTHORIZATION_STATUS,
        "authorization_id": "yaxgate1auth_v1_" + "f" * 64,
        "authorization_file_sha256": "c" * 64,
        "authorization_git_commit": "d" * 40,
        "authorized_implementation_commit": "e" * 40,
        "issued_at_utc": "2026-09-06T00:00:00Z",
        "not_before_utc": "2026-09-06T00:00:00Z",
        "not_after_utc": "2026-09-07T00:00:00Z",
        "canonical_spec": copy.deepcopy(TRANSFER.CANONICAL_BINDING),
        "source_registry_sha256": "a" * 64,
        "modules": {
            key: {
                "typed_spec_id": TRANSFER.MODULE_CONTRACTS[key]["typed_spec"]["id"],
                "typed_spec_sha256": TRANSFER.MODULE_CONTRACTS[key]["typed_spec"]["sha256"],
                "code_sha256": TRANSFER.MODULE_CONTRACTS[key]["code_hash"],
            }
            for key in TRANSFER.MODULE_KEYS
        },
    }
    synthetic_authorization = TRANSFER.AuthorizationState(
        public=authorization_public,
        snapshot=None,
        committed_payload_sha256="0" * 64,
    )
    monkeypatch.setattr(
        TRANSFER,
        "capture_committed_authorization_state",
        lambda expected: copy.deepcopy(synthetic_authorization),
    )
    monkeypatch.setattr(
        TRANSFER,
        "verify_committed_authorization_state_unchanged",
        lambda expected: None,
    )
    monkeypatch.setattr(
        TRANSFER,
        "verify_normalizer_toolchain",
        lambda: {"status": "SYNTHETIC_PINNED_TOOLCHAIN_FOR_UNIT_TEST"},
    )
    monkeypatch.setattr(
        TRANSFER,
        "utc_wall_clock",
        lambda: datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc),
    )


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_binding(key: str, argv: list[str] | None = None) -> dict[str, object]:
    argv = copy.deepcopy(argv or ARGV[key])
    core: dict[str, object] = {
        "schema_version": TRANSFER.COMMAND_BINDING_SCHEMA,
        "status": TRANSFER.COMMAND_BINDING_STATUS,
        "module_key": key,
        "run_id": RUN_IDS[key],
        "scheduler_jobnumber": JOB_IDS[key],
        "sanitized_argv": argv,
        "sanitized_argv_sha256": hashlib.sha256(
            TRANSFER.canonical_bytes(argv)
        ).hexdigest(),
    }
    return {
        **core,
        "binding_sha256": hashlib.sha256(TRANSFER.canonical_bytes(core)).hexdigest(),
    }


def execution_runtime(key: str) -> dict[str, object]:
    value: dict[str, object] = {
        "status": "AUTHENTICATED_ISOLATED_PINNED_EXECUTABLES",
        "python_invocation": "<YAX_PYTHON_BIN>",
        "python_resolved_executable_sha256": TRANSFER.EXPECTED_PYTHON_RESOLVED_SHA256,
        "python_version": "3.13.8",
        "isolated_mode": True,
        "ignore_environment": True,
        "no_user_site": True,
        "safe_path": True,
        "git_invocation": "<YAX_GIT_BIN>",
        "git_resolved_executable_sha256": TRANSFER.EXPECTED_GIT_SHA256,
        "git_version": TRANSFER.EXPECTED_GIT_VERSION,
        "import_affecting_environment_absent": True,
    }
    if key == "numerical":
        value["omp_num_threads"] = "1"
    return value


def execution_authorization(key: str) -> dict[str, object]:
    contract = TRANSFER.MODULE_CONTRACTS[key]
    return {
        "schema_version": TRANSFER.PRE_EXECUTION_AUTHORIZATION_SCHEMA,
        "status": TRANSFER.PRE_EXECUTION_AUTHORIZATION_STATUS,
        "authorization_id": "yaxgate1auth_v1_" + "f" * 64,
        "authorization_file_sha256": "c" * 64,
        "authorization_git_commit": "d" * 40,
        "authorized_implementation_commit": "e" * 40,
        "issued_at_utc": "2026-09-06T00:00:00Z",
        "not_before_utc": "2026-09-06T00:00:00Z",
        "not_after_utc": "2026-09-07T00:00:00Z",
        "module_key": key,
        "typed_spec_id": contract["typed_spec"]["id"],
        "typed_spec_sha256": contract["typed_spec"]["sha256"],
        "code_sha256": contract["code_hash"],
        "source_registry_sha256": "a" * 64,
    }


def scheduler(job: str, start: str, end: str) -> dict[str, object]:
    return {
        "jobnumber": job,
        "qname": "econ.q",
        "hostname": "scc-ab1",
        "start_time": start,
        "end_time": end,
        "failed": 0,
        "exit_status": 0,
        "ru_wallclock": "60.0",
        "maxvmem": "512M",
        "qacct_export_provenance": {
            "status": "RUNNER_RECORDED_BYTE_PINNED_CONSISTENCY",
            "role": "scheduler_accounting_export",
            "qacct_resolved_executable_sha256": TRANSFER.EXPECTED_QACCT_SHA256,
            "qacct_version": TRANSFER.EXPECTED_QACCT_VERSION,
            "exporter_code_sha256": TRANSFER.QACCT_EXPORTER_SHA256,
            "join_rule": "one_delimiter_one_record_exact_jobnumber_nonarray",
        },
    }


def source_receipts() -> dict[str, dict[str, object]]:
    cells: dict[str, object] = {
        "schema_version": "yax-numerical-cells-receipt-v1",
        "status": "PASS_FRESH_AGGREGATE_REBUILD",
        "aggregate_schema_version": "yax-numerical-cells-v1",
        "canonical_spec_id": TRANSFER.CANONICAL_BINDING["id"],
        "canonical_spec_sha256": TRANSFER.CANONICAL_BINDING["sha256"],
        "analysis_spec_id": TRANSFER.NUMERICAL_SPEC_ID,
        "analysis_spec_sha256": TRANSFER.NUMERICAL_SPEC_SHA256,
        "cell_build_spec_id": TRANSFER.CELL_SPEC_ID,
        "cell_build_spec_sha256": TRANSFER.CELL_SPEC_SHA256,
        "generated_at_utc": "2026-09-06T12:00:30Z",
        "cells_filename": "aggregate_cells.csv",
        "cells_sha256": CELL_ARTIFACT_SHA,
        "runtime_code_hashes": {
            TRANSFER.CELL_CODE_PATH: TRANSFER.CELL_CODE_SHA256,
        },
        "builder_code_sha256": TRANSFER.CELL_CODE_SHA256,
        "builder_transitive_code_sha256": TRANSFER.CELL_TRANSITIVE_SHA256,
        "assignment_fingerprint_sha256": ASSIGNMENT_SHA,
        "assignment_fingerprint_artifact_sha256": ASSIGNMENT_ARTIFACT_SHA,
        "weight_application_count": 1,
        "balanced_grid_complete": True,
        "occupation_count": 468,
        "observed_month_count": 114,
        "cells_row_count": 53352,
        "grid": {
            "occupation_count": 468,
            "observed_month_count": 114,
            "row_count": 53352,
        },
        "contains_resolved_private_paths": False,
        "execution_command_binding": command_binding("cells"),
        "execution_runtime_authentication": execution_runtime("cells"),
        "pre_execution_authorization": execution_authorization("cells"),
        # Safe extra producer details must not leak into the public projection.
        "producer_internal_safe_note": "not projected",
    }
    return {"cells": cells}


def make_fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, object]]:
    source = tmp_path / "receipts"
    output = tmp_path / "public"
    receipts = source_receipts()
    dump(source / "cells/EXECUTION_RECEIPT.json", receipts["cells"])
    cells_receipt_sha = digest(source / "cells/EXECUTION_RECEIPT.json")

    receipts["target"] = {
        "schema_version": "yax-exact-target-audit-receipt-v1",
        "status": "PASS_EXACT_TARGET_AUDIT",
        "canonical_spec_id": TRANSFER.CANONICAL_BINDING["id"],
        "canonical_spec_sha256": TRANSFER.CANONICAL_BINDING["sha256"],
        "target_audit_spec_id": TRANSFER.TARGET_SPEC_ID,
        "target_audit_spec_sha256": TRANSFER.TARGET_SPEC_SHA256,
        "cell_build_spec_id": TRANSFER.CELL_SPEC_ID,
        "cell_build_spec_sha256": TRANSFER.CELL_SPEC_SHA256,
        "authenticated_cells_sha256": CELL_ARTIFACT_SHA,
        "source_aggregate_receipt_sha256": cells_receipt_sha,
        "generated_at_utc": "2026-09-06T12:02:30Z",
        "code_hashes": TRANSFER.TARGET_CODE_HASHES,
        "audit_result_id": "yaxtargetaudit_v1_" + "a" * 64,
        "artifact_hashes": {
            key: str(index + 1) * 64
            for index, key in enumerate(sorted(TRANSFER.TARGET_ARTIFACTS))
        },
        "execution_command_binding": command_binding("target"),
        "execution_runtime_authentication": execution_runtime("target"),
        "pre_execution_authorization": execution_authorization("target"),
    }
    receipts["numerical"] = {
        "schema_version": "yax-numerical-existence-receipt-v1",
        "status": "PASS_ALL_CORE_TARGETS_NUMERICALLY_AUDITED",
        "canonical_spec_id": TRANSFER.CANONICAL_BINDING["id"],
        "canonical_spec_sha256": TRANSFER.CANONICAL_BINDING["sha256"],
        "audit_spec_id": TRANSFER.NUMERICAL_SPEC_ID,
        "audit_spec_sha256": TRANSFER.NUMERICAL_SPEC_SHA256,
        "cells_sha256": CELL_ARTIFACT_SHA,
        "cells_receipt_sha256": cells_receipt_sha,
        "code_sha256": TRANSFER.NUMERICAL_CODE_SHA256,
        "artifact_safety_sha256": TRANSFER.ARTIFACT_SAFETY_SHA256,
        "cell_builder_sha256": TRANSFER.CELL_CODE_SHA256,
        "legacy_engine_sha256": TRANSFER.LEGACY_ENGINE_SHA256,
        "submitted_design_source_sha256": TRANSFER.NUMERICAL_SUBMITTED_CODE_HASHES,
        "started_at_utc": "2026-09-06T12:04:01Z",
        "finished_at_utc": "2026-09-06T12:09:59Z",
        "model_count": 11,
        "passed_model_count": 11,
        "protected_microdata_read_by_this_program": False,
        "output_hashes": {
            key: hashlib.sha256(key.encode()).hexdigest()
            for key in sorted(TRANSFER.NUMERICAL_ARTIFACTS)
        },
        "execution_command_binding": command_binding("numerical"),
        "execution_runtime_authentication": execution_runtime("numerical"),
        "pre_execution_authorization": execution_authorization("numerical"),
    }
    for key in ("target", "numerical"):
        dump(source / key / "EXECUTION_RECEIPT.json", receipts[key])

    schedulers = {
        "cells": scheduler(
            JOB_IDS["cells"], "Sun Sep 06 08:00:00 2026", "Sun Sep 06 08:01:00 2026"
        ),
        "target": scheduler(
            JOB_IDS["target"], "Sun Sep 06 08:02:00 2026", "Sun Sep 06 08:03:00 2026"
        ),
        "numerical": scheduler(
            JOB_IDS["numerical"], "Sun Sep 06 08:04:00 2026", "Sun Sep 06 08:10:00 2026"
        ),
    }
    for key, value in schedulers.items():
        dump(source / "scheduler" / f"{key}.json", value)

    modules: list[dict[str, object]] = []
    for key in TRANSFER.MODULE_KEYS:
        contract = TRANSFER.MODULE_CONTRACTS[key]
        receipt_rel = Path(contract["receipt_file"])
        scheduler_rel = Path(contract["scheduler_file"])
        module: dict[str, object] = {
            "key": key,
            "run_id": RUN_IDS[key],
            "module_receipt_file": str(receipt_rel),
            "module_receipt_sha256": digest(source / receipt_rel),
            "scheduler_record_file": str(scheduler_rel),
            "scheduler_record_sha256": digest(source / scheduler_rel),
            "expected_jobnumber": JOB_IDS[key],
            "expected_receipt_schema": contract["receipt_schema"],
            "expected_receipt_status": contract["receipt_status"],
            "canonical_id_pointer": "/canonical_spec_id",
            "canonical_sha256_pointer": "/canonical_spec_sha256",
            "typed_spec": copy.deepcopy(contract["typed_spec"]),
            "code_hash_pointer": contract["code_hash_pointer"],
            "expected_code_hash": contract["code_hash"],
            "mode": contract["mode"],
            "time_source": contract["time_source"],
            "depends_on": list(contract["depends_on"]),
            "scheduler_boundary_tolerance_seconds": contract[
                "scheduler_boundary_tolerance_seconds"
            ],
        }
        if key in {"cells", "target"}:
            module["generated_at_pointer"] = contract["generated_at_pointer"]
        if key == "numerical":
            module.update({
                "start_time_pointer": contract["start_time_pointer"],
                "end_time_pointer": contract["end_time_pointer"],
            })
        modules.append(module)
    spec: dict[str, object] = {
        "schema_version": TRANSFER.SPEC_SCHEMA,
        "status": TRANSFER.SPEC_STATUS,
        "canonical_spec": copy.deepcopy(TRANSFER.CANONICAL_BINDING),
        "scheduler_time_zone": "America/New_York",
        "execution_command_policy": TRANSFER.COMMAND_POLICY,
        "modules": modules,
    }
    spec_path = tmp_path / "terminal_spec.json"
    dump(spec_path, spec)
    return spec_path, source, output, spec


def find_module(spec: dict[str, object], key: str) -> dict[str, object]:
    return next(row for row in spec["modules"] if row["key"] == key)  # type: ignore[index]


def refresh_hash(
    spec: dict[str, object], source: Path, key: str, scheduler_only: bool = False
) -> None:
    module = find_module(spec, key)
    field = "scheduler_record_file" if scheduler_only else "module_receipt_file"
    hash_field = "scheduler_record_sha256" if scheduler_only else "module_receipt_sha256"
    module[hash_field] = digest(source / str(module[field]))


def mutate_receipt(
    spec_path: Path,
    source: Path,
    spec: dict[str, object],
    key: str,
    mutation,
) -> None:
    module = find_module(spec, key)
    path = source / str(module["module_receipt_file"])
    value = json.loads(path.read_text())
    mutation(value)
    dump(path, value)
    refresh_hash(spec, source, key)
    dump(spec_path, spec)


def refresh_downstream_cell_receipt_links(
    spec_path: Path, source: Path, spec: dict[str, object]
) -> None:
    cells_sha = digest(source / "cells/EXECUTION_RECEIPT.json")
    for key, field in (
        ("target", "source_aggregate_receipt_sha256"),
        ("numerical", "cells_receipt_sha256"),
    ):
        module = find_module(spec, key)
        path = source / str(module["module_receipt_file"])
        value = json.loads(path.read_text())
        value[field] = cells_sha
        dump(path, value)
        refresh_hash(spec, source, key)
    dump(spec_path, spec)


def test_valid_transfer_uses_public_projections_and_receipt_native_commands(tmp_path: Path):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    original = (source / "cells/EXECUTION_RECEIPT.json").read_bytes()
    report = TRANSFER.validate_and_publish(spec_path, source, output)
    assert report["status"] == TRANSFER.PASS_STATUS
    normalized = json.loads((output / "normalized_receipts/cells.json").read_text())
    assert json.loads(normalized["command"]) == ARGV["cells"]
    assert normalized["mode"] == "empirical_reestimate"
    assert normalized["code_hash"] == TRANSFER.CELL_CODE_SHA256
    assert normalized["spec_id"] == TRANSFER.CANONICAL_BINDING["id"]
    projection = json.loads((output / "receipt_projections/cells.json").read_text())
    assert projection["module_key"] == "cells"
    assert "producer_internal_safe_note" not in projection
    assert set(projection) == {
        "schema_version", "module_key", "source_receipt_schema",
        "source_receipt_status", "source_receipt_sha256", "generated_at_utc",
        "canonical_spec", "typed_spec", "numerical_consumer_spec",
        "code_hashes", "aggregate_artifact", "assignment_fingerprint_sha256",
        "assignment_fingerprint_artifact_sha256", "grid",
        "weight_application_count", "execution_command_binding",
        "execution_runtime_authentication", "pre_execution_authorization",
    }
    assert not (output / "source_receipts").exists()
    assert not (output / "RUN_LEDGER_MAP.json").exists()
    assert report["source_receipts_copied"] is False
    assert report["run_ledger_map_generated"] is False
    assert report["normalizer_execution_provenance"]["tracked_worktree_clean"] is True
    assert normalized["source_bindings"]["normalizer_source_sha256"] == digest(SCRIPT)
    assert (source / "cells/EXECUTION_RECEIPT.json").read_bytes() == original

    numerical = json.loads((output / "normalized_receipts/numerical.json").read_text())
    dependency = next(
        row for row in numerical["normalization_dependencies"]
        if row["module_key"] == "target"
    )
    assert dependency == {
        "module_key": "target",
        "typed_spec_id": TRANSFER.TARGET_SPEC_ID,
        "module_run_fingerprint_sha256": json.loads(
            (output / "normalized_receipts/target.json").read_text()
        )["module_run_fingerprint_sha256"],
        "source_receipt_hash_link_present": False,
        "relationship": "temporal_and_topological_dependency_only",
    }


def test_qacct_exporter_code_hash_is_pinned_by_normalizer():
    assert TRANSFER.QACCT_EXPORTER_SHA256 == digest(
        HERE / "export_sanitized_qacct.py"
    )


def test_v3_delivery_receipt_contract_accepts_normalized_receipts(tmp_path: Path):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    TRANSFER.validate_and_publish(spec_path, source, output)
    delivery_path = HERE.parents[0] / "scripts" / "validate_revision_delivery.py"
    loader = importlib.util.spec_from_file_location("delivery_validator", delivery_path)
    assert loader is not None and loader.loader is not None
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    for key in TRANSFER.MODULE_KEYS:
        value = json.loads((output / "normalized_receipts" / f"{key}.json").read_text())
        module.valid_receipt(value, empirical=True)


def test_exact_topology_modes_and_module_order_are_immutable(tmp_path: Path):
    _spec_path, _source, _output, spec = make_fixture(tmp_path)
    target = find_module(spec, "target")
    target["depends_on"] = []
    with pytest.raises(TRANSFER.TransferBlocked, match="immutable depends_on"):
        TRANSFER.validate_spec(spec)
    target["depends_on"] = ["cells"]
    target["mode"] = "analysis_simulation"
    with pytest.raises(TRANSFER.TransferBlocked, match="immutable mode"):
        TRANSFER.validate_spec(spec)
    target["mode"] = "aggregate_analysis"
    spec["modules"][0], spec["modules"][1] = spec["modules"][1], spec["modules"][0]  # type: ignore[index]
    with pytest.raises(TRANSFER.TransferBlocked, match="keys and order"):
        TRANSFER.validate_spec(spec)


@pytest.mark.parametrize(
    "key,field,replacement",
    [
        ("cells", "expected_receipt_schema", "other"),
        ("target", "code_hash_pointer", "/other"),
        ("numerical", "expected_code_hash", "f" * 64),
        ("cells", "module_receipt_file", "other.json"),
        ("numerical", "time_source", "scheduler"),
        ("cells", "scheduler_boundary_tolerance_seconds", 2.1),
        ("target", "generated_at_pointer", "/other"),
    ],
)
def test_module_contract_fields_are_not_configurable(
    tmp_path: Path, key: str, field: str, replacement: object
):
    _spec_path, _source, _output, spec = make_fixture(tmp_path)
    find_module(spec, key)[field] = replacement
    with pytest.raises(TRANSFER.TransferBlocked, match="immutable"):
        TRANSFER.validate_spec(spec)


def test_exact_canonical_and_typed_values_are_immutable(tmp_path: Path):
    _spec_path, _source, _output, spec = make_fixture(tmp_path)
    spec["canonical_spec"] = {"id": "yaxspec_v1_" + "f" * 64, "sha256": "f" * 64}
    with pytest.raises(TRANSFER.TransferBlocked, match="immutable Gate-1"):
        TRANSFER.validate_spec(spec)
    spec["canonical_spec"] = copy.deepcopy(TRANSFER.CANONICAL_BINDING)
    find_module(spec, "target")["typed_spec"]["id"] = "yaxtargetspec_v1_" + "f" * 64  # type: ignore[index]
    with pytest.raises(TRANSFER.TransferBlocked, match="immutable typed_spec"):
        TRANSFER.validate_spec(spec)


def test_run_and_job_ids_must_be_unique_and_typed(tmp_path: Path):
    _spec_path, _source, _output, spec = make_fixture(tmp_path)
    find_module(spec, "target")["run_id"] = RUN_IDS["cells"]
    with pytest.raises(TRANSFER.TransferBlocked, match="wrong immutable prefix|unique"):
        TRANSFER.validate_spec(spec)
    find_module(spec, "target")["run_id"] = RUN_IDS["target"]
    find_module(spec, "target")["expected_jobnumber"] = JOB_IDS["cells"]
    with pytest.raises(TRANSFER.TransferBlocked, match="derived|unique"):
        TRANSFER.validate_spec(spec)
    find_module(spec, "target")["expected_jobnumber"] = "7.0"
    with pytest.raises(TRANSFER.TransferBlocked, match="positive digit"):
        TRANSFER.validate_spec(spec)


def test_current_actual_receipt_shape_without_command_binding_fails_closed(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "target",
        lambda value: value.pop("execution_command_binding"),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="receipt-native.*not runner-recorded"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    assert not output.exists()


@pytest.mark.parametrize(
    "key,field,value",
    [
        ("cells", "isolated_mode", False),
        ("target", "python_version", "3.13.9"),
        ("numerical", "omp_num_threads", "2"),
    ],
)
def test_execution_runtime_authentication_is_exact(
    tmp_path: Path, key: str, field: str, value: object
):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, key,
        lambda receipt: receipt["execution_runtime_authentication"].__setitem__(
            field, value
        ),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="runtime differs"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_pre_execution_authorization_is_required_and_module_bound(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "target",
        lambda receipt: receipt.pop("pre_execution_authorization"),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="authorization is absent"):
        TRANSFER.validate_and_publish(spec_path, source, output)

    spec_path, source, output, spec = make_fixture(tmp_path / "wrong-module")
    mutate_receipt(
        spec_path, source, spec, "target",
        lambda receipt: receipt["pre_execution_authorization"].__setitem__(
            "module_key", "cells"
        ),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="binding differs"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_authorization_must_be_shared_and_cover_scheduler_intervals(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "target",
        lambda receipt: receipt["pre_execution_authorization"].__setitem__(
            "authorization_file_sha256", "b" * 64
        ),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="authorization consistency"):
        TRANSFER.validate_and_publish(spec_path, source, output)

    spec_path, source, output, spec = make_fixture(tmp_path / "expired")
    for key in TRANSFER.MODULE_KEYS:
        mutate_receipt(
            spec_path, source, spec, key,
            lambda receipt: receipt["pre_execution_authorization"].__setitem__(
                "not_after_utc", "2026-09-06T12:05:00Z"
            ),
        )
    refresh_downstream_cell_receipt_links(spec_path, source, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="authorization consistency"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_receipt_summaries_must_match_committed_authorization(
    tmp_path: Path, monkeypatch
):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    committed = TRANSFER.capture_committed_authorization_state({}).public
    committed["source_registry_sha256"] = "b" * 64
    monkeypatch.setattr(
        TRANSFER,
        "capture_committed_authorization_state",
        lambda expected: TRANSFER.AuthorizationState(
            public=copy.deepcopy(committed),
            snapshot=None,
            committed_payload_sha256="0" * 64,
        ),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="authorization consistency"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    assert not output.exists()


def test_arbitrary_transfer_spec_exact_command_is_rejected(tmp_path: Path):
    _spec_path, _source, _output, spec = make_fixture(tmp_path)
    find_module(spec, "cells")["exact_command"] = "python3 anything.py"
    with pytest.raises(TRANSFER.TransferBlocked, match="field set is not exact"):
        TRANSFER.validate_spec(spec)


@pytest.mark.parametrize("field", ["sanitized_argv_sha256", "binding_sha256"])
def test_command_binding_hashes_are_verified(tmp_path: Path, field: str):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "cells",
        lambda value: value["execution_command_binding"].__setitem__(field, "f" * 64),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="argv hash|self-hash"):
        TRANSFER.validate_and_publish(spec_path, source, output)


@pytest.mark.parametrize(
    "field,value",
    [
        ("module_key", "target"),
        ("run_id", RUN_IDS["target"]),
        ("scheduler_jobnumber", JOB_IDS["target"]),
    ],
)
def test_command_binding_identity_must_match_run_and_scheduler(
    tmp_path: Path, field: str, value: str
):
    spec_path, source, output, spec = make_fixture(tmp_path)

    def mutation(receipt):
        binding = receipt["execution_command_binding"]
        binding[field] = value
        core = {key: binding[key] for key in binding if key != "binding_sha256"}
        binding["binding_sha256"] = hashlib.sha256(
            TRANSFER.canonical_bytes(core)
        ).hexdigest()

    mutate_receipt(spec_path, source, spec, "cells", mutation)
    with pytest.raises(TRANSFER.TransferBlocked, match="binding differs"):
        TRANSFER.validate_and_publish(spec_path, source, output)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda argv: argv.__setitem__(0, "python3"),
        lambda argv: argv.__setitem__(1, "never_executed.py"),
        lambda argv: argv.append("a" * 48),
        lambda argv: argv.__setitem__(-1, "file:///projectnb/hidden/output"),
        lambda argv: argv.append("--extra"),
        lambda argv: argv.pop(),
        lambda argv: argv.__setitem__(slice(2, 6), argv[4:6] + argv[2:4]),
    ],
)
def test_exact_sanitized_argv_grammar_rejects_every_variant(tmp_path: Path, mutation):
    spec_path, source, output, spec = make_fixture(tmp_path)

    def change(receipt):
        binding = receipt["execution_command_binding"]
        argv = binding["sanitized_argv"]
        mutation(argv)
        binding["sanitized_argv_sha256"] = hashlib.sha256(
            TRANSFER.canonical_bytes(argv)
        ).hexdigest()
        core = {key: binding[key] for key in binding if key != "binding_sha256"}
        binding["binding_sha256"] = hashlib.sha256(
            TRANSFER.canonical_bytes(core)
        ).hexdigest()

    mutate_receipt(spec_path, source, spec, "cells", change)
    with pytest.raises(TRANSFER.TransferBlocked, match="argv|private path"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_legacy_command_binding_without_argv_field_fails_closed(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)

    def remove_argv(receipt):
        binding = receipt["execution_command_binding"]
        binding.pop("sanitized_argv")

    mutate_receipt(spec_path, source, spec, "target", remove_argv)
    with pytest.raises(TRANSFER.TransferBlocked, match="field set is not exact"):
        TRANSFER.validate_and_publish(spec_path, source, output)


@pytest.mark.parametrize(
    "key,field",
    [
        ("target", "source_aggregate_receipt_sha256"),
        ("target", "authenticated_cells_sha256"),
        ("numerical", "cells_receipt_sha256"),
        ("numerical", "cells_sha256"),
    ],
)
def test_reciprocal_cell_receipt_and_artifact_hashes_are_required(
    tmp_path: Path, key: str, field: str
):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, key,
        lambda value: value.__setitem__(field, "f" * 64),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="cross-receipt"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_cell_receipt_must_reciprocally_bind_numerical_spec(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "cells",
        lambda value: value.__setitem__("analysis_spec_sha256", "f" * 64),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="reciprocally bound"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_schema_specific_code_hash_maps_are_exact(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "target",
        lambda value: value["code_hashes"].__setitem__("unapproved.py", "f" * 64),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="code-hash map"):
        TRANSFER.validate_and_publish(spec_path, source, output)


@pytest.mark.parametrize(
    "key,field,error",
    [
        ("target", "artifact_hashes", "artifact hashes key set"),
        ("numerical", "output_hashes", "output hashes key set"),
    ],
)
def test_schema_specific_artifact_hash_maps_are_exact(
    tmp_path: Path, key: str, field: str, error: str
):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, key,
        lambda value: value[field].__setitem__("UNDECLARED.txt", "f" * 64),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match=error):
        TRANSFER.validate_and_publish(spec_path, source, output)


@pytest.mark.parametrize("key,field", [("cells", "runtime_code_hashes"),
                                        ("numerical", "submitted_design_source_sha256")])
def test_all_schema_specific_code_maps_reject_extra_keys(
    tmp_path: Path, key: str, field: str
):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, key,
        lambda value: value[field].__setitem__("unapproved.py", "f" * 64),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="code-hash|code hashes"):
        TRANSFER.validate_and_publish(spec_path, source, output)


@pytest.mark.parametrize(
    "payload",
    [
        "/projectnb/econdept/private/result.json",
        "github_pat_notarealcredential",
        "prefix_github_pat_notarealcredential",
        "prefix_ghp_notarealcredential",
        "Authorization: Bearer notarealcredentialvalue",
        "export IPUMS_API_KEY=not-a-real-key",
        "curl -u user:password https://example.invalid",
        "sshpass -p password ssh host",
        "https://user:password@example.invalid/path",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
    ],
)
def test_decoded_recursive_private_and_credential_forms_are_blocked(
    tmp_path: Path, payload: str
):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "cells",
        lambda value: value.__setitem__("nested", {"deeper": [{"value": payload}]}),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="decoded private path|credential"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_unicode_escaped_private_path_is_decoded_before_scan(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    path = source / "cells/EXECUTION_RECEIPT.json"
    text = path.read_text()
    text = text[:-2] + ',\n  "nested_escape": "\\u002fprojectnb\\u002fecondept\\u002fsecret"\n}\n'
    path.write_text(text, encoding="utf-8")
    refresh_hash(spec, source, "cells")
    dump(spec_path, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="decoded private path"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_unicode_format_characters_cannot_split_a_credential_marker(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "cells",
        lambda value: value.__setitem__("nested", "github\u200b_pat_notarealcredential"),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="credential"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_secret_name_in_decoded_object_key_is_scanned(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "cells",
        lambda value: value.__setitem__("IPUMS_API_KEY", "not-a-real-key"),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="credential"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_generic_secret_shaped_decoded_key_is_blocked(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "cells",
        lambda value: value.__setitem__("api_key", "redacted"),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="credential-shaped key"):
        TRANSFER.validate_and_publish(spec_path, source, output)


@pytest.mark.parametrize(
    "probe",
    [
        "openai_api_key", "db_password", "github_token", "service_secret",
        "x-access-token", "aws_access_key_id", "private_key",
    ],
)
def test_suspicious_secret_key_components_are_blocked(
    tmp_path: Path, probe: str
):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "cells",
        lambda value: value.__setitem__(probe, "redacted"),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="credential"):
        TRANSFER.validate_and_publish(spec_path, source, output)


@pytest.mark.parametrize("value", ["inf", "-inf", "nan", 1e309])
def test_nonfinite_scheduler_numeric_is_blocked(tmp_path: Path, value: object):
    spec_path, source, output, spec = make_fixture(tmp_path)
    path = source / "scheduler/cells.json"
    scheduler_value = json.loads(path.read_text())
    scheduler_value["ru_wallclock"] = value
    if isinstance(value, float) and not (value == value and abs(value) != float("inf")):
        # Write a standards-invalid nonfinite JSON constant deliberately.
        payload = json.dumps(scheduler_value, allow_nan=True, sort_keys=True).encode() + b"\n"
        path.write_bytes(payload)
    else:
        dump(path, scheduler_value)
    refresh_hash(spec, source, "cells", scheduler_only=True)
    dump(spec_path, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="finite|nonfinite"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_implausibly_future_scheduler_record_is_blocked(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    path = source / "scheduler/numerical.json"
    value = json.loads(path.read_text())
    value["start_time"] = "Mon Sep 07 08:04:00 2026"
    value["end_time"] = "Mon Sep 07 08:10:00 2026"
    dump(path, value)
    refresh_hash(spec, source, "numerical", scheduler_only=True)
    dump(spec_path, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="future-dated"):
        TRANSFER.validate_and_publish(spec_path, source, output)


@pytest.mark.parametrize(
    "bad_time,word",
    [
        ("Sun Nov 01 01:30:00 2026", "ambiguous"),
        ("Sun Mar 08 02:30:00 2026", "nonexistent"),
    ],
)
def test_ambiguous_and_nonexistent_dst_times_are_blocked(
    tmp_path: Path, bad_time: str, word: str
):
    spec_path, source, output, spec = make_fixture(tmp_path)
    path = source / "scheduler/cells.json"
    value = json.loads(path.read_text())
    value["start_time"] = bad_time
    value["end_time"] = bad_time
    dump(path, value)
    refresh_hash(spec, source, "cells", scheduler_only=True)
    dump(spec_path, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match=word):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_explicit_offset_resolves_dst_overlap(tmp_path: Path):
    _spec_path, source, _output, spec = make_fixture(tmp_path)
    path = source / "scheduler/cells.json"
    value = json.loads(path.read_text())
    value["start_time"] = "2026-11-01T01:30:00-04:00"
    value["end_time"] = "2026-11-01T01:31:00-04:00"
    dump(path, value)
    normalized = TRANSFER.validate_scheduler(
        value, find_module(spec, "cells"), "America/New_York"
    )
    assert normalized["start_utc"] == "2026-11-01T05:30:00Z"


def test_stale_receipt_hash_is_blocked(tmp_path: Path):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    path = source / "cells/EXECUTION_RECEIPT.json"
    value = json.loads(path.read_text())
    value["extra"] = "changed"
    dump(path, value)
    with pytest.raises(TRANSFER.TransferBlocked, match="byte hash differs"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_scheduler_failure_and_extra_fields_are_blocked(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    path = source / "scheduler/cells.json"
    value = json.loads(path.read_text())
    value["exit_status"] = 1
    dump(path, value)
    refresh_hash(spec, source, "cells", scheduler_only=True)
    dump(spec_path, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="successful run"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    value["exit_status"] = 0
    value["cwd"] = "hidden"
    dump(path, value)
    refresh_hash(spec, source, "cells", scheduler_only=True)
    dump(spec_path, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="contain exactly"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_module_interval_outside_scheduler_is_blocked(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "numerical",
        lambda value: value.__setitem__("started_at_utc", "2026-09-06T11:00:00Z"),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="precedes scheduler"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_cells_and_target_must_finish_before_downstream_starts(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    path = source / "scheduler/cells.json"
    value = json.loads(path.read_text())
    value["end_time"] = "Sun Sep 06 08:02:01 2026"
    dump(path, value)
    refresh_hash(spec, source, "cells", scheduler_only=True)
    dump(spec_path, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="cells execution must end"):
        TRANSFER.validate_and_publish(spec_path, source, output)

    spec_path, source, output, spec = make_fixture(tmp_path / "target_case")
    path = source / "scheduler/target.json"
    value = json.loads(path.read_text())
    value["end_time"] = "Sun Sep 06 08:04:02 2026"
    dump(path, value)
    refresh_hash(spec, source, "target", scheduler_only=True)
    dump(spec_path, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="target execution must end"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_generated_at_is_bound_to_scheduler_with_exact_two_second_tolerance(tmp_path: Path):
    spec_path, source, output, spec = make_fixture(tmp_path)
    mutate_receipt(
        spec_path, source, spec, "cells",
        lambda value: value.__setitem__("generated_at_utc", "2026-09-06T11:59:58Z"),
    )
    refresh_downstream_cell_receipt_links(spec_path, source, spec)
    TRANSFER.validate_and_publish(spec_path, source, output)

    spec_path, source, output, spec = make_fixture(tmp_path / "outside")
    mutate_receipt(
        spec_path, source, spec, "cells",
        lambda value: value.__setitem__(
            "generated_at_utc", "2026-09-06T11:59:57.999999Z"
        ),
    )
    refresh_downstream_cell_receipt_links(spec_path, source, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="generated_at precedes"):
        TRANSFER.validate_and_publish(spec_path, source, output)

    spec_path, source, output, spec = make_fixture(tmp_path / "after")
    mutate_receipt(
        spec_path, source, spec, "target",
        lambda value: value.__setitem__(
            "generated_at_utc", "2026-09-06T12:03:02.000001Z"
        ),
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="generated_at follows"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_forbidden_aggregate_is_rejected_before_open(tmp_path: Path, monkeypatch):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    aggregate = source / "aggregate_cells.csv"
    aggregate.write_text("must not be read", encoding="utf-8")
    original = os.open

    def guarded(path, *args, **kwargs):
        if Path(path).name == "aggregate_cells.csv":
            raise AssertionError("aggregate file was opened")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", guarded)
    with pytest.raises(TRANSFER.TransferBlocked, match="was not opened"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_unexpected_file_symlink_and_duplicate_key_are_blocked(tmp_path: Path):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    (source / "extra.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(TRANSFER.TransferBlocked, match="inventory differs"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    (source / "extra.json").unlink()
    scheduler_path = source / "scheduler/cells.json"
    backup = source / "scheduler/cells-real.json"
    scheduler_path.rename(backup)
    scheduler_path.symlink_to(backup.name)
    with pytest.raises(TRANSFER.TransferBlocked, match="symlink"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    scheduler_path.unlink()
    backup.rename(scheduler_path)
    receipt = source / "cells/EXECUTION_RECEIPT.json"
    receipt.write_text('{"schema_version":"x","schema_version":"y"}\n')
    spec = json.loads(spec_path.read_text())
    refresh_hash(spec, source, "cells")
    dump(spec_path, spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="duplicate JSON key"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_empty_extra_directory_and_hardlinked_input_are_blocked(tmp_path: Path):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    (source / "empty-extra").mkdir()
    with pytest.raises(TRANSFER.TransferBlocked, match="inventory differs"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    (source / "empty-extra").rmdir()
    outside_link = tmp_path / "outside-hardlink.json"
    os.link(source / "scheduler/cells.json", outside_link)
    with pytest.raises(TRANSFER.TransferBlocked, match="hardlinks"):
        TRANSFER.validate_and_publish(spec_path, source, output)


def test_source_change_is_detected_by_final_recheck(tmp_path: Path):
    _spec_path, source, _output, spec = make_fixture(tmp_path)
    allowed = {
        Path(module[field])
        for module in spec["modules"]  # type: ignore[union-attr]
        for field in ("module_receipt_file", "scheduler_record_file")
    }
    snapshots = TRANSFER.snapshot_sources(source, allowed)
    path = source / "scheduler/cells.json"
    original = path.read_bytes()
    changed = original.replace(b"512M", b"513M")
    assert len(changed) == len(original)
    path.write_bytes(changed)
    with pytest.raises(TRANSFER.TransferBlocked, match="source changed"):
        TRANSFER.final_source_recheck(source.resolve(), allowed, snapshots)


def test_validate_publish_rechecks_sources_immediately_before_publish(
    tmp_path: Path, monkeypatch
):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    original = TRANSFER.final_source_recheck

    def mutate_then_check(root, allowed, snapshots):
        path = source / "scheduler/cells.json"
        path.write_bytes(path.read_bytes().replace(b"512M", b"513M"))
        return original(root, allowed, snapshots)

    monkeypatch.setattr(TRANSFER, "final_source_recheck", mutate_then_check)
    with pytest.raises(TRANSFER.TransferBlocked, match="source changed"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    assert not output.exists()


def test_validate_publish_rechecks_spec_after_source_recheck(tmp_path: Path, monkeypatch):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    original = TRANSFER.final_source_recheck

    def check_then_mutate_spec(root, allowed, snapshots):
        original(root, allowed, snapshots)
        spec_path.write_bytes(spec_path.read_bytes() + b" ")

    monkeypatch.setattr(TRANSFER, "final_source_recheck", check_then_mutate_spec)
    with pytest.raises(TRANSFER.TransferBlocked, match="transfer spec changed"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    assert not output.exists()


def test_validate_publish_rechecks_normalizer_state_before_publish(
    tmp_path: Path, monkeypatch
):
    spec_path, source, output, _spec = make_fixture(tmp_path)

    def changed(_expected):
        raise TRANSFER.TransferBlocked("normalizer Git/source state changed before publication")

    monkeypatch.setattr(TRANSFER, "verify_normalizer_state_unchanged", changed)
    with pytest.raises(TRANSFER.TransferBlocked, match="normalizer Git/source state changed"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    assert not output.exists()


def test_validate_publish_rechecks_authorization_before_publish(
    tmp_path: Path, monkeypatch
):
    spec_path, source, output, _spec = make_fixture(tmp_path)

    def changed(_expected):
        raise TRANSFER.TransferBlocked("committed authorization changed before publication")

    monkeypatch.setattr(
        TRANSFER, "verify_committed_authorization_state_unchanged", changed
    )
    with pytest.raises(TRANSFER.TransferBlocked, match="authorization changed"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    assert not output.exists()


def test_output_lock_and_no_replace_publish_prevent_same_name_races(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "public"
    first = TRANSFER.OutputReservation.reserve(target, [source])
    try:
        metadata = json.loads(first.lock.read_text())
        assert metadata["pid"] == os.getpid()
        assert metadata["host"]
        assert metadata["created_at_utc"].endswith("Z")
        assert metadata["target_leaf"] == "public"
        with pytest.raises(TRANSFER.TransferBlocked, match="locked"):
            TRANSFER.OutputReservation.reserve(target, [source])
        competitor = target
        competitor.mkdir()
        marker = competitor / "keep.txt"
        marker.write_text("keep")
        with pytest.raises(TRANSFER.TransferBlocked, match="appeared"):
            first.publish()
        assert marker.read_text() == "keep"
    finally:
        first.abandon()


def test_stale_lock_is_never_auto_deleted(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "public"
    lock = tmp_path / ".public.transfer.lock"
    lock.write_text('{"pid":999999,"host":"old","created_at_utc":"2020-01-01T00:00:00Z"}\n')
    with pytest.raises(TRANSFER.TransferBlocked, match="remove the lock manually"):
        TRANSFER.OutputReservation.reserve(target, [source])
    assert lock.exists()


def test_atomic_no_replace_primitive_refuses_existing_target(tmp_path: Path):
    source = tmp_path / "staging"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    with pytest.raises(TRANSFER.TransferBlocked, match="refusing overwrite"):
        TRANSFER._atomic_rename_noreplace(source, target)
    assert source.exists() and target.exists()


def test_post_commit_cleanup_failure_is_success_with_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "published"
    reservation = TRANSFER.OutputReservation.reserve(target, [source])
    dump(reservation.staging / "artifact.json", {"status": "safe"})

    def fail_release() -> None:
        if reservation.lock_fd is not None:
            os.close(reservation.lock_fd)
            reservation.lock_fd = None
        raise OSError(errno.EIO, "synthetic post-commit cleanup failure")

    monkeypatch.setattr(reservation, "release", fail_release)
    warnings = reservation.publish()
    assert target.is_dir()
    assert (target / "artifact.json").is_file()
    assert warnings == (f"lock_cleanup_errno_{errno.EIO}",)
    reservation.lock.unlink(missing_ok=True)


def test_unexpected_exception_after_commit_never_reports_failed_publication(
    tmp_path: Path, monkeypatch
):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    original = TRANSFER.OutputReservation.publish

    def publish_then_raise(self):
        original(self)
        raise RuntimeError("synthetic exception after commit point")

    monkeypatch.setattr(TRANSFER.OutputReservation, "publish", publish_then_raise)
    report = TRANSFER.validate_and_publish(spec_path, source, output)
    assert report["status"] == TRANSFER.PASS_STATUS
    assert output.is_dir()
    assert report["post_commit_cleanup_warnings"] == [
        "post_commit_internal_RuntimeError"
    ]


def test_output_must_be_new_and_disjoint(tmp_path: Path):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("keep")
    with pytest.raises(TRANSFER.TransferBlocked, match="already exists"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    assert marker.read_text() == "keep"
    nested_output = source / "public"
    with pytest.raises(TRANSFER.TransferBlocked, match="disjoint"):
        TRANSFER.validate_and_publish(spec_path, source, nested_output)


def test_replay_to_distinct_fresh_leaf_preserves_identity(tmp_path: Path):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    second = tmp_path / "public-replay"
    TRANSFER.validate_and_publish(spec_path, source, output)
    TRANSFER.validate_and_publish(spec_path, source, second)
    first_files = {
        path.relative_to(output): path.read_bytes()
        for path in output.rglob("*") if path.is_file()
    }
    second_files = {
        path.relative_to(second): path.read_bytes()
        for path in second.rglob("*") if path.is_file()
    }
    assert first_files == second_files


def test_staged_inventory_rejects_empty_extra_directory(tmp_path: Path):
    root = tmp_path / "stage"
    dump(root / "expected.json", {})
    (root / "empty-extra").mkdir()
    with pytest.raises(TRANSFER.TransferBlocked, match="file/directory inventory"):
        TRANSFER.validate_staged_json(root, {Path("expected.json")})


def test_normalizer_git_provenance_requires_committed_clean_source(
    tmp_path: Path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "normalizer.py"
    source.write_text("print('clean')\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "normalizer.py"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "fixture"],
        cwd=repo, check=True,
    )
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text("#!/bin/sh\necho fabricated\n", encoding="utf-8")
    fake_git.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin))
    state = CAPTURE_NORMALIZER_STATE(source)
    assert state["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert state["tracked_worktree_clean"] is True

    (repo / "untracked.txt").write_text("x", encoding="utf-8")
    with pytest.raises(TRANSFER.TransferBlocked, match="dirty or contains untracked"):
        CAPTURE_NORMALIZER_STATE(source)
    monkeypatch.setattr(TRANSFER, "__file__", str(source))
    with pytest.raises(TRANSFER.TransferBlocked, match="changed before publication"):
        VERIFY_NORMALIZER_STATE(state)
    (repo / "untracked.txt").unlink()
    source.write_text("print('dirty')\n", encoding="utf-8")
    with pytest.raises(TRANSFER.TransferBlocked, match="dirty or contains untracked"):
        CAPTURE_NORMALIZER_STATE(source)


def test_committed_authorization_is_independently_bound_to_current_head(
    tmp_path: Path, monkeypatch
):
    repo = tmp_path / "repo"
    source = repo / TRANSFER.AUTHORIZATION_REL.parent / "normalize_public_receipts.py"
    source.parent.mkdir(parents=True)
    source.write_text("# synthetic tracked normalizer\n", encoding="utf-8")
    canonical_source = HERE.parents[3] / TRANSFER.CANONICAL_SPEC_REL
    canonical_target = repo / TRANSFER.CANONICAL_SPEC_REL
    canonical_target.parent.mkdir(parents=True)
    canonical_target.write_bytes(canonical_source.read_bytes())

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["/usr/bin/git", *args], cwd=repo, check=True,
            text=True, capture_output=True,
        )
        return completed.stdout.strip()

    git("init", "-q")
    git("config", "user.email", "synthetic@example.invalid")
    git("config", "user.name", "Synthetic Test")
    git("add", ".")
    git("commit", "-q", "-m", "implementation")
    implementation = git("rev-parse", "HEAD")

    canonical = json.loads(canonical_target.read_text(encoding="utf-8"))
    source_hashes = {
        row["source_id"]: row["sha256"] for row in canonical["data"]["sources"]
    }
    authorization = {
        "schema_version": TRANSFER.PRE_EXECUTION_AUTHORIZATION_SCHEMA,
        "status": TRANSFER.PRE_EXECUTION_AUTHORIZATION_STATUS,
        "issued_at_utc": "2026-09-06T00:00:00Z",
        "not_before_utc": "2026-09-06T00:00:00Z",
        "not_after_utc": "2026-09-07T00:00:00Z",
        "authorized_implementation_commit": implementation,
        "canonical_spec": copy.deepcopy(TRANSFER.CANONICAL_BINDING),
        "source_registry_sha256": hashlib.sha256(
            TRANSFER.canonical_bytes(source_hashes)
        ).hexdigest(),
        "modules": {
            key: {
                "typed_spec_id": TRANSFER.MODULE_CONTRACTS[key]["typed_spec"]["id"],
                "typed_spec_sha256": TRANSFER.MODULE_CONTRACTS[key]["typed_spec"]["sha256"],
                "code_sha256": TRANSFER.MODULE_CONTRACTS[key]["code_hash"],
            }
            for key in TRANSFER.MODULE_KEYS
        },
    }
    authorization["authorization_id"] = TRANSFER._authorization_identifier(
        authorization
    )
    authorization_path = repo / TRANSFER.AUTHORIZATION_REL
    dump(authorization_path, authorization)
    git("add", TRANSFER.AUTHORIZATION_REL.as_posix())
    git("commit", "-q", "-m", "authorization")
    authorization_commit = git("rev-parse", "HEAD")

    monkeypatch.setattr(TRANSFER, "__file__", str(source))
    captured = CAPTURE_AUTHORIZATION_STATE({"git_commit": authorization_commit})
    assert captured.public["authorization_git_commit"] == authorization_commit
    assert captured.public["authorized_implementation_commit"] == implementation
    assert captured.public["authorization_file_sha256"] == digest(authorization_path)

    authorization["source_registry_sha256"] = "0" * 64
    dump(authorization_path, authorization)
    with pytest.raises(TRANSFER.TransferBlocked, match="committed HEAD bytes"):
        CAPTURE_AUTHORIZATION_STATE({"git_commit": authorization_commit})


def test_ignored_importable_artifact_in_v3_scope_is_blocked(tmp_path: Path):
    repo = tmp_path / "repo"
    source = (
        repo / "yax/revision/substantive_v3_20260906/gate1_transfer/normalizer.py"
    )
    source.parent.mkdir(parents=True)
    source.write_text("print('clean')\n", encoding="utf-8")
    (repo / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", ".gitignore", str(source.relative_to(repo))], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "fixture"],
        cwd=repo, check=True,
    )
    ignored = source.parent / "adversarial.pyc"
    ignored.write_bytes(b"not bytecode")
    with pytest.raises(TRANSFER.TransferBlocked, match="ignored importable"):
        CAPTURE_NORMALIZER_STATE(source)


def test_generated_public_projection_is_recursively_secret_scanned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    spec_path, source, output, _spec = make_fixture(tmp_path)
    original = TRANSFER.PROJECTORS["cells"]

    def leaking_projector(*args, **kwargs):
        projection, identity, binding = original(*args, **kwargs)
        projection["safe_prefix_github_pat_suffix"] = "synthetic"
        return projection, identity, binding

    monkeypatch.setitem(TRANSFER.PROJECTORS, "cells", leaking_projector)
    with pytest.raises(TRANSFER.TransferBlocked, match="credential"):
        TRANSFER.validate_and_publish(spec_path, source, output)
    assert not output.exists()


def test_unstamped_template_and_cli_fail_closed(tmp_path: Path):
    template = json.loads((HERE / "TRANSFER_SPEC.template.json").read_text())
    with pytest.raises(TRANSFER.TransferBlocked, match="not terminal"):
        TRANSFER.validate_spec(template)
    _spec_path, source, output, _spec = make_fixture(tmp_path)
    result = subprocess.run(
        [
            sys.executable, "-I", str(SCRIPT), "--spec",
            str(HERE / "TRANSFER_SPEC.template.json"),
            "--input-dir", str(source), "--output-dir", str(output),
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "TRANSFER BLOCKED" in result.stderr
    assert not output.exists()
