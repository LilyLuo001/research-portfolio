#!/usr/bin/env python3
import argparse
import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

batch = load("batch", HERE / "run_semantic_narrow_batch.py")
lean = load("lean", ROOT / "stage_c_release_v1/lean_writer.py")

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def blank(schema, values=None):
    out = {field.name: None for field in schema}; out.update(values or {}); return out


class BatchTest(unittest.TestCase):
    def test_failed_resume_identity_and_zero_ad_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); plans = root / "plan.jsonl"; manifest = root / "manifest.jsonl"
            gate = root / "gate.json"; work = root / "work"; source_rows = []
            gate.write_text(json.dumps({"status":"complete", "final_publication_complete":True, "total_shards":2}))
            plans.write_text("".join(json.dumps({"shard_id":sid})+"\n" for sid in ("a","b")))
            for sid in ("a", "b"):
                shard = root / sid; chunk = shard / "chunk_00000"; chunk.mkdir(parents=True)
                ads = []
                exps = []
                if sid == "b":
                    key={"JOB_HASH":"j", "SOURCE_FILE":"f", "SOURCE_ROW":1, "RECORD_SOURCE_ROW":2}
                    bad_key={"JOB_HASH":"bad", "SOURCE_FILE":"f", "SOURCE_ROW":3, "RECORD_SOURCE_ROW":4}
                    ads=[blank(lean.AD_SCHEMA,{**key,"CREATED":datetime(2024,1,1),"STATE":"MA",
                        "DESCRIPTION_EMPTY":False,"PARSE_ERROR":False,"INPUT_EVIDENCE_TRUNCATED":False,
                        "ENRICHMENT_INCOMPLETE":False,"EXPERIENCE_EVIDENCE_COUNT":2,"TECHNOLOGY_EVIDENCE_COUNT":0,"V6_AUDIT_EVIDENCE_COUNT":0}),
                        blank(lean.AD_SCHEMA,{**bad_key,"CREATED":datetime(2024,1,1),"STATE":"MA",
                        "DESCRIPTION_EMPTY":False,"PARSE_ERROR":True,"INPUT_EVIDENCE_TRUNCATED":False,
                        "ENRICHMENT_INCOMPLETE":False,"EXPERIENCE_EVIDENCE_COUNT":1,"TECHNOLOGY_EVIDENCE_COUNT":0,"V6_AUDIT_EVIDENCE_COUNT":0})]
                    exps=[blank(lean.EXP_SCHEMA,{**key,"EVIDENCE_ORDINAL":0,"OBJECT_TYPE":"general_work","MIN_YEARS":3.0,
                        "BOUND_TYPE":"minimum","DURATION_UNIT":"year","BINDING_STATUS":"explicit",
                        "APPLICANT_CONTEXT_CANDIDATE":True,"REQUIREMENT_STRENGTH":"required"}),
                        blank(lean.EXP_SCHEMA,{**key,"EVIDENCE_ORDINAL":1,"OBJECT_TYPE":"general_work","MAX_YEARS":2.0,
                        "BOUND_TYPE":"maximum","DURATION_UNIT":"year","BINDING_STATUS":"explicit",
                        "APPLICANT_CONTEXT_CANDIDATE":True,"REQUIREMENT_STRENGTH":"preferred"}),
                        blank(lean.EXP_SCHEMA,{**bad_key,"EVIDENCE_ORDINAL":0,"OBJECT_TYPE":"general_work","MIN_YEARS":7.0,
                        "BOUND_TYPE":"minimum","DURATION_UNIT":"year","BINDING_STATUS":"explicit",
                        "APPLICANT_CONTEXT_CANDIDATE":True,"REQUIREMENT_STRENGTH":"required"})]
                for name,schema,rows in (("ad_status",lean.AD_SCHEMA,ads),("experience",lean.EXP_SCHEMA,exps),("technology",lean.TECH_SCHEMA,[])):
                    pq.write_table(pa.Table.from_pylist(rows,schema=schema),chunk/(name+".parquet"))
                complete={"status":"complete","accounting":{"shard_id":sid,"canonical_usa_rows":len(ads)}}
                complete_path=shard/"SHARD_COMPLETE.json"; complete_path.write_text(json.dumps(complete))
                receipt={"status":"published_verified","shard_id":sid,"shard_complete_sha256":digest(complete_path),"shard_complete":complete}
                receipt_path=root/(sid+".source.json"); receipt_path.write_text(json.dumps(receipt))
                source_rows.append({"shard_id":sid,"shard_dir":str(shard),"receipt":str(receipt_path)})
            manifest.write_text("".join(json.dumps(row)+"\n" for row in source_rows))
            wrapper=root/"builder.py"; real=HERE/"build_semantic_narrow.py"
            wrapper.write_text(f'''import argparse,hashlib,importlib.util,json\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument("--shard");p.add_argument("--receipt");p.add_argument("--gate");p.add_argument("--output");p.add_argument("--threads");p.add_argument("--memory-limit");a=p.parse_args()\nshard=Path(a.shard)\nif shard.name=="b" and not (shard/".failed_once").exists(): (shard/".failed_once").write_text("1");raise SystemExit(9)\nspec=importlib.util.spec_from_file_location("n",{str(real)!r});n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)\nn.build(shard,Path(a.output),None,1,"2GB")\nrp=Path(a.output).with_suffix(".receipt.json");r=json.loads(rp.read_text());r["source_receipt_sha256"]=hashlib.sha256(Path(a.receipt).read_bytes()).hexdigest();rp.write_text(json.dumps(r))\n''')
            args=argparse.Namespace(gate=gate,manifest=manifest,plans=[plans],work_dir=work,builder=wrapper,workers=2)
            with self.assertRaises(Exception): batch.execute(args,expected_shards=2)
            self.assertTrue((work/"shards/a.batch.json").is_file())
            batch.execute(args,expected_shards=2)
            receipt=json.loads((work/"BATCH_RECEIPT.json").read_text())
            self.assertEqual(receipt["actions"],{"built":1,"resumed":1})
            zero=pq.read_table(work/"shards/a.parquet")
            self.assertEqual(zero.num_rows,0)
            self.assertEqual(zero.schema.field("exp_occupation_task_main").type,pa.bool_())
            with (work/"aggregate/T2_EXPERIENCE_AD_RATES.csv").open() as handle:
                rates={row["experience_object"]:row for row in csv.DictReader(handle)}
            self.assertEqual(rates["occupation_task"]["measurement_available"],"false")
            self.assertEqual(rates["occupation_task"]["main_rate"],"")
            self.assertEqual(rates["general_work"]["required_ads"],"1")
            self.assertEqual(rates["general_work"]["preferred_ads"],"1")
            with (work/"aggregate/T2_DURATION_BOUND_DISTRIBUTION.csv").open() as handle:
                duration_rows=list(csv.DictReader(handle))
            self.assertEqual(sum(int(row["evidence_rows"] or 0) for row in duration_rows),2)
            forms={row["bound_category"] for row in duration_rows if row["classification"]=="bound_form"}
            self.assertTrue({"minimum","upper_only"} <= forms)
            self.assertTrue((work/"aggregate/T3_TECHNOLOGY_PAIR_OVERLAP.csv").is_file())
            batch.execute(args,expected_shards=2)
            receipt=json.loads((work/"BATCH_RECEIPT.json").read_text())
            self.assertEqual(receipt["actions"],{"resumed":2})
            self.assertEqual(receipt["aggregate_action"],"resumed")
            wrapper.write_text(wrapper.read_text()+"\n")
            with self.assertRaisesRegex(RuntimeError,"identity changed"):
                batch.execute(args,expected_shards=2)


if __name__ == "__main__": unittest.main()
