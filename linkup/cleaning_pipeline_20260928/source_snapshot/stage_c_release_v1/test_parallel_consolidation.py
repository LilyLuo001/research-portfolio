#!/usr/bin/env python3
import tempfile
import unittest
import sys
import types
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# The consolidation path does not call DuckDB; the production Python 3.8
# runtime supplies it, while this local focused unit-test runtime does not.
sys.modules.setdefault("duckdb", types.SimpleNamespace())
import parallel_consolidate_release_dispositions as parallel
import prepare_release_dispositions as prep


def row(source_row, source_file="source.parquet"):
    return {"SOURCE_ROW": source_row, "JOB_HASH": ("%032x" % (source_row + 1)),
            "MATCH_DISPOSITION": "matched_usa_canonical", "RECORD_SOURCE_ROW": source_row,
            "CREATED": None, "COUNTRY": "USA", "STATE": "CA", "SOURCE_FILE": source_file,
            "GLOBAL_KEY_OCCURRENCES": 1, "DESCRIPTION_COMPANY_ID": 1,
            "RECORD_COMPANY_ID": 1, "COMPANY_ID_MATCH": True}


class ParallelConsolidationTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def make_task(self, tag="a", orphan=False):
        sid = "sid-" + tag; fragment_dir = self.root / "fragments" / tag
        fragment_dir.mkdir(parents=True)
        fragments = []
        for index, values in enumerate(([row(1)], [row(0)])):
            path = fragment_dir / ("%d.parquet" % index)
            pq.write_table(pa.Table.from_pylist(values, schema=prep.SIDECAR_SCHEMA), path)
            fragments.append({"path": str(path), "bytes": path.stat().st_size})
        task = {"region": "kunshan", "source_file": "source.parquet",
                "source": {"shard_id": sid, "source_path": "/raw/source.parquet",
                           "source_bytes": 9, "source_sha256_cached": "0" * 64},
                "expected_rows": 2, "fragments": fragments,
                "sidecar_root": str(self.root / "sidecars")}
        if orphan:
            output, _, _ = parallel.output_paths(task)
            output.parent.mkdir(parents=True)
            output.write_bytes(b"unsealed-generated-output")
        return task

    def test_restart_orphan_denominator_and_delete_after_receipt(self):
        task = self.make_task(orphan=True)
        result = parallel.consolidate_task(task)
        output, receipt, temp = parallel.output_paths(task)
        self.assertEqual(result["status"], "sealed")
        self.assertTrue(result["recovered_orphan"])
        self.assertTrue(output.is_file() and receipt.is_file())
        self.assertFalse(temp.exists())
        self.assertEqual(pq.ParquetFile(output).metadata.num_rows, 2)
        self.assertFalse(any(Path(x["path"]).exists() for x in task["fragments"]))
        saved = output.read_bytes()
        resumed = parallel.consolidate_task(task)
        self.assertEqual(resumed["status"], "resumed_sealed")
        self.assertEqual(output.read_bytes(), saved)

    def test_budget_and_unique_task_plan_helpers(self):
        task = self.make_task(tag="b")
        reservation = parallel.task_reservation(task)
        batch, observed = parallel.choose_batch([task], 16, 100, 100 + reservation, 10**9, 1)
        self.assertEqual(batch, [task]); self.assertEqual(observed, reservation)
        with self.assertRaises(RuntimeError):
            parallel.choose_batch([task], 16, 100, 100 + reservation - 1, 10**9, 1)


if __name__ == "__main__":
    unittest.main()
