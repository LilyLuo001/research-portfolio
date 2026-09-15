#!/usr/bin/env python3
"""SCC-only bounded, outcomes-free uncapped metadata census."""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

START, END = "2019-01-01", "2026-09-01"
META_SHA = "97a3c35c1f59013047924b89859df67ff361327a61b7bec0a28bdf3412c562cb"
LINK_SHA = "fd259ac817ab9ea64553e0cdacadc22fcd94de361d1f1851855f9e27ed87e326"
META = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/p1_roster_earnings_20260913/ibes_metadata_projection_v2/ibes_announcement_metadata.csv")
LINK = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw/crsp_ibes_link_full.parquet")

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def norm(x): return "" if pd.isna(x) else str(x).strip().upper()[:8]

def main():
 a=argparse.ArgumentParser(); a.add_argument("--candidates",type=Path,required=True);a.add_argument("--old-keys",type=Path,required=True);a.add_argument("--out",type=Path,required=True); args=a.parse_args()
 if sha(META)!=META_SHA or sha(LINK)!=LINK_SHA: raise ValueError("source hash mismatch")
 cand=pd.read_csv(args.candidates,dtype=str,usecols=["candidate_id","wave_id","permno","provisional_tier","announcement_cutoff","post_20_session_threshold"])
 cand["permno"]=pd.to_numeric(cand.permno,errors="raise").astype("int64")
 if len(cand)!=2794 or set(cand.provisional_tier)!={"high","low"} or cand.candidate_id.nunique()!=len(cand): raise ValueError("pinned H/L candidate manifest mismatch")
 link=pd.read_parquet(LINK,columns=["permno","ncusip","sdate","edate","score"])
 link=link[link.permno.isin(cand.permno)].copy(); link["permno"]=link.permno.astype("int64");link["cusip"]=link.ncusip.map(norm);link["sdate"]=pd.to_datetime(link.sdate,errors="coerce");link["edate"]=pd.to_datetime(link.edate,errors="coerce").fillna(pd.Timestamp("2099-12-31"))
 old=pd.read_csv(args.old_keys,dtype=str,usecols=["wave_id","permno","pends","anndats","old_analyst_status"]);old.permno=pd.to_numeric(old.permno,errors="raise").astype("int64")
 parts=[]
 for chunk in pd.read_csv(META,dtype=str,usecols=["ticker","cusip","pends","pdicity","anndats","anntims","actdats","acttims","source_partition"],chunksize=200000):
  chunk["source_row_id"]=chunk.source_partition+":"+(chunk.index+1).astype(str)
  chunk["cusip"]=chunk.cusip.map(norm);chunk["anndats_dt"]=pd.to_datetime(chunk.anndats,errors="coerce")
  chunk=chunk[chunk.pdicity.eq("QTR") & chunk.anndats_dt.ge(START) & chunk.anndats_dt.lt(END)]
  if not chunk.empty: parts.append(chunk)
 meta=pd.concat(parts,ignore_index=True)
 # A PERMNO can be a source candidate in more than one wave; retain each
 # wave-specific candidate path instead of incorrectly demanding uniqueness.
 merged=cand.merge(link,on="permno",how="left",validate="many_to_many").merge(meta,on="cusip",how="left",validate="many_to_many")
 merged=merged[(merged.sdate<=merged.anndats_dt)&(merged.anndats_dt<=merged.edate)].copy()
 merged["event_side_provisional"]="TRANSITION_OR_BUFFER"
 merged.loc[merged.anndats_dt<pd.to_datetime(merged.announcement_cutoff),"event_side_provisional"]="PRE"
 merged.loc[merged.anndats_dt>=pd.to_datetime(merged.post_20_session_threshold),"event_side_provisional"]="POST"
 merged=merged.merge(old,on=["wave_id","permno","pends","anndats"],how="left",validate="many_to_one")
 merged["analyst_status"]=merged.old_analyst_status.fillna("UNKNOWN_NEW_UNCAPPED_RECORD")
 merged["accounting_period_key"]=merged.wave_id+":"+merged.permno.astype(str)+":"+merged.pends.fillna("MISSING")
 merged["public_event_candidate_key"]=merged.wave_id+":"+merged.permno.astype(str)+":"+merged.anndats.fillna("MISSING")+":"+merged.anntims.fillna("MISSING")
 args.out.mkdir(parents=True,exist_ok=False)
 # Row-level protected projection remains SCC-only, with exact source row IDs.
 cols=["candidate_id","wave_id","permno","provisional_tier","announcement_cutoff","post_20_session_threshold","ncusip","sdate","edate","score","source_row_id","source_partition","ticker","cusip","pends","pdicity","anndats","anntims","actdats","acttims","event_side_provisional","accounting_period_key","public_event_candidate_key","analyst_status"]
 merged[cols].to_csv(args.out/"protected_uncapped_metadata_projection.csv",index=False)
 agg=merged.groupby(["wave_id","provisional_tier","event_side_provisional","analyst_status"],dropna=False).agg(raw_source_record_candidates=("source_row_id","size"),accounting_period_keys=("accounting_period_key","nunique"),public_event_candidate_keys=("public_event_candidate_key","nunique"),stock_wave_candidates=("candidate_id","nunique")).reset_index()
 agg.to_csv(args.out/"uncapped_metadata_aggregate.csv",index=False)
 receipt={"status":"COMPLETE_SOURCE_WINDOW_METADATA_CENSUS_NOT_FINAL_ANALYSIS_SUPPORT","candidate_count":len(cand),"date_bounds":{"lower_inclusive":START,"upper_exclusive":END},"source_hashes":{"metadata":sha(META),"link":sha(LINK)},"source_columns":{"metadata":["ticker","cusip","pends","pdicity","anndats","anntims","actdats","acttims","source_partition"],"link":["permno","ncusip","sdate","edate","score"]},"raw_financial_values_read":False,"quote_or_native_files_read":False,"economic_events_certified":False,"clock_timezone":"UNVERIFIED","output_row_level":"SCC_ONLY","aggregate_sha256":sha(args.out/"uncapped_metadata_aggregate.csv"),"protected_projection_sha256":sha(args.out/"protected_uncapped_metadata_projection.csv")}
 (args.out/"uncapped_metadata_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
if __name__=="__main__": main()
