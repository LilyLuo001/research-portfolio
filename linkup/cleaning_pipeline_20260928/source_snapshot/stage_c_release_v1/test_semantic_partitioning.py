import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from login_transfer_worker import sealed_outputs
from semantic_server_controller import promote_ks_compute_complete, split_balanced, write_jsonl


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SemanticPartitioningTest(unittest.TestCase):
    def test_split_is_complete_disjoint_and_balanced(self):
        rows = [{"shard_id": "s%d" % i, "raw_rows": value}
                for i, value in enumerate([11, 9, 7, 5, 3, 2, 1])]
        parts = split_balanced(rows, 2)
        ids = [{x["shard_id"] for x in part} for part in parts]
        self.assertFalse(ids[0] & ids[1])
        self.assertEqual(ids[0] | ids[1], {x["shard_id"] for x in rows})
        self.assertLessEqual(abs(sum(x["raw_rows"] for x in parts[0]) -
                                 sum(x["raw_rows"] for x in parts[1])), 1)

    def test_partial_completion_does_not_publish_global_marker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); checkpoints = root / "checkpoints"; checkpoints.mkdir()
            rows = [{"shard_id": "s%d" % i, "raw_rows": i + 1} for i in range(6)]
            parts = split_balanced(rows, 2)
            full = root / "plan.jsonl"; write_jsonl(full, rows)
            paths = []
            for index, part in enumerate(parts):
                path = root / ("plan.part%d.jsonl" % index); write_jsonl(path, part); paths.append(path)
                for row in part:
                    (checkpoints / (row["shard_id"] + ".queued.json")).write_text("{}")
            marker0 = {"status": "compute_queue_complete", "partition_id": "part0",
                       "planned_shards": len(parts[0]), "completed_plan_shards": len(parts[0]),
                       "plan_sha256": digest(paths[0])}
            (checkpoints / "REGION_QUEUE_COMPLETE.part0.json").write_text(json.dumps(marker0))
            self.assertFalse(promote_ks_compute_complete(full, paths, checkpoints))
            self.assertFalse((checkpoints / "REGION_PARTS_QUEUE_COMPLETE.json").exists())
            marker1 = {"status": "compute_queue_complete", "partition_id": "part1",
                       "planned_shards": len(parts[1]), "completed_plan_shards": len(parts[1]),
                       "plan_sha256": digest(paths[1])}
            (checkpoints / "REGION_QUEUE_COMPLETE.part1.json").write_text(json.dumps(marker1))
            self.assertTrue(promote_ks_compute_complete(full, paths, checkpoints))
            global_marker = json.loads((checkpoints / "REGION_PARTS_QUEUE_COMPLETE.json").read_text())
            self.assertEqual(global_marker["planned_shards"], 6)
            self.assertEqual(global_marker["partition_count"], 2)

    def test_publisher_sees_both_direct_partition_buffers_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for part, shard in (("part0", "a"), ("part1", "b")):
                output = root / part / shard; output.mkdir(parents=True)
                (output / "SHARD_COMPLETE.json").write_text("{}")
                work = root / part / (shard + ".work"); work.mkdir()
                (work / "SHARD_COMPLETE.json").write_text("{}")
            self.assertEqual([x.name for x in sealed_outputs(root, ["part0", "part1"])], ["a", "b"])
            self.assertEqual(sealed_outputs(root, []), [])


if __name__ == "__main__":
    unittest.main()
