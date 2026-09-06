"""Tests that stale and failed upstream runs cannot pass downstream gates."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dependency_guard as guard


H = "a" * 64
SPEC = "yaxspec_v1_" + "b" * 64


class DependencyGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "upstream.json").write_text('{"value":1}\n', encoding="utf-8")
        (self.root / "downstream.json").write_text('{"value":2}\n', encoding="utf-8")
        up_sha = hashlib.sha256((self.root / "upstream.json").read_bytes()).hexdigest()
        down_sha = hashlib.sha256((self.root / "downstream.json").read_bytes()).hexdigest()
        self.up = {
            "run_id": "up", "spec_id": SPEC, "status": "SUCCESS",
            "code_sha256": H, "environment_sha256": H, "command": "run up",
            "dependencies": [],
            "outputs": [{"result_id": "result-up", "path": "upstream.json", "sha256": up_sha}],
        }
        self.up["run_fingerprint"] = guard.compute_run_fingerprint(self.up)
        self.down = {
            "run_id": "down", "spec_id": SPEC, "status": "SUCCESS",
            "code_sha256": H, "environment_sha256": H, "command": "run down",
            "dependencies": [{"run_id": "up", "result_id": "result-up", "artifact_sha256": up_sha}],
            "outputs": [{"result_id": "result-down", "path": "downstream.json", "sha256": down_sha}],
        }
        self.down["run_fingerprint"] = guard.compute_run_fingerprint(self.down)

    def tearDown(self):
        self.tmp.cleanup()

    def document(self):
        return {"schema_version": "yax-run-dag-v1", "runs": [self.up, self.down]}

    def test_valid_dependency_chain(self):
        guard.validate_manifest(self.document(), self.root)

    def test_upstream_hash_change_invalidates_downstream(self):
        document = copy.deepcopy(self.document())
        document["runs"][0]["outputs"][0]["sha256"] = "c" * 64
        with self.assertRaises(guard.DependencyError):
            guard.validate_manifest(document, self.root)

    def test_fingerprint_detects_command_change(self):
        document = copy.deepcopy(self.document())
        document["runs"][1]["command"] = "changed command"
        with self.assertRaises(guard.DependencyError):
            guard.validate_manifest(document, self.root)

    def test_failed_upstream_blocks_only_descendant(self):
        document = copy.deepcopy(self.document())
        log = self.root / "failure.log"
        log.write_text("retained failure\n", encoding="utf-8")
        failed = document["runs"][0]
        failed["status"] = "FAILED"
        failed["failure"] = {
            "message": "synthetic failure", "log_path": "failure.log",
            "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        }
        failed["run_fingerprint"] = guard.compute_run_fingerprint(failed)
        independent_file = self.root / "independent.json"
        independent_file.write_text("{}\n", encoding="utf-8")
        independent = {
            "run_id": "independent", "spec_id": SPEC, "status": "SUCCESS",
            "code_sha256": H, "environment_sha256": H, "command": "run independent",
            "dependencies": [], "outputs": [{"result_id": "result-independent",
              "path": "independent.json",
              "sha256": hashlib.sha256(independent_file.read_bytes()).hexdigest()}],
        }
        independent["run_fingerprint"] = guard.compute_run_fingerprint(independent)
        document["runs"].append(independent)
        with self.assertRaises(guard.DependencyError):
            guard.validate_manifest(document, self.root)
        # Removing only the invalid descendant leaves the failed record and
        # independent successful branch structurally valid.
        document["runs"] = [failed, independent]
        guard.validate_manifest(document, self.root)

    def test_cycle_fails(self):
        document = self.document()
        document["runs"][0]["dependencies"] = [{
            "run_id": "down", "result_id": "result-down",
            "artifact_sha256": document["runs"][1]["outputs"][0]["sha256"],
        }]
        document["runs"][0]["run_fingerprint"] = guard.compute_run_fingerprint(document["runs"][0])
        with self.assertRaises(guard.DependencyError):
            guard.validate_manifest(document, self.root)


if __name__ == "__main__":
    unittest.main()
