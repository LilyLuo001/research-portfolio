#!/usr/bin/env python3
"""Corrected metadata-only census; protected row-level output remains SCC-only."""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

ALLOWED_META=["ticker","cusip","pends","pdicity","anndats","anntims","actdats","acttims","source_partition"]
ALLOWED_LINK=["permno","ncusip","sdate","edate","score"]
ANALYST_KEYS=["wave_id","permno","provisional_tier","event_side","pends","anndats"]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for x in iter(lambda:f.read(1048576),b""):h.update(x)
 return h.hexdigest()
def norm_cusip(x):
 if pd.isna(x):return None
 z=str(x).strip().upper()
 return z if len(z)==8 and z.isalnum() else None
def norm_permno(s):
 x=pd.to_numeric(s,errors="raise")
 if x.isna().any() or ((x%1)!=0).any():raise ValueError("non-finite/non-integral PERMNO")
 return x.astype("int64")
def parse_link_permno(s):
 x=pd.to_numeric(s,errors="coerce")
 valid=x.notna() & ((x%1)==0)
 return x.where(valid).astype("Int64"), valid.map({True:"VALID_INTEGER_PERMNO",False:"INVALID_OR_MISSING_PERMNO_UNKNOWN"})
def to_bool(s):
 if s.dtype==bool:return s
 x=s.astype(str).str.lower().map({"true":True,"false":False})
 if x.isna().any():raise ValueError("invalid boolean")
 return x
def classify_link_bounds(sraw,eraw,sdt,edt):
 if pd.isna(sraw) or str(sraw).strip()=="":return "OPEN_START_UNKNOWN"
 if pd.isna(sdt):return "INVALID_START_DATE"
 if pd.isna(eraw) or str(eraw).strip()=="":return "OPEN_END_UNKNOWN"
 if pd.isna(edt):return "INVALID_END_DATE"
 if sdt>edt:return "INVALID_CLOSED_RANGE"
 return "CLOSED_VALID_BOUNDS"
def in_source_window(d,start,end):return pd.notna(d) and d>=start and d<end
def classify_event_side(d,cutoff,post):
 if pd.isna(d) or pd.isna(cutoff) or pd.isna(post):return "UNKNOWN_MISSING_BOUND"
 if d<cutoff:return "PRE"
 if d>=post:return "POST"
 return "TRANSITION"
def source_mapping_status(valid_permnos,has_unknown):
 n=len(set(valid_permnos))
 if n==1:return "UNIQUE_VALID_PERMNO"
 if n>1:return "AMBIGUOUS_VALID_PERMNO"
 return "NO_VALID_PERMNO_LINK_DATE_UNKNOWN" if has_unknown else "NO_VALID_PERMNO"
def distinct_pair_count(df,left,right):
 return int(df[[left,right]].drop_duplicates().shape[0])
def verify_gate(mode,gate,code_hash,config_hash,manifest_hash):
 if mode!="full":return
 if gate is None or not gate.exists():raise SystemExit("FULL_BLOCKED_MISSING_METADATA_PILOT_PASS_BEFORE_SOURCE_OPEN")
 g=json.loads(gate.read_text())
 expected={"code_sha256":code_hash,"config_sha256":config_hash,"manifest_sha256":manifest_hash}
 if g.get("status")!="METADATA_PILOT_PASS" or any(g.get(k)!=v for k,v in expected.items()) or not g.get("required_invariants_passed") or g.get("lineage_verification_status")!="PASS":
  raise SystemExit("FULL_BLOCKED_MISMATCHED_METADATA_PILOT_PASS_BEFORE_SOURCE_OPEN")
