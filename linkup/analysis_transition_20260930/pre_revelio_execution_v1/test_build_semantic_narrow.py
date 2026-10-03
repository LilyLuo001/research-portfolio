#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("narrow", Path(__file__).with_name("build_semantic_narrow.py"))
narrow = importlib.util.module_from_spec(spec); spec.loader.exec_module(narrow)
spec2 = importlib.util.spec_from_file_location("lean", ROOT / "stage_c_release_v1" / "lean_writer.py")
lean = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(lean)


def row(schema, values):
    result = {field.name: None for field in schema}; result.update(values); return result


class NarrowTest(unittest.TestCase):
    def test_dedup_missing_and_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); chunk = root / "shard/chunk_00000"; chunk.mkdir(parents=True)
            key = {"JOB_HASH":"a", "SOURCE_FILE":"s", "SOURCE_ROW":1, "RECORD_SOURCE_ROW":2}
            ad = row(lean.AD_SCHEMA, {**key, "CREATED":datetime(2024,1,1), "STATE":"MA",
                "DESCRIPTION_EMPTY":False,"PARSE_ERROR":False,"INPUT_EVIDENCE_TRUNCATED":False,
                "ENRICHMENT_INCOMPLETE":False,"EXPERIENCE_EVIDENCE_COUNT":2,
                "TECHNOLOGY_EVIDENCE_COUNT":2,"V6_AUDIT_EVIDENCE_COUNT":0})
            ex = [row(lean.EXP_SCHEMA, {**key,"EVIDENCE_ORDINAL":i,"OBJECT_TYPE":"general_work",
                "MIN_YEARS":v,"MAX_YEARS":None,"BOUND_TYPE":b,"BINDING_STATUS":"explicit",
                "APPLICANT_CONTEXT_CANDIDATE":True,"REQUIREMENT_STRENGTH":"required"})
                  for i,(v,b) in enumerate(((3.0,"minimum"),(2.0,"exact_or_unspecified")))]
            tech = [row(lean.TECH_SCHEMA, {**key,"EVIDENCE_ORDINAL":i,"TECHNOLOGY_TYPE":typ,
                "ROLE":"use","BINDING_STATUS":"explicit","ROLE_CANDIDATE":True,
                "APPLICANT_CONTEXT_CANDIDATE":True}) for i,typ in enumerate(("generative_ai","traditional_software"))]
            for name,schema,rows in (("ad_status",lean.AD_SCHEMA,[ad]),("experience",lean.EXP_SCHEMA,ex),
                                     ("technology",lean.TECH_SCHEMA,tech)):
                pq.write_table(pa.Table.from_pylist(rows,schema=schema),chunk/(name+".parquet"))
            out=root/"narrow.parquet"; narrow.build(root/"shard",out,None,1,"1GB")
            got=pq.read_table(out).to_pylist()[0]
            self.assertTrue(got["exp_general_work_main"])
            self.assertTrue(got["exp_general_work_exact_or_unspecified"])
            self.assertTrue(got["tech_generative_ai_use_explicit"])
            self.assertIsNone(got["exp_occupation_task_main"])
            self.assertFalse(got["exp_occupation_task_available"])
            durations=pq.read_table(out.with_suffix(".durations.parquet")).to_pylist()
            self.assertEqual([(x["MIN_YEARS"],x["BOUND_TYPE"]) for x in durations],
                             [(3.0,"minimum"),(2.0,"exact_or_unspecified")])


if __name__ == "__main__": unittest.main()
