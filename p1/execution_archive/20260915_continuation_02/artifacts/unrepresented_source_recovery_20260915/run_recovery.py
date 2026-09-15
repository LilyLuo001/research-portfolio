#!/usr/bin/env python3
"""Metadata-only recovery check for the fixed 202 previously-unrepresented candidates."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def norm_cusip(s):
    z=s.astype("string").str.strip().str.upper()
    return z.where(z.str.fullmatch(r"[A-Z0-9]{8}",na=False))

def event_side(d, cutoff, post):
    return pd.Series(pd.NA,index=d.index,dtype="string").mask(d<cutoff,"PRE").mask(d>=post,"POST").fillna("TRANSITION")

def distinct_pair_count(d,a,b): return int(d[[a,b]].drop_duplicates().shape[0])

def load_manifest(path):
    m=json.load(open(path))
    for x in m["inputs"]:
        p=Path(x["path"])
        if not p.exists(): raise ValueError(f"manifest missing {p}")
        if x["verification"]=="sha256" and sha(p)!=x["sha256"]: raise ValueError(f"hash mismatch {p}")
        if x["verification"]=="stat" and (p.stat().st_size!=x["size_bytes"] or int(p.stat().st_mtime)!=x["mtime_epoch"]): raise ValueError(f"stat mismatch {p}")
    return m

def read_candidates(path,cfg,mode):
    use=["candidate_id","wave_id","permno","provisional_tier","announcement_cutoff","post_20_session_threshold","previous_v1_representation_status"]
    c=pd.read_csv(path,usecols=use,dtype=str); c["permno"]=pd.to_numeric(c.permno,errors="raise").astype(int)
    if len(c)!=2794 or c.candidate_id.nunique()!=2794: raise ValueError("fixed 2794 universe mismatch")
    u=c[c.previous_v1_representation_status.eq("PREVIOUS_V1_UNREPRESENTED_UNKNOWN")].copy()
    got=(u.groupby(["wave_id","provisional_tier"]).size().rename_axis(["w","t"]).to_dict())
    exp={tuple(k.split("|")):v for k,v in cfg["expected_unrepresented_breakdown"].items()}
    if len(u)!=202 or got!=exp: raise ValueError("fixed 202 subset mismatch")
    if mode=="full": return u
    p=pd.concat([u.sort_values("candidate_id").head(10),c[c.previous_v1_representation_status.eq("PREVIOUS_V1_REPRESENTED")].sort_values("candidate_id").head(10)]).reset_index(drop=True)
    if len(p)!=20 or p.candidate_id.nunique()!=20: raise ValueError("pilot must contain 20 distinct candidates")
    return p

def map_family(frames,links,candidates,family):
    s=pd.concat(frames,ignore_index=True); s["cusip_norm"]=norm_cusip(s.cusip); s["anndats_dt"]=pd.to_datetime(s.anndats,errors="coerce"); s["pends_dt"]=pd.to_datetime(s.pends,errors="coerce")
    s["source_row_id"]=family+":"+s.source_partition+":"+s.source_partition_row.astype(str)
    # Invalid/missing CUSIP8 never joins (pandas otherwise matches NA to NA).
    m=s[s.cusip_norm.notna()].merge(links[links.ncusip_norm.notna()],left_on="cusip_norm",right_on="ncusip_norm",how="left",suffixes=("","_link"))
    m["closed_date_path"]=m.sdate_dt.notna()&m.edate_dt.notna()&m.anndats_dt.ge(m.sdate_dt)&m.anndats_dt.le(m.edate_dt)&m.permno_link.notna()
    m["unknown_link_path"]=m.sdate_dt.isna()|m.edate_dt.isna()|m.permno_link.isna()
    counts=m[m.closed_date_path].groupby("source_row_id").permno_link.nunique()
    unknown=m.groupby("source_row_id").unknown_link_path.any()
    s["valid_permno_count"]=s.source_row_id.map(counts).fillna(0).astype(int)
    s["has_unknown_link_path"]=s.source_row_id.map(unknown).fillna(False).astype(bool)
    s["source_mapping_status"]=s.apply(lambda r:"UNKNOWN_LINK_PATH_PRESENT" if r.has_unknown_link_path else ("UNIQUE_VALID_PERMNO" if r.valid_permno_count==1 else ("AMBIGUOUS_VALID_PERMNOS" if r.valid_permno_count>1 else "NO_CLOSED_VALID_PERMNO")),axis=1)
    paths=m[m.closed_date_path].merge(candidates,left_on="permno_link",right_on="permno",how="inner",suffixes=("","_candidate"))
    paths=paths.merge(s[["source_row_id","source_mapping_status"]],on="source_row_id",how="left")
    paths["event_side"]=event_side(paths.anndats_dt,pd.to_datetime(paths.announcement_cutoff),pd.to_datetime(paths.post_20_session_threshold))
    paths["period_key"]=paths.wave_id+"|"+paths.permno.astype(str)+"|"+paths.pends.astype(str)
    paths["release_key"]=paths.wave_id+"|"+paths.permno.astype(str)+"|"+paths.anndats.astype(str)+"|"+paths.anntims.astype(str)
    paths["source_candidate_key"]=paths.source_row_id+"|"+paths.candidate_id
    return s,paths

def main():
    import pyarrow.parquet as pq
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["pilot","full"],required=True); ap.add_argument("--config",required=True); ap.add_argument("--manifest",required=True); ap.add_argument("--out",required=True); ap.add_argument("--gate"); ap.add_argument("--pilot-receipt"); ap.add_argument("--lineage-receipt"); a=ap.parse_args()
    code_h,config_h,manifest_h=sha(__file__),sha(a.config),sha(a.manifest)
    if a.mode=="full":
        if not a.gate or not a.pilot_receipt or not a.lineage_receipt: raise ValueError("gate and pilot/lineage receipts required before source read")
        lineage=json.load(open(a.lineage_receipt))
        if lineage.get("status")!="PASS" or lineage.get("observations_checked")!=20: raise ValueError("lineage receipt failed")
        expected={"status":"SOURCE_RECOVERY_PILOT_PASS","code_sha256":code_h,"config_sha256":config_h,"manifest_sha256":manifest_h,"pilot_receipt_sha256":sha(a.pilot_receipt),"lineage_receipt_sha256":sha(a.lineage_receipt),"required_invariants_passed":True}
        if json.load(open(a.gate))!=expected: raise ValueError("gate mismatch before source read")
    cfg=json.load(open(a.config)); load_manifest(a.manifest); c=read_candidates(cfg["candidate_path"],cfg,a.mode)
    out=Path(a.out)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    l=pd.read_parquet(cfg["link_path"],columns=cfg["allowed_link_columns"]); l["ncusip_norm"]=norm_cusip(l.ncusip); l["permno_link"]=pd.to_numeric(l.permno,errors="coerce"); l.loc[l.permno_link.mod(1).ne(0),"permno_link"]=pd.NA; l["sdate_dt"]=pd.to_datetime(l.sdate,errors="coerce"); l["edate_dt"]=pd.to_datetime(l.edate,errors="coerce")
    family_status=[]; support=[]; record_sets={}; protected=[]; source_stats=[]
    for family,tmpl in cfg["families"].items():
        frames=[]
        for y in cfg["years"]:
            p=Path(tmpl.format(year=y)); missing=set(cfg["allowed_actual_columns"])-set(pq.read_schema(p).names)
            if missing: raise ValueError(f"missing allowed columns {p}: {sorted(missing)}")
            d=pd.read_parquet(p,columns=cfg["allowed_actual_columns"]); d["source_partition"]=p.name; d["source_partition_row"]=range(1,len(d)+1); frames.append(d)
            source_stats.append({"family":family,"year":y,"source_rows":len(d),"size_bytes":p.stat().st_size})
        s=pd.concat(frames,ignore_index=True); dates=pd.to_datetime(s.anndats,errors="coerce"); s=s[dates.ge(cfg["date_lower_inclusive"])&dates.lt(cfg["date_upper_exclusive"])&s.pdicity.astype(str).str.upper().eq("QTR")].copy()
        mapped,paths=map_family([s],l,c,family); protected.append(paths)
        valid=paths[paths.source_mapping_status.eq("UNIQUE_VALID_PERMNO")]
        uncertain=paths[paths.source_mapping_status.isin(["AMBIGUOUS_VALID_PERMNOS","UNKNOWN_LINK_PATH_PRESENT"])]
        vc=valid.groupby("candidate_id").source_row_id.nunique(); uc=uncertain.groupby("candidate_id").source_row_id.nunique()
        x=c[["candidate_id","wave_id","provisional_tier","previous_v1_representation_status"]].copy(); x["family"]=family; x["unique_source_rows"]=x.candidate_id.map(vc).fillna(0).astype(int); x["uncertain_source_rows"]=x.candidate_id.map(uc).fillna(0).astype(int)
        x["family_recovery_status"]=x.apply(lambda r:"RECOVERED_UNIQUE_SOURCE_MAPPING" if r.unique_source_rows else ("UNCERTAIN_LINK_PATH_ONLY_NOT_RECOVERED" if r.uncertain_source_rows else "NO_MATCH_IN_CHECKED_SCC_FAMILY"),axis=1); family_status.append(x)
        q=valid.groupby(["wave_id","provisional_tier","event_side"],dropna=False).agg(link_path_rows=("source_row_id","size"),distinct_source_row_candidate_ids=("source_candidate_key","nunique"),period_keys=("period_key","nunique"),release_keys=("release_key","nunique"),candidate_ids=("candidate_id","nunique")).reset_index(); q["family"]=family; support.append(q)
        keycols=["ticker","cusip","pends","pdicity","anndats","anntims","actdats","acttims"]
        record_sets[family]=set(mapped[keycols].astype("string").fillna("<NA>").agg("|".join,axis=1))
    fs=pd.concat(family_status,ignore_index=True); fs.to_csv(out/"protected_candidate_family_status.csv",index=False); pd.concat(protected,ignore_index=True).to_csv(out/"protected_source_candidate_paths.csv",index=False)
    agg=fs.groupby(["wave_id","provisional_tier","previous_v1_representation_status","family","family_recovery_status"]).agg(candidate_denominator=("candidate_id","nunique"),unique_source_rows=("unique_source_rows","sum"),uncertain_source_rows=("uncertain_source_rows","sum")).reset_index(); agg.to_csv(out/"recovery_by_wave_tier_family.csv",index=False)
    sup=pd.concat(support,ignore_index=True); sup.to_csv(out/"support_by_wave_tier_family_side.csv",index=False)
    wide=fs.pivot(index=["candidate_id","wave_id","provisional_tier","previous_v1_representation_status"],columns="family",values="family_recovery_status").reset_index(); fams=list(cfg["families"]); wide["source_overlap_status"]=wide.apply(lambda r:("RECOVERED_BOTH_FAMILIES" if all(r[f]=="RECOVERED_UNIQUE_SOURCE_MAPPING" for f in fams) else ("RECOVERED_CORE_ONLY" if r[fams[0]]=="RECOVERED_UNIQUE_SOURCE_MAPPING" else ("RECOVERED_RESCUE_ONLY" if r[fams[1]]=="RECOVERED_UNIQUE_SOURCE_MAPPING" else "NOT_RECOVERED_UNIQUELY_IN_EITHER_CHECKED_FAMILY"))),axis=1); wide.to_csv(out/"protected_candidate_source_overlap.csv",index=False)
    ov=wide.groupby(["wave_id","provisional_tier","previous_v1_representation_status","source_overlap_status"]).candidate_id.nunique().rename("candidate_denominator").reset_index(); ov.to_csv(out/"candidate_source_overlap_aggregate.csv",index=False)
    f0,f1=fams; rs=pd.DataFrame([{"denominator_scope":"FULL_QTR_ARCHIVE_ROWS_IN_DATE_WINDOW_NOT_202_TARGET","core_distinct_metadata_rows":len(record_sets[f0]),"rescue_distinct_metadata_rows":len(record_sets[f1]),"intersection_distinct_metadata_rows":len(record_sets[f0]&record_sets[f1]),"core_only_distinct_metadata_rows":len(record_sets[f0]-record_sets[f1]),"rescue_only_distinct_metadata_rows":len(record_sets[f1]-record_sets[f0])}]); rs.to_csv(out/"full_archive_qtr_source_family_record_overlap.csv",index=False)
    pd.DataFrame(source_stats).to_csv(out/"source_partition_counts.csv",index=False)
    invariants={"candidate_universe_2794_verified_before_subset":True,"full_subset_exact_202":a.mode!="full" or len(c)==202,"ambiguity_assessed_all_links_before_candidate_filter":True,"score_threshold_applied":False,"actual_value_column_read":False,"families_pooled":False,"no_match_labeled_global_vendor_absence":False,"protected_rows_local_exported":False}
    expected={"candidate_universe_2794_verified_before_subset":True,"full_subset_exact_202":True,"ambiguity_assessed_all_links_before_candidate_filter":True,"score_threshold_applied":False,"actual_value_column_read":False,"families_pooled":False,"no_match_labeled_global_vendor_absence":False,"protected_rows_local_exported":False}
    hashes={f:sha(out/f) for f in ["recovery_by_wave_tier_family.csv","support_by_wave_tier_family_side.csv","candidate_source_overlap_aggregate.csv","full_archive_qtr_source_family_record_overlap.csv","source_partition_counts.csv"]}
    rec={"status":f"UNREPRESENTED_SOURCE_RECOVERY_{a.mode.upper()}_COMPLETE","mode":a.mode,"code_sha256":code_h,"config_sha256":config_h,"manifest_sha256":manifest_h,"candidate_denominator":len(c),"unrepresented_candidates":int(c.previous_v1_representation_status.eq("PREVIOUS_V1_UNREPRESENTED_UNKNOWN").sum()),"positive_control_candidates":int(c.previous_v1_representation_status.eq("PREVIOUS_V1_REPRESENTED").sum()),"aggregate_hashes":hashes,"required_invariants":invariants,"required_invariant_expectations":expected,"required_invariants_passed":invariants==expected,"source_record_overlap_scope":"FULL_QTR_ARCHIVE_ROWS_IN_DATE_WINDOW_NOT_202_TARGET","source_families_kept_separate":True,"actual_eps_or_financial_values_read":False,"backend_telemetry":"NOT_OBSERVED"}; (out/"receipt.json").write_text(json.dumps(rec,indent=2,sort_keys=True)+"\n"); print(json.dumps({k:rec[k] for k in ["status","candidate_denominator","unrepresented_candidates","positive_control_candidates","required_invariants_passed"]}))

if __name__=="__main__": main()
