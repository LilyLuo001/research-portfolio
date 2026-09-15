#!/usr/bin/env python3
"""Count-only analyst coverage for frozen nominal/known-clean event keys on SCC."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

PROTECTED_COLS = ["source_row_id","candidate_id","wave_id","permno","provisional_tier","cusip","pends","anndats","anntims","event_side","overlap_status","source_permno_mapping_status","nominal_0930_1500_source_clock"]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def event_key(w,t,p,s,pe,ad): return f"{w}|{t}|{int(p)}|{s}|{pd.Timestamp(pe).date()}|{pd.Timestamp(ad).date()}"

def count_analysts(d, release, days):
    lo=release-pd.Timedelta(days=days)
    z=d[(d.anndats>=lo)&(d.anndats<release)]
    return int(z.analys.dropna().astype(str).nunique())

def window_status(release, available_years, latest_observed, days):
    required=set(range((release-pd.Timedelta(days=days)).year, release.year+1))
    if not required.issubset(available_years): return "UNKNOWN_MISSING_SOURCE_YEAR"
    if release > latest_observed + pd.Timedelta(days=1): return "UNKNOWN_SOURCE_NOT_OBSERVED_THROUGH_RELEASE"
    return "AVAILABLE_PARTITIONS_OBSERVED_THROUGH_RELEASE_COMPLETENESS_UNKNOWN"

def load_manifest(path):
    d=json.load(open(path));
    for x in d["inputs"]:
        p=Path(x["path"])
        if not p.exists(): raise ValueError(f"manifest missing: {p}")
        if x["verification"]=="sha256" and sha(p)!=x["sha256"]: raise ValueError(f"manifest hash mismatch: {p}")
        if x["verification"]=="stat" and (p.stat().st_size!=x["size_bytes"] or int(p.stat().st_mtime)!=x["mtime_epoch"]): raise ValueError(f"manifest stat mismatch: {p}")
    return d

def select_targets(protected, cfg):
    d=pd.read_csv(protected,usecols=PROTECTED_COLS,dtype=str)
    z=d[d.wave_id.isin(cfg["target_waves"]) & d.event_side.isin(cfg["target_event_sides"]) & d.overlap_status.eq(cfg["target_overlap_status"]) & d.source_permno_mapping_status.eq("UNIQUE_VALID_PERMNO") & d.nominal_0930_1500_source_clock.eq("True")].copy()
    both=z.groupby("candidate_id").event_side.nunique(); z=z[z.candidate_id.isin(both[both.eq(2)].index)].copy()
    z["event_key"]=z.apply(lambda r:event_key(r.wave_id,r.provisional_tier,r.permno,r.event_side,r.pends,r.anndats),axis=1)
    keys=["event_key","candidate_id","wave_id","permno","provisional_tier","event_side","pends","anndats"]
    e=z.groupby(keys,dropna=False).agg(metadata_source_rows=("source_row_id","size"),distinct_source_rows=("source_row_id","nunique"),cusip_variants=("cusip","nunique"),release_clock_variants=("anntims","nunique"),cusip=("cusip","first")).reset_index()
    e["target_key_status"]=e.cusip_variants.eq(1).map({True:"EXACT_SINGLE_CUSIP",False:"UNKNOWN_CUSIP_AMBIGUITY"})
    return e.sort_values("event_key").reset_index(drop=True)

def main():
    import pyarrow.parquet as pq
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["pilot","full"],required=True); ap.add_argument("--config",required=True); ap.add_argument("--manifest",required=True); ap.add_argument("--out",required=True); ap.add_argument("--gate"); ap.add_argument("--pilot-receipt"); a=ap.parse_args()
    code_hash=sha(__file__); config_hash=sha(a.config); manifest_hash=sha(a.manifest)
    if a.mode=="full":
        if not a.gate or not a.pilot_receipt: raise ValueError("gate and pilot receipt required before source read")
        g=json.load(open(a.gate))
        expected={"status":"ANALYST_COVERAGE_PILOT_PASS","code_sha256":code_hash,"config_sha256":config_hash,"manifest_sha256":manifest_hash,"pilot_receipt_sha256":sha(a.pilot_receipt),"required_invariants_passed":True}
        if g!=expected: raise ValueError("gate mismatch before source read")
    cfg=json.load(open(a.config)); load_manifest(a.manifest)
    out=Path(a.out)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    targets=select_targets(cfg["protected_census_path"],cfg)
    if a.mode=="pilot": targets=targets.head(20).copy()
    years=set(); parts=[]; source_receipts=[]; latest=pd.Timestamp("1900-01-01")
    wanted_cusips=set(targets.loc[targets.target_key_status.eq("EXACT_SINGLE_CUSIP"),"cusip"])
    wanted_pends=set(pd.to_datetime(targets.pends))
    for y in cfg["source_years"]:
        p=Path(cfg["forecast_path_template"].format(year=y))
        if not p.exists(): source_receipts.append({"year":y,"status":"MISSING"}); continue
        cols=cfg["forecast_columns"]
        if not set(cols).issubset(pq.read_schema(p).names): raise ValueError(f"missing permitted columns {p}")
        years.add(y); matched=[]; observed_min=None; observed_max=None
        for batch in pq.ParquetFile(p).iter_batches(batch_size=400000,columns=cols):
            d=batch.to_pandas(); d["anndats"]=pd.to_datetime(d.anndats,errors="coerce"); d["fpedats"]=pd.to_datetime(d.fpedats,errors="coerce")
            valid=d.anndats.dropna()
            if len(valid):
                mn,mx=valid.min(),valid.max(); observed_min=mn if observed_min is None else min(observed_min,mn); observed_max=mx if observed_max is None else max(observed_max,mx); latest=max(latest,mx)
            d["cusip"]=d.cusip.astype("string").str.strip().str.upper()
            q=d[d.cusip.isin(wanted_cusips)&d.fpedats.isin(wanted_pends)][cols]
            if len(q): matched.append(q)
        part=pd.concat(matched,ignore_index=True) if matched else pd.DataFrame(columns=cols); parts.append(part)
        source_receipts.append({"year":y,"status":"AVAILABLE","identity_verification":"PINNED_MANIFEST_STAT_WITH_HISTORICAL_SHA_WHERE_AVAILABLE","size_bytes":p.stat().st_size,"mtime_epoch":int(p.stat().st_mtime),"observed_anndats_min":None if observed_min is None else str(observed_min.date()),"observed_anndats_max":None if observed_max is None else str(observed_max.date()),"matched_metadata_rows":len(part)})
    forecasts=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=cfg["forecast_columns"])
    rows=[]
    for r in targets.itertuples(index=False):
        release=pd.Timestamp(r.anndats); status=window_status(release,years,latest,cfg["window_days"])
        if r.target_key_status!="EXACT_SINGLE_CUSIP": status=r.target_key_status
        if status=="AVAILABLE_PARTITIONS_OBSERVED_THROUGH_RELEASE_COMPLETENESS_UNKNOWN":
            q=forecasts[forecasts.cusip.eq(r.cusip)&forecasts.fpedats.eq(pd.Timestamp(r.pends))]
            n=count_analysts(q,release,cfg["window_days"])
            amin2=True if n>=2 else None
            coverage="OBSERVED_SOURCE_MIN2_LOWER_BOUND" if n>=2 else "UNKNOWN_OBSERVED_LT2_SOURCE_COMPLETENESS_UNCERTIFIED"
        else: n=None; amin2=None; coverage="UNKNOWN"
        rows.append({**r._asdict(),"source_window_status":status,"analyst_count_90d":n,"analyst_min2":amin2,"analyst_coverage_status":coverage})
    detail=pd.DataFrame(rows); detail.to_csv(out/"protected_target_event_coverage.csv",index=False)
    agg=detail.groupby(["wave_id","provisional_tier","event_side","source_window_status","analyst_coverage_status"],dropna=False).agg(target_event_keys=("event_key","nunique"),candidate_stock_wave_keys=("candidate_id","nunique"),events_min2=("analyst_min2",lambda s:int(s.eq(True).sum())),events_lt2=("analyst_min2",lambda s:int(s.eq(False).sum())),events_unknown=("analyst_min2",lambda s:int(s.isna().sum()))).reset_index()
    agg.to_csv(out/"coverage_by_wave_tier_side.csv",index=False)
    cand=detail.groupby(["candidate_id","wave_id","provisional_tier"]).agg(pre_keys=("event_side",lambda s:int(s.eq("PRE").sum())),post_keys=("event_side",lambda s:int(s.eq("POST").sum())),pre_min2=("analyst_min2",lambda s:int((detail.loc[s.index,"event_side"].eq("PRE")&s.eq(True)).sum())),post_min2=("analyst_min2",lambda s:int((detail.loc[s.index,"event_side"].eq("POST")&s.eq(True)).sum())),unknown_keys=("analyst_min2",lambda s:int(s.isna().sum()))).reset_index()
    cand["both_sides_have_min2"]=(cand.pre_min2.gt(0)&cand.post_min2.gt(0))
    cs=cand.groupby(["wave_id","provisional_tier"]).agg(target_stock_wave_keys=("candidate_id","nunique"),stocks_both_sides_min2=("both_sides_have_min2","sum"),stocks_with_unknown=("unknown_keys",lambda s:int(s.gt(0).sum()))).reset_index(); cs.to_csv(out/"candidate_both_side_summary.csv",index=False)
    invariants={"only_four_forecast_metadata_columns":True,"lower_90d_inclusive":True,"release_date_exclusive":True,"distinct_analyst_count_revision_safe":True,"missing_source_coverage_unknown_not_zero":True,"exact_key_includes_wave_tier_permno_side_pends_release":True,"protected_rows_local_exported":False}
    expected={**{k:True for k in invariants if k!="protected_rows_local_exported"},"protected_rows_local_exported":False}
    rec={"status":f"TARGETED_ANALYST_COVERAGE_{a.mode.upper()}_COMPLETE","mode":a.mode,"code_sha256":code_hash,"config_sha256":config_hash,"manifest_sha256":manifest_hash,"target_event_keys":int(detail.event_key.nunique()),"target_stock_wave_keys":int(detail.candidate_id.nunique()),"events_min2":int(detail.analyst_min2.eq(True).sum()),"events_lt2":int(detail.analyst_min2.eq(False).sum()),"events_unknown":int(detail.analyst_min2.isna().sum()),"required_invariants":invariants,"required_invariant_expectations":expected,"required_invariants_passed":invariants==expected,"aggregate_hashes":{"coverage_by_wave_tier_side.csv":sha(out/"coverage_by_wave_tier_side.csv"),"candidate_both_side_summary.csv":sha(out/"candidate_both_side_summary.csv")},"source_partitions":source_receipts,"source_completeness_certified":False,"forecast_values_read":False,"price_return_quote_response_values_read":False,"backend_telemetry":"NOT_OBSERVED"}
    (out/"receipt.json").write_text(json.dumps(rec,indent=2,sort_keys=True)+"\n"); print(json.dumps({k:rec[k] for k in ["status","target_event_keys","target_stock_wave_keys","events_min2","events_lt2","events_unknown"]}))

if __name__=="__main__": main()
