from __future__ import annotations

from argparse import Namespace
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock

import numpy as np
import pandas as pd
import pytest


TEST_FILE = Path(__file__).resolve()
REPO = TEST_FILE.parents[5]
TARGET_DIR = TEST_FILE.parents[1]
SCRIPT = TARGET_DIR / "run_exact_target_audit.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("yax_v3_target_audit_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load_runner()


def synthetic_pre_execution_authorization(
    module_key: str, cell_spec: dict, canonical: dict
) -> dict:
    common = {
        "schema_version": RUNNER.PRE_EXECUTION_AUTHORIZATION_SCHEMA,
        "status": RUNNER.PRE_EXECUTION_AUTHORIZATION_STATUS,
        "authorization_id": RUNNER.PRE_EXECUTION_AUTHORIZATION_PREFIX + "a" * 64,
        "authorization_file_sha256": "b" * 64,
        "authorization_git_commit": "c" * 40,
        "authorized_implementation_commit": "d" * 40,
        "issued_at_utc": "2026-09-06T11:00:00+00:00",
        "not_before_utc": "2026-09-06T11:30:00+00:00",
        "not_after_utc": "2026-09-06T13:30:00+00:00",
        "source_registry_sha256": RUNNER.hashlib.sha256(
            RUNNER.canonical_bytes(RUNNER.canonical_source_hashes(canonical))
        ).hexdigest(),
    }
    if module_key == "cells":
        return {
            **common,
            "module_key": "cells",
            "typed_spec_id": cell_spec["cell_build_spec_id"],
            "typed_spec_sha256": RUNNER.sha256_file(REPO / RUNNER.CELL_SPEC_REL),
            "code_sha256": cell_spec["runtime_code_hashes"][str(RUNNER.BUILDER_REL)],
        }
    target = RUNNER.load_json(REPO / RUNNER.TARGET_SPEC_REL)
    return {
        **common,
        "module_key": "target",
        "typed_spec_id": target["target_audit_spec_id"],
        "typed_spec_sha256": RUNNER.sha256_file(REPO / RUNNER.TARGET_SPEC_REL),
        "code_sha256": RUNNER.sha256_file(SCRIPT),
    }


def target_entry_fixture(tmp_path: Path) -> tuple[Namespace, list[str], list[str]]:
    cells_leaf = tmp_path / "gate1_cells_sge_699999"
    args = Namespace(
        repo_root=REPO,
        cells=cells_leaf / "aggregate_cells.csv",
        cells_receipt=cells_leaf / RUNNER.RECEIPT_FILENAME,
        output_parent=tmp_path,
    )
    raw = [
        "--repo-root", str(args.repo_root),
        "--cells", str(args.cells),
        "--cells-receipt", str(args.cells_receipt),
        "--output-parent", str(args.output_parent),
    ]
    original = [sys.executable, "-I", str(SCRIPT), *raw]
    return args, raw, original


def execute_target(args: Namespace):
    """Exercise the one-argument production wrapper under a synthetic runner.

    Entry attestations are replaced at their internal acquisition boundaries;
    they are never accepted as arguments by ``execute``.  The helper renames a
    successfully derived synthetic leaf only so older content tests can keep
    their descriptive per-test output names.
    """
    desired_output = args.output_leaf
    execution_args = Namespace(
        repo_root=args.repo_root,
        cells=args.cells,
        cells_receipt=args.cells_receipt,
        output_parent=desired_output.parent,
    )
    binding = {
        "schema_version": RUNNER.COMMAND_BINDING_SCHEMA,
        "status": RUNNER.COMMAND_BINDING_STATUS,
        "module_key": "target",
        "run_id": "gate1_target_sge_700002",
        "scheduler_jobnumber": "700002",
        "sanitized_argv": ["synthetic-unit-test"],
        "sanitized_argv_sha256": "a" * 64,
        "binding_sha256": "b" * 64,
    }
    runtime = {
        "status": "SYNTHETIC_UNIT_TEST_ENTRY_ATTESTATION",
        "private_paths_persisted": False,
    }
    target = RUNNER.load_json(REPO / RUNNER.TARGET_SPEC_REL)
    live_code_hashes = {
        relative: RUNNER.sha256_file(REPO / relative)
        for relative in target["code_hashes"]
    }
    with (
        mock.patch.object(RUNNER, "scheduler_jobnumber", return_value="700002"),
        mock.patch.object(
            RUNNER, "build_execution_command_binding", return_value=binding
        ),
        mock.patch.object(
            RUNNER, "execution_runtime_authentication", return_value=runtime
        ),
        mock.patch.object(
            RUNNER, "authenticate_code", return_value=live_code_hashes
        ),
    ):
        result = RUNNER.execute(execution_args)
    actual_output = desired_output.parent / "gate1_target_sge_700002"
    if actual_output != desired_output:
        actual_output.rename(desired_output)
    return result


