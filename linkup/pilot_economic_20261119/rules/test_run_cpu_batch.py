"""Filesystem tests use synthetic records only and stay inside rules/."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

try:
    from . import run_cpu_batch as batch
except ImportError:
    import run_cpu_batch as batch


def record(text, **extra):
    return {"case": "synthetic-only", "row": {"record_id": "private-test-id", "context_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "full_document": text, **extra}}


class BatchTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root = Path(self.directory.name)
        self.input = self.root / "input.jsonl"
        self.cache = self.root / "cache.sqlite"

    def tearDown(self):
        self.directory.cleanup()

    def run_rows(self, rows, stem="first", **kwargs):
        self.input.write_text("".join(json.dumps(row) + "\n" for row in rows))
        return batch.run_batch(self.input, self.root / (stem + ".jsonl"), self.root / (stem + ".json"), self.cache, **kwargs)

    def test_all_rows_including_nohit_and_no_ids_public(self):
        rows = [record("At least 5 years of Python experience."), record("Welcome aboard.")]
        receipt = self.run_rows(rows)
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["input_rows_processed"], 2)
        self.assertEqual(receipt["records_without_retained_candidates"], 1)
        public = json.dumps(receipt)
        for private in ("private-test-id", "synthetic-only", "Welcome aboard", "At least 5"):
            self.assertNotIn(private, public)
        result = [json.loads(line) for line in (self.root / "first.jsonl").read_text().splitlines()]
        self.assertEqual(result[0]["context_sha256"], rows[0]["row"]["context_sha256"])
        self.assertTrue(all(row["result"]["field_updates"] == {} for row in result))

    def test_cache_reused_and_output_deterministic(self):
        rows = [record("3 years of work experience")]
        first = self.run_rows(rows)
        second = self.run_rows(rows, "second")
        self.assertEqual(first["cache_misses"], 1)
        self.assertEqual(second["cache_hits"], 1)
        self.assertEqual(first["output_sha256"], second["output_sha256"])

    def test_identical_completed_run_verified_not_overwritten(self):
        rows = [record("Python experience")]
        self.run_rows(rows)
        self.assertTrue(self.run_rows(rows)["already_complete"])

    def test_changed_input_does_not_overwrite(self):
        self.run_rows([record("Python experience")])
        with self.assertRaises(FileExistsError):
            self.run_rows([record("SQL experience")])

    def test_explicit_no_missing_fields_preserves_noop(self):
        result = self.run_rows([record("5 years Python experience", missing_fields=[])])
        self.assertEqual(result["candidate_count_before_limit"], 0)
        self.assertEqual(result["result_status_counts"], {"no_fields_requested": 1})

    def test_row_field_selection_overrides_default(self):
        receipt = self.run_rows([record("5 years of Python experience", missing_fields=["technology"])])
        self.assertEqual(set(receipt["candidate_kind_counts"]), {"technology_keyword"})
        self.assertEqual(receipt["field_selection_counts"], {"row_missing_fields": 1})

    def test_bad_context_hash_remains_failure(self):
        row = record("Python")
        row["row"]["context_sha256"] = "0" * 64
        receipt = self.run_rows([row])
        self.assertEqual(receipt["status"], "incomplete")
        self.assertEqual(receipt["failed_or_limited_rows"], 1)
        self.assertEqual(receipt["result_status_counts"], {"invalid_input_record": 1})

    def test_invalid_cache_recomputed(self):
        rows = [record("Python experience")]
        self.run_rows(rows)
        with sqlite3.connect(self.cache) as conn:
            conn.execute("UPDATE rule_cache SET result_sha256='bad'")
        receipt = self.run_rows(rows, "second")
        self.assertEqual(receipt["invalid_cache_entries"], 1)
        self.assertEqual(receipt["cache_misses"], 1)

    def test_record_limit_never_claims_completion(self):
        receipt = self.run_rows([record("Python"), record("SQL")], max_records=1)
        self.assertEqual(receipt["status"], "incomplete")
        self.assertEqual(receipt["failure_code"], "input_record_limit_exceeded")
        self.assertFalse(receipt["output_published"])
        self.assertFalse((self.root / "first.jsonl").exists())
        self.assertTrue((self.root / "first.jsonl.partial").is_file())

    def test_out_of_pilot_bounds_rejected(self):
        with self.assertRaises(ValueError):
            self.run_rows([record("Python")], max_records=10001)


if __name__ == "__main__":
    unittest.main()
