#!/usr/bin/env python3
"""Build exact, metadata-only local inputs and manifest for census v2."""
import hashlib, json
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
MD=ROOT.parent/"missing_data_round_20260914"
CFG=HERE/"census_config.json"
SOURCES={
 "candidates_original":(ROOT/"local_inputs/candidates.csv","64a0bbbeb9d7ca288b4a9438b52adca25a6a0018a5cd1d4acac1020e929f6d6e"),
 "tier_universe":(MD/"PREANNOUNCEMENT_EXPOSURE_PROVISIONAL_TIERS.csv","9f31091f3b7ea9ecbaba39c8c43b64e76713227e361552c9ca6bc52a895fa35e"),
 "v1_representation":(MD/"EARNINGS_METADATA_ELIGIBILITY.csv","cc7a7f32913f5a0ef72eab30bb69ea714a2c2d882d20b248ebf39ed42b10cf5b"),
 "old_analyst_events":(MD/"full_pool_analyst_coverage/event_analyst_coverage.csv","95c720b62390e513742fc85bbb464712c75b98c3e1a5763c43ae1b64f1fd29e3"),
 "overlap_flags":(MD/"clean_acquisition/full_supported_pool_with_overlap_flag.csv","be9b710a2a2ab3ccf1e84534d6fb96e1885c3522119116d2a29b61c0fa930ba4"),
 "scope_review":(ROOT.parent/"pilot_design_build_20260915/INDEPENDENT_BUILD_REVIEW.md","319cef2db5264831abf7de65bd634fb17734ebc0f9383d5c9fa24c45546f1018"),
}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def permno(s):
 x=pd.to_numeric(s,errors="raise");
 if x.isna().any() or ((x%1)!=0).any(): raise ValueError("non-finite/non-integral PERMNO")
 return x.astype("int64")
def b(s):
 if s.dtype==bool:return s
 z=s.astype(str).str.lower().map({"true":True,"false":False})
 if z.isna().any():raise ValueError("invalid boolean")
 return z
def rr(df,n):
 parts=[g.sort_values("candidate_id") for _,g in df.groupby(["wave_id","provisional_tier"],sort=True)]
 out=[];i=0
 while len(out)<n:
  progressed=False
  for g in parts:
   if i<len(g) and len(out)<n: out.append(g.iloc[i]); progressed=True
  if not progressed:break
  i+=1
 return pd.DataFrame(out)
