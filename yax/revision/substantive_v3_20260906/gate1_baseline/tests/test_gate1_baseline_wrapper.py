from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


TEST_FILE = Path(__file__).resolve()
REPO = TEST_FILE.parents[5]
SCRIPT = TEST_FILE.parents[1] / "run_gate1_baseline.py"


def load_wrapper():
    spec = importlib.util.spec_from_file_location("yax_v3_gate1_wrapper_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


WRAPPER = load_wrapper()
SPEC = REPO / WRAPPER.SPEC_REL
REFERENCE = REPO / WRAPPER.REFERENCE_REL


def test_cli_help_is_available_without_touching_private_data():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"], text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 0
    assert "--microdata" in completed.stdout
    assert "--audit-dir" in completed.stdout


def test_canonical_contract_and_reference_bundle_authenticate():
    contract = WRAPPER.load_and_validate_contract(REPO, SPEC)
    assert contract["spec_id"].startswith("yaxspec_v1_")
    code = WRAPPER.authenticate_code(REPO, contract)
    assert code["runner_sha256"] == contract["execution"]["code_sha256"]
    dependencies = WRAPPER.authenticate_dependencies(contract, REFERENCE)
    reference = WRAPPER.authenticate_reference_bundle(
        contract, REFERENCE, code["transitive_source_commit"],
    )
    assert reference["reference_output_manifest_authenticated"] is True
    assert len(dependencies) == 2
    assert len(code["transitive_imports"]) == 4
    assert len(code["companion_files"]) == 2


def test_restamped_substitute_contract_is_refused(tmp_path: Path):
    contract = json.loads(SPEC.read_text(encoding="utf-8"))
    contract["analysis"]["name"] = "substituted analysis"
    tool_path = REPO / WRAPPER.SPEC_TOOL_REL
    tool_spec = importlib.util.spec_from_file_location("gate1_spec_tool_test", tool_path)
    assert tool_spec is not None and tool_spec.loader is not None
    tool = importlib.util.module_from_spec(tool_spec)
    sys.modules[tool_spec.name] = tool
    tool_spec.loader.exec_module(tool)
    contract["spec_id"] = tool.compute_spec_id(contract)
    substitute = tmp_path / "substitute.json"
    substitute.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(WRAPPER.Gate1Error, match="substituted or restamped"):
        WRAPPER.load_and_validate_contract(REPO, substitute)


def test_versioned_reference_satisfies_post_run_comparison_contract():
    contract = WRAPPER.load_and_validate_contract(REPO, SPEC)
    result = WRAPPER.compare_fresh_outputs(contract, REFERENCE, REFERENCE)
    assert result["status"] == "PASS_POST_RUN_CHECKPOINT_COMPARISON"
    assert result["membership"]["occupation_count"] == 468
    assert set(result["checkpoints"]) == set(WRAPPER.CHECKPOINT_ROWS)
    result_ids = WRAPPER.compute_checkpoint_result_ids(REPO, contract, REFERENCE)
    assert set(result_ids) == set(WRAPPER.CHECKPOINT_ROWS)
    assert all(value.startswith("yaxresult_v1_") for value in result_ids.values())


def test_post_run_comparison_fails_on_normalization_drift(tmp_path: Path):
    contract = WRAPPER.load_and_validate_contract(REPO, SPEC)
    fresh = tmp_path / "fresh"
    shutil.copytree(REFERENCE, fresh)
    path = fresh / "REBUILT_NORMALIZATION_AND_CUTS.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["webb_weighted_mean"] += 0.01
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(WRAPPER.Gate1Error, match="Webb weighted mean"):
        WRAPPER.compare_fresh_outputs(contract, fresh, REFERENCE)


def test_nonempty_output_is_refused(tmp_path: Path):
    destination = tmp_path / "results"
    destination.mkdir()
    (destination / "stale.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(WRAPPER.Gate1Error, match="refusing nonempty"):
        WRAPPER.require_new_or_empty(destination, "BASE-03 result directory")


def test_atomic_reservation_refuses_even_preexisting_empty_leaf(tmp_path: Path):
    destination = tmp_path / "results"
    WRAPPER.reserve_new_directory(destination, "BASE-03 result directory")
    with pytest.raises(WRAPPER.Gate1Error, match="unique new run path"):
        WRAPPER.reserve_new_directory(destination, "BASE-03 result directory")


def test_repository_descendants_are_detected():
    assert WRAPPER.path_is_within(REPO / "private-output", REPO)
    assert not WRAPPER.path_is_within(REPO.parent / "external-output", REPO)


def test_reference_bundle_is_pinned_not_merely_self_authenticating(tmp_path: Path):
    contract = WRAPPER.load_and_validate_contract(REPO, SPEC)
    code = WRAPPER.authenticate_code(REPO, contract)
    altered = tmp_path / "reference"
    shutil.copytree(REFERENCE, altered)
    receipt_path = altered / "EXECUTION_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["model_rows"][0]["coefficient"] += 0.01
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(WRAPPER.Gate1Error, match="pinned checkpoint bundle"):
        WRAPPER.authenticate_reference_bundle(
            contract, altered, code["transitive_source_commit"],
        )


def test_runtime_lock_parser_extracts_execution_environment():
    text = (REPO / WRAPPER.ENVIRONMENT_REL).read_text(encoding="utf-8")
    parsed = WRAPPER.parse_scc_environment_lock(text)
    assert parsed == {
        "python": "3.13.8",
        "python_compiler": "GCC 12.2.0",
        "numpy": "2.5.1",
        "pandas": "3.0.3",
        "pytest": "9.1.1",
        "kernel_system": "Linux",
        "kernel_release": "4.18.0-553.158.1.el8_10",
        "machine": "x86_64",
        "libc": "2.28",
    }


def test_runtime_auth_accepts_only_the_separately_declared_machine_suffix(
    monkeypatch: pytest.MonkeyPatch,
):
    lock = REPO / WRAPPER.ENVIRONMENT_REL
    observed = {
        "python": "3.13.8",
        "python_compiler": "GCC 12.2.0",
        "numpy": "2.5.1",
        "pandas": "3.0.3",
        "pytest": "9.1.1",
        "kernel_system": "Linux",
        "kernel_release": "4.18.0-553.158.1.el8_10.x86_64",
        "machine": "x86_64",
        "libc_name": "glibc",
        "libc": "2.28",
    }
    monkeypatch.setattr(
        WRAPPER.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=json.dumps(observed), stderr="",
        ),
    )
    result = WRAPPER.authenticate_runtime("python", lock, WRAPPER.sha256_file(lock))
    assert result["status"] == "AUTHENTICATED_DECLARED_RUNTIME"
    assert result["kernel_release_comparison"]["runtime"].endswith(".x86_64")

    observed["kernel_release"] += ".unexpected"
    with pytest.raises(WRAPPER.Gate1Error, match="runtime differs"):
        WRAPPER.authenticate_runtime("python", lock, WRAPPER.sha256_file(lock))


def test_redaction_removes_private_paths_and_common_secret_shapes(tmp_path: Path):
    replacements = {
        "/projectnb/private/cps.csv.gz": "<INPUT:microdata>",
        str(tmp_path): "<AUDIT_ROOT>",
    }
    synthetic_token = "ghp" + "_" + ("a" * 26)
    raw = (
        f"failed at /projectnb/private/cps.csv.gz in {tmp_path}; "
        f"token=abc123; {synthetic_token}; /usr3/graduate/example/private/python"
    )
    cleaned = WRAPPER.sanitize_text(raw, replacements)
    assert "/projectnb/" not in cleaned
    assert str(tmp_path) not in cleaned
    assert "ghp_" not in cleaned
    assert "/usr3/" not in cleaned
    assert "abc123" not in cleaned
    WRAPPER.assert_public_artifact({"log": cleaned})


def test_support_hash_matches_canonical_reference():
    rows = WRAPPER.csv_rows(REFERENCE / "REBUILT_TREATMENT_MEMBERSHIP.csv")
    observed = WRAPPER.support_hash(row["occupation_code"] for row in rows)
    contract = WRAPPER.load_and_validate_contract(REPO, SPEC)
    assert observed == contract["occupation"]["universe"]["content_support_sha256"]
