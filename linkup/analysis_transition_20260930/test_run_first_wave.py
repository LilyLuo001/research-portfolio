import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import run_first_wave as driver


class ReceiptIdentityTest(unittest.TestCase):
    def test_stale_summary_and_mismatched_shard_complete_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shard = root / "sid-a"
            shard.mkdir()
            complete = {"status": "complete", "accounting": {
                "shard_id": "sid-a", "raw_rows": 1, "row_conservation": True,
                "disposition_counts": {"matched_usa_canonical": 1}}}
            complete_path = shard / "SHARD_COMPLETE.json"
            complete_path.write_text(json.dumps(complete))
            receipt_value = {
                "status": "published_verified", "shard_id": "sid-a",
                "shard_complete_sha256": hashlib.sha256(complete_path.read_bytes()).hexdigest(),
                "shard_complete": complete}
            receipt = root / "sid-a.published.json"
            receipt.write_text(json.dumps(receipt_value))
            row = {"shard_id": "sid-a", "shard_dir": str(shard), "receipt": str(receipt)}
            driver.validate_shard_identity(row)
            with self.assertRaisesRegex(RuntimeError, "published receipt identity mismatch"):
                driver.validate_shard_identity({**row, "shard_id": "sid-b"})

            summary = root / "summary.json"
            summary.write_text(json.dumps({"version": driver.EXPECTED_VERSION, "shards": 1,
                                           "leaf_summary_ids": ["stale"]}))
            self.assertFalse(driver.summary_valid(summary, receipt))

            complete_path.write_text(json.dumps({**complete, "status": "changed"}))
            with self.assertRaisesRegex(RuntimeError, "digest differs"):
                driver.validate_shard_identity(row)


if __name__ == "__main__":
    unittest.main()
