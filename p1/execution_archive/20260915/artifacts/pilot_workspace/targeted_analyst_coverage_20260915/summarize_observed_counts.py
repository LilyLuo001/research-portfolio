#!/usr/bin/env python3
"""Aggregate already-produced protected analyst counts; no source reread."""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--out",required=True); ap.add_argument("--receipt",required=True); a=ap.parse_args()
d=pd.read_csv(a.input,usecols=["wave_id","provisional_tier","event_side","source_window_status","analyst_coverage_status","analyst_count_90d"])
z=d.groupby(["wave_id","provisional_tier","event_side","source_window_status","analyst_coverage_status","analyst_count_90d"],dropna=False).size().rename("exact_event_keys").reset_index()
z.to_csv(a.out,index=False,lineterminator="\n")
r={"status":"PASS","input":"PROTECTED_OUTPUT_ONLY_NO_SOURCE_REREAD","input_sha256":sha(a.input),"output_sha256":sha(a.out),"code_sha256":sha(__file__),"row_identifiers_exported":False}
Path(a.receipt).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
