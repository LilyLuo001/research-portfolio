"""Dry synthetic control tests: no source, Azure, model, or real ledger access."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

import finite_pipeline as f


class FiniteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root = Path(self.tmp.name)
        (self.root / "control").mkdir()
        (self.root / "preparation").mkdir()
        (self.root / "preparation/cloud_controller.py").write_text('# synthetic, never executed\n')
        (self.root / "policy.json").write_text('{}')
        (self.root / "preparation/batch0001_CONFIG_PRIVATE.json").write_text('{"preserved_initial_config":true}')
        self.origin = {"shard_ordinal": 7, "shard_rows": 20000}
        self.append("batch0001", 100)
        self.append("batch0002", 900)
        with sqlite3.connect(self.root / "ADMISSION_PRIVATE.sqlite3") as conn:
            conn.executescript("CREATE TABLE meta(key TEXT,value TEXT); CREATE TABLE claims(context TEXT); CREATE TABLE quarantine(context TEXT); CREATE TABLE attempts(state TEXT,dollars_nano INTEGER);")
            conn.execute("INSERT INTO meta VALUES('identity',?)", (json.dumps({"policy_sha256": f.sha(self.root / "policy.json")}),))

    def tearDown(self):
        self.tmp.cleanup()

    def append(self, name, count):
        previous = f.manifest_chain(self.root)
        prior = previous[-1] if previous else None
        folder = self.root / "preparation" / name
        folder.mkdir()
        text = "synthetic document " + name
        context = hashlib.sha256(text.encode()).hexdigest()
        row = {"case": name, "row": {"context_sha256": context, "full_document": text}}
        (folder / "INPUTS_PRIVATE.jsonl").write_bytes(f.encoded(row))
        start = prior["end_cursor_exclusive"]["row_offset"] if prior else 150
        manifest = {"batch_id": name, "physical_rows": count, "new_unique_contexts": 1,
            "cumulative_physical_rows": (prior["cumulative_physical_rows"] if prior else 0) + count,
            "cumulative_new_unique_contexts": len(previous) + 1, "origin": self.origin, "origin_sha256": "a" * 64,
            "start_cursor": {"shard_ordinal": 7, "row_offset": start},
            "end_cursor_exclusive": {"shard_ordinal": 7, "row_offset": start + count},
            "inputs_sha256": f.sha(folder / "INPUTS_PRIVATE.jsonl"),
            "previous_batch_manifest_sha256": prior["manifest_sha256"] if prior else None}
        (folder / "BATCH_MANIFEST_PUBLIC.json").write_bytes(f.encoded(manifest))
        return manifest

    def supervisor_stub(self):
        obj = f.Supervisor.__new__(f.Supervisor)
        obj.root, obj.control = self.root, self.root / "control"
        obj.policy_sha = f.sha(self.root / "policy.json")
        obj.deadline = time.time() + 60
        obj.stopfile = self.root / "STOP"
        obj.state = {"completed_batches": [], "events": 0, "policy_sha256": obj.policy_sha}
        obj.statepath = obj.control / "FINITE_PIPELINE_STATE_PUBLIC.json"
        return obj

    def test_actual_window_and_initial_config_preserved(self):
        manifests = f.manifest_chain(self.root)
        self.assertEqual(f.next_window(manifests[-1]), ("batch0003", 1000))
        snapshot = {"claims": ["b" * 64], "quarantined": ["c" * 64]}
        batch, count, path = f.prepare_config(self.root, manifests, snapshot)
        config = f.read(path)
        self.assertTrue(config["preserved_initial_config"])
        self.assertEqual(config["previous_manifest"]["sha256"], manifests[-1]["manifest_sha256"])
        exclusions = f.read(config["pilot_runtime_exclusions"]["path"])
        self.assertEqual(len(exclusions["context_sha256"]), 3)
        self.assertEqual(exclusions["quarantined_contexts"], ["c" * 64])

    def test_cap_and_shard_boundary(self):
        value = f.manifest_chain(self.root)[-1]
        value["cumulative_physical_rows"] = 9500
        self.assertEqual(f.next_window(value)[1], 500)
        value["cumulative_physical_rows"] = 10000
        with self.assertRaisesRegex(f.StopPipeline, "physical_pilot_limit_reached"):
            f.next_window(value)
        value["cumulative_physical_rows"] = 1000
        value["origin"]["shard_rows"] = value["end_cursor_exclusive"]["row_offset"]
        with self.assertRaisesRegex(f.StopPipeline, "actual_source_shard_boundary_reached"):
            f.next_window(value)

    def test_no_guessed_shard_transition(self):
        value = f.manifest_chain(self.root)[-1]
        value["end_cursor_exclusive"]["shard_ordinal"] += 1
        with self.assertRaisesRegex(f.StopPipeline, "shard_binding_change_not_authorized"):
            f.next_window(value)

    def test_partial_preparation_checkpoint_keeps_last_commit(self):
        (self.root / "preparation/batch0003").mkdir()
        obj = self.supervisor_stub()
        obj.checkpoint("preparation_failed")
        self.assertEqual(obj.state["last_committed_batch"], "batch0002")
        self.assertEqual(obj.state["end_cursor_exclusive"]["row_offset"], 1150)
        with self.assertRaisesRegex(f.StopPipeline, "partial_preparation"):
            f.manifest_chain(self.root)

    def test_manifest_inputs_sha_failure(self):
        path = self.root / "preparation/batch0002/INPUTS_PRIVATE.jsonl"
        path.write_text("changed")
        with self.assertRaisesRegex(f.StopPipeline, "prepared_input_sha_mismatch"):
            f.manifest_chain(self.root)

    def test_global_hold_preserved(self):
        with sqlite3.connect(self.root / "ADMISSION_PRIVATE.sqlite3") as conn:
            conn.execute("INSERT INTO meta VALUES('global_hold','existing_hold')")
        obj = self.supervisor_stub()
        with self.assertRaisesRegex(f.StopPipeline, "global_admission_hold_preserved"):
            obj.guards()
        self.assertEqual(f.ledger_snapshot(self.root)["meta"]["global_hold"], "existing_hold")

    def test_unknown_transport_halts(self):
        with sqlite3.connect(self.root / "ADMISSION_PRIVATE.sqlite3") as conn:
            conn.execute("INSERT INTO attempts VALUES('transport_uncertain_no_retry',10)")
        with self.assertRaisesRegex(f.StopPipeline, "uncertain_transport_no_retry"):
            self.supervisor_stub().guards()

    def test_budget_halts_without_reset(self):
        with sqlite3.connect(self.root / "ADMISSION_PRIVATE.sqlite3") as conn:
            conn.execute("INSERT INTO attempts VALUES('saved',?)", (f.PILOT_CAP_NANO,))
        with self.assertRaisesRegex(f.StopPipeline, "persistent_150usd_pilot_cap_reached"):
            self.supervisor_stub().guards()
        self.assertEqual(f.ledger_snapshot(self.root)["reserved_nano"], f.PILOT_CAP_NANO)

    def test_existing_active_worker_prevents_launch(self):
        with patch.object(f, "active_workers", return_value=[123]):
            with self.assertRaisesRegex(f.StopPipeline, "another_model_leg"):
                self.supervisor_stub().guards()

    def test_stopfile_and_wall_limit(self):
        obj = self.supervisor_stub()
        obj.deadline = time.time() - 1
        with self.assertRaisesRegex(f.StopPipeline, "finite_48h_wall_limit"):
            obj.guards()
        self.assertTrue(obj.stopfile.exists())
        obj.deadline = time.time() + 60
        with self.assertRaisesRegex(f.StopPipeline, "operator_stop_file"):
            obj.guards()

    def test_duplicate_controller_flock(self):
        with f.controller_lock(self.root):
            with self.assertRaisesRegex(f.StopPipeline, "finite_controller_already_active"):
                with f.controller_lock(self.root):
                    pass

    def test_dry_full_finite_10000_loop(self):
        obj = self.supervisor_stub()
        stages, processed = [], []
        obj.ensure_amendment = lambda: None
        def process(manifest):
            processed.append(manifest["batch_id"])
            obj.state["completed_batches"].append(manifest["batch_id"])
        obj.process_batch = process
        def execute(command, stage, **kwargs):
            self.assertIn("prepare_physical.py", command[2])
            batch = command[command.index("--batch-id") + 1]
            count = int(command[command.index("--row-limit") + 1])
            stages.append((batch, count))
            self.append(batch, count)
        obj.execute = execute
        with self.assertRaisesRegex(f.StopPipeline, "physical_pilot_limit_reached"):
            obj.run()
        self.assertEqual(len(processed), 11)
        self.assertEqual(stages, [("batch%04d" % number, 1000) for number in range(3, 12)])
        self.assertEqual(f.manifest_chain(self.root)[-1]["cumulative_physical_rows"], 10000)


if __name__ == "__main__":
    unittest.main()