def test_production_entry_and_command_binding_are_not_caller_attested(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    assert list(inspect.signature(RUNNER.execute).parameters) == ["args"]
    assert RUNNER.main([]) == 2
    assert "substituted argv" in capsys.readouterr().err
    args, raw, original = target_entry_fixture(tmp_path)
    binding = RUNNER.build_execution_command_binding(
        args, raw, original, {"JOB_ID": "700002", "SGE_JOB_ID": "700002"}
    )
    assert binding["run_id"] == "gate1_target_sge_700002"
    assert binding["scheduler_jobnumber"] == "700002"
    assert str(tmp_path) not in json.dumps(binding)
    with pytest.raises(RUNNER.TargetAuditError, match="direct isolated"):
        RUNNER.build_execution_command_binding(
            args, raw, [sys.executable, str(SCRIPT), *raw], {"JOB_ID": "700002"}
        )
    with pytest.raises(RUNNER.TargetAuditError, match="array jobs"):
        RUNNER.build_execution_command_binding(
            args, raw, original, {"JOB_ID": "700002", "SGE_TASK_ID": "1"}
        )


def test_target_command_binding_rejects_noncolocated_inputs(tmp_path: Path):
    args, raw, original = target_entry_fixture(tmp_path)
    args.cells_receipt = tmp_path / "other" / RUNNER.RECEIPT_FILENAME
    raw[5] = str(args.cells_receipt)
    original = [sys.executable, "-I", str(SCRIPT), *raw]
    with pytest.raises(RUNNER.TargetAuditError, match="colocated"):
        RUNNER.build_execution_command_binding(
            args, raw, original, {"JOB_ID": "700002"}
        )


def test_target_postcommit_stdout_failure_does_not_change_success_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    observed = {}

    def completed(args):
        observed["output_leaf"] = args.output_leaf
        return {"status": "PASS_EXACT_TARGET_AUDIT"}

    monkeypatch.setattr(RUNNER, "execute", completed)
    monkeypatch.setattr(RUNNER, "scheduler_jobnumber", lambda _env: "23456")
    monkeypatch.setattr(
        RUNNER.sys, "argv",
        [
            str(RUNNER.__file__), "--repo-root", str(REPO),
            "--cells", str(tmp_path / "cells" / "aggregate_cells.csv"),
            "--cells-receipt", str(tmp_path / "cells" / "EXECUTION_RECEIPT.json"),
            "--output-parent", str(tmp_path),
        ],
    )
    monkeypatch.setattr(
        "builtins.print",
        lambda *args, **kwargs: (_ for _ in ()).throw(BrokenPipeError()),
    )
    assert RUNNER.main() == 0
    assert observed["output_leaf"] == tmp_path / "gate1_target_sge_23456"


def fixed_assignments() -> pd.DataFrame:
    membership = pd.read_csv(
        REPO
        / "yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv",
        dtype={"occupation_code": str},
        float_precision="round_trip",
    )
    family = pd.read_csv(
        REPO / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv",
        dtype={"census2018": str, "soc_major_group": str},
    )[["census2018", "soc_major_group"]]
    frame = membership.merge(
        family,
        left_on="occupation_code",
        right_on="census2018",
        how="left",
        validate="one_to_one",
    )
    result = frame.rename(
        columns={"occupation_code": "occ_code", "soc_major_group": "family"}
    )[["occ_code", "family", "beta_quintile", "webb_z"]]
    result["occ_code"] = result.occ_code.str.zfill(4)
    result["family"] = result.family.str.zfill(2)
    result["beta_quintile"] = result.beta_quintile.astype(int)
    result["webb_z"] = result.webb_z.astype(float)
    return result.sort_values("occ_code", kind="mergesort").reset_index(drop=True)


def make_authenticated_product(root: Path) -> tuple[Path, Path, pd.DataFrame]:
    root.mkdir()
    target, canonical, cell_spec = RUNNER.load_and_validate_specs(REPO)
    assignments = fixed_assignments()
    months = RUNNER.expected_observed_months(canonical)
    rows = []
    for assignment in assignments.itertuples(index=False):
        for month in months:
            rows.append(
                {
                    "occ_code": assignment.occ_code,
                    "month": month,
                    "family": assignment.family,
                    "young": 1.25 + assignment.beta_quintile / 100.0,
                    "older": 10.5 + assignment.beta_quintile / 100.0,
                    "beta_quintile": assignment.beta_quintile,
                    "webb_z": assignment.webb_z,
                }
            )
    frame = pd.DataFrame(rows, columns=cell_spec["output_contract"]["columns"])
    frame.loc[(frame.occ_code == assignments.iloc[0].occ_code) & (frame.month == "2017-01"), "young"] = 0.0
    frame.loc[(frame.occ_code == assignments.iloc[0].occ_code) & (frame.month == "2017-02"), ["young", "older"]] = 0.0
    frame.loc[(frame.occ_code == assignments.iloc[0].occ_code) & (frame.month == "2017-03"), "older"] = 0.0
    cells = root / cell_spec["output_contract"]["cells_filename"]
    frame.to_csv(cells, index=False, lineterminator="\n", float_format="%.17g")
    # Re-read the exact serialized assignments so the test exercises the
    # production floating-point fingerprint path.
    serialized = pd.read_csv(
        cells,
        dtype={"occ_code": str, "month": str, "family": str},
        float_precision="round_trip",
    )
    fixed = serialized[["occ_code", "family", "beta_quintile", "webb_z"]].drop_duplicates()
    fingerprint = RUNNER.assignment_fingerprint(fixed)
    assert fingerprint == cell_spec["assignment_contract"]["fingerprint_sha256"]
    canonical_sources = RUNNER.canonical_source_hashes(canonical)
    authenticated_sources = {
        key: value
        for key, value in canonical_sources.items()
        if key not in RUNNER.UNREAD_CANONICAL_SOURCE_IDS
    }
    lookup_sources = {
        key: canonical_sources[key]
        for key in RUNNER.LOOKUP_AND_AUTHORIZATION_SOURCE_IDS
    }
    source_ids = list(RUNNER.RAW_SOURCE_IDS)
    raw = {
        "source_ids": source_ids,
        "runtime_raw_fields": ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL"],
        "physical_rows_read_total": 100000,
        "physical_rows_read_by_source": dict(zip(source_ids, [80000, 20000])),
        "eligible_employed_age_22_65_records_total": 75000,
        "eligible_employed_age_22_65_records_by_source": dict(
            zip(source_ids, [71000, 4000])
        ),
        "wide_march_rows_explicitly_replaced": 5000,
        # The authenticated wide source contains ASEC March rows, all with
        # zero final Basic weight.  The repair source supplies the positive-
        # weight Basic-month records.
        "wide_march_positive_weight_rows_explicitly_replaced": 0,
        "repair_eligible_employed_age_22_65_records": 4000,
        "aggregate_rows": 60000,
        "observed_month_count": 114,
        "repair_observed_months": list(RUNNER.MARCH_REPAIR_MONTHS),
    }
    partition_values = {
        "invalid_raw_occ_records": [17, 0],
        "valid_raw_occ_records": [70983, 4000],
        "early_valid_source_records": [30000, 3000],
        "current_valid_source_records": [40983, 1000],
        "early_matched_source_records": [29100, 3000],
        "early_unmatched_source_records": [900, 0],
        "early_expanded_route_descendants": [50000, 5000],
        "early_fractional_route_contributions": [40000, 4000],
        "early_unit_route_contributions": [10000, 1000],
        "early_zero_mass_route_contributions": [0, 0],
        "current_direct_route_contributions": [40983, 1000],
        "routed_contribution_rows": [90983, 6000],
    }
    for field, values in partition_values.items():
        raw[f"{field}_by_source"] = dict(zip(source_ids, values))
        raw[field] = sum(values)
    raw["routed_rows"] = raw["routed_contribution_rows"]

    source_identities = {}
    for source in source_ids:
        value = lambda field: raw[f"{field}_by_source"][source]
        source_identities[source] = {
            "eligible_equals_invalid_plus_valid": raw[
                "eligible_employed_age_22_65_records_by_source"
            ][source]
            == value("invalid_raw_occ_records") + value("valid_raw_occ_records"),
            "valid_equals_early_plus_current": value("valid_raw_occ_records")
            == value("early_valid_source_records") + value("current_valid_source_records"),
            "early_equals_matched_plus_unmatched": value("early_valid_source_records")
            == value("early_matched_source_records")
            + value("early_unmatched_source_records"),
            "expanded_descendants_cover_each_matched_record": value(
                "early_expanded_route_descendants"
            )
            >= value("early_matched_source_records"),
            "early_descendants_partition_by_route_weight": value(
                "early_expanded_route_descendants"
            )
            == value("early_fractional_route_contributions")
            + value("early_unit_route_contributions")
            + value("early_zero_mass_route_contributions"),
            "direct_contributions_equal_current_valid_records": value(
                "current_direct_route_contributions"
            )
            == value("current_valid_source_records"),
            "routed_contributions_equal_descendants_plus_direct": value(
                "routed_contribution_rows"
            )
            == value("early_expanded_route_descendants")
            + value("current_direct_route_contributions"),
        }
    total_identities = {
        "physical_total_equals_source_sum": True,
        "eligible_total_equals_source_sum": True,
        "eligible_equals_invalid_plus_valid": True,
        "valid_equals_early_plus_current": True,
        "early_equals_matched_plus_unmatched": True,
        "early_descendants_partition_by_route_weight": True,
        "direct_contributions_equal_current_valid_records": True,
        "routed_contributions_equal_descendants_plus_direct": True,
    }
    stock_values = {
        source_ids[0]: {
            "raw_early_valid_stock": 300000.0,
            "raw_early_matched_stock": 291000.0,
            "expected_early_routed_stock": 291000.0,
            "actual_early_routed_stock": 291000.0,
            "raw_current_valid_stock": 409830.0,
            "actual_current_direct_stock": 409830.0,
        },
        source_ids[1]: {
            "raw_early_valid_stock": 30000.0,
            "raw_early_matched_stock": 30000.0,
            "expected_early_routed_stock": 30000.0,
            "actual_early_routed_stock": 30000.0,
            "raw_current_valid_stock": 10000.0,
            "actual_current_direct_stock": 10000.0,
        },
    }
    source_stock_reconciliation = {}
    for source, values in stock_values.items():
        early_gap = values["actual_early_routed_stock"] - values[
            "expected_early_routed_stock"
        ]
        current_gap = values["actual_current_direct_stock"] - values[
            "raw_current_valid_stock"
        ]
        source_stock_reconciliation[source] = {
            **values,
            "early_absolute_gap": early_gap,
            "early_relative_gap": early_gap
            / max(abs(values["expected_early_routed_stock"]), 1.0),
            "current_absolute_gap": current_gap,
            "current_relative_gap": current_gap
            / max(abs(values["raw_current_valid_stock"]), 1.0),
            "unmatched_early_stock": values["raw_early_valid_stock"]
            - values["raw_early_matched_stock"],
            "route_conservation_pass": True,
        }
    stock_totals = {
        field: sum(values[field] for values in stock_values.values())
        for field in next(iter(stock_values.values()))
    }
    route = {
        **stock_totals,
        "early_absolute_gap": 0.0,
        "early_relative_gap": 0.0,
        "current_absolute_gap": 0.0,
        "current_relative_gap": 0.0,
        "unmatched_early_stock": stock_totals["raw_early_valid_stock"]
        - stock_totals["raw_early_matched_stock"],
        "bridge_source_count": 500,
        "bridge_mass_min": 1.0,
        "bridge_mass_max": 1.0,
        "record_count_definitions": {
            "physical_rows": "integer input-file records before filtering",
            "eligible_records": "integer employed age-22-through-65 positive-weight source records after explicit March replacement and before occupation routing",
            "expanded_route_descendants": "integer early-period source-to-destination bridge rows after matching; not respondents",
            "fractional_route_contributions": "expanded early bridge rows with route weight strictly between zero and one",
            "aggregate_rows": "unique occupation-month-age-route cells after summing routed contributions",
        },
        "record_identities_by_source": source_identities,
        "total_record_identities": total_identities,
        "source_stock_reconciliation": source_stock_reconciliation,
        "route_conservation_pass": True,
    }
    runtime_contract = cell_spec["runtime_contract"]
    runtime_payload = runtime_contract["runtime_payload"]
    runtime_contract_sha = RUNNER.hashlib.sha256(
        RUNNER.canonical_bytes(runtime_contract)
    ).hexdigest()
    packages = runtime_payload["packages"]
    observed_runtime = {
        "python": runtime_payload["python_version"],
        "python_implementation": runtime_payload["python_implementation"],
        "python_compiler": runtime_payload["python_compiler"],
        "numpy": packages["numpy"],
        "pandas": packages["pandas"],
        "pytest": packages["pytest"],
        "scipy": packages["scipy"],
        "kernel_system": runtime_contract["expected_runtime"]["kernel_system"],
        "kernel_release": runtime_contract["expected_runtime"]["kernel_release"],
        "machine": runtime_payload["architecture"],
        "libc_name": runtime_payload["libc"]["name"],
        "libc": runtime_payload["libc"]["version"],
    }
    assignment_document = {
        "schema_version": "yax-assignment-fingerprint-v1",
        "algorithm": cell_spec["assignment_contract"]["fingerprint_algorithm"],
        "columns": cell_spec["assignment_contract"]["columns"],
        "record_count": cell_spec["assignment_contract"]["record_count"],
        "sha256": fingerprint,
    }
    assignment_path = root / RUNNER.ASSIGNMENT_FILENAME
    assignment_path.write_text(
        json.dumps(assignment_document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    git_hashes = {
        str(RUNNER.BUILDER_REL): cell_spec["runtime_code_hashes"][
            str(RUNNER.BUILDER_REL)
        ],
        str(RUNNER.CELL_SPEC_REL): RUNNER.sha256_file(REPO / RUNNER.CELL_SPEC_REL),
        str(RUNNER.NUMERICAL_SPEC_REL): cell_spec["consumer_contract"][
            "analysis_spec_sha256"
        ],
        str(RUNNER.ENVIRONMENT_REL): runtime_contract["environment_lock_sha256"],
    }
    sanitized_cell_argv = [
        "<YAX_PYTHON_BIN>", "-I",
        str(RUNNER.V3_REL / "gate1_cells/run_gate1_cells.py"),
        "--repo-root", "<YAX_REPO_ROOT>",
        "--microdata", "<INPUT:ipums_cps_extract_9_wide>",
        "--repair-microdata", "<INPUT:ipums_cps_extract_11_march_basic_repair>",
        "--output-parent", "<YAX_V3_RUN_ROOT>",
    ]
    command_core = {
        "schema_version": RUNNER.COMMAND_BINDING_SCHEMA,
        "status": RUNNER.COMMAND_BINDING_STATUS,
        "module_key": "cells",
        "run_id": "gate1_cells_sge_700001",
        "scheduler_jobnumber": "700001",
        "sanitized_argv": sanitized_cell_argv,
        "sanitized_argv_sha256": RUNNER.hashlib.sha256(
            RUNNER.canonical_bytes(sanitized_cell_argv)
        ).hexdigest(),
    }
    receipt = {
        "schema_version": RUNNER.EXPECTED_UPSTREAM_RECEIPT_SCHEMA,
        "status": RUNNER.EXPECTED_UPSTREAM_STATUS,
        "aggregate_schema_version": RUNNER.EXPECTED_AGGREGATE_SCHEMA,
        "canonical_spec_id": canonical["spec_id"],
        "canonical_spec_sha256": RUNNER.sha256_file(REPO / RUNNER.CANONICAL_SPEC_REL),
        "analysis_spec_id": cell_spec["consumer_contract"]["analysis_spec_id"],
        "analysis_spec_sha256": cell_spec["consumer_contract"]["analysis_spec_sha256"],
        "cell_build_spec_id": cell_spec["cell_build_spec_id"],
        "cell_build_spec_sha256": RUNNER.sha256_file(REPO / RUNNER.CELL_SPEC_REL),
        "generated_at_utc": "2026-09-06T12:00:00+00:00",
        "cells_filename": cells.name,
        "cells_sha256": RUNNER.sha256_file(cells),
        "source_hashes": canonical_sources,
        "authenticated_source_hashes": authenticated_sources,
        "unread_canonical_source_ids": list(RUNNER.UNREAD_CANONICAL_SOURCE_IDS),
        "runtime_code_hashes": cell_spec["runtime_code_hashes"],
        "historical_reference_code_hashes": cell_spec[
            "historical_reference_code_hashes"
        ],
        "builder_code_sha256": cell_spec["runtime_code_hashes"][
            str(RUNNER.BUILDER_REL)
        ],
        "builder_transitive_code_sha256": cell_spec[
            "runtime_transitive_code_fingerprint"
        ]["sha256"],
        "builder_transitive_code_sha256_algorithm": (
            "SHA-256 of canonical JSON runtime path-to-hash map excluding the builder; "
            "the empty map proves that historical reference code is not imported at runtime"
        ),
        "command_template": runtime_contract["command_template"],
        "execution_command_binding": {
            **command_core,
            "binding_sha256": RUNNER.hashlib.sha256(
                RUNNER.canonical_bytes(command_core)
            ).hexdigest(),
        },
        "execution_runtime_authentication": {
            "status": "AUTHENTICATED_ISOLATED_PINNED_EXECUTABLES",
            "python_invocation": "<YAX_PYTHON_BIN>",
            "python_resolved_executable_sha256": RUNNER.EXPECTED_PYTHON_RESOLVED_SHA256,
            "python_version": "3.13.8",
            "isolated_mode": True,
            "ignore_environment": True,
            "no_user_site": True,
            "safe_path": True,
            "git_invocation": "<YAX_GIT_BIN>",
            "git_resolved_executable_sha256": RUNNER.EXPECTED_GIT_SHA256,
            "git_version": RUNNER.EXPECTED_GIT_VERSION,
            "import_affecting_environment_absent": True,
        },
        "pre_execution_authorization": synthetic_pre_execution_authorization(
            "cells", cell_spec, canonical
        ),
        "runtime_environment_lock_sha256": runtime_contract[
            "environment_lock_sha256"
        ],
        "runtime_environment_lock_path": runtime_contract["environment_lock_path"],
        "runtime_contract_sha256": runtime_contract_sha,
        "runtime_payload_sha256": runtime_contract["runtime_payload_sha256"],
        "runtime_authentication": {
            "status": "AUTHENTICATED_DECLARED_RUNTIME",
            "observed": observed_runtime,
            "kernel_release_rule": (
                "recorded but nonbinding because SCC compute-node kernel patch levels may differ"
            ),
            "environment_lock_path": runtime_contract["environment_lock_path"],
            "environment_lock_sha256": runtime_contract["environment_lock_sha256"],
            "runtime_contract_sha256": runtime_contract_sha,
            "runtime_payload": runtime_payload,
            "runtime_payload_sha256": runtime_contract["runtime_payload_sha256"],
            "command_template": runtime_contract["command_template"],
        },
        "git_status": "PASS_COMMITTED_CLEAN_WORKTREE",
        "git_commit": "b" * 40,
        "git_tree": "c" * 40,
        "git_required_ancestor_commit": cell_spec["git_contract"][
            "required_ancestor_commit"
        ],
        "git_worktree_clean": True,
        "git_porcelain_sha256": RUNNER.hashlib.sha256(b"").hexdigest(),
        "git_committed_artifact_hashes": git_hashes,
        "lookup_and_bridge_hashes": lookup_sources,
        "reference_artifacts": {
            "fixed_membership_sha256": canonical["exposure"]["fixed_membership"][
                "sha256"
            ]
        },
        "fixed_membership_sha256": canonical["exposure"]["fixed_membership"][
            "sha256"
        ],
        "authorization": {
            "status": "PASS_AUTHORIZATION_CHAIN",
            "checks": {
                "status": True,
                "frozen_tag": True,
                "microdata_sha256": True,
            },
            "repair_source_bound_by_canonical_v2": True,
        },
        "balanced_grid_complete": True,
        "freshness_and_security": {
            "new_output_leaf_required": True,
            "output_outside_repository": True,
            "atomic_directory_publish": True,
            "row_level_microdata_written": False,
            "historical_preperiod_cells_read": False,
            "historical_reference_code_imported_at_runtime": False,
            "only_six_canonical_raw_fields_read": True,
            "private_paths_persisted": False,
            "credentials_persisted": False,
        },
        "weight_application_count": 1,
        "weight_once_checks": {
            "status": "PASS_WEIGHT_ONCE",
            "weight_application_count": 1,
            "survey_weight_field": "WTFINL",
            "route_weight_is_allocation_not_second_survey_weight": True,
            "output_applies_no_additional_weight": True,
            "independent_aggregation_max_absolute_gap": 0.0,
            "rows": len(frame),
            "young_stock": float(frame.young.sum()),
            "older_stock": float(frame.older.sum()),
        },
        "route_checks": route,
        "calendar_checks": {
            "status": "PASS_CALENDAR",
            "observed_month_count": len(months),
            "observed_start": cell_spec["calendar_contract"]["observed_start"],
            "observed_end": cell_spec["calendar_contract"]["observed_end"],
            "missing_months": cell_spec["calendar_contract"][
                "excluded_missing_months"
            ],
            "transition_2022_12_present": True,
            "october_2025_absent_not_interpolated": True,
            "preperiod_month_count": cell_spec["calendar_contract"][
                "preperiod_month_count"
            ],
            "restored_march_months": list(RUNNER.MARCH_REPAIR_MONTHS),
        },
        "raw_column_contract": {
            "runtime_fields": ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL"],
            "required_columns_present": True,
            "source_column_counts": {
                "ipums_cps_extract_9_wide": 20,
                "ipums_cps_extract_11_march_basic_repair": 8,
            },
            "canonical_v2_variable_universe_parity": True,
            "rejected_inherited_helper_fields": ["OCC2010", "IND1990"],
        },
        "six_field_cell_build_checks": raw,
        "grid": {
            "occupation_count": len(assignments),
            "observed_month_count": len(months),
            "row_count": len(frame),
        },
        "support_checks": {
            "occupation_count": len(assignments),
            "content_support_sha256": RUNNER.support_hash(assignments.occ_code),
        },
        "assignment_fingerprint": assignment_document,
        "assignment_fingerprint_sha256": fingerprint,
        "assignment_fingerprint_artifact_sha256": RUNNER.sha256_file(
            assignment_path
        ),
        "occupation_count": len(assignments),
        "observed_month_count": len(months),
        "cells_row_count": len(frame),
        "support_hash_sha256": RUNNER.support_hash(assignments.occ_code),
        "contains_resolved_private_paths": False,
    }
    receipt_path = root / "EXECUTION_RECEIPT.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return cells, receipt_path, frame


@pytest.fixture(scope="module")
def product(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("authenticated-target-product") / "cells"
    return make_authenticated_product(root)


def clone_authenticated_leaf(cells: Path, receipt: Path, destination: Path) -> tuple[Path, Path]:
    destination.mkdir()
    copied_cells = destination / cells.name
    copied_receipt = destination / receipt.name
    copied_cells.write_bytes(cells.read_bytes())
    copied_receipt.write_bytes(receipt.read_bytes())
    source_assignment = receipt.parent / RUNNER.ASSIGNMENT_FILENAME
    (destination / RUNNER.ASSIGNMENT_FILENAME).write_bytes(source_assignment.read_bytes())
    return copied_cells, copied_receipt


@pytest.fixture(autouse=True)
def isolate_synthetic_product_from_live_git(request, monkeypatch: pytest.MonkeyPatch):
    """Product tests exercise receipt fields; isolated tests exercise real Git objects."""
    if "product" not in request.fixturenames:
        return

    def synthetic_verification(repo, receipt, expected_hashes, required_ancestor):
        return {
            "commit_object_exists": True,
            "commit_tree_verified": True,
            "required_ancestor_verified": True,
            "committed_blob_hashes_verified": True,
            "consuming_head_matches": True,
            "consuming_tree_matches": True,
            "consuming_worktree_clean": True,
        }

    monkeypatch.setattr(RUNNER, "verify_producer_git_checkout", synthetic_verification)
    _target, canonical, cell_spec = RUNNER.load_and_validate_specs(REPO)
    monkeypatch.setattr(
        RUNNER,
        "validate_pre_execution_authorization",
        lambda *_args, **_kwargs: synthetic_pre_execution_authorization(
            "target", cell_spec, canonical
        ),
    )


def test_target_spec_and_semantic_contracts_authenticate():
    target, canonical, cell_spec = RUNNER.load_and_validate_specs(REPO)
    assert target["target_audit_spec_id"].startswith(RUNNER.TARGET_SPEC_PREFIX)
    assert canonical["outcome"]["age_groups"] == {
        "young": "ages 22 through 25",
        "comparison": "ages 26 through 65",
    }
    assert cell_spec["output_contract"]["columns"] == [
        "occ_code",
        "month",
        "family",
        "young",
        "older",
        "beta_quintile",
        "webb_z",
    ]
    observed = RUNNER.authenticate_code(REPO, target, cell_spec)
    assert str(RUNNER.HERE_REL / "run_exact_target_audit.py") in observed
    binding = RUNNER.validate_requirement_source(REPO, target)
    assert binding["status"] == "PASS_T01_REQUIREMENT_BINDING"


def test_cli_help_needs_only_aggregate_inputs():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--cells" in completed.stdout
    assert "--cells-receipt" in completed.stdout
    assert "--microdata" not in completed.stdout


def git_output(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def make_git_authentication_fixture(tmp_path: Path):
    repo = tmp_path / "producer-git"
    repo.mkdir()
    git_output(repo, "init", "-q")
    git_output(repo, "config", "user.email", "test@example.invalid")
    git_output(repo, "config", "user.name", "YAX target test")
    (repo / "ancestor.txt").write_text("required ancestor\n", encoding="utf-8")
    git_output(repo, "add", "ancestor.txt")
    git_output(repo, "commit", "-q", "-m", "required ancestor")
    required_ancestor = git_output(repo, "rev-parse", "HEAD")

    paths = [
        str(RUNNER.BUILDER_REL),
        str(RUNNER.CELL_SPEC_REL),
        str(RUNNER.NUMERICAL_SPEC_REL),
        str(RUNNER.ENVIRONMENT_REL),
    ]
    for index, relative in enumerate(paths):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"producer artifact {index}\n", encoding="utf-8")
    git_output(repo, "add", *paths)
    git_output(repo, "commit", "-q", "-m", "producer commit")
    commit = git_output(repo, "rev-parse", "HEAD")
    tree = git_output(repo, "rev-parse", "HEAD^{tree}")
    hashes = {relative: RUNNER.sha256_file(repo / relative) for relative in paths}
    cell_spec = {
        "runtime_code_hashes": {str(RUNNER.BUILDER_REL): hashes[str(RUNNER.BUILDER_REL)]},
        "consumer_contract": {
            "analysis_spec_sha256": hashes[str(RUNNER.NUMERICAL_SPEC_REL)]
        },
        "runtime_contract": {
            "environment_lock_sha256": hashes[str(RUNNER.ENVIRONMENT_REL)]
        },
        "git_contract": {
            "clean_worktree_required": True,
            "live_files_must_equal_head_blobs": True,
            "runtime_head_and_tree_recorded": True,
            "required_ancestor_commit": required_ancestor,
            "committed_paths": paths,
        },
    }
    receipt = {
        "cell_build_spec_sha256": hashes[str(RUNNER.CELL_SPEC_REL)],
        "git_status": "PASS_COMMITTED_CLEAN_WORKTREE",
        "git_commit": commit,
        "git_tree": tree,
        "git_required_ancestor_commit": required_ancestor,
        "git_worktree_clean": True,
        "git_porcelain_sha256": RUNNER.hashlib.sha256(b"").hexdigest(),
        "git_committed_artifact_hashes": hashes,
    }
    return repo, cell_spec, receipt


def test_producer_git_objects_and_consuming_checkout_authenticate(tmp_path: Path):
    repo, cell_spec, receipt = make_git_authentication_fixture(tmp_path)
    result = RUNNER.authenticate_producer_git(receipt, cell_spec, repo)
    assert all(result["object_and_checkout_checks"].values())


def test_nonexistent_producer_commit_is_refused(tmp_path: Path):
    repo, cell_spec, receipt = make_git_authentication_fixture(tmp_path)
    receipt["git_commit"] = "d" * 40
    with pytest.raises(RUNNER.TargetAuditError, match="commit object does not exist"):
        RUNNER.authenticate_producer_git(receipt, cell_spec, repo)


def test_wrong_producer_tree_is_refused(tmp_path: Path):
    repo, cell_spec, receipt = make_git_authentication_fixture(tmp_path)
    receipt["git_tree"] = "e" * 40
    with pytest.raises(RUNNER.TargetAuditError, match="tree does not match"):
        RUNNER.authenticate_producer_git(receipt, cell_spec, repo)


def test_failed_producer_ancestry_is_refused(tmp_path: Path):
    repo, cell_spec, receipt = make_git_authentication_fixture(tmp_path)
    completed = subprocess.run(
        ["git", "mktree"], cwd=repo, input="", text=True, capture_output=True, check=True
    )
    unrelated = subprocess.run(
        ["git", "commit-tree", completed.stdout.strip(), "-m", "unrelated root"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    cell_spec["git_contract"]["required_ancestor_commit"] = unrelated
    receipt["git_required_ancestor_commit"] = unrelated
    with pytest.raises(RUNNER.TargetAuditError, match="not an ancestor"):
        RUNNER.authenticate_producer_git(receipt, cell_spec, repo)


def test_producer_blob_mismatch_is_refused(tmp_path: Path):
    repo, cell_spec, receipt = make_git_authentication_fixture(tmp_path)
    wrong = "f" * 64
    cell_spec["runtime_code_hashes"][str(RUNNER.BUILDER_REL)] = wrong
    receipt["git_committed_artifact_hashes"][str(RUNNER.BUILDER_REL)] = wrong
    with pytest.raises(RUNNER.TargetAuditError, match="committed blob hash differs"):
        RUNNER.authenticate_producer_git(receipt, cell_spec, repo)


def test_consuming_head_mismatch_is_refused(tmp_path: Path):
    repo, cell_spec, receipt = make_git_authentication_fixture(tmp_path)
    (repo / "later.txt").write_text("later clean commit\n", encoding="utf-8")
    git_output(repo, "add", "later.txt")
    git_output(repo, "commit", "-q", "-m", "later checkout")
    with pytest.raises(RUNNER.TargetAuditError, match="checkout HEAD differs"):
        RUNNER.authenticate_producer_git(receipt, cell_spec, repo)


def test_dirty_consuming_checkout_is_refused(tmp_path: Path):
    repo, cell_spec, receipt = make_git_authentication_fixture(tmp_path)
    (repo / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(RUNNER.TargetAuditError, match="checkout is not clean"):
        RUNNER.authenticate_producer_git(receipt, cell_spec, repo)


def test_authenticated_synthetic_execution_reconciles_zero_and_fractional_cells(
    product, tmp_path: Path
):
    cells, receipt, _ = product
    producer = json.loads(receipt.read_text(encoding="utf-8"))
    assert producer["six_field_cell_build_checks"][
        "wide_march_positive_weight_rows_explicitly_replaced"
    ] == 0
    output = tmp_path / "target-audit"
    result = execute_target(
        Namespace(repo_root=REPO, cells=cells, cells_receipt=receipt, output_leaf=output)
    )
    assert result["status"] == "PASS_EXACT_TARGET_AUDIT"
    audit = json.loads((output / RUNNER.AUDIT_FILENAME).read_text(encoding="utf-8"))
    facts = audit["observed_estimating_data"]["facts"]
    assert facts["static_grid_rows"] == 468 * 113
    assert facts["one_sided_zero_rows_retained"] == 2
    assert facts["zero_young_positive_older_rows_retained"] == 1
    assert facts["positive_young_zero_older_rows_retained"] == 1
    assert facts["both_zero_rows_no_criterion_contribution"] == 1
    assert facts["positive_total_estimating_rows"] == 468 * 113 - 1
    assert facts["static_young_noninteger_stock_rows"] > 0
    assert facts["static_older_noninteger_stock_rows"] > 0
    assert audit["criterion_and_parameter"]["coefficient_unit"] == "log points"
    forbidden = " ".join(audit["interpretation_bounds"]["forbidden"])
    assert "individual employment probability" in forbidden
    assert "employer hiring rate" in forbidden
    execution = json.loads((output / RUNNER.RECEIPT_FILENAME).read_text(encoding="utf-8"))
    assert execution["security"]["row_level_microdata_read"] is False
    assert execution["security"]["coefficient_estimated"] is False


def test_weight_once_failure_is_blocking(product, tmp_path: Path):
    cells, receipt, _ = product
    altered = tmp_path / "altered"
    altered_cells, altered_receipt = clone_authenticated_leaf(cells, receipt, altered)
    value = json.loads(receipt.read_text(encoding="utf-8"))
    value["weight_application_count"] = 2
    altered_receipt.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RUNNER.TargetAuditError, match="weight count differs from one"):
        execute_target(
            Namespace(
                repo_root=REPO,
                cells=altered_cells,
                cells_receipt=altered_receipt,
                output_leaf=tmp_path / "out",
            )
        )


def test_fractional_physical_count_is_refused(product, tmp_path: Path):
    cells, receipt, _ = product
    altered = tmp_path / "altered-count"
    altered_cells, altered_receipt = clone_authenticated_leaf(cells, receipt, altered)
    value = json.loads(receipt.read_text(encoding="utf-8"))
    value["six_field_cell_build_checks"]["routed_rows"] = 10.5
    altered_receipt.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RUNNER.TargetAuditError, match="physical integer count"):
        execute_target(
            Namespace(
                repo_root=REPO,
                cells=altered_cells,
                cells_receipt=altered_receipt,
                output_leaf=tmp_path / "out-count",
            )
        )


def test_by_source_physical_count_must_reconcile(product, tmp_path: Path):
    cells, receipt, _ = product
    altered = tmp_path / "altered-source-count"
    altered_cells, altered_receipt = clone_authenticated_leaf(cells, receipt, altered)
    value = json.loads(receipt.read_text(encoding="utf-8"))
    value["six_field_cell_build_checks"][
        "eligible_employed_age_22_65_records_by_source"
    ]["ipums_cps_extract_9_wide"] -= 1
    altered_receipt.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RUNNER.TargetAuditError, match="eligible source-record total"):
        execute_target(
            Namespace(
                repo_root=REPO,
                cells=altered_cells,
                cells_receipt=altered_receipt,
                output_leaf=tmp_path / "out-source-count",
            )
        )


def test_six_field_runtime_universe_is_binding(product, tmp_path: Path):
    cells, receipt, _ = product
    altered = tmp_path / "altered-raw-fields"
    altered_cells, altered_receipt = clone_authenticated_leaf(cells, receipt, altered)
    value = json.loads(receipt.read_text(encoding="utf-8"))
    value["six_field_cell_build_checks"]["runtime_raw_fields"].append("OCC2010")
    altered_receipt.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RUNNER.TargetAuditError, match="raw-field universe"):
        execute_target(
            Namespace(
                repo_root=REPO,
                cells=altered_cells,
                cells_receipt=altered_receipt,
                output_leaf=tmp_path / "out-raw-fields",
            )
        )


def test_unexpected_cell_column_is_refused(product, tmp_path: Path):
    cells, receipt, frame = product
    altered = tmp_path / "altered-schema"
    altered_cells, altered_receipt = clone_authenticated_leaf(cells, receipt, altered)
    changed = frame.copy()
    changed["WTFINL"] = 1.0
    changed.to_csv(altered_cells, index=False)
    value = json.loads(receipt.read_text(encoding="utf-8"))
    value["cells_sha256"] = RUNNER.sha256_file(altered_cells)
    value["weight_once_checks"]["young_stock"] = float(changed.young.sum())
    value["weight_once_checks"]["older_stock"] = float(changed.older.sum())
    altered_receipt.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RUNNER.TargetAuditError, match="columns or column order"):
        execute_target(
            Namespace(
                repo_root=REPO,
                cells=altered_cells,
                cells_receipt=altered_receipt,
                output_leaf=tmp_path / "out-schema",
            )
        )


def test_hash_mismatch_is_refused_before_reading_target(product, tmp_path: Path):
    cells, receipt, _ = product
    altered = tmp_path / "altered-hash"
    altered_cells, altered_receipt = clone_authenticated_leaf(cells, receipt, altered)
    altered_cells.write_bytes(cells.read_bytes() + b"\n")
    with pytest.raises(RUNNER.TargetAuditError, match="cells_sha256"):
        execute_target(
            Namespace(
                repo_root=REPO,
                cells=altered_cells,
                cells_receipt=altered_receipt,
                output_leaf=tmp_path / "out-hash",
            )
        )


def mutate_producer_receipt(value: dict, case: str) -> None:
    if case == "missing_analysis_id":
        value.pop("analysis_spec_id")
    elif case == "canonical_source_map":
        value["source_hashes"].pop("historical_preperiod_cells")
    elif case == "authenticated_source_map":
        value["authenticated_source_hashes"]["historical_preperiod_cells"] = "a" * 64
    elif case == "unread_source":
        value["unread_canonical_source_ids"] = []
    elif case == "authorization_subcheck":
        value["authorization"]["checks"]["microdata_sha256"] = False
    elif case == "runtime_status":
        value["runtime_authentication"]["status"] = "UNVERIFIED"
    elif case == "execution_command_binding":
        value["execution_command_binding"]["scheduler_jobnumber"] = "700099"
    elif case == "execution_runtime_authentication":
        value["execution_runtime_authentication"]["isolated_mode"] = False
    elif case == "pre_execution_authorization":
        value["pre_execution_authorization"]["authorization_id"] = (
            RUNNER.PRE_EXECUTION_AUTHORIZATION_PREFIX + "e" * 64
        )
    elif case == "runtime_code_map":
        value["runtime_code_hashes"] = {}
    elif case == "builder_hash":
        value["builder_code_sha256"] = "a" * 64
    elif case == "git_committed_map":
        value["git_committed_artifact_hashes"].pop(str(RUNNER.BUILDER_REL))
    elif case == "repair_months":
        value["six_field_cell_build_checks"]["repair_observed_months"] = ["2017-03"]
    elif case == "wide_march_positive_weight_rows":
        value["six_field_cell_build_checks"][
            "wide_march_positive_weight_rows_explicitly_replaced"
        ] = 1
    elif case == "route_record_identity":
        value["route_checks"]["total_record_identities"][
            "valid_equals_early_plus_current"
        ] = False
    elif case == "route_source_gap":
        value["route_checks"]["source_stock_reconciliation"][
            "ipums_cps_extract_9_wide"
        ]["early_relative_gap"] = 0.1
    elif case == "freshness_field":
        value["freshness_and_security"].pop("historical_reference_code_imported_at_runtime")
    elif case == "calendar_repair_months":
        value["calendar_checks"]["restored_march_months"] = ["2017-03"]
    else:
        raise AssertionError(f"unknown producer-receipt mutation: {case}")


@pytest.mark.parametrize(
    "case",
    [
        "missing_analysis_id",
        "canonical_source_map",
        "authenticated_source_map",
        "unread_source",
        "authorization_subcheck",
        "runtime_status",
        "execution_command_binding",
        "execution_runtime_authentication",
        "pre_execution_authorization",
        "runtime_code_map",
        "builder_hash",
        "git_committed_map",
        "repair_months",
        "wide_march_positive_weight_rows",
        "route_record_identity",
        "route_source_gap",
        "freshness_field",
        "calendar_repair_months",
    ],
)
def test_each_load_bearing_producer_receipt_mutation_is_refused(
    product, tmp_path: Path, case: str
):
    cells, receipt, _ = product
    altered = tmp_path / f"altered-producer-{case}"
    altered_cells, altered_receipt = clone_authenticated_leaf(cells, receipt, altered)
    value = json.loads(receipt.read_text(encoding="utf-8"))
    mutate_producer_receipt(value, case)
    altered_receipt.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RUNNER.TargetAuditError):
        execute_target(
            Namespace(
                repo_root=REPO,
                cells=altered_cells,
                cells_receipt=altered_receipt,
                output_leaf=tmp_path / f"out-producer-{case}",
            )
        )


def test_output_leaf_must_be_new_and_outside_repo(product, tmp_path: Path):
    cells, receipt, _ = product
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(RUNNER.TargetAuditError, match="pre-existing"):
        RUNNER.reserve_output_leaf(existing, REPO, cells.parent)
    with pytest.raises(RUNNER.TargetAuditError, match="outside the Git repository"):
        execute_target(
            Namespace(
                repo_root=REPO,
                cells=cells,
                cells_receipt=receipt,
                output_leaf=TARGET_DIR / "forbidden-output",
            )
        )


def test_dangling_symlink_output_leaf_is_refused(tmp_path: Path):
    input_leaf = tmp_path / "input-leaf"
    input_leaf.mkdir()
    dangling = tmp_path / "dangling-output"
    dangling.symlink_to(tmp_path / "missing-target", target_is_directory=True)
    assert RUNNER.os.path.lexists(dangling)
    with pytest.raises(RUNNER.TargetAuditError, match="pre-existing output leaf"):
        RUNNER.reserve_output_leaf(dangling, REPO, input_leaf)


def test_target_atomic_publish_is_noreplace_and_inventory_bound(tmp_path: Path):
    staging = tmp_path / ".staging"
    staging.mkdir()
    (staging / "expected.txt").write_text("complete\n", encoding="utf-8")
    destination = tmp_path / "published"
    RUNNER.atomic_publish(staging, destination, {"expected.txt"})
    assert (destination / "expected.txt").read_text(encoding="utf-8") == "complete\n"
    second = tmp_path / ".second"
    second.mkdir()
    with pytest.raises(RUNNER.TargetAuditError, match="appeared"):
        RUNNER.atomic_publish(second, destination)

    inventory = tmp_path / ".inventory"
    inventory.mkdir()
    (inventory / "expected.txt").write_text("expected\n", encoding="utf-8")
    (inventory / "extra.txt").write_text("extra\n", encoding="utf-8")
    with pytest.raises(RUNNER.TargetAuditError, match="inventory"):
        RUNNER.atomic_publish(
            inventory, tmp_path / "inventory-output", {"expected.txt"}
        )


def test_target_atomic_publish_uses_reserved_gpfs_fallback_on_einval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    staging = tmp_path / ".gpfs-staging"
    staging.mkdir()
    (staging / "expected.txt").write_text("complete\n", encoding="utf-8")
    destination = tmp_path / "gpfs-published"
    monkeypatch.setattr(
        RUNNER, "atomic_noreplace_rename_errno",
        lambda _source, _target: RUNNER.errno.EINVAL,
    )
    RUNNER.atomic_publish(staging, destination, {"expected.txt"})
    assert (destination / "expected.txt").read_text(encoding="utf-8") == "complete\n"
    assert not (tmp_path / ".gpfs-published.publish.lock").exists()


def test_target_gpfs_fallback_has_no_raising_postcommit_destination_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    staging = tmp_path / ".gpfs-postcommit-staging"
    staging.mkdir()
    (staging / "expected.txt").write_text("complete\n", encoding="utf-8")
    destination = tmp_path / "gpfs-postcommit-published"
    real_rename = RUNNER.os.rename
    real_stat = RUNNER.os.stat
    committed = False

    def tracked_rename(source, target):
        nonlocal committed
        real_rename(source, target)
        committed = True

    def guarded_stat(path, *args, **kwargs):
        if committed and Path(path) == destination:
            raise OSError("postcommit destination probe must not occur")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(
        RUNNER, "atomic_noreplace_rename_errno",
        lambda _source, _target: RUNNER.errno.EINVAL,
    )
    monkeypatch.setattr(RUNNER.os, "rename", tracked_rename)
    monkeypatch.setattr(RUNNER.os, "stat", guarded_stat)
    RUNNER.atomic_publish(staging, destination, {"expected.txt"})
    assert (destination / "expected.txt").read_text(encoding="utf-8") == "complete\n"


def test_target_gpfs_postcommit_cleanup_failure_is_reported_not_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    staging = tmp_path / ".gpfs-cleanup-staging"
    staging.mkdir()
    (staging / "expected.txt").write_text("complete\n", encoding="utf-8")
    destination = tmp_path / "gpfs-cleanup-published"
    lock = tmp_path / ".gpfs-cleanup-published.publish.lock"
    real_unlink = Path.unlink

    def guarded_unlink(path, *args, **kwargs):
        if path == lock:
            raise OSError(RUNNER.errno.EIO, "injected cleanup failure")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(
        RUNNER, "atomic_noreplace_rename_errno",
        lambda _source, _target: RUNNER.errno.EINVAL,
    )
    monkeypatch.setattr(Path, "unlink", guarded_unlink)
    warnings = RUNNER.atomic_publish(staging, destination, {"expected.txt"})
    assert warnings == (f"publication_lock_unlink_errno_{RUNNER.errno.EIO}",)
    assert (destination / "expected.txt").read_text(encoding="utf-8") == "complete\n"


def test_target_gpfs_fallback_refuses_existing_reservation(tmp_path: Path):
    staging = tmp_path / ".reserved-staging"
    staging.mkdir()
    destination = tmp_path / "reserved-published"
    (tmp_path / ".reserved-published.publish.lock").write_text(
        "other publisher\n", encoding="utf-8"
    )
    with pytest.raises(RUNNER.TargetAuditError, match="reserved"):
        RUNNER.gpfs_atomic_publish_under_reservation(staging, destination)
    assert staging.exists()
    assert not destination.exists()


def test_target_atomic_publish_rejects_hardlinked_outputs(tmp_path: Path):
    linked = tmp_path / ".linked"
    linked.mkdir()
    source = linked / "expected.txt"
    source.write_text("linked\n", encoding="utf-8")
    os.link(source, linked / "alias.txt")
    with pytest.raises(RUNNER.TargetAuditError, match="multiply linked"):
        RUNNER.atomic_publish(
            linked,
            tmp_path / "linked-output",
            {"expected.txt", "alias.txt"},
        )


def test_semantic_mutation_of_age_contract_is_refused():
    target, canonical, _ = RUNNER.load_and_validate_specs(REPO)
    mutated = json.loads(json.dumps(canonical))
    mutated["outcome"]["age_groups"]["young"] = "ages 18 through 25"
    with pytest.raises(RUNNER.TargetAuditError, match="young_age_group"):
        RUNNER.validate_assertions(mutated, target["canonical_assertions"], "canonical")


def test_redaction_removes_private_paths_and_secret_shapes(tmp_path: Path):
    token = "ghp" + "_" + "a" * 30
    raw = f"token=abc at /projectnb/private/cells and {tmp_path}; {token}"
    cleaned = RUNNER.sanitize_text(raw, {str(tmp_path): "<OUTPUT>"})
    assert "/projectnb/" not in cleaned
    assert str(tmp_path) not in cleaned
    assert "ghp_" not in cleaned
    assert "abc" not in cleaned
    RUNNER.assert_sanitized({"message": cleaned})