def emit_gate(receipt_path,lineage_path,out_path,code_hash,config_hash,manifest_hash):
 r=json.loads(receipt_path.read_text())
 if r.get("status")!="METADATA_20_CANDIDATE_PILOT_COMPLETE" or r.get("candidate_denominator")!=20:
  raise ValueError("pilot receipt not eligible for gate")
 expected={"identity_ambiguity_assessed_before_candidate_filter":True,"open_invalid_link_dates_not_imputed":True,"score_threshold_applied":False,"candidate_denominator_preserved":True,"new_uncapped_analyst_is_unknown":True,"overlap_unknown_outside_exact_existing_view":True,"source_clock_not_rth":True,"protected_rows_local_exported":False}
 if any(r.get("invariants",{}).get(k)!=v for k,v in expected.items()):raise ValueError("required pilot invariant failed")
 lr=json.loads(lineage_path.read_text())
 if lr.get("status")!="PASS" or lr.get("sample_observations_checked",0)<20 or not all(lr.get("assertions",{}).values()):raise ValueError("required lineage verification failed")
 bindings={"code_sha256":code_hash,"config_sha256":config_hash,"manifest_sha256":manifest_hash,"pilot_receipt_sha256":sha(receipt_path)}
 if any(lr.get("bindings",{}).get(k)!=v for k,v in bindings.items()):raise ValueError("lineage verification binding mismatch")
 g={"status":"METADATA_PILOT_PASS","scope":"IMPLEMENTATION_GATE_NOT_RESEARCH_PILOT_PASS","code_sha256":code_hash,"config_sha256":config_hash,"manifest_sha256":manifest_hash,"pilot_receipt_sha256":sha(receipt_path),"lineage_receipt_sha256":sha(lineage_path),"lineage_verification_status":"PASS","required_invariants_passed":True,"required_invariant_expectations":expected}
 out_path.write_text(json.dumps(g,indent=2,sort_keys=True)+"\n")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",choices=["pilot","full","gate"],required=True);ap.add_argument("--candidates",type=Path);ap.add_argument("--old-events",type=Path);ap.add_argument("--overlap",type=Path);ap.add_argument("--config",type=Path,required=True);ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--out",type=Path);ap.add_argument("--gate",type=Path);ap.add_argument("--pilot-receipt",type=Path);ap.add_argument("--lineage-receipt",type=Path);ap.add_argument("--gate-out",type=Path);a=ap.parse_args()
 code_hash=sha(Path(__file__));config_hash=sha(a.config);manifest_hash=sha(a.manifest)
 if a.mode=="gate":emit_gate(a.pilot_receipt,a.lineage_receipt,a.gate_out,code_hash,config_hash,manifest_hash);return
 verify_gate(a.mode,a.gate,code_hash,config_hash,manifest_hash)
 cfg=json.loads(a.config.read_text());man=json.loads(a.manifest.read_text())
 candidate_input_name="pilot_candidates_20.csv" if a.mode=="pilot" else "candidates_v2.csv"
 for name,p in [(candidate_input_name,a.candidates),("old_event_keys_v2.csv",a.old_events),("overlap_flags_v2.csv",a.overlap)]:
  if sha(p)!=man["local_input_hashes"][name]:raise ValueError(f"local input hash mismatch {name}")
 if man["code_hashes"][Path(__file__).name]!=code_hash or man["config_sha256"]!=config_hash:raise ValueError("manifest code/config lineage mismatch")
 meta_path=Path(cfg["source_metadata"]["path"]);link_path=Path(cfg["identity_link_metadata"]["path"])
 if sha(meta_path)!=cfg["source_metadata"]["sha256"] or sha(link_path)!=cfg["identity_link_metadata"]["sha256"]:raise ValueError("remote source hash mismatch")
 cand=pd.read_csv(a.candidates,dtype=str);cand["permno"]=norm_permno(cand.permno);cand["provisional_tier"]=cand.provisional_tier.str.lower()
 expected=20 if a.mode=="pilot" else 2794
 if len(cand)!=expected or cand.candidate_id.nunique()!=expected or cand.duplicated(["wave_id","permno"]).any():raise ValueError("candidate denominator/key failure")
 old=pd.read_csv(a.old_events,dtype=str);old["permno"]=norm_permno(old.permno);old["provisional_tier"]=old.provisional_tier.str.lower();old["analyst_min2"]=to_bool(old.analyst_min2)
 ov=pd.read_csv(a.overlap,dtype=str);ov["permno"]=norm_permno(ov.permno);ov["provisional_tier"]=ov.provisional_tier.str.lower();ov["proposed_overlap_clean"]=to_bool(ov.proposed_overlap_clean)
 link=pd.read_parquet(link_path,columns=ALLOWED_LINK);link["link_path_id"]=[f"LINK_ROW:{i+1}" for i in range(len(link))];link["permno"],link["link_permno_status"]=parse_link_permno(link.permno);link["cusip8"]=link.ncusip.map(norm_cusip);link["link_cusip_status"]=link.cusip8.map(lambda x:"VALID_CUSIP8" if pd.notna(x) else "INVALID_OR_MISSING_CUSIP8_UNKNOWN");link["cusip_join_key"]=[c if pd.notna(c) else f"__INVALID_LINK__{i}" for c,i in zip(link.cusip8,link.link_path_id)];link["sdate_dt"]=pd.to_datetime(link.sdate,errors="coerce");link["edate_dt"]=pd.to_datetime(link.edate,errors="coerce")
 link["link_bound_status"]=[classify_link_bounds(sr,er,sd,ed) for sr,er,sd,ed in zip(link.sdate,link.edate,link.sdate_dt,link.edate_dt)]
 link["score_stratum"]=link.score.fillna("MISSING").astype(str)
 start=pd.Timestamp(cfg["date_bounds"]["announcement_date_lower_inclusive"]);end=pd.Timestamp(cfg["date_bounds"]["announcement_date_upper_exclusive"])
 chunks=[];source_total=0;source_qtr_in_window=0;invalid_source_dates=0
 for ch in pd.read_csv(meta_path,dtype=str,usecols=ALLOWED_META,chunksize=200000):
  ch["source_file_row_number"]=ch.index+2;ch["source_row_id"]=ch.source_partition.fillna("MISSING_PARTITION")+":CSV_ROW:"+ch.source_file_row_number.astype(str);ch["cusip8"]=ch.cusip.map(norm_cusip);ch["source_cusip_status"]=ch.cusip8.map(lambda x:"VALID_CUSIP8" if pd.notna(x) else "INVALID_OR_MISSING_CUSIP8_UNKNOWN");ch["cusip_join_key"]=[c if pd.notna(c) else f"__INVALID_META__{i}" for c,i in zip(ch.cusip8,ch.source_row_id)];ch["anndats_dt"]=pd.to_datetime(ch.anndats,errors="coerce");source_total+=len(ch);invalid_source_dates+=int(ch.anndats_dt.isna().sum());ch=ch[ch.pdicity.eq("QTR") & ch.anndats_dt.ge(start)&ch.anndats_dt.lt(end)];source_qtr_in_window+=len(ch);chunks.append(ch)
 meta=pd.concat(chunks,ignore_index=True)
 paths=meta.merge(link,on="cusip_join_key",how="left",validate="many_to_many",suffixes=("_meta","_link"))
 paths["valid_closed_date_path"]=paths.link_bound_status.eq("CLOSED_VALID_BOUNDS") & paths.anndats_dt.ge(paths.sdate_dt)&paths.anndats_dt.le(paths.edate_dt)
 paths["link_event_status"]=paths.link_bound_status.fillna("NO_LINK_CUSIP")
 closed=paths.link_bound_status.eq("CLOSED_VALID_BOUNDS");paths.loc[closed&paths.valid_closed_date_path,"link_event_status"]="VALID_CLOSED_DATE_PATH";paths.loc[closed&~paths.valid_closed_date_path,"link_event_status"]="OUTSIDE_CLOSED_DATE_PATH"
 unknown_status={"OPEN_START_UNKNOWN","OPEN_END_UNKNOWN","INVALID_START_DATE","INVALID_END_DATE","INVALID_CLOSED_RANGE"}
 sm=[]
 for sid,g in paths.groupby("source_row_id",sort=False):
  valid=g.loc[g.valid_closed_date_path&g.permno.notna(),"permno"].astype(int).tolist();has_unknown=g.link_event_status.isin(unknown_status).any();sm.append((sid,source_mapping_status(valid,has_unknown),len(set(valid))))
 sm=pd.DataFrame(sm,columns=["source_row_id","source_permno_mapping_status","source_valid_permno_count"]);paths=paths.merge(sm,on="source_row_id",validate="many_to_one")
 valid=paths[paths.valid_closed_date_path & paths.permno.isin(cand.permno)].copy();valid["permno"]=valid.permno.astype("int64");mapped=valid.merge(cand,on="permno",how="inner",validate="many_to_many")
 mapped["event_side"]=[classify_event_side(d,pd.to_datetime(c),pd.to_datetime(q)) for d,c,q in zip(mapped.anndats_dt,mapped.announcement_cutoff,mapped.post_20_session_threshold)]
 mapped=mapped.merge(old,on=ANALYST_KEYS,how="left",validate="many_to_one");mapped["analyst_status"]=mapped.analyst_min2.map({True:"EXISTING_EXACT_EVENT_MIN2",False:"EXISTING_EXACT_EVENT_LT2"}).fillna("UNKNOWN_NEW_UNCAPPED_EVENT_KEY")
 mapped=mapped.merge(ov,on=["wave_id","permno","provisional_tier"],how="left",validate="many_to_one");mapped["overlap_status"]=mapped.proposed_overlap_clean.map({True:"PROPOSED_CLEAN_TRUE",False:"PROPOSED_CLEAN_FALSE"}).fillna("UNKNOWN_NOT_IN_EXISTING_V1_8PRE4POST_VIEW")
 mapped["period_key"]=mapped.wave_id+":"+mapped.permno.astype(str)+":"+mapped.pends.fillna("MISSING")
 mapped["public_release_key"]=mapped.wave_id+":"+mapped.permno.astype(str)+":"+mapped.anndats+":"+mapped.anntims.fillna("MISSING")
 mapped["source_candidate_key"]=mapped.source_row_id+":"+mapped.candidate_id
 mapped["exact_path_signature"]=mapped.source_candidate_key+":"+mapped.ncusip.map(lambda x:"MISSING" if pd.isna(x) else str(x))+":"+mapped.sdate.map(lambda x:"MISSING" if pd.isna(x) else str(x))+":"+mapped.edate.map(lambda x:"MISSING" if pd.isna(x) else str(x))+":"+mapped.score_stratum
 mapped["exact_path_duplicate_count"]=mapped.groupby("exact_path_signature")["link_path_id"].transform("size")
 mapped["nominal_0930_1500_source_clock"]=pd.to_datetime(mapped.anntims,format="%H:%M:%S",errors="coerce").dt.time.between(pd.Timestamp("09:30").time(),pd.Timestamp("15:00").time(),inclusive="both")
 candidate_counts=mapped.groupby("candidate_id").agg(valid_link_path_rows=("link_path_id","size"),distinct_source_candidate_paths=("source_candidate_key","nunique"),distinct_period_keys=("period_key","nunique"),distinct_public_release_keys=("public_release_key","nunique"),has_ambiguous_source_row=("source_permno_mapping_status",lambda s:(s=="AMBIGUOUS_VALID_PERMNO").any())).reset_index()
 all_candidate_paths=paths[paths.permno.isin(cand.permno)].copy();all_candidate_paths["permno"]=all_candidate_paths.permno.astype("int64");all_candidate_paths=all_candidate_paths.merge(cand[["candidate_id","permno"]],on="permno",how="inner")
 path_state=all_candidate_paths.groupby("candidate_id").agg(has_link_date_unknown_path=("link_event_status",lambda s:s.isin(unknown_status).any()),has_outside_closed_path=("link_event_status",lambda s:(s=="OUTSIDE_CLOSED_DATE_PATH").any())).reset_index()
 den=cand.merge(candidate_counts,on="candidate_id",how="left",validate="one_to_one").merge(path_state,on="candidate_id",how="left",validate="one_to_one");num=["valid_link_path_rows","distinct_source_candidate_paths","distinct_period_keys","distinct_public_release_keys"];den[num]=den[num].fillna(0).astype(int)
 for z in ["has_ambiguous_source_row","has_link_date_unknown_path","has_outside_closed_path"]:den[z]=den[z].fillna(False).astype(bool)
 den["mapping_status"]="NO_SOURCE_ROW_PATH_FOR_CANDIDATE";den.loc[den.has_outside_closed_path,"mapping_status"]="ONLY_OUTSIDE_CLOSED_DATE_PATH";den.loc[den.has_link_date_unknown_path,"mapping_status"]="LINK_DATE_UNKNOWN_PATH_PRESENT";den.loc[den.valid_link_path_rows.gt(0),"mapping_status"]="HAS_UNIQUE_SOURCE_MAPPING_ROWS";den.loc[den.has_ambiguous_source_row,"mapping_status"]="HAS_AMBIGUOUS_SOURCE_MAPPING_ROW"
 den=den.merge(ov[["wave_id","permno","provisional_tier","proposed_overlap_clean"]],on=["wave_id","permno","provisional_tier"],how="left",validate="many_to_one");den["overlap_status"]=den.proposed_overlap_clean.map({True:"PROPOSED_CLEAN_TRUE",False:"PROPOSED_CLEAN_FALSE"}).fillna("UNKNOWN_NOT_IN_EXISTING_V1_8PRE4POST_VIEW")
 a.out.mkdir(parents=True,exist_ok=False)
 candidate_path_cols=["source_row_id","source_file_row_number","source_partition","source_cusip_status","candidate_id","permno","link_path_id","link_permno_status","link_cusip_status","link_bound_status","link_event_status","score_stratum","source_permno_mapping_status","source_valid_permno_count"]
 all_candidate_paths[candidate_path_cols].to_csv(a.out/"protected_candidate_link_path_status.csv",index=False)
 all_candidate_paths["source_candidate_key"]=all_candidate_paths.source_row_id+":"+all_candidate_paths.candidate_id
 path_status_agg=all_candidate_paths.groupby(["link_event_status","source_permno_mapping_status"],dropna=False).agg(link_path_rows=("link_path_id","size"),distinct_source_row_candidate_ids=("source_candidate_key","nunique"),candidate_ids=("candidate_id","nunique")).reset_index();path_status_agg.to_csv(a.out/"candidate_link_path_status_aggregate.csv",index=False)
 protected_cols=["source_row_id","source_file_row_number","source_partition","source_cusip_status","candidate_id","wave_id","permno","provisional_tier","previous_v1_representation_status","link_path_id","link_permno_status","link_cusip_status","ncusip","sdate","edate","link_bound_status","score_stratum","source_permno_mapping_status","source_valid_permno_count","ticker","cusip","pends","pdicity","anndats","anntims","actdats","acttims","event_side","analyst_status","overlap_status","period_key","public_release_key","source_candidate_key","exact_path_signature","exact_path_duplicate_count","nominal_0930_1500_source_clock"]
 mapped[protected_cols].to_csv(a.out/"protected_metadata_paths.csv",index=False)
 den.to_csv(a.out/"protected_candidate_denominator_status.csv",index=False)
 agg=mapped.groupby(["wave_id","provisional_tier","event_side","source_permno_mapping_status","analyst_status","overlap_status"],dropna=False).agg(link_path_rows=("link_path_id","size"),distinct_source_candidate_paths=("source_candidate_key","nunique"),distinct_exact_path_signatures=("exact_path_signature","nunique"),period_keys=("period_key","nunique"),public_release_keys=("public_release_key","nunique"),candidate_ids=("candidate_id","nunique")).reset_index();agg["exact_duplicate_extra_paths"]=agg.link_path_rows-agg.distinct_exact_path_signatures;agg.to_csv(a.out/"support_by_wave_tier_regime_mapping_analyst.csv",index=False)
 oldsub=old.merge(cand[["wave_id","permno","provisional_tier"]],on=["wave_id","permno","provisional_tier"],how="inner");oldsub["old_key"]=oldsub.astype({"permno":str}).wave_id+":"+oldsub.permno.astype(str)+":"+oldsub.provisional_tier+":"+oldsub.event_side+":"+oldsub.pends+":"+oldsub.anndats;mapped["comparable_key"]=mapped.wave_id+":"+mapped.permno.astype(str)+":"+mapped.provisional_tier+":"+mapped.event_side+":"+mapped.pends+":"+mapped.anndats
 newcomp=mapped[mapped.event_side.isin(["PRE","POST"])]
 oldagg=oldsub.groupby(["wave_id","provisional_tier","event_side"]).old_key.nunique();newagg=newcomp.groupby(["wave_id","provisional_tier","event_side"]).comparable_key.nunique();cmp=pd.concat([oldagg.rename("old_capped_exact_metadata_event_keys"),newagg.rename("uncapped_exact_metadata_event_keys")],axis=1).fillna(0).astype(int).reset_index();cmp["change_keys"]=cmp.uncapped_exact_metadata_event_keys-cmp.old_capped_exact_metadata_event_keys;cmp.to_csv(a.out/"old_cap_vs_uncapped.csv",index=False)
 cov=den.groupby(["wave_id","provisional_tier","previous_v1_representation_status","mapping_status"],dropna=False).agg(candidate_denominator=("candidate_id","nunique"),candidates_with_public_release_key=("distinct_public_release_keys",lambda s:int((s>0).sum())),public_release_keys=("distinct_public_release_keys","sum")).reset_index();cov.to_csv(a.out/"candidate_coverage_status.csv",index=False)
 eligible=newcomp[newcomp.nominal_0930_1500_source_clock & newcomp.analyst_status.eq("EXISTING_EXACT_EVENT_MIN2")];side=eligible.groupby(["wave_id","provisional_tier","permno"]).event_side.agg(lambda s:set(s));both=side.map(lambda s:{"PRE","POST"}.issubset(s)).groupby(level=[0,1]).sum();base=cand.groupby(["wave_id","provisional_tier"]).candidate_id.nunique();nom=pd.concat([base.rename("candidate_denominator"),both.rename("stocks_with_nominal_source_clock_min2_both_pre_post")],axis=1).fillna(0).astype(int).reset_index();nom["clock_interpretation"]="SOURCE_DISPLAY_CLOCK_ONLY_NOT_ET_OR_RTH";nom.to_csv(a.out/"nominal_both_pre_post_stocks.csv",index=False)
 inv={"identity_ambiguity_assessed_before_candidate_filter":True,"open_invalid_link_dates_not_imputed":True,"score_threshold_applied":False,"candidate_denominator_preserved":len(den)==expected,"analyst_exact_key_fields":ANALYST_KEYS,"new_uncapped_analyst_is_unknown":True,"overlap_unknown_outside_exact_existing_view":True,"source_clock_not_rth":True,"protected_rows_local_exported":False}
 rec={"status":"METADATA_20_CANDIDATE_PILOT_COMPLETE" if a.mode=="pilot" else "CORRECTED_UNCAPPED_METADATA_FULL_COMPLETE","mode":a.mode,"candidate_denominator":len(den),"candidate_previous_unrepresented_unknown":int((den.previous_v1_representation_status=="PREVIOUS_V1_UNREPRESENTED_UNKNOWN").sum()),"source_lineage":{"metadata_source_rows":source_total,"quarterly_rows_in_closed_window":source_qtr_in_window,"invalid_announcement_date_rows":invalid_source_dates,"invalid_or_missing_cusip8_rows_in_window":int((meta.source_cusip_status!="VALID_CUSIP8").sum())},"path_units":{"valid_candidate_link_path_rows":len(mapped),"distinct_source_row_candidate_ids":mapped.source_candidate_key.nunique(),"distinct_exact_path_signatures":mapped.exact_path_signature.nunique(),"period_keys":mapped.period_key.nunique(),"public_release_keys":mapped.public_release_key.nunique()},"candidate_link_event_status_counts":all_candidate_paths.link_event_status.value_counts(dropna=False).to_dict(),"mapping_status_counts":den.mapping_status.value_counts().to_dict(),"date_bounds":cfg["date_bounds"],"source_hashes":{"metadata":sha(meta_path),"identity_link":sha(link_path)},"input_hashes":{"candidates":sha(a.candidates),"old_events":sha(a.old_events),"overlap":sha(a.overlap)},"code_sha256":code_hash,"config_sha256":config_hash,"manifest_sha256":manifest_hash,"invariants":inv,"raw_financial_or_response_values_read":False,"quote_native_files_read":False,"purchase":False,"protected_output":"SCC_ONLY","aggregate_hashes":{p.name:sha(p) for p in a.out.glob("*.csv") if not p.name.startswith("protected_")}}
 (a.out/"census_receipt.json").write_text(json.dumps(rec,indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
