"""Release, raw-data, and outcome-seal checks for Mapping A artifacts."""

import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
MAPPING = ROOT / "mapping"
sys.path.insert(0, str(MAPPING))

from mapA_adjudication import assert_release_safe  # noqa: E402


EXPECTED_HASHES = {
    "mapping_a_gdpval.csv": "d1ebd110134a69807a94211691a1e1ef49ea8b478173dfc76e6be37b87468868",
    "mapA_adjudication_queue.csv": "edfc03e56ecab88a8c756a6fc069b18e23d50678ff32dc98325ca1c49e22a625",
    "mapA_occupation_coverage.csv": "294ba2754a12161a9a74122dc27ae7492514144fee8ded1ea2ff3fd71841ecdd",
}


def load(name):
    return json.loads((MAPPING / name).read_text(encoding="utf-8"))


def test_sanitized_receipt_is_release_safe_and_sealed():
    receipt = load("mapA_run_receipt.json")
    assert_release_safe([receipt])
    encoded = json.dumps(receipt, sort_keys=True)
    assert "/usr3/" not in encoded
    assert "dax-private" not in encoded
    assert receipt["release"]["task_text_committed"] is False
    assert receipt["release"]["id_level_artifacts_committed"] is False
    assert receipt["release"]["outcomes_opened"] is False
    assert receipt["adjudication_queue"]["machine_judgments_certified_as_audited"] is False


def test_sanitized_manifest_pins_private_hashes_without_ids():
    manifest = load("mapA_private_artifacts_manifest.json")
    assert_release_safe([manifest])
    assert manifest["contains_task_text"] is False
    assert manifest["contains_task_ids"] is False
    assert manifest["id_level_artifacts_committed"] is False
    assert manifest["outcomes_opened"] is False
    assert manifest["determinism"] == {
        "independent_execution_count": 2,
        "byte_identical": True,
    }
    assert {name: value["sha256"] for name, value in manifest["artifacts"].items()} == EXPECTED_HASHES


def test_receipt_and_manifest_agree_on_exact_private_outputs():
    receipt = load("mapA_run_receipt.json")
    manifest = load("mapA_private_artifacts_manifest.json")
    assert {name: value["sha256"] for name, value in receipt["private_outputs"].items()} == EXPECTED_HASHES
    assert receipt["determinism_verification"]["byte_identical_private_outputs"] is True
    assert receipt["determinism_verification"]["independent_execution_count"] == 2
    assert receipt["results"]["n_onet_tasks"] == 19259
    assert receipt["results"]["accepted"] + receipt["results"]["queued"] + receipt["results"]["unmatched"] == 19259


def test_no_private_id_level_or_text_bearing_mapping_artifact_is_tracked():
    repo = ROOT.parent
    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "dax/mapping"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    forbidden = {
        "dax/mapping/mapping_a_gdpval.csv",
        "dax/mapping/mapA_adjudication_queue.csv",
        "dax/mapping/mapA_occupation_coverage.csv",
    }
    assert forbidden.isdisjoint(tracked)
    assert not any("task_text" in path or "task_statement" in path for path in tracked)
