from __future__ import annotations

import argparse
from argparse import Namespace
import ast
import hashlib
import importlib.util
import inspect
import json
import os
import pathlib
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


TEST_FILE = Path(__file__).resolve()
REPO = TEST_FILE.parents[5]
SCRIPT = TEST_FILE.parents[1] / "run_gate1_cells.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = load_module("yax_v3_gate1_cells_test", SCRIPT)


def cell_entry_fixture(tmp_path: Path) -> tuple[Namespace, list[str], list[str]]:
    args = Namespace(
        repo_root=REPO,
        microdata=tmp_path / "wide.dat.gz",
        repair_microdata=tmp_path / "repair.dat.gz",
        output_parent=tmp_path,
    )
    raw = [
        "--repo-root", str(args.repo_root),
        "--microdata", str(args.microdata),
        "--repair-microdata", str(args.repair_microdata),
        "--output-parent", str(args.output_parent),
    ]
    original = [sys.executable, "-I", str(SCRIPT), *raw]
    return args, raw, original


def test_cli_help_does_not_read_protected_inputs():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--microdata" in completed.stdout
    assert "--repair-microdata" in completed.stdout
    assert "--output-parent" in completed.stdout
    assert "--output-leaf" not in completed.stdout


def test_production_entry_and_command_binding_are_not_caller_attested(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    assert list(inspect.signature(BUILDER.execute).parameters) == ["args"]
    assert BUILDER.main([]) == 2
    assert "substituted argv" in capsys.readouterr().err
    args, raw, original = cell_entry_fixture(tmp_path)
    binding = BUILDER.build_execution_command_binding(
        args, raw, original, {"JOB_ID": "700001", "SGE_JOB_ID": "700001"}
    )
    assert binding["run_id"] == "gate1_cells_sge_700001"
    assert binding["scheduler_jobnumber"] == "700001"
    assert str(tmp_path) not in json.dumps(binding)
    with pytest.raises(BUILDER.CellBuildError, match="direct isolated"):
        BUILDER.build_execution_command_binding(
            args, raw, [sys.executable, str(SCRIPT), *raw], {"JOB_ID": "700001"}
        )
    with pytest.raises(BUILDER.CellBuildError, match="array jobs"):
        BUILDER.build_execution_command_binding(
            args, raw, original, {"JOB_ID": "700001", "SGE_TASK_ID": "1"}
        )


def test_command_binding_rejects_repo_root_other_than_executing_checkout(tmp_path: Path):
    args, raw, original = cell_entry_fixture(tmp_path)
    args.repo_root = tmp_path
    raw[1] = str(tmp_path)
    original = [sys.executable, "-I", str(SCRIPT), *raw]
    with pytest.raises(BUILDER.CellBuildError, match="executing runner checkout"):
        BUILDER.build_execution_command_binding(
            args, raw, original, {"JOB_ID": "700001"}
        )


def test_postcommit_stdout_failure_does_not_change_success_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    observed = {}

    def completed(args):
        observed["output_leaf"] = args.output_leaf
        return {"status": "PASS_FRESH_AGGREGATE_REBUILD"}

    monkeypatch.setattr(BUILDER, "execute", completed)
    monkeypatch.setattr(BUILDER, "scheduler_jobnumber", lambda _env: "12345")
    monkeypatch.setattr(
        BUILDER.sys, "argv",
        [
            str(BUILDER.__file__), "--repo-root", str(REPO),
            "--microdata", str(tmp_path / "wide.csv.gz"),
            "--repair-microdata", str(tmp_path / "repair.csv.gz"),
            "--output-parent", str(tmp_path),
        ],
    )
    monkeypatch.setattr(
        "builtins.print",
        lambda *args, **kwargs: (_ for _ in ()).throw(BrokenPipeError()),
    )
    assert BUILDER.main() == 0
    assert observed["output_leaf"] == tmp_path / "gate1_cells_sge_12345"


def test_pre_result_spec_and_runtime_reference_locks_authenticate():
    cell_spec, canonical = BUILDER.load_and_validate_specs(REPO)
    observed = BUILDER.authenticate_code(REPO, cell_spec)
    assert canonical["spec_id"] == BUILDER.EXPECTED_CANONICAL_SPEC_ID
    assert cell_spec["cell_build_spec_id"] == BUILDER.expected_cell_spec_id(cell_spec)
    assert set(observed["runtime"]) == set(cell_spec["runtime_code_hashes"])
    assert set(observed["historical_reference"]) == set(
        cell_spec["historical_reference_code_hashes"]
    )
    assert set(observed["runtime"]) == {
        str(BUILDER.HERE_REL / "run_gate1_cells.py")
    }


def test_one_file_runtime_fingerprint_is_explicit_empty_map_hash():
    builder = str(BUILDER.HERE_REL / "run_gate1_cells.py")
    observed = BUILDER.transitive_code_fingerprint({builder: "a" * 64})
    assert observed == hashlib.sha256(b"{}").hexdigest()
    with pytest.raises(BUILDER.CellBuildError, match="incomplete"):
        BUILDER.transitive_code_fingerprint({"reference.py": "b" * 64})


def test_numerical_consumer_contract_is_exactly_bound():
    cell_spec, canonical = BUILDER.load_and_validate_specs(REPO)
    consumer = BUILDER.validate_consumer_contract(REPO, cell_spec, canonical)
    assert consumer["analysis_spec_id"] == cell_spec["consumer_contract"][
        "analysis_spec_id"
    ]
    assert consumer["analysis_spec_sha256"] == cell_spec["consumer_contract"][
        "analysis_spec_sha256"
    ]
    assert all(consumer["input_contract_checks"].values())


def test_public_source_hashes_and_fixed_assignment_fingerprint_authenticate():
    cell_spec, canonical = BUILDER.load_and_validate_specs(REPO)
    expected = BUILDER.canonical_source_hashes(canonical)
    for source_id, relative in BUILDER.REPO_SOURCE_PATHS.items():
        assert BUILDER.sha256_file(REPO / relative) == expected[source_id]

    comp = pd.read_csv(
        REPO / BUILDER.REPO_SOURCE_PATHS["computerization_measures_census2018"],
        dtype={"census2018": str},
    )
    comp["census2018"] = comp.census2018.str.zfill(4)
    family_map = comp.set_index("census2018").soc_major_group.astype(str).to_dict()
    fixed = BUILDER.load_fixed_assignments(REPO, canonical, family_map)
    assert len(fixed) == 468
    assert BUILDER.assignment_fingerprint(fixed) == cell_spec["assignment_contract"][
        "fingerprint_sha256"
    ]
    assert BUILDER.support_hash(fixed.occ_code) == canonical["occupation"]["universe"][
        "content_support_sha256"
    ]


def synthetic_inputs(tmp_path: Path, *, helpers: bool) -> SimpleNamespace:
    primary_rows = [
        {"YEAR": 2019, "MONTH": 2, "AGE": 22, "EMPSTAT": 10, "OCC": 100,
         "WTFINL": 10.0, "OCC2010": 100, "IND1990": 10},
        {"YEAR": 2019, "MONTH": 2, "AGE": 18, "EMPSTAT": 10, "OCC": 100,
         "WTFINL": 7.0, "OCC2010": 100, "IND1990": 10},
        {"YEAR": 2020, "MONTH": 1, "AGE": 30, "EMPSTAT": 12, "OCC": 200,
         "WTFINL": 20.0, "OCC2010": 100, "IND1990": 641},
        {"YEAR": 2023, "MONTH": 1, "AGE": 25, "EMPSTAT": 10, "OCC": 300,
         "WTFINL": 8.0, "OCC2010": 100, "IND1990": 10},
    ]
    repair_rows = []
    for year in range(2017, 2022):
        primary_rows.append(
            {"YEAR": year, "MONTH": 3, "AGE": 22, "EMPSTAT": 10, "OCC": 100,
             "WTFINL": 0.0, "OCC2010": 100, "IND1990": 10}
        )
        repair_rows.append(
            {"YEAR": year, "MONTH": 3, "AGE": 22 if year % 2 else 26,
             "EMPSTAT": 10, "OCC": 100 if year <= 2019 else 200,
             "WTFINL": float(year - 2016), "OCC2010": 100, "IND1990": 10}
        )
    columns = list(BUILDER.REQUIRED_RAW_COLUMNS)
    if helpers:
        columns += ["OCC2010", "IND1990"]
    primary = pd.DataFrame(primary_rows)[columns]
    repair = pd.DataFrame(repair_rows)[columns]
    bridge = pd.DataFrame(
        {
            "census_2010": ["0100", "0100"],
            "census_2018": ["0200", "0300"],
            "bridge_weight": [0.25, 0.75],
        }
    )
    primary_path = tmp_path / ("primary-helper.csv" if helpers else "primary.csv")
    repair_path = tmp_path / ("repair-helper.csv" if helpers else "repair.csv")
    bridge_path = tmp_path / "bridge.csv"
    primary.to_csv(primary_path, index=False)
    repair.to_csv(repair_path, index=False)
    bridge.to_csv(bridge_path, index=False)
    return SimpleNamespace(
        microdata=primary_path,
        repair_microdata=repair_path,
        bridge=bridge_path,
    )


def normalized_target(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.loc[frame.age.between(22, 65)]
        .groupby(["occ_code", "month", "age", "route_kind"], as_index=False, observed=True)
        .stock.sum()
        .sort_values(["occ_code", "month", "age", "route_kind"], kind="mergesort")
        .reset_index(drop=True)
    )


def load_byte_locked_historical_cells_module():
    expected = {
        BUILDER.R3_CELLS_REL: "a82b1331153645d438509a71e43080e568838ebdb9cdc509fd98cec257e1d4b0",
        BUILDER.R3_CORE_REL: "1f084084ba67425f398c6bfa5237d74621bad3c1ba63ffd2df7f0d0954563ade",
        BUILDER.FROZEN_REL: "e40fdda2353dd0c0d6f92401e7bdfb5874c8a32ffa9d641b38144cc07054ddff",
        BUILDER.ENGINE_REL: "096f0290b057e565077278ef38b352a9af5551c3b525438015bf9f192087bddf",
    }
    for relative, digest in expected.items():
        assert BUILDER.sha256_file(REPO / relative) == digest
    # Do not import the historical module: its top level dynamically imports a
    # large analysis closure unrelated to this target-router parity check.
    # Compile only the byte-locked constants and functions the parity fixture
    # invokes, in a controlled namespace whose non-stdlib objects are explicit.
    source_path = REPO / BUILDER.R3_CELLS_REL
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    allowed_names = {
        "MARCH_GAPS",
        "MARCH_REPAIR_POLICY",
        "LEISURE_HOSPITALITY_IND1990",
        "month_string",
        "replaced_base_march_mask",
        "build_exact_age_cells",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        names: set[str] = set()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = {node.name}
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {
                target.id for target in targets if isinstance(target, ast.Name)
            }
        if names & allowed_names:
            selected.append(node)
    selected_names = {
        node.name
        for node in selected
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    assert selected_names == {
        "month_string", "replaced_base_march_mask", "build_exact_age_cells"
    }
    controlled = {
        "__builtins__": __builtins__,
        "argparse": argparse,
        "np": np,
        "pd": pd,
        "pathlib": pathlib,
    }
    module_ast = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    exec(compile(module_ast, str(source_path), "exec"), controlled)
    return SimpleNamespace(**{name: controlled[name] for name in allowed_names})


def test_local_six_field_router_matches_byte_locked_historical_target(tmp_path: Path):
    args = synthetic_inputs(tmp_path, helpers=True)
    historical = load_byte_locked_historical_cells_module()
    inherited, _stable, _old_counts = historical.build_exact_age_cells(
        Namespace(**vars(args))
    )
    local, counts, route = BUILDER.build_six_field_target_cells(
        args.microdata, args.repair_microdata, args.bridge
    )
    pd.testing.assert_frame_equal(normalized_target(local), normalized_target(inherited))
    assert counts["physical_rows_read_total"] == 14
    assert counts["eligible_employed_age_22_65_records_total"] == 8
    assert counts["repair_eligible_employed_age_22_65_records"] == 5
    assert counts["wide_march_rows_explicitly_replaced"] == 5
    assert counts["wide_march_positive_weight_rows_explicitly_replaced"] == 0
    assert route["route_conservation_pass"] is True
    assert route["early_absolute_gap"] == 0.0
    assert route["current_absolute_gap"] == 0.0
    assert 18 not in set(local.age)


def test_producer_counts_unexpected_positive_weight_wide_march_rows(tmp_path: Path):
    """The producer reports, rather than conceals, a source-contract violation."""
    args = synthetic_inputs(tmp_path, helpers=False)
    baseline_cells, _baseline_counts, _baseline_route = (
        BUILDER.build_six_field_target_cells(
            args.microdata, args.repair_microdata, args.bridge
        )
    )
    primary = pd.read_csv(args.microdata)
    march = primary.MONTH.eq(3)
    primary.loc[primary.index[march][0], "WTFINL"] = 2.5
    primary.to_csv(args.microdata, index=False)

    cells, counts, _route = BUILDER.build_six_field_target_cells(
        args.microdata, args.repair_microdata, args.bridge
    )
    assert counts["wide_march_rows_explicitly_replaced"] == 5
    assert counts["wide_march_positive_weight_rows_explicitly_replaced"] == 1
    assert counts["repair_eligible_employed_age_22_65_records"] == 5
    pd.testing.assert_frame_equal(
        normalized_target(cells), normalized_target(baseline_cells)
    )


def test_physical_records_reconcile_through_routes_and_fractional_descendants(
    tmp_path: Path,
):
    args = synthetic_inputs(tmp_path, helpers=False)
    primary = pd.read_csv(args.microdata)
    primary = pd.concat(
        [
            primary,
            pd.DataFrame(
                [
                    {
                        "YEAR": 2019, "MONTH": 2, "AGE": 23, "EMPSTAT": 10,
                        "OCC": "0999", "WTFINL": 2.0,
                    },
                    {
                        "YEAR": 2020, "MONTH": 2, "AGE": 23, "EMPSTAT": 10,
                        "OCC": "invalid", "WTFINL": 3.0,
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    primary.to_csv(args.microdata, index=False)
    _cells, counts, route = BUILDER.build_six_field_target_cells(
        args.microdata, args.repair_microdata, args.bridge
    )
    primary_id = "ipums_cps_extract_9_wide"
    repair_id = "ipums_cps_extract_11_march_basic_repair"
    assert counts["physical_rows_read_total"] == sum(
        counts["physical_rows_read_by_source"].values()
    )
    assert counts["eligible_employed_age_22_65_records_total"] == (
        counts["invalid_raw_occ_records"] + counts["valid_raw_occ_records"]
    )
    assert counts["early_unmatched_source_records_by_source"][primary_id] == 1
    assert counts["early_unmatched_source_records_by_source"][repair_id] == 0
    assert counts["early_expanded_route_descendants_by_source"][primary_id] == 2
    assert counts["early_fractional_route_contributions_by_source"][primary_id] == 2
    assert counts["current_direct_route_contributions_by_source"][primary_id] == 2
    assert counts["routed_contribution_rows_by_source"][primary_id] == 4
    assert all(route["total_record_identities"].values())
    assert all(
        all(identity.values())
        for identity in route["record_identities_by_source"].values()
    )
    assert route["source_stock_reconciliation"][primary_id][
        "unmatched_early_stock"
    ] == 2.0
    assert all(
        value["route_conservation_pass"]
        for value in route["source_stock_reconciliation"].values()
    )


def test_production_router_reads_only_six_fields_and_needs_no_helpers(tmp_path: Path):
    args = synthetic_inputs(tmp_path, helpers=False)
    assert BUILDER.inspect_required_raw_columns(args.microdata, "synthetic") == list(
        BUILDER.REQUIRED_RAW_COLUMNS
    )
    local, counts, route = BUILDER.build_six_field_target_cells(
        args.microdata, args.repair_microdata, args.bridge
    )
    assert not local.empty
    assert counts["runtime_raw_fields"] == list(BUILDER.REQUIRED_RAW_COLUMNS)
    assert route["route_conservation_pass"] is True


def test_each_canonical_raw_field_is_required(tmp_path: Path):
    for missing in BUILDER.REQUIRED_RAW_COLUMNS:
        remaining = [field for field in BUILDER.REQUIRED_RAW_COLUMNS if field != missing]
        path = tmp_path / f"missing-{missing}.csv"
        pd.DataFrame([{field: 1 for field in remaining}]).to_csv(path, index=False)
        with pytest.raises(BUILDER.CellBuildError, match=missing):
            BUILDER.inspect_required_raw_columns(path, "synthetic")


def test_production_source_has_no_dynamic_historical_import_route():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "import importlib.util" not in source
    assert "def _load_module" not in source
    assert "build_exact_age_cells(" not in source
    assert "OCC2010" not in BUILDER.REQUIRED_RAW_COLUMNS
    assert "IND1990" not in BUILDER.REQUIRED_RAW_COLUMNS


def test_production_has_no_duplicate_literal_dictionary_keys():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [key.value for key in node.keys if isinstance(key, ast.Constant)]
        assert len(keys) == len(set(keys)), f"duplicate literal key on line {node.lineno}"


def test_balanced_output_retains_zero_cells_and_exact_grouped_stocks(tmp_path: Path):
    args = synthetic_inputs(tmp_path, helpers=False)
    cells, _counts, _route = BUILDER.build_six_field_target_cells(
        args.microdata, args.repair_microdata, args.bridge
    )
    fixed = pd.DataFrame(
        [
            {"occ_code": "0200", "family": "15", "beta_quintile": 4, "webb_z": 0.5},
            {"occ_code": "0300", "family": "17", "beta_quintile": 5, "webb_z": -0.5},
        ]
    )
    months = ["2019-02", "2020-01", "2023-01"]
    output, checks = BUILDER.build_balanced_output(cells, fixed, months)
    assert len(output) == 6
    assert checks["weight_application_count"] == 1
    assert checks["independent_aggregation_max_absolute_gap"] == 0.0
    assert output.young.sum() == 18.0
    assert output.older.sum() == 20.0
    zero = output.loc[
        output.occ_code.eq("0300") & output.month.eq("2020-01")
    ].iloc[0]
    assert zero.young == 0.0 and zero.older == 0.0


def test_assignment_fingerprint_is_order_invariant_but_value_sensitive():
    frame = pd.DataFrame(
        [
            {"occ_code": "0002", "family": "13", "beta_quintile": 2, "webb_z": 0.1},
            {"occ_code": "0001", "family": "11", "beta_quintile": 1, "webb_z": -0.1},
        ]
    )
    baseline = BUILDER.assignment_fingerprint(frame)
    assert BUILDER.assignment_fingerprint(frame.iloc[::-1]) == baseline
    altered = frame.copy()
    altered.loc[altered.occ_code.eq("0002"), "webb_z"] = 0.1000000000001
    assert BUILDER.assignment_fingerprint(altered) != baseline


def test_fresh_contract_comparison_rejects_assignment_drift():
    cell_spec, canonical = BUILDER.load_and_validate_specs(REPO)
    fixed = pd.DataFrame(
        [
            {"occ_code": "0001", "family": "11", "beta_quintile": 1, "webb_z": -0.1},
            {"occ_code": "0002", "family": "13", "beta_quintile": 2, "webb_z": 0.1},
        ]
    )
    rebuilt = {
        "membership": [
            {"occupation_code": "0001", "beta_quintile": 1, "webb_z": -0.1},
            {"occupation_code": "0002", "beta_quintile": 2, "webb_z": 0.1},
        ],
        "cuts": canonical["exposure"]["cutoffs"],
        "normalization": {
            "webb_weighted_mean": canonical["exposure"]["webb_normalization"]["mean"],
            "webb_weighted_sd": canonical["exposure"]["webb_normalization"]["sd"],
            "construction_months": 71,
            "no_postperiod_stock_used": True,
        },
    }
    result = BUILDER.validate_rebuilt_contract(rebuilt, fixed, canonical, cell_spec)
    assert result["fresh_quintiles_match_fixed"] is True
    rebuilt["membership"][1]["beta_quintile"] = 3
    with pytest.raises(BUILDER.CellBuildError, match="quintile"):
        BUILDER.validate_rebuilt_contract(rebuilt, fixed, canonical, cell_spec)


def test_environment_lock_payload_is_strong_and_kernel_patch_nonbinding():
    text = (REPO / BUILDER.ENVIRONMENT_REL).read_text(encoding="utf-8")
    expected = BUILDER.parse_scc_environment_lock(text)
    observed = {
        **expected,
        "python_implementation": "CPython",
        "scipy": "1.16.2",
        "libc_name": "glibc",
        "kernel_release": "4.18.0-DIFFERENT-COMPUTE-NODE",
    }
    assert BUILDER.compare_runtime(expected, observed)["status"].startswith("AUTHENTICATED")
    bad = dict(observed)
    bad["python_compiler"] = "different"
    with pytest.raises(BUILDER.CellBuildError, match="runtime differs"):
        BUILDER.compare_runtime(expected, bad)
    payload = {
        "architecture": "x86_64",
        "libc": {"name": "glibc", "version": "2.28"},
        "packages": {
            "numpy": "2.5.1", "pandas": "3.0.3", "pytest": "9.1.1", "scipy": "1.16.2"
        },
        "python_compiler": "GCC 12.2.0",
        "python_implementation": "CPython",
        "python_version": "3.13.8",
    }
    assert hashlib.sha256(BUILDER.canonical_bytes(payload)).hexdigest() == (
        "8003414233a40768089a6c584b3ecc4e3a1de9ca89c1c0b6cf5c5810024f7f79"
    )


def test_git_contract_requires_committed_clean_artifacts(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "YAX test"], cwd=repo, check=True)
    paths = [
        Path("run_gate1_cells.py"), Path("cell.json"), Path("analysis.json"), Path("env.txt")
    ]
    for path in paths:
        (repo / path).write_text(f"{path}\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    monkeypatch.setattr(BUILDER, "HERE_REL", Path("."))
    monkeypatch.setattr(BUILDER, "CELL_SPEC_REL", paths[1])
    monkeypatch.setattr(BUILDER, "NUMERICAL_SPEC_REL", paths[2])
    monkeypatch.setattr(BUILDER, "ENVIRONMENT_REL", paths[3])
    contract = {
        "git_contract": {
            "clean_worktree_required": True,
            "required_ancestor_commit": head,
            "committed_paths": [str(path) for path in paths],
            "live_files_must_equal_head_blobs": True,
            "runtime_head_and_tree_recorded": True,
        }
    }
    result = BUILDER.authenticate_git(repo, contract)
    assert result["git_status"] == "PASS_COMMITTED_CLEAN_WORKTREE"
    assert result["git_commit"] == head
    (repo / paths[0]).write_text("changed\n", encoding="utf-8")
    with pytest.raises(BUILDER.CellBuildError, match="not clean"):
        BUILDER.authenticate_git(repo, contract)


def test_output_leaf_must_be_new_and_outside_repository(tmp_path: Path):
    outside = tmp_path / "new-leaf"
    staging = BUILDER.reserve_staging_leaf(outside, REPO)
    assert staging.parent == tmp_path
    shutil.rmtree(staging)
    outside.mkdir()
    with pytest.raises(BUILDER.CellBuildError, match="pre-existing"):
        BUILDER.reserve_staging_leaf(outside, REPO)
    with pytest.raises(BUILDER.CellBuildError, match="outside"):
        BUILDER.reserve_staging_leaf(REPO / "protected-cells", REPO)
    broken = tmp_path / "broken-link"
    broken.symlink_to(tmp_path / "absent-target", target_is_directory=True)
    with pytest.raises(BUILDER.CellBuildError, match="pre-existing"):
        BUILDER.reserve_staging_leaf(broken, REPO)


def test_atomic_publish_refuses_overwrite(tmp_path: Path):
    destination = tmp_path / "published"
    staging = Path(tmp_path / ".staging")
    staging.mkdir()
    (staging / "file.txt").write_text("complete\n", encoding="utf-8")
    BUILDER.atomic_publish(staging, destination, {"file.txt"})
    assert (destination / "file.txt").read_text(encoding="utf-8") == "complete\n"
    second = tmp_path / ".second"
    second.mkdir()
    with pytest.raises(BUILDER.CellBuildError, match="appeared"):
        BUILDER.atomic_publish(second, destination)


def test_atomic_publish_uses_reserved_gpfs_fallback_on_einval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    staging = tmp_path / ".gpfs-staging"
    staging.mkdir()
    (staging / "file.txt").write_text("complete\n", encoding="utf-8")
    destination = tmp_path / "gpfs-published"
    monkeypatch.setattr(
        BUILDER, "atomic_noreplace_rename_errno",
        lambda _source, _target: BUILDER.errno.EINVAL,
    )
    BUILDER.atomic_publish(staging, destination, {"file.txt"})
    assert (destination / "file.txt").read_text(encoding="utf-8") == "complete\n"
    assert not (tmp_path / ".gpfs-published.publish.lock").exists()


def test_gpfs_fallback_has_no_raising_postcommit_destination_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    staging = tmp_path / ".gpfs-postcommit-staging"
    staging.mkdir()
    (staging / "file.txt").write_text("complete\n", encoding="utf-8")
    destination = tmp_path / "gpfs-postcommit-published"
    real_rename = BUILDER.os.rename
    real_stat = BUILDER.os.stat
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
        BUILDER, "atomic_noreplace_rename_errno",
        lambda _source, _target: BUILDER.errno.EINVAL,
    )
    monkeypatch.setattr(BUILDER.os, "rename", tracked_rename)
    monkeypatch.setattr(BUILDER.os, "stat", guarded_stat)
    BUILDER.atomic_publish(staging, destination, {"file.txt"})
    assert (destination / "file.txt").read_text(encoding="utf-8") == "complete\n"


def test_gpfs_postcommit_cleanup_failure_is_reported_not_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    staging = tmp_path / ".gpfs-cleanup-staging"
    staging.mkdir()
    (staging / "file.txt").write_text("complete\n", encoding="utf-8")
    destination = tmp_path / "gpfs-cleanup-published"
    lock = tmp_path / ".gpfs-cleanup-published.publish.lock"
    real_unlink = Path.unlink

    def guarded_unlink(path, *args, **kwargs):
        if path == lock:
            raise OSError(BUILDER.errno.EIO, "injected cleanup failure")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(
        BUILDER, "atomic_noreplace_rename_errno",
        lambda _source, _target: BUILDER.errno.EINVAL,
    )
    monkeypatch.setattr(Path, "unlink", guarded_unlink)
    warnings = BUILDER.atomic_publish(staging, destination, {"file.txt"})
    assert warnings == (f"publication_lock_unlink_errno_{BUILDER.errno.EIO}",)
    assert (destination / "file.txt").read_text(encoding="utf-8") == "complete\n"


def test_gpfs_fallback_refuses_an_existing_reservation(tmp_path: Path):
    staging = tmp_path / ".reserved-staging"
    staging.mkdir()
    destination = tmp_path / "reserved-published"
    (tmp_path / ".reserved-published.publish.lock").write_text(
        "other publisher\n", encoding="utf-8"
    )
    with pytest.raises(BUILDER.CellBuildError, match="reserved"):
        BUILDER.gpfs_atomic_publish_under_reservation(staging, destination)
    assert staging.exists()
    assert not destination.exists()


def test_atomic_publish_rejects_inventory_drift_and_hardlinks(tmp_path: Path):
    inventory = tmp_path / ".inventory"
    inventory.mkdir()
    (inventory / "expected.txt").write_text("expected\n", encoding="utf-8")
    (inventory / "extra.txt").write_text("extra\n", encoding="utf-8")
    with pytest.raises(BUILDER.CellBuildError, match="inventory"):
        BUILDER.atomic_publish(
            inventory, tmp_path / "inventory-output", {"expected.txt"}
        )

    linked = tmp_path / ".linked"
    linked.mkdir()
    source = linked / "expected.txt"
    source.write_text("linked\n", encoding="utf-8")
    os.link(source, linked / "alias.txt")
    with pytest.raises(BUILDER.CellBuildError, match="multiply linked"):
        BUILDER.atomic_publish(
            linked,
            tmp_path / "linked-output",
            {"expected.txt", "alias.txt"},
        )


def test_private_paths_and_common_secret_shapes_are_removed():
    secret = "ghp_" + "a" * 30
    raw = "failed /projectnb/econdept/private/cps.csv.gz; password=example; " + secret
    cleaned = BUILDER.sanitize_text(raw, {})
    assert "/projectnb/" not in cleaned
    assert "password=example" not in cleaned
    assert "ghp_" not in cleaned
    BUILDER.assert_sanitized({"log": cleaned})
    with pytest.raises(BUILDER.CellBuildError, match="sanitization"):
        BUILDER.assert_sanitized({"log": raw})


def test_receipt_minimum_fields_cover_execution_authentication_contract():
    required = {
        "command_template",
        "runtime_environment_lock_sha256",
        "runtime_contract_sha256",
        "runtime_payload_sha256",
        "runtime_authentication",
        "git_commit",
        "git_tree",
        "git_required_ancestor_commit",
        "git_worktree_clean",
        "git_committed_artifact_hashes",
        "builder_transitive_code_sha256",
        "raw_column_contract",
    }
    source = SCRIPT.read_text(encoding="utf-8")
    for field in required:
        assert f'"{field}"' in source
    assert "<YAX_PYTHON_BIN>" in BUILDER.COMMAND_TEMPLATE
    assert "/projectnb/" not in BUILDER.COMMAND_TEMPLATE
    assert list(BUILDER.OUTPUT_COLUMNS) == [
        "occ_code", "month", "family", "young", "older", "beta_quintile", "webb_z"
    ]
