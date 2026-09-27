import json
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import compact_candidate_batch as compact

ROOT=Path(__file__).resolve().parents[1]
PARSER=ROOT/"stage_c_v5"/"requirement_candidates.py"

class CompactTests(unittest.TestCase):
    def source(self,root,texts):
        path=root/"source.parquet"
        pq.write_table(pa.table({"JOB_HASH":["h%d"%i for i in range(len(texts))],"DESCRIPTION":texts}),path)
        return path

    def test_roundtrip_preserves_candidate_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=self.source(root,["Friendly workplace.","Qualifications:\n3 years Python experience required.","Bachelor's degree or five years experience required."])
            out=root/"out"; receipt=compact.process_source(source,PARSER,out,3,2,10_000_000)
            self.assertEqual(receipt["processed_rows"],3)
            self.assertEqual(compact.verify_roundtrip(source,PARSER,out)["status"],"PASS")
            self.assertEqual(pq.ParquetFile(out/"source_index.parquet").metadata.num_rows,3)
            self.assertTrue((out/"relations.parquet").is_file())

    def test_insufficient_cap_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=self.source(root,["Python SQL Excel Tableau"]*20); out=root/"out"
            with self.assertRaisesRegex(ValueError,"at least"):
                compact.process_source(source,PARSER,out,20,10,compact.MIN_FORMAT_BUDGET_BYTES-1)
            self.assertFalse(out.exists())

    def test_actual_footer_and_receipt_bytes_respect_cap(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=self.source(root,["Python SQL Excel Tableau"]*20); out=root/"out"
            receipt=compact.process_source(source,PARSER,out,20,10,compact.MIN_FORMAT_BUDGET_BYTES)
            actual=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
            self.assertLessEqual(actual,compact.MIN_FORMAT_BUDGET_BYTES)
            self.assertEqual(receipt["persistent_bytes_including_checkpoint"],actual)
            self.assertGreaterEqual(receipt["pending_rows"],0)

    def test_forced_exception_preserves_declared_and_actual_fingerprints(self):
        class ForcedParser:
            def extract(self, raw):
                raise RuntimeError("forced")
            def _normalize(self, raw):
                return raw
        parser=ForcedParser(); raw="raw input"
        source,ad,evidence,relations,original=compact.compact_payload("h",raw,"f",0,parser)
        rebuilt=compact.reconstruct_payload(source,ad,evidence,raw,parser)
        self.assertEqual(rebuilt,original)
        self.assertEqual(source["RAW_SHA256"],compact.sha256_bytes(raw.encode()))
        self.assertIsNone(source["PARSER_SOURCE_FINGERPRINT_SHA256"])
        self.assertIn("runner caught RuntimeError: forced",rebuilt["errors"])
        self.assertIn("source_fingerprint_sha256 mismatch",rebuilt["errors"])

    def test_null_text_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=self.source(root,[None,"Qualifications: 2 years experience required."])
            out=root/"out"; receipt=compact.process_source(source,PARSER,out,2,2,2_000_000)
            self.assertEqual(receipt["processed_rows"],2)
            self.assertEqual(receipt["status_counts"]["parse_error"],1)
            self.assertEqual(compact.verify_roundtrip(source,PARSER,out)["status"],"PASS")

if __name__=="__main__": unittest.main()
