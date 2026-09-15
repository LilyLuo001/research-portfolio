#!/usr/bin/env python3
"""Reread 20 actual pilot paths on SCC; emit aggregate assertions only."""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

ap=argparse.ArgumentParser(); ap.add_argument("--protected",required=True); ap.add_argument("--pilot-receipt",required=True); ap.add_argument("--code",required=True); ap.add_argument("--config",required=True); ap.add_argument("--manifest",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
d=pd.read_csv(a.protected,dtype=str)
z=d[d.source_mapping_status.eq("UNIQUE_VALID_PERMNO")].drop_duplicates(["source_row_id","candidate_id"]).sort_values(["source_row_id","candidate_id"]).head(20)
if len(z)!=20: raise ValueError(f"only {len(z)} actual unique pilot observations")
cfg=json.load(open(a.config)); reread_ok=True
for r in z.itertuples(index=False):
    family,filename,rownum=r.source_row_id.split(":",2); year=int(filename.rsplit("_",1)[1].split(".")[0]); path=cfg["families"][family].format(year=year)
    src=pd.read_parquet(path,columns=cfg["allowed_actual_columns"]).iloc[int(rownum)-1]
    for col in ["ticker","cusip","pdicity","anntims","acttims"]:
        left="<NA>" if pd.isna(src[col]) else str(src[col]); right="<NA>" if pd.isna(getattr(r,col)) else str(getattr(r,col)); reread_ok &= left==right
    for col in ["pends","anndats","actdats"]:
        left=pd.to_datetime(src[col],errors="coerce"); right=pd.to_datetime(getattr(r,col),errors="coerce"); reread_ok &= (pd.isna(left) and pd.isna(right)) or left==right
checks={
 "twenty_actual_source_candidate_observations":bool(len(z)==20),
 "source_row_ids_present":bool(z.source_row_id.notna().all()),
 "candidate_ids_present":bool(z.candidate_id.notna().all()),
 "closed_date_paths":bool(z.closed_date_path.eq("True").all()),
 "unique_mapping_status":bool(z.source_mapping_status.eq("UNIQUE_VALID_PERMNO").all()),
 "candidate_permno_matches_link":bool(pd.to_numeric(z.permno_link).eq(pd.to_numeric(z.permno_candidate)).all()),
 "valid_cusip8":bool(z.cusip_norm.str.fullmatch(r"[A-Z0-9]{8}").all())
 ,"source_row_allowed_fields_reread_exact":bool(reread_ok)
}
pilot=json.load(open(a.pilot_receipt)); bindings={"code_sha256":sha(a.code),"config_sha256":sha(a.config),"manifest_sha256":sha(a.manifest),"pilot_receipt_sha256":sha(a.pilot_receipt)}
if pilot["code_sha256"]!=bindings["code_sha256"] or pilot["config_sha256"]!=bindings["config_sha256"] or pilot["manifest_sha256"]!=bindings["manifest_sha256"]: raise ValueError("pilot binding mismatch")
r={"status":"PASS" if all(checks.values()) else "FAIL","observations_checked":20,"assertions":checks,"bindings":bindings,"protected_rows_exported_local":False,"financial_values_read":False,"sample_keyset_sha256":hashlib.sha256("\n".join((z.source_row_id+"|"+z.candidate_id).tolist()).encode()).hexdigest()}
Path(a.out).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
if r["status"]!="PASS": raise ValueError("lineage failed")
