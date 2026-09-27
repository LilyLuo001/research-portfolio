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

    def test_cap_stop_records_pending_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=self.source(root,["Python SQL Excel Tableau"]*20); out=root/"out"
            receipt=compact.process_source(source,PARSER,out,20,10,1)
            self.assertEqual(receipt["status"],"stopped_cap")
            self.assertEqual(receipt["processed_rows"],0)
            self.assertEqual(receipt["pending_rows"],20)
            self.assertEqual(json.loads((out/"CHECKPOINT.json").read_text())["next_source_row"],0)

if __name__=="__main__": unittest.main()
