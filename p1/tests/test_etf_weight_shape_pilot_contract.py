import copy
import hashlib
import json
import importlib.util
import sys
from pathlib import Path

import pytest

from p1.etf_weight_shape_gates import pilot_contract as pc


CODE_FILES = ("golden_sample_spec.json", "model.py", "subdir/transform.py")
INVARIANT_IDS = tuple(sorted(pc.MINIMUM_REQUIRED_INVARIANT_IDS))


def _write_json(path: Path, value, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(value, indent=4, ensure_ascii=False)
    else:
        text = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def _workspace(tmp_path: Path) -> tuple[dict, dict]:
    tmp_path = tmp_path.resolve()
    code_root = tmp_path / "code"
    (code_root / "subdir").mkdir(parents=True)
    (code_root / "model.py").write_bytes(b"FORMULA = 'registered-v1'\n")
    (code_root / "subdir" / "transform.py").write_bytes(
        b"def transform(value):\n    return value / 100\n"
    )
    golden_spec = {
        "golden_sample_id": "TEST_GOLDEN_V1",
        "categories": {
            category: [f"{category}_CASE"]
            for category in pc.REQUIRED_GOLDEN_CATEGORIES
        },
    }
    _write_json(code_root / "golden_sample_spec.json", golden_spec)

    config_path = tmp_path / "state" / "gate01_config.json"
    contract_path = tmp_path / "state" / "data_contract.json"
    config = {
        "full_run_enabled": False,
        "candidate_implementation": {
            "status": "LEGACY_DISABLED_PENDING_CONTRACT_REWRITE",
            "contract_conformant": False,
            "activation_permitted": False,
            "contract_controls": {
                name: False for name in pc.CANDIDATE_CONTRACT_CONTROLS
            },
        },
        "formula_version": "registered-v1",
        "staleness_days": 120,
        "counterfactuals": [1, 5, 10, 25, 50, 100],
        "golden_sample_file": "golden_sample_spec.json",
        "required_pilot_artifacts": list(pc.REQUIRED_PILOT_ARTIFACTS),
        "scientific_fileset": list(CODE_FILES),
        "required_invariant_ids": list(INVARIANT_IDS),
    }
    contract = {
        "contract_version": 1,
        "indices": {
            "pooled_portfolio": "crsp_portno",
            "share_class": "crsp_fundno",
            "etf_security": "etf_permno",
            "underlying_security": "holding_permno",
            "economic_date": "report_dt",
            "availability_timestamp": "availability_ts",
        },
    }
    _write_json(config_path, config)
    _write_json(contract_path, contract)

    archive_root = tmp_path / "canonical_archive"
    manifest_path = archive_root / "_migration_meta" / "FINAL_SCC_MANIFEST.tsv"
    manifest_path.parent.mkdir(parents=True)
    manifest_bytes = b"123\tp1_refraction_wrds_shared/raw/example.parquet\n"
    manifest_path.write_bytes(manifest_bytes)

    code_hash, canonical_files = pc.compute_code_fileset_hash(
        code_root,
        CODE_FILES,
        archive_root=archive_root,
    )
    config_hash, _, _ = pc.compute_json_file_hash(
        config_path,
        label="config",
        archive_root=archive_root,
    )
    contract_hash, _, _ = pc.compute_json_file_hash(
        contract_path,
        label="contract",
        archive_root=archive_root,
    )
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    invariants = [
        {
            "id": invariant_id,
            "passed": True,
            "result": {"status": "PASS", "observations": 1},
        }
        for invariant_id in INVARIANT_IDS
    ]
    artifact_root = tmp_path / "state"
    trace_bytes = (
        "final_observation_key,reconciled\n"
        + "".join(f"observation-{index},True\n" for index in range(20))
    ).encode("utf-8")
    artifact_payloads = {
        "etf_flag_history_audits.json": b"[]\n",
        "golden_case_results.json": b"[]\n",
        "pilot_exposure_observations.csv": trace_bytes,
        "pilot_input_files.json": b"{}\n",
        "pilot_invariants.json": (
            json.dumps(invariants, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8"),
        "pilot_raw_trace_inspection.csv": trace_bytes,
    }
    for name, payload in artifact_payloads.items():
        (artifact_root / name).write_bytes(payload)
    artifact_registry = {
        name: {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        for name, payload in sorted(artifact_payloads.items())
    }
    pilot = {
        "schema_version": pc.PILOT_SCHEMA_VERSION,
        "status": "PASS",
        "hashes": {
            "code": {
                "algorithm": pc.CODE_HASH_ALGORITHM,
                "digest": code_hash,
                "files": list(canonical_files),
            },
            "config": {
                "algorithm": pc.JSON_HASH_ALGORITHM,
                "digest": config_hash,
            },
            "data_contract": {
                "algorithm": pc.JSON_HASH_ALGORITHM,
                "digest": contract_hash,
            },
            "manifest": {
                "algorithm": pc.RAW_HASH_ALGORITHM,
                "digest": manifest_hash,
            },
        },
        "required_invariant_ids": list(INVARIANT_IDS),
        "invariants": invariants,
        "golden_sample": {
            "categories": {
                category: 1 for category in pc.REQUIRED_GOLDEN_CATEGORIES
            },
            "content_sha256": pc.canonical_json_hash(golden_spec),
        },
        "raw_trace_inspection": {
            "observation_count": 20,
            "all_reconciled": True,
            "artifact_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        },
        "artifacts": artifact_registry,
    }
    pilot_path = tmp_path / "state" / "PILOT_PASS.json"
    _write_json(pilot_path, pilot)
    arguments = {
        "pilot_pass_path": pilot_path,
        "code_root": code_root,
        "code_files": CODE_FILES,
        "config_path": config_path,
        "data_contract_path": contract_path,
        "required_invariant_ids": INVARIANT_IDS,
        "archive_root": archive_root,
        "manifest_path": manifest_path,
    }
    return arguments, pilot


def _replace_artifact(arguments, pilot, name: str, payload: bytes) -> None:
    path = arguments["pilot_pass_path"].parent / name
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    pilot["artifacts"][name] = {"sha256": digest, "bytes": len(payload)}
    if name == "pilot_raw_trace_inspection.csv":
        pilot["raw_trace_inspection"]["artifact_sha256"] = digest


def _load_full_runner(monkeypatch):
    code_dir = (
        Path(__file__).resolve().parents[1] / "etf_weight_shape_gates"
    )
    monkeypatch.syspath_prepend(str(code_dir))
    name = "p1_gate01_runner_test"
    spec = importlib.util.spec_from_file_location(
        name,
        code_dir / "run_gate0_gate1.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_pilot_runner(monkeypatch):
    code_dir = (
        Path(__file__).resolve().parents[1] / "etf_weight_shape_gates"
    )
    monkeypatch.syspath_prepend(str(code_dir))
    name = "p1_data_contract_pilot_test"
    spec = importlib.util.spec_from_file_location(
        name,
        code_dir / "run_data_contract_pilot.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _assert_manifest_never_read(monkeypatch, arguments, expected_reason: str):
    calls = []
    original = pc.compute_raw_file_hash
    manifest = Path(arguments["manifest_path"]).absolute()

    def guarded(path, *, label="file"):
        if Path(path).absolute() == manifest:
            calls.append(Path(path))
            raise AssertionError("manifest hash attempted before local authorization")
        return original(path, label=label)

    monkeypatch.setattr(pc, "compute_raw_file_hash", guarded)
    with pytest.raises(pc.PilotContractError) as excinfo:
        pc.authorize_full_run(**arguments)
    assert excinfo.value.reason == expected_reason
    assert excinfo.value.exit_code == 78
    assert calls == []


def test_full_authorization_verifies_local_inputs_before_exact_manifest(tmp_path):
    arguments, _ = _workspace(tmp_path)
    authorization = pc.authorize_full_run(**arguments)
    assert authorization.manifest_path == arguments["manifest_path"]
    assert authorization.manifest_hash == hashlib.sha256(
        arguments["manifest_path"].read_bytes()
    ).hexdigest()
    assert authorization.local.code_files == tuple(sorted(CODE_FILES))


def test_missing_pilot_exits_before_manifest_read(tmp_path, monkeypatch):
    arguments, _ = _workspace(tmp_path)
    arguments["pilot_pass_path"].unlink()
    _assert_manifest_never_read(monkeypatch, arguments, "MISSING_FILE")


def test_code_mismatch_exits_before_manifest_read(tmp_path, monkeypatch):
    arguments, _ = _workspace(tmp_path)
    (arguments["code_root"] / "model.py").write_text(
        "FORMULA = 'amended-v2'\n",
        encoding="utf-8",
    )
    _assert_manifest_never_read(monkeypatch, arguments, "CODE_HASH_MISMATCH")


@pytest.mark.parametrize(
    ("target", "replacement", "reason"),
    [
        (
            "config",
            {
                "formula_version": "registered-v2",
                "staleness_days": 120,
                "counterfactuals": [1, 5, 10, 25, 50, 100],
            },
            "CONFIG_HASH_MISMATCH",
        ),
        (
            "contract",
            {
                "contract_version": 2,
                "indices": {
                    "pooled_portfolio": "crsp_portno",
                    "share_class": "crsp_fundno",
                    "etf_security": "etf_permno",
                    "underlying_security": "holding_permno",
                    "economic_date": "report_dt",
                    "availability_timestamp": "publication_ts",
                },
            },
            "DATA_CONTRACT_HASH_MISMATCH",
        ),
    ],
)
def test_specification_amendment_invalidates_before_manifest(
    tmp_path,
    monkeypatch,
    target,
    replacement,
    reason,
):
    arguments, _ = _workspace(tmp_path)
    selected = (
        arguments["config_path"]
        if target == "config"
        else arguments["data_contract_path"]
    )
    _write_json(selected, replacement)
    _assert_manifest_never_read(monkeypatch, arguments, reason)


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda p: p.update(status="FAIL"), "PILOT_NOT_PASS"),
        (
            lambda p: p.update(unregistered_field=True),
            "SCHEMA_ERROR",
        ),
        (
            lambda p: p["invariants"][0].update(passed=False),
            "INVARIANT_FAILED",
        ),
        (
            lambda p: p["invariants"].pop(),
            "INVARIANT_RESULT_SET_MISMATCH",
        ),
        (
            lambda p: p["golden_sample"]["categories"].update(PURE_ETF=0),
            "GOLDEN_CATEGORY_EMPTY",
        ),
        (
            lambda p: p["raw_trace_inspection"].update(observation_count=19),
            "INSUFFICIENT_RAW_TRACE",
        ),
        (
            lambda p: p["raw_trace_inspection"].update(all_reconciled=False),
            "RAW_TRACE_FAILED",
        ),
    ],
)
def test_strict_pilot_failures_never_read_manifest(
    tmp_path,
    monkeypatch,
    mutator,
    reason,
):
    arguments, pilot = _workspace(tmp_path)
    changed = copy.deepcopy(pilot)
    mutator(changed)
    _write_json(arguments["pilot_pass_path"], changed)
    _assert_manifest_never_read(monkeypatch, arguments, reason)


def test_manifest_mismatch_is_checked_only_after_local_authorization(
    tmp_path,
    monkeypatch,
):
    arguments, _ = _workspace(tmp_path)
    arguments["manifest_path"].write_bytes(b"changed manifest\n")
    original = pc.compute_raw_file_hash
    calls = []

    def recording(path, *, label="file"):
        calls.append(Path(path))
        return original(path, label=label)

    monkeypatch.setattr(pc, "compute_raw_file_hash", recording)
    with pytest.raises(pc.PilotContractError) as excinfo:
        pc.authorize_full_run(**arguments)
    assert excinfo.value.reason == "MANIFEST_HASH_MISMATCH"
    expected_artifact_calls = [
        arguments["pilot_pass_path"].parent / name
        for name in sorted(pc.REQUIRED_PILOT_ARTIFACTS)
    ]
    assert calls == expected_artifact_calls + [arguments["manifest_path"]]


def test_trace_artifact_mismatch_exits_before_manifest_read(tmp_path, monkeypatch):
    arguments, _ = _workspace(tmp_path)
    trace = arguments["pilot_pass_path"].parent / "pilot_raw_trace_inspection.csv"
    trace.write_bytes(b"tampered trace")
    _assert_manifest_never_read(monkeypatch, arguments, "ARTIFACT_SIZE_MISMATCH")


def test_exact_artifact_registry_is_required_before_manifest(tmp_path, monkeypatch):
    arguments, pilot = _workspace(tmp_path)
    del pilot["artifacts"]["golden_case_results.json"]
    _write_json(arguments["pilot_pass_path"], pilot)
    _assert_manifest_never_read(
        monkeypatch,
        arguments,
        "ARTIFACT_REGISTRY_MISMATCH",
    )


def test_invariant_receipt_must_equal_hashed_invariant_artifact(
    tmp_path,
    monkeypatch,
):
    arguments, pilot = _workspace(tmp_path)
    pilot["invariants"][0]["result"]["observations"] = 999
    _write_json(arguments["pilot_pass_path"], pilot)
    _assert_manifest_never_read(
        monkeypatch,
        arguments,
        "INVARIANT_ARTIFACT_MISMATCH",
    )


def test_golden_digest_and_category_counts_are_recomputed(
    tmp_path,
    monkeypatch,
):
    arguments, pilot = _workspace(tmp_path)
    pilot["golden_sample"]["content_sha256"] = "0" * 64
    _write_json(arguments["pilot_pass_path"], pilot)
    _assert_manifest_never_read(
        monkeypatch,
        arguments,
        "GOLDEN_SAMPLE_HASH_MISMATCH",
    )

    arguments, pilot = _workspace(tmp_path / "count_case")
    pilot["golden_sample"]["categories"]["PURE_ETF"] = 2
    _write_json(arguments["pilot_pass_path"], pilot)
    _assert_manifest_never_read(
        monkeypatch,
        arguments,
        "GOLDEN_CATEGORY_COUNT_MISMATCH",
    )


def test_trace_csv_unique_count_and_reconciliation_are_recomputed(
    tmp_path,
    monkeypatch,
):
    arguments, pilot = _workspace(tmp_path)
    duplicate_trace = (
        "final_observation_key,reconciled\n"
        + "".join(f"observation-{index},True\n" for index in range(19))
        + "observation-0,True\n"
    ).encode()
    _replace_artifact(
        arguments,
        pilot,
        "pilot_raw_trace_inspection.csv",
        duplicate_trace,
    )
    _write_json(arguments["pilot_pass_path"], pilot)
    _assert_manifest_never_read(
        monkeypatch,
        arguments,
        "TRACE_DUPLICATE_OBSERVATION",
    )

    arguments, pilot = _workspace(tmp_path / "false_case")
    unreconciled_trace = (
        "final_observation_key,reconciled\n"
        + "".join(
            f"observation-{index},{'False' if index == 19 else 'True'}\n"
            for index in range(20)
        )
    ).encode()
    _replace_artifact(
        arguments,
        pilot,
        "pilot_raw_trace_inspection.csv",
        unreconciled_trace,
    )
    _write_json(arguments["pilot_pass_path"], pilot)
    _assert_manifest_never_read(monkeypatch, arguments, "RAW_TRACE_FAILED")


def test_manifest_cannot_be_read_without_genuine_local_authorization(tmp_path):
    arguments, _ = _workspace(tmp_path)
    fake = pc.LocalPilotAuthorization(
        pilot_pass_path=arguments["pilot_pass_path"],
        code_hash="0" * 64,
        config_hash="0" * 64,
        data_contract_hash="0" * 64,
        expected_manifest_hash="0" * 64,
        code_files=tuple(sorted(CODE_FILES)),
        invariant_ids=INVARIANT_IDS,
        _seal=object(),
    )
    with pytest.raises(pc.PilotContractError) as excinfo:
        pc.authorize_manifest(fake, arguments["manifest_path"])
    assert excinfo.value.reason == "LOCAL_AUTHORIZATION_REQUIRED"


def test_code_fileset_hash_is_order_independent_and_commits_path_and_length(
    tmp_path,
):
    arguments, _ = _workspace(tmp_path)
    digest, paths = pc.compute_code_fileset_hash(
        arguments["code_root"],
        reversed(CODE_FILES),
        archive_root=arguments["archive_root"],
    )
    expected = hashlib.sha256(b"P1_CODE_FILESET_SHA256_V1\0")
    for relative in sorted(CODE_FILES):
        data = (arguments["code_root"] / relative).read_bytes()
        encoded = relative.encode("utf-8")
        expected.update(len(encoded).to_bytes(8, "big"))
        expected.update(encoded)
        expected.update(len(data).to_bytes(8, "big"))
        expected.update(data)
    assert paths == tuple(sorted(CODE_FILES))
    assert digest == expected.hexdigest()


@pytest.mark.parametrize("bad_path", ["../model.py", "/abs/model.py", "subdir/../model.py"])
def test_code_fileset_rejects_traversal_and_absolute_paths(tmp_path, bad_path):
    arguments, _ = _workspace(tmp_path)
    with pytest.raises(pc.PilotContractError) as excinfo:
        pc.compute_code_fileset_hash(
            arguments["code_root"],
            [bad_path],
            archive_root=arguments["archive_root"],
        )
    assert excinfo.value.reason == "INVALID_RELATIVE_PATH"


def test_code_fileset_rejects_missing_and_symlink_files(tmp_path):
    arguments, _ = _workspace(tmp_path)
    with pytest.raises(pc.PilotContractError) as missing:
        pc.compute_code_fileset_hash(
            arguments["code_root"],
            ["missing.py"],
            archive_root=arguments["archive_root"],
        )
    assert missing.value.reason == "MISSING_FILE"

    link = arguments["code_root"] / "linked.py"
    link.symlink_to(arguments["code_root"] / "model.py")
    with pytest.raises(pc.PilotContractError) as linked:
        pc.compute_code_fileset_hash(
            arguments["code_root"],
            ["linked.py"],
            archive_root=arguments["archive_root"],
        )
    assert linked.value.reason == "SYMLINK_REJECTED"


def test_any_symlink_in_path_ancestry_is_rejected(tmp_path):
    root = tmp_path.resolve()
    real_parent = root / "real_parent"
    real_parent.mkdir()
    _write_json(real_parent / "config.json", {"value": 1})
    linked_parent = root / "linked_parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(pc.PilotContractError) as excinfo:
        pc.compute_json_file_hash(
            linked_parent / "config.json",
            label="linked config",
            archive_root=root / "archive",
        )
    assert excinfo.value.reason == "SYMLINK_REJECTED"


def test_canonical_json_hash_ignores_formatting_but_not_semantics(tmp_path):
    one = tmp_path / "one.json"
    two = tmp_path / "two.json"
    three = tmp_path / "three.json"
    value = {"z": [3, 2, 1], "a": {"formula": "v1"}}
    _write_json(one, value)
    _write_json(two, value, pretty=True)
    _write_json(three, {"z": [3, 2, 1], "a": {"formula": "v2"}})
    first, _, _ = pc.compute_json_file_hash(one, label="one")
    second, _, _ = pc.compute_json_file_hash(two, label="two")
    third, _, _ = pc.compute_json_file_hash(three, label="three")
    assert first == second
    assert first != third


def test_local_inputs_inside_archive_are_refused_without_reading_them(tmp_path):
    arguments, _ = _workspace(tmp_path)
    archive_config = arguments["archive_root"] / "config.json"
    # The file intentionally does not need to exist: lexical refusal precedes
    # lstat/open, so the preflight cannot accidentally use an archive config.
    arguments["config_path"] = archive_config
    with pytest.raises(pc.PilotContractError) as excinfo:
        pc.authorize_local_pilot(
            **{k: v for k, v in arguments.items() if k != "manifest_path"}
        )
    assert excinfo.value.reason == "LOCAL_INPUT_IN_ARCHIVE"


def test_candidate_state_has_no_false_to_true_pilot_deadlock():
    disabled = {
        "full_run_enabled": False,
        "candidate_implementation": {
            "status": "LEGACY_DISABLED_PENDING_CONTRACT_REWRITE",
            "contract_conformant": False,
            "activation_permitted": False,
            "contract_controls": {
                name: False for name in pc.CANDIDATE_CONTRACT_CONTROLS
            },
        },
    }
    passed, result = pc.candidate_implementation_conformance(disabled)
    assert passed is True
    assert result["activation_permitted"] is False

    enabled = copy.deepcopy(disabled)
    enabled["full_run_enabled"] = True
    candidate = enabled["candidate_implementation"]
    candidate["status"] = "CONTRACT_CONFORMANT_CANDIDATE"
    candidate["contract_conformant"] = True
    candidate["activation_permitted"] = True
    candidate["contract_controls"] = {
        name: True for name in pc.CANDIDATE_CONTRACT_CONTROLS
    }
    passed, result = pc.candidate_implementation_conformance(enabled)
    assert passed is True
    assert result["activation_state_consistent"] is True


def test_public_receipt_omits_proprietary_invariant_results(
    tmp_path,
    monkeypatch,
):
    _, pilot = _workspace(tmp_path)
    pilot["created_at_utc"] = "2026-09-05T00:00:00+00:00"
    pilot["pilot_run_id"] = "TEST_GOLDEN_V1"
    pilot_runner = _load_pilot_runner(monkeypatch)
    receipt = pilot_runner.make_public_receipt(pilot)
    assert receipt["hashes"] == pilot["hashes"]
    assert receipt["artifacts"] == pilot["artifacts"]
    assert receipt["golden_sample"]["case_count"] == 7
    assert receipt["raw_trace_inspection"]["observation_count"] == 20
    assert all(set(item) == {"id", "passed"} for item in receipt["invariants"])
    assert '"result"' not in json.dumps(receipt)


@pytest.mark.parametrize(
    ("argument", "reason"),
    [
        ("--code-root", "CODE_ROOT_PATH_MISMATCH"),
        ("--manifest", "MANIFEST_PATH_MISMATCH"),
    ],
)
def test_actual_runner_rejects_alternate_bound_paths_before_any_access(
    tmp_path,
    monkeypatch,
    argument,
    reason,
):
    runner = _load_full_runner(monkeypatch)
    touched = []

    monkeypatch.setattr(
        runner,
        "authorize_manifest",
        lambda *args, **kwargs: touched.append("manifest"),
    )
    monkeypatch.setattr(
        runner,
        "load_names",
        lambda: touched.append("raw"),
    )
    output = tmp_path / "must_not_exist"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_gate0_gate1.py",
            "--output",
            str(output),
            "--pilot-pass",
            str(tmp_path / "missing-pilot.json"),
            argument,
            str(tmp_path / "alternate"),
        ],
    )
    with pytest.raises(SystemExit) as excinfo:
        runner.main()
    assert excinfo.value.code == 78
    assert reason in str(excinfo.value.__context__)
    assert touched == []
    assert not output.exists()


def test_actual_runner_missing_pilot_exits_before_manifest_raw_or_output(
    tmp_path,
    monkeypatch,
):
    runner = _load_full_runner(monkeypatch)
    touched = []
    monkeypatch.setattr(
        runner,
        "authorize_manifest",
        lambda *args, **kwargs: touched.append("manifest"),
    )
    monkeypatch.setattr(
        runner,
        "load_names",
        lambda: touched.append("raw"),
    )
    output = tmp_path / "must_not_exist"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_gate0_gate1.py",
            "--output",
            str(output),
            "--pilot-pass",
            str(tmp_path / "missing-pilot.json"),
        ],
    )
    with pytest.raises(SystemExit) as excinfo:
        runner.main()
    assert excinfo.value.code == 78
    assert touched == []
    assert not output.exists()


def test_v3_woo_pro_rata_evidence_is_limited_to_exact_supported_date(
    monkeypatch,
):
    pilot_runner = _load_pilot_runner(monkeypatch)
    code_dir = Path(__file__).resolve().parents[1] / "etf_weight_shape_gates"
    spec = json.loads((code_dir / "golden_sample_spec.json").read_text())
    evidence_id = "SEC_VANGUARD_500_MULTIPLE_CLASS_PLAN"
    evidence = spec["external_evidence"][evidence_id]
    cases = {case["case_id"]: case for case in spec["cases"]}

    assert evidence["covered_pilot_dates"] == ["2024-12-31"]
    assert (
        cases["VOO_NVIDIA_SPLIT_2024_06_30"]["external_pro_rata_evidence"]
        is None
    )
    assert pilot_runner.date_scoped_pro_rata_evidence(
        spec,
        evidence_id,
        pilot_runner.pd.Timestamp("2024-12-31"),
        4,
    ) == (True, "POOLED_MULTICLASS_PRO_RATA")
    assert pilot_runner.date_scoped_pro_rata_evidence(
        spec,
        evidence_id,
        pilot_runner.pd.Timestamp("2024-06-30"),
        4,
    ) == (False, None)
