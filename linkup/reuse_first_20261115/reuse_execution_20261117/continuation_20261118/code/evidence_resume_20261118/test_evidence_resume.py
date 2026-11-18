"""Synthetic SQLite fixtures only; no cloud, models or advertisement data."""
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest import mock

import cloud_evidence_resume as module

HERE = Path(__file__).resolve().parent
LEGACY_DIR = HERE.parent / "evidence_readiness_20261117"
LEGACY_PATH = LEGACY_DIR / "cloud_evidence_readiness.py"
sys.path.insert(0, str(LEGACY_DIR))
import cloud_evidence_readiness as original
from test_evidence_readiness import fixture


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    with sqlite3.connect(path) as db:
        result = db.execute("SELECT * FROM evidence_readiness ORDER BY source_rowid").fetchall()
    db.close()
    return result


def metadata(path):
    with sqlite3.connect(path) as db:
        result = {k: json.loads(v) for k, v in db.execute("SELECT key,value_json FROM run_metadata")}
    db.close()
    return result


def checkpoint(root, count=6, inherited=2, cap=module.MAX_ATOMS, **fixture_options):
    source, runtime = fixture(root, count, **fixture_options)
    prior, out = root / "run001", root / "run002"
    calls = 0
    inspect = original.inspect_declarations
    def stop_after_inherited(*args):
        nonlocal calls
        calls += 1
        if calls > inherited:
            raise original.TimeBudgetExceeded()
        return inspect(*args)
    with mock.patch.object(original, "BATCH", 1), mock.patch.object(original, "inspect_declarations", stop_after_inherited):
        report = original.run(root, prior, max_atoms=cap)
    expected = module.Checkpoint(
        sha(prior / module.DB_NAME), sha(prior / module.REPORT_NAME),
        (prior / module.DB_NAME).stat().st_size, report["total_evidence_atoms"],
        report["processed_evidence_atoms"], report["remaining_allowed_evidence_atoms"],
        report["elapsed_seconds_cumulative"], report["status"])
    return source, runtime, prior, out, expected