def main():
 for name,(p,e) in SOURCES.items():
  if sha(p)!=e:raise ValueError(f"hash mismatch {name}")
 cfg=json.loads(CFG.read_text())
 c=pd.read_csv(SOURCES["candidates_original"][0],dtype=str,usecols=["candidate_id","wave_id","permno","provisional_tier","announcement_cutoff","post_20_session_threshold"])
 c["permno"]=permno(c.permno); c["provisional_tier"]=c.provisional_tier.str.lower()
 u=pd.read_csv(SOURCES["tier_universe"][0],dtype=str,usecols=["wave_id","permno","provisional_tier"]);u["permno"]=permno(u.permno);u["provisional_tier"]=u.provisional_tier.str.lower();u=u[u.provisional_tier.isin(["high","low"])]
 if len(c)!=2794 or len(u)!=2794 or c.duplicated(["wave_id","permno"]).any() or u.duplicated(["wave_id","permno"]).any():raise ValueError("candidate universe shape")
 ck=set(zip(c.wave_id,c.permno,c.provisional_tier));uk=set(zip(u.wave_id,u.permno,u.provisional_tier))
 if ck!=uk:raise ValueError("candidate keys do not exactly match pinned H/L tier universe")
 v=pd.read_csv(SOURCES["v1_representation"][0],dtype=str,usecols=["wave_id","permno"]);v["permno"]=permno(v.permno)
 vk=set(zip(v.wave_id,v.permno)); c["previous_v1_representation_status"]=["PREVIOUS_V1_REPRESENTED" if (w,p) in vk else "PREVIOUS_V1_UNREPRESENTED_UNKNOWN" for w,p in zip(c.wave_id,c.permno)]
 for w,vals in cfg["wave_cutoffs"].items():
  m=c.wave_id.eq(w); c.loc[m,"announcement_cutoff"]=vals["announcement_cutoff"];c.loc[m,"post_20_session_threshold"]=vals["post_20_session_threshold"]
 c["threshold_source_status"]=[cfg["wave_cutoffs"][w]["threshold_source_status"] for w in c.wave_id]
 cols=["candidate_id","wave_id","permno","provisional_tier","announcement_cutoff","post_20_session_threshold","threshold_source_status","previous_v1_representation_status"]
 out=HERE/"local_inputs";out.mkdir(exist_ok=True)
 c.sort_values("candidate_id")[cols].to_csv(out/"candidates_v2.csv",index=False,lineterminator="\n")
 old=pd.read_csv(SOURCES["old_analyst_events"][0],dtype=str,usecols=["wave_id","permno","provisional_tier","event_side","pends","anndats","analyst_min2"]);old["permno"]=permno(old.permno);old["provisional_tier"]=old.provisional_tier.str.lower();old["analyst_min2"]=b(old.analyst_min2)
 keys=["wave_id","permno","provisional_tier","event_side","pends","anndats"]
 conflict=old.groupby(keys,dropna=False).analyst_min2.nunique()
 if (conflict>1).any():raise ValueError("conflicting old analyst flags")
 old=old.drop_duplicates(keys).sort_values(keys);old.to_csv(out/"old_event_keys_v2.csv",index=False,lineterminator="\n")
 ov=pd.read_csv(SOURCES["overlap_flags"][0],dtype=str,usecols=["wave_id","permno","provisional_tier","proposed_overlap_clean"]);ov["permno"]=permno(ov.permno);ov["provisional_tier"]=ov.provisional_tier.str.lower();ov["proposed_overlap_clean"]=b(ov.proposed_overlap_clean)
 if len(ov)!=2088 or ov.duplicated(["wave_id","permno","provisional_tier"]).any():raise ValueError("overlap key shape")
 ov.sort_values(["wave_id","permno"]).to_csv(out/"overlap_flags_v2.csv",index=False,lineterminator="\n")
 absent=c[c.previous_v1_representation_status.eq("PREVIOUS_V1_UNREPRESENTED_UNKNOWN")];represented=c[c.previous_v1_representation_status.eq("PREVIOUS_V1_REPRESENTED")]
 pilot=pd.concat([rr(absent,10),rr(represented,10)],ignore_index=True).sort_values("candidate_id")
 if len(pilot)!=20 or pilot.candidate_id.nunique()!=20:raise ValueError("pilot selection")
 pilot[cols].to_csv(out/"pilot_candidates_20.csv",index=False,lineterminator="\n")
 files={"candidates_v2.csv":out/"candidates_v2.csv","old_event_keys_v2.csv":out/"old_event_keys_v2.csv","overlap_flags_v2.csv":out/"overlap_flags_v2.csv","pilot_candidates_20.csv":out/"pilot_candidates_20.csv"}
 manifest={"status":"CORRECTED_V2_INPUT_MANIFEST","candidate_keyset_exact_match_pinned_HL_2794":True,"candidate_count":2794,"previous_v1_represented":int((c.previous_v1_representation_status=="PREVIOUS_V1_REPRESENTED").sum()),"previous_v1_unrepresented_unknown":int((c.previous_v1_representation_status=="PREVIOUS_V1_UNREPRESENTED_UNKNOWN").sum()),"source_hashes":{k:e for k,(p,e) in SOURCES.items()},"remote_source_hashes":{"metadata":cfg["source_metadata"]["sha256"],"identity_link":cfg["identity_link_metadata"]["sha256"]},"local_input_hashes":{k:sha(p) for k,p in files.items()},"local_input_allowed_columns":{"candidates_v2.csv":cols,"pilot_candidates_20.csv":cols,"old_event_keys_v2.csv":keys+["analyst_min2"],"overlap_flags_v2.csv":["wave_id","permno","provisional_tier","proposed_overlap_clean"]},"code_hashes":{p.name:sha(p) for p in [HERE/"prepare_local_inputs.py",HERE/"run_uncapped_census_v2.py",HERE/"test_census_semantics.py",HERE/"verify_pilot_lineage.py"]},"config_sha256":sha(CFG),"date_bounds":cfg["date_bounds"],"authority":cfg["authority"]}
 (HERE/"input_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"candidates":2794,"previous_unrepresented_unknown":202,"pilot_candidates":20,"manifest":str(HERE/"input_manifest.json")},sort_keys=True))
if __name__=="__main__":main()
