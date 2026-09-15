#!/usr/bin/env python3
"""Independent SCC-only reread of 20 mapped pilot observations."""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

META_COLS=["ticker","cusip","pends","pdicity","anndats","anntims","actdats","acttims","source_partition"]
LINK_COLS=["permno","ncusip","sdate","edate","score"]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for x in iter(lambda:f.read(1048576),b""):h.update(x)
 return h.hexdigest()
def text(x):return "" if pd.isna(x) else str(x).strip()
def cusip8(x):
 z=text(x).upper();return z if len(z)==8 and z.isalnum() else None
def date(x):return pd.to_datetime(x,errors="coerce")
def score(x):
 if pd.isna(x) or text(x)=="":return "MISSING"
 try:return f"{float(x):.12g}"
 except:return text(x)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--protected",type=Path,required=True);ap.add_argument("--candidates",type=Path,required=True);ap.add_argument("--config",type=Path,required=True);ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--pilot-receipt",type=Path,required=True);ap.add_argument("--code",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
 cfg=json.loads(a.config.read_text());manifest=json.loads(a.manifest.read_text());pilot=json.loads(a.pilot_receipt.read_text())
 bindings={"code_sha256":sha(a.code),"config_sha256":sha(a.config),"manifest_sha256":sha(a.manifest),"pilot_receipt_sha256":sha(a.pilot_receipt)}
 if bindings["code_sha256"]!=manifest["code_hashes"][a.code.name] or bindings["config_sha256"]!=manifest["config_sha256"]:raise ValueError("binding mismatch")
 meta_path=Path(cfg["source_metadata"]["path"]);link_path=Path(cfg["identity_link_metadata"]["path"])
 if sha(meta_path)!=cfg["source_metadata"]["sha256"] or sha(link_path)!=cfg["identity_link_metadata"]["sha256"]:raise ValueError("source hash mismatch")
 protected=pd.read_csv(a.protected,dtype=str);sample=protected.sort_values(["source_row_id","candidate_id","link_path_id"]).drop_duplicates(["source_row_id","candidate_id"]).head(20)
 if len(sample)!=20:raise ValueError("fewer than 20 mapped observations")
 candidates=pd.read_csv(a.candidates,dtype=str).set_index("candidate_id")
 meta=pd.read_csv(meta_path,dtype=str,usecols=META_COLS);meta["source_file_row_number"]=meta.index+2;meta=meta.set_index("source_file_row_number")
 link=pd.read_parquet(link_path,columns=LINK_COLS);link["link_row_number"]=link.index+1;link=link.set_index("link_row_number",drop=False)
 checks={"csv_row_provenance_exact":True,"metadata_allowed_fields_exact":True,"candidate_key_exact":True,"link_row_identity_exact":True,"link_cusip8_exact":True,"closed_link_date_path_valid":True,"source_row_permno_ambiguity_recomputed":True}
 sample_ids=[]
 for r in sample.itertuples(index=False):
  rn=int(float(r.source_file_row_number));lr=int(str(r.link_path_id).split(":")[-1]);m=meta.loc[rn];l=link.loc[lr];c=candidates.loc[r.candidate_id]
  checks["csv_row_provenance_exact"] &= (r.source_row_id==f"{text(m.source_partition) if text(m.source_partition) else 'MISSING_PARTITION'}:CSV_ROW:{rn}")
  for col in META_COLS:checks["metadata_allowed_fields_exact"] &= (text(getattr(r,col))==text(m[col]))
  checks["candidate_key_exact"] &= (text(r.wave_id)==text(c.wave_id) and int(float(r.permno))==int(float(c.permno)) and text(r.provisional_tier)==text(c.provisional_tier))
  checks["link_row_identity_exact"] &= (int(float(r.permno))==int(float(l.permno)) and text(r.ncusip).upper()==text(l.ncusip).upper() and date(r.sdate)==date(l.sdate) and date(r.edate)==date(l.edate) and score(r.score_stratum)==score(l.score))
  checks["link_cusip8_exact"] &= (cusip8(m.cusip) is not None and cusip8(m.cusip)==cusip8(l.ncusip))
  event=date(m.anndats);checks["closed_link_date_path_valid"] &= (pd.notna(date(l.sdate)) and pd.notna(date(l.edate)) and date(l.sdate)<=event<=date(l.edate))
  lc=link.copy();lc["cusip8"]=lc.ncusip.map(cusip8);z=lc[lc.cusip8.eq(cusip8(m.cusip))].copy();z["sd"]=pd.to_datetime(z.sdate,errors="coerce");z["ed"]=pd.to_datetime(z.edate,errors="coerce");z=z[z.sd.notna()&z.ed.notna()&z.sd.le(event)&z.ed.ge(event)];n=z.permno.dropna().astype(float).loc[lambda x:(x%1)==0].astype(int).nunique();expected="UNIQUE_VALID_PERMNO" if n==1 else "AMBIGUOUS_VALID_PERMNO" if n>1 else "NO_VALID_PERMNO";checks["source_row_permno_ambiguity_recomputed"] &= (int(float(r.source_valid_permno_count))==n and r.source_permno_mapping_status==expected)
  sample_ids.append(r.source_row_id+":"+r.candidate_id)
 checks={k:bool(v) for k,v in checks.items()}
 status="PASS" if all(checks.values()) else "FAIL"
 receipt={"status":status,"sample_observations_checked":len(sample),"sample_lineage_keyset_sha256":hashlib.sha256("\n".join(sorted(sample_ids)).encode()).hexdigest(),"assertions":checks,"bindings":bindings,"source_hashes":{"metadata":sha(meta_path),"identity_link":sha(link_path)},"metadata_columns_reread":META_COLS,"link_columns_reread":LINK_COLS,"protected_rows_exported_local":False,"financial_forecast_quote_response_values_read":False}
 a.out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 if status!="PASS":raise SystemExit(1)
 print(json.dumps({"status":status,"sample_observations_checked":len(sample),"assertions_passed":len(checks)}))
if __name__=="__main__":main()