class ResumeTests(unittest.TestCase):
    def test_prior_code_directory_is_preserved_without_bytecode_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, prior, out, expected = checkpoint(root)
            code_dir = prior / "code"
            code_dir.mkdir()
            staged = code_dir / "cloud_evidence_readiness.py"
            staged.write_bytes(LEGACY_PATH.read_bytes())
            nested = code_dir / "support"
            nested.mkdir()
            (nested / "receipt.txt").write_bytes(b"preserve this nested member")
            before = {str(p.relative_to(prior)): p.read_bytes() for p in prior.rglob("*") if p.is_file()}
            before_dirs = sorted(str(p.relative_to(prior)) for p in prior.rglob("*") if p.is_dir())
            # The loader must avoid .pyc writes even if the process permits them.
            with mock.patch.object(sys, "dont_write_bytecode", False):
                report = module.run(root, prior, out, staged, expected=expected)
            after = {str(p.relative_to(prior)): p.read_bytes() for p in prior.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(before_dirs, sorted(str(p.relative_to(prior)) for p in prior.rglob("*") if p.is_dir()))
            self.assertTrue(report["prior_directory_stat_unchanged"])
            self.assertEqual(report["remaining_allowed_evidence_atoms"], 0)

    def test_recursive_inventory_rejects_symlinks_specials_and_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = module.load_legacy(LEGACY_PATH)
            nested = root / "code"
            nested.mkdir()
            link = nested / "alias"
            link.symlink_to(LEGACY_PATH)
            with self.assertRaisesRegex(ValueError, "unsupported_member"):
                module.inventory(root, legacy)
            link.unlink()
            fifo = nested / "pipe"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(ValueError, "unsupported_member"):
                module.inventory(root, legacy)
            fifo.unlink()
            (nested / "file").write_text("fixture")
            with mock.patch.object(module, "MAX_INVENTORY_ENTRIES", 1):
                with self.assertRaisesRegex(ValueError, "entry_limit"):
                    module.inventory(root, legacy)
            with mock.patch.object(module, "MAX_INVENTORY_DEPTH", 0):
                with self.assertRaisesRegex(ValueError, "depth_limit"):
                    module.inventory(root, legacy)

    def test_preserves_old_rows_cursor_pins_elapsed_and_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _, prior, out, expected = checkpoint(root)
            before_files = {p.name: p.read_bytes() for p in prior.iterdir()}
            source_before = source.read_bytes()
            old = metadata(prior / module.DB_NAME)
            old_rows = rows(prior / module.DB_NAME)
            legacy = module.load_legacy(LEGACY_PATH)
            inspected_ordinals = []
            inspect = legacy.inspect_declarations
            def spy(raw, path, anchor):
                inspected_ordinals.append(anchor["source_ordinal"])
                return inspect(raw, path, anchor)
            with mock.patch.object(module, "load_legacy", return_value=legacy), mock.patch.object(legacy, "inspect_declarations", spy):
                report = module.run(root, prior, out, LEGACY_PATH, expected=expected)
            new = metadata(out / module.DB_NAME)
            self.assertEqual(inspected_ordinals, [2, 3, 4, 5])
            self.assertEqual(rows(out / module.DB_NAME)[:2], old_rows)
            self.assertEqual(new["pins"], old["pins"])
            self.assertEqual(new["resume_segment_v2"]["inherited_progress"], old["progress"])
            private = json.loads((out / module.PRIVATE_PROVENANCE_NAME).read_text())
            self.assertEqual(private["inherited_progress"], old["progress"])
            self.assertNotIn("inherited_progress", report["resume_provenance"])
            self.assertEqual(report["resume_provenance"]["private_provenance_sha256"], sha(out / module.PRIVATE_PROVENANCE_NAME))
            self.assertGreaterEqual(new["progress"]["elapsed_seconds"], expected.elapsed_seconds)
            self.assertAlmostEqual(report["elapsed_seconds_cumulative"], expected.elapsed_seconds + report["additional_engineering_elapsed_seconds"])
            self.assertEqual(report["newly_audited_evidence_atoms"], 4)
            self.assertEqual(report["remaining_allowed_evidence_atoms"], 0)
            self.assertEqual(report["inherited_cursor_rowid"], old["progress"]["cursor_rowid"])
            self.assertEqual(before_files, {p.name: p.read_bytes() for p in prior.iterdir()})
            self.assertEqual(source_before, source.read_bytes())
            self.assertTrue(report["prior_directory_stat_unchanged"])
            self.assertEqual(report["output_database_sha256"], sha(out / module.DB_NAME))
            self.assertEqual(report["output_hash_status"], "complete")

    def test_masks_unknown_saved_states_and_nonacceptance_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _, prior, out, expected = checkpoint(root)
            report = module.run(root, prior, out, LEGACY_PATH, expected=expected)
            with sqlite3.connect(out / module.DB_NAME) as db, sqlite3.connect(source) as src:
                produced = db.execute("SELECT source_rowid,original_measurement_state,original_workflow_state,original_engineering_state,original_eligible_scope,original_mask,original_metadata_json FROM evidence_readiness ORDER BY source_rowid").fetchall()
                originals = src.execute("SELECT rowid,measurement_state,workflow_state,engineering_state,eligible_original_scope,original_mask,metadata_json FROM variable_value ORDER BY rowid").fetchall()
                self.assertEqual(produced, originals)
                self.assertEqual(db.execute("SELECT SUM(full_text_reverified),SUM(new_semantic_acceptance) FROM evidence_readiness").fetchone(), (0, 0))
            db.close(); src.close()
            self.assertEqual(report["new_model_calls"], 0)
            self.assertEqual(report["new_production_accepted"], 0)
            self.assertFalse(report["offsets_reverified_against_text"])
            self.assertFalse(report["entire_delivery_or_all_variables_complete"])
            self.assertEqual(report["resume_provenance"]["financial_envelope_usd_unchanged"], 450)

    def test_all_protection_sources_and_bad_anchor_before_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, prior, out, expected = checkpoint(root, count=8, inherited=1,
                denied_runtime=[1], denied_original=[2], denied_reuse=[3], denied_context_protected=[4], bad_anchor=[6])
            legacy = module.load_legacy(LEGACY_PATH)
            inspect = legacy.inspect_declarations
            inspected = []
            def spy(raw, path, anchor):
                inspected.append(anchor["source_ordinal"])
                self.assertNotIn("forbidden", raw)
                return inspect(raw, path, anchor)
            with mock.patch.object(module, "load_legacy", return_value=legacy), mock.patch.object(legacy, "inspect_declarations", spy):
                report = module.run(root, prior, out, LEGACY_PATH, expected=expected)
            self.assertEqual(inspected, [5, 7])
            self.assertEqual(report["excluded_context_union"], 4)
            self.assertEqual(report["excluded_evidence_atoms"], 4)
            self.assertEqual(report["state_counts"]["source_trace_incomplete_payload_not_read"], 1)
            self.assertNotIn("invalid_saved_value_json", report["state_counts"])

    def test_changed_source_and_each_guard_fail_closed(self):
        for target in ("source", "runtime", "state", "release", "original"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source, runtime, prior, out, expected = checkpoint(root)
                paths = {"source": source, "runtime": runtime,
                    "state": root / "execution_20261116/run001/AZURE_RESEARCH_STATE.json",
                    "release": source.parent / "STEP1_RELEASE_PUBLIC.json",
                    "original": root / "execution_20261116/run001/ORIGINAL.sqlite"}
                path = paths[target]
                if target in ("source", "original"):
                    stat = path.stat()
                    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000))
                else:
                    path.write_text(path.read_text() + "\n")
                with self.assertRaisesRegex(ValueError, "pins_changed"):
                    module.run(root, prior, out, LEGACY_PATH, expected=expected)
                self.assertFalse(out.exists())

    def test_changed_legacy_implementation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, prior, out, expected = checkpoint(root)
            changed = root / "changed_legacy.py"
            changed.write_bytes(LEGACY_PATH.read_bytes() + b"\n# changed\n")
            with self.assertRaisesRegex(ValueError, "legacy_code_sha256_changed"):
                module.run(root, prior, out, changed, expected=expected)
            self.assertFalse(out.exists())

    def test_wrong_database_and_report_sha_rejected(self):
        for field in ("database_sha256", "report_sha256"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, _, prior, out, expected = checkpoint(root)
                with self.assertRaisesRegex(ValueError, "sha256_changed"):
                    module.run(root, prior, out, LEGACY_PATH, expected=replace(expected, **{field: "0" * 64}))
                self.assertFalse(out.exists())

    def test_existing_destination_is_never_overwritten_or_restarted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, prior, out, expected = checkpoint(root)
            out.mkdir(); marker = out / "leave_this_alone"; marker.write_bytes(b"preserve")
            with self.assertRaisesRegex(FileExistsError, "no_restart_or_overwrite"):
                module.run(root, prior, out, LEGACY_PATH, expected=expected)
            self.assertEqual(marker.read_bytes(), b"preserve")
            self.assertEqual(list(out.iterdir()), [marker])

    def test_total_atom_cap_is_inherited_not_enlarged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, prior, out, expected = checkpoint(root, count=6, inherited=1, cap=3)
            report = module.run(root, prior, out, LEGACY_PATH, expected=expected)
            self.assertEqual(report["status"], "atom_cap_reached_cursor_preserved")
            self.assertEqual(report["processed_evidence_atoms"], 3)
            self.assertEqual(report["remaining_allowed_evidence_atoms"], 3)
            self.assertEqual(report["max_atoms_cumulative"], 3)
            self.assertEqual(metadata(out / module.DB_NAME)["pins"]["max_atoms_cumulative"], 3)

    def test_above_additional_time_limit_rejected(self):
        with self.assertRaisesRegex(ValueError, "authorized_limit"):
            module.run("/unused", "/unused/a", "/unused/b", LEGACY_PATH, additional_seconds=301)

    def test_timeout_rolls_back_partial_batch_with_prior_cursor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, prior, out, expected = checkpoint(root)
            legacy = module.load_legacy(LEGACY_PATH)
            inspect = legacy.inspect_declarations
            calls = 0
            def interrupt_second(*args):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise module.WindowExceeded("synthetic_interrupt")
                return inspect(*args)
            with mock.patch.object(module, "load_legacy", return_value=legacy), mock.patch.object(legacy, "inspect_declarations", interrupt_second):
                report = module.run(root, prior, out, LEGACY_PATH, expected=expected)
            self.assertEqual(report["status"], "time_cap_reached_cursor_preserved")
            self.assertEqual(report["newly_audited_evidence_atoms"], 0)
            self.assertEqual(report["cursor_rowid"], report["inherited_cursor_rowid"])
            self.assertEqual(rows(out / module.DB_NAME), rows(prior / module.DB_NAME))
            self.assertEqual(report["output_database_sha256"], sha(out / module.DB_NAME))

    def test_real_signal_time_limit_retains_checkpoint_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, prior, out, expected = checkpoint(root)
            legacy = module.load_legacy(LEGACY_PATH)
            inspect = legacy.inspect_declarations
            def slow(*args):
                time.sleep(.5)
                return inspect(*args)
            with mock.patch.object(module, "load_legacy", return_value=legacy), mock.patch.object(legacy, "inspect_declarations", slow):
                report = module.run(root, prior, out, LEGACY_PATH, additional_seconds=.2, expected=expected)
            self.assertEqual(report["status"], "time_cap_reached_cursor_preserved")
            self.assertEqual(report["newly_audited_evidence_atoms"], 0)
            self.assertLess(report["additional_window_wall_seconds"], .2)
            self.assertEqual(report["output_database_sha256"], sha(out / module.DB_NAME))

    def test_historical_provenance_records_authorization_and_not_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, prior, out, expected = checkpoint(root)
            report = module.run(root, prior, out, LEGACY_PATH, additional_seconds=20, expected=expected)
            resume = report["resume_provenance"]
            self.assertEqual(resume["authorization"], "user_continue_2026-11-18_Asia_Shanghai")
            self.assertEqual(resume["prior_database_sha256"], expected.database_sha256)
            self.assertEqual(resume["prior_report_sha256"], expected.report_sha256)
            self.assertEqual(resume["legacy_parser_code_sha256"], module.LEGACY_CODE_SHA256)
            self.assertEqual(resume["resume_code_sha256"], sha(Path(module.__file__)))
            self.assertEqual(resume["inherited_elapsed_seconds"], expected.elapsed_seconds)
            self.assertEqual(resume["effective_cumulative_time_cap_seconds"], expected.elapsed_seconds + 20)
            self.assertEqual(resume["additional_window_seconds"], 20)
            self.assertEqual(report["inherited_original_time_cap_seconds"], 300)

    def test_public_report_excludes_full_pins_paths_and_context_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, prior, out, expected = checkpoint(root)
            report = module.run(root, prior, out, LEGACY_PATH, expected=expected)
            encoded = json.dumps(report)
            for private_key in ("inherited_pins", "inherited_progress", "inherited_input_counts",
                                "prior_directory_relative_to_root", "source_stat", "inode", "device"):
                self.assertNotIn('"' + private_key + '"', encoded)
            self.assertNotIn(str(root), encoded)
            self.assertNotIn("run001", encoded)
            private = json.loads((out / module.PRIVATE_PROVENANCE_NAME).read_text())
            self.assertEqual(private, metadata(out / module.DB_NAME)["resume_segment_v2"])


if __name__ == "__main__":
    unittest.main()
