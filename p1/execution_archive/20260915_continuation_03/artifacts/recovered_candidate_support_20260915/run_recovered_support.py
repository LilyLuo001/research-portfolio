#!/usr/bin/env python3
"""CORE-only diagnostic support for the 99 recovered candidates; protected rows remain SCC."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import time
from pathlib import Path
import pandas as pd

RECOVERY_COLS=["source_row_id","candidate_id","wave_id","permno_candidate","provisional_tier","cusip","pends","anndats","anntims","source_mapping_status","event_side","period_key","release_key","source_candidate_key"]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def parse_clock(v):
    try: return time.fromisoformat(str(v).strip())
    except (ValueError,TypeError): return None

def nominal_clock(v):
    t=parse_clock(v)
    return bool(t is not None and time(9,30)<=t<=time(15,0))

def analyst_count(d,release,days):
    lo=release-pd.Timedelta(days=days)
    z=d[(d.anndats>=lo)&(d.anndats<release)]
    return int(z.analys.dropna().astype(str).nunique())

def norm_cusip(s):
    z=s.astype("string").str.strip().str.upper()
    return z.where(z.str.fullmatch(r"[A-Z0-9]{8}",na=False))

def verify_manifest(path):
    m=json.load(open(path))
    for x in m["inputs"]:
        p=Path(x["path"])
        if not p.exists(): raise ValueError(f"missing manifest input {p}")
        if x["verification"]=="stat" and (p.stat().st_size!=x["size_bytes"] or int(p.stat().st_mtime)!=x["mtime_epoch"]): raise ValueError(f"stat mismatch {p}")
        if x["verification"]=="sha256" and sha(p)!=x["sha256"]: raise ValueError(f"hash mismatch {p}")
    return m

def candidate_support(events, candidates):
    rows=[]
    for (wave,tier), universe in candidates.groupby(["wave_id","provisional_tier"]):
        z=events[(events.wave_id==wave)&(events.provisional_tier==tier)]
        def sides(frame): return frame.groupby("candidate_id").event_side.agg(lambda s:set(s))
        allsets=sides(z); nomsets=sides(z[z.nominal_0930_1500_source_clock])
        rows.append({"wave_id":wave,"provisional_tier":tier,"recovered_candidate_stock_wave_keys":universe.candidate_id.nunique(),"all_clock_pre_candidate_keys":z.loc[z.event_side.eq("PRE"),"candidate_id"].nunique(),"all_clock_post_candidate_keys":z.loc[z.event_side.eq("POST"),"candidate_id"].nunique(),"all_clock_both_pre_post_candidate_keys":int(allsets.map(lambda x:{"PRE","POST"}.issubset(x)).sum()),"nominal_source_clock_pre_candidate_keys":z.loc[z.event_side.eq("PRE")&z.nominal_0930_1500_source_clock,"candidate_id"].nunique(),"nominal_source_clock_post_candidate_keys":z.loc[z.event_side.eq("POST")&z.nominal_0930_1500_source_clock,"candidate_id"].nunique(),"nominal_source_clock_both_pre_post_candidate_keys":int(nomsets.map(lambda x:{"PRE","POST"}.issubset(x)).sum())})
    return pd.DataFrame(rows)

def main():
    import pyarrow.parquet as pq
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["pilot","full"],required=True); ap.add_argument("--config",required=True); ap.add_argument("--manifest",required=True); ap.add_argument("--out",required=True); ap.add_argument("--gate"); ap.add_argument("--pilot-receipt"); a=ap.parse_args()
    code_h,config_h,manifest_h=sha(__file__),sha(a.config),sha(a.manifest)
    if a.mode=="full":
        if not a.gate or not a.pilot_receipt: raise ValueError("gate and pilot receipt required before protected/source read")
        expected={"status":"RECOVERED_SUPPORT_PILOT_PASS","code_sha256":code_h,"config_sha256":config_h,"manifest_sha256":manifest_h,"pilot_receipt_sha256":sha(a.pilot_receipt),"required_invariants_passed":True}
        if json.load(open(a.gate))!=expected: raise ValueError("gate mismatch before source read")
    cfg=json.load(open(a.config)); verify_manifest(a.manifest)
    out=Path(a.out)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    p=pd.read_csv(cfg["protected_recovery_paths"],usecols=RECOVERY_COLS,dtype=str)
    core=p[p.source_row_id.str.startswith(cfg["source_family_primary"]+":") & p.event_side.isin(cfg["event_sides"])].copy()
    candidate_flags=core.groupby(["candidate_id","wave_id","provisional_tier"]).source_mapping_status.agg(lambda s:set(s)).reset_index(name="observed_source_mapping_statuses")
    recovered=candidate_flags[candidate_flags.observed_source_mapping_statuses.map(lambda s:"UNIQUE_VALID_PERMNO" in s)].copy()
    recovered["has_nonunique_source_row_status"]=recovered.observed_source_mapping_statuses.map(lambda s:any(x!="UNIQUE_VALID_PERMNO" for x in s))
    if a.mode=="full" and recovered.candidate_id.nunique()!=cfg["expected_recovered_candidates"]: raise ValueError("recovered99 mismatch")
    if a.mode=="pilot": recovered=recovered.sort_values("candidate_id").head(20).copy()
    core=core[core.candidate_id.isin(recovered.candidate_id)&core.source_mapping_status.eq("UNIQUE_VALID_PERMNO")].copy()
    core["permno"]=pd.to_numeric(core.permno_candidate,errors="raise").astype(int)
    core["cusip_norm"]=norm_cusip(core.cusip)
    core["pends_dt"]=pd.to_datetime(core.pends,errors="coerce")
    core["anndats_dt"]=pd.to_datetime(core.anndats,errors="coerce")
    core["clock_parseable"]=core.anntims.map(parse_clock).notna()
    core["nominal_0930_1500_source_clock"]=core.anntims.map(nominal_clock)
    core["analyst_event_key"]=core.wave_id+"|"+core.provisional_tier+"|"+core.permno.astype(str)+"|"+core.event_side+"|"+core.pends_dt.dt.strftime("%Y-%m-%d")+"|"+core.anndats_dt.dt.strftime("%Y-%m-%d")
    keycols=["analyst_event_key","candidate_id","wave_id","provisional_tier","permno","event_side","pends_dt","anndats_dt"]
    events=core.groupby(keycols,dropna=False).agg(source_row_ids=("source_row_id","nunique"),source_candidate_paths=("source_candidate_key","nunique"),period_keys=("period_key","nunique"),release_keys=("release_key","nunique"),cusip_variants=("cusip_norm","nunique"),cusip_norm=("cusip_norm","first"),parseable_clock_variants=("clock_parseable","sum"),nominal_0930_1500_source_clock=("nominal_0930_1500_source_clock","max")).reset_index()
    events["conversion_status"]="UNIQUE_VALID_PERMNO_SOURCE_ROW"
    events["analyst_join_status"]=events.cusip_variants.eq(1).map({True:"EXACT_SINGLE_CUSIP8",False:"UNKNOWN_CUSIP_VARIANTS"})
    support=candidate_support(events,recovered)
    if a.mode=="full" and support.all_clock_both_pre_post_candidate_keys.sum()!=cfg["expected_all_clock_both_side_candidates"]: raise ValueError("expected 27 all-clock both-side candidates")
    keyagg=core.groupby(["wave_id","provisional_tier","event_side"]).agg(source_path_rows=("source_row_id","size"),distinct_source_rows=("source_row_id","nunique"),distinct_source_row_candidate_keys=("source_candidate_key","nunique"),distinct_period_keys=("period_key","nunique"),distinct_release_keys=("release_key","nunique"),distinct_analyst_event_keys=("analyst_event_key","nunique"),candidate_stock_wave_keys=("candidate_id","nunique"),parseable_source_clock_release_keys=("release_key",lambda s:s[core.loc[s.index,"clock_parseable"]].nunique()),nominal_source_clock_release_keys=("release_key",lambda s:s[core.loc[s.index,"nominal_0930_1500_source_clock"]].nunique())).reset_index()
    source_parts=[]; available=set(); latest=pd.Timestamp("1900-01-01"); source_receipts=[]
    wanted_cusips=set(events.loc[events.analyst_join_status.eq("EXACT_SINGLE_CUSIP8"),"cusip_norm"]); wanted_pends=set(events.pends_dt)
    for y in cfg["forecast_years"]:
        fp=Path(cfg["forecast_path_template"].format(year=y))
        if not fp.exists(): source_receipts.append({"year":y,"status":"MISSING"}); continue
        if not set(cfg["forecast_columns"]).issubset(pq.read_schema(fp).names): raise ValueError(f"missing allowed columns {fp}")
        available.add(y); matched=[]; observed_max=None
        for batch in pq.ParquetFile(fp).iter_batches(batch_size=400000,columns=cfg["forecast_columns"]):
            d=batch.to_pandas(); d["anndats"]=pd.to_datetime(d.anndats,errors="coerce"); d["fpedats"]=pd.to_datetime(d.fpedats,errors="coerce"); d["cusip_norm"]=norm_cusip(d.cusip)
            valid=d.anndats.dropna()
            if len(valid): observed_max=valid.max() if observed_max is None else max(observed_max,valid.max()); latest=max(latest,valid.max())
            q=d[d.cusip_norm.isin(wanted_cusips)&d.fpedats.isin(wanted_pends)][["cusip_norm","fpedats","analys","anndats"]]
            if len(q): matched.append(q)
        part=pd.concat(matched,ignore_index=True) if matched else pd.DataFrame(columns=["cusip_norm","fpedats","analys","anndats"]); source_parts.append(part)
        source_receipts.append({"year":y,"status":"AVAILABLE_PARTITION_COMPLETENESS_UNKNOWN","size_bytes":fp.stat().st_size,"mtime_epoch":int(fp.stat().st_mtime),"observed_anndats_max":None if observed_max is None else str(observed_max.date()),"matched_metadata_rows":len(part)})
    forecasts=pd.concat(source_parts,ignore_index=True) if source_parts else pd.DataFrame(columns=["cusip_norm","fpedats","analys","anndats"])
    rows=[]
    for r in events.itertuples(index=False):
        required=set(range((r.anndats_dt-pd.Timedelta(days=cfg["analyst_window_days"])).year,r.anndats_dt.year+1))
        if r.analyst_join_status!="EXACT_SINGLE_CUSIP8": status=r.analyst_join_status; n=None
        elif not required.issubset(available): status="UNKNOWN_MISSING_SOURCE_YEAR"; n=None
        elif r.anndats_dt>latest+pd.Timedelta(days=1): status="UNKNOWN_SOURCE_NOT_OBSERVED_THROUGH_RELEASE"; n=None
        else:
            q=forecasts[forecasts.cusip_norm.eq(r.cusip_norm)&forecasts.fpedats.eq(r.pends_dt)]
            n=analyst_count(q,r.anndats_dt,cfg["analyst_window_days"]); status="OBSERVED_SOURCE_MIN2_LOWER_BOUND" if n>=2 else "UNKNOWN_OBSERVED_LT2_SOURCE_COMPLETENESS_UNCERTIFIED"
        rows.append({**r._asdict(),"analyst_count_90d":n,"analyst_coverage_status":status,"observed_source_min2":True if n is not None and n>=2 else pd.NA})
    detail=pd.DataFrame(rows)
    detail.to_csv(out/"protected_recovered99_event_sidecar.csv",index=False)
    cov=detail.groupby(["wave_id","provisional_tier","event_side","nominal_0930_1500_source_clock","analyst_coverage_status"],dropna=False).agg(exact_analyst_event_keys=("analyst_event_key","nunique"),candidate_stock_wave_keys=("candidate_id","nunique"),observed_source_min2_event_keys=("observed_source_min2",lambda s:int(s.eq(True).sum())),unknown_event_keys=("observed_source_min2",lambda s:int(s.isna().sum()))).reset_index()
    crows=[]
    for (wave,tier), g in detail.groupby(["wave_id","provisional_tier"]):
        base=recovered[(recovered.wave_id==wave)&(recovered.provisional_tier==tier)]
        def both(frame):
            x=frame.groupby("candidate_id").event_side.agg(lambda s:set(s)); return int(x.map(lambda s:{"PRE","POST"}.issubset(s)).sum())
        amin=g[g.observed_source_min2.eq(True)]
        crows.append({"wave_id":wave,"provisional_tier":tier,"recovered_candidate_stock_wave_keys":base.candidate_id.nunique(),"all_clock_both_pre_post_candidate_keys":both(g),"all_clock_observed_min2_both_pre_post_candidate_keys":both(amin),"nominal_source_clock_both_pre_post_candidate_keys":both(g[g.nominal_0930_1500_source_clock]),"nominal_source_clock_observed_min2_both_pre_post_candidate_keys":both(amin[amin.nominal_0930_1500_source_clock]),"candidate_keys_with_any_unknown_analyst_event":g.groupby("candidate_id").observed_source_min2.apply(lambda s:s.isna().any()).sum()})
    analyst_candidate=pd.DataFrame(crows)
    keyagg.to_csv(out/"source_key_support_by_wave_tier_side.csv",index=False); support.to_csv(out/"candidate_clock_support_by_wave_tier.csv",index=False); cov.to_csv(out/"analyst_coverage_by_wave_tier_side_clock.csv",index=False); analyst_candidate.to_csv(out/"candidate_analyst_support_by_wave_tier.csv",index=False)
    mapping=recovered.groupby(["wave_id","provisional_tier","has_nonunique_source_row_status"]).candidate_id.nunique().rename("candidate_stock_wave_keys").reset_index(); mapping.to_csv(out/"candidate_conversion_status_aggregate.csv",index=False)
    inv={"core_only_primary_not_pooled":True,"rescue_comparison_not_read_as_primary":True,"exact_recovered_candidate_count":a.mode!="full" or recovered.candidate_id.nunique()==99,"all_clock_before_analyst_reported":True,"unknown_conversion_status_retained":True,"clock_timezone_or_rth_certified":False,"analyst_exact_release_inclusive_key":True,"analyst_90d_lower_inclusive_release_exclusive":True,"source_completeness_certified":False,"financial_values_read":False,"protected_rows_local_exported":False}
    expected={**{k:True for k in inv if k not in ["clock_timezone_or_rth_certified","source_completeness_certified","financial_values_read","protected_rows_local_exported"]},"clock_timezone_or_rth_certified":False,"source_completeness_certified":False,"financial_values_read":False,"protected_rows_local_exported":False}
    files=["source_key_support_by_wave_tier_side.csv","candidate_clock_support_by_wave_tier.csv","analyst_coverage_by_wave_tier_side_clock.csv","candidate_analyst_support_by_wave_tier.csv","candidate_conversion_status_aggregate.csv"]
    receipt={"status":f"RECOVERED_CANDIDATE_SUPPORT_{a.mode.upper()}_COMPLETE","mode":a.mode,"code_sha256":code_h,"config_sha256":config_h,"manifest_sha256":manifest_h,"source_primary":cfg["source_family_primary"],"source_comparison_not_pooled":cfg["source_family_comparison"],"recovered_candidate_stock_wave_keys":int(recovered.candidate_id.nunique()),"source_path_rows":len(core),"distinct_source_rows":int(core.source_row_id.nunique()),"distinct_source_row_candidate_keys":int(core.source_candidate_key.nunique()),"distinct_period_keys":int(core.period_key.nunique()),"distinct_release_keys":int(core.release_key.nunique()),"distinct_analyst_event_keys":int(events.analyst_event_key.nunique()),"all_clock_both_pre_post_candidate_keys":int(support.all_clock_both_pre_post_candidate_keys.sum()),"nominal_clock_both_pre_post_candidate_keys":int(support.nominal_source_clock_both_pre_post_candidate_keys.sum()),"observed_min2_event_keys":int(detail.observed_source_min2.eq(True).sum()),"unknown_analyst_event_keys":int(detail.observed_source_min2.isna().sum()),"required_invariants":inv,"required_invariant_expectations":expected,"required_invariants_passed":inv==expected,"aggregate_hashes":{f:sha(out/f) for f in files},"forecast_source_partitions":source_receipts,"source_clock_interpretation":cfg["source_clock_interpretation"],"source_completeness_certified":False,"financial_forecast_price_return_response_values_read":False,"backend_telemetry":"NOT_OBSERVED"}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:receipt[k] for k in ["status","recovered_candidate_stock_wave_keys","distinct_release_keys","distinct_analyst_event_keys","all_clock_both_pre_post_candidate_keys","nominal_clock_both_pre_post_candidate_keys","observed_min2_event_keys","unknown_analyst_event_keys","required_invariants_passed"]}))

if __name__=="__main__": main()
