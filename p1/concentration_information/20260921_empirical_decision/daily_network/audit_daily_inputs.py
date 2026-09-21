#!/usr/bin/env python3
"""Aggregate adjacency and date-valid class coverage audit; no return values read."""
import argparse, json
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,required=True); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); root=a.root; out=a.out; private=out/"private"
    roster=pd.read_parquet(root/"derived/p1_concentration_information/20260920/roster/private_top500_permco_marketcap.parquet")
    pop=set(roster.permco.astype(int))
    parts=[]
    for year,flt in [(2022,[("date","==","2022-12-30")]),(2023,[("date",">=","2023-01-01"),("date","<=","2023-06-30")])]:
        x=pd.read_parquet(root/f"raw/crsp_dsf_{year}.parquet",columns=["permno","permco","date","prc","shrout"],filters=flt)
        x["date"]=pd.to_datetime(x.date); parts.append(x[x.permco.isin(pop)])
    dsf=pd.concat(parts,ignore_index=True).drop_duplicates(["permno","date"],keep=False)
    names=pd.read_parquet(root/"raw/crsp_dsenames_full.parquet",columns=["permno","permco","namedt","nameendt","shrcd"])
    names["namedt"]=pd.to_datetime(names.namedt); names["nameendt"]=pd.to_datetime(names.nameendt)
    names=names[names.shrcd.isin([10,11])].drop_duplicates()
    m=dsf.merge(names,on=["permno","permco"],how="left")
    m=m[(m.namedt.isna()|(m.namedt<=m.date))&(m.nameendt.isna()|(m.nameendt>=m.date))].copy()
    calendar=sorted(dsf.date.unique()); prior={pd.Timestamp(d):pd.Timestamp(calendar[i-1]) for i,d in enumerate(calendar) if i>0}
    m=m.sort_values(["permno","date"]); m["prior_observed_date"]=m.groupby("permno").date.shift(1); m["expected_prior_date"]=m.date.map(prior)
    m["nonadjacent_lag"]=(m.prior_observed_date.notna()&(m.prior_observed_date!=m.expected_prior_date))

    response=pd.read_parquet(private/"private_receiver_event_responses.parquet",columns=["event_date","permco"])
    cp=pd.read_parquet(private/"private_control_window_provenance.parquet")
    h1cal=[pd.Timestamp(d) for d in calendar if pd.Timestamp(d)>=pd.Timestamp("2023-01-01")]
    req=[]
    for r in response.itertuples(index=False):
        ix=next(i for i,d in enumerate(h1cal) if d>=r.event_date)
        req.extend([(int(r.permco),h1cal[ix]),(int(r.permco),h1cal[ix+1])])
    for r in cp.itertuples(index=False): req.extend([(int(r.permco),r.control_start),(int(r.permco),r.control_end)])
    required=pd.DataFrame(req,columns=["permco","date"]).drop_duplicates()
    used=m.merge(required,on=["permco","date"],how="inner")
    nonadj=used[used.nonadjacent_lag]

    expected=[]
    for d,g in required.groupby("date"):
        pcs=set(g.permco)
        n=names[names.permco.isin(pcs)&(names.namedt.isna()|(names.namedt<=d))&(names.nameendt.isna()|(names.nameendt>=d))]
        expected.append(n[["permco","permno"]].drop_duplicates().assign(date=d))
    expected=pd.concat(expected,ignore_index=True).drop_duplicates(["permco","permno","date"])
    present=m[["permco","permno","date"]].drop_duplicates()
    miss=expected.merge(present,on=["permco","permno","date"],how="left",indicator=True)
    miss=miss[miss._merge=="left_only"]
    receipt={
      "required_company_dates":int(len(required)),"required_present_security_class_rows":int(len(used)),
      "nonadjacent_lag_security_rows":int(len(nonadj)),"company_dates_with_any_nonadjacent_lag":int(nonadj[["permco","date"]].drop_duplicates().shape[0]),
      "date_valid_expected_class_rows":int(len(expected)),"missing_date_valid_class_rows":int(len(miss)),
      "company_dates_with_missing_date_valid_class":int(miss[["permco","date"]].drop_duplicates().shape[0]),
      "interpretation":"Date-valid name interval is an eligibility expectation, not proof a security should have traded; missing class rows require caution. Nonadjacent lags identify stale prior-observed cap use.",
      "return_values_read":False}
    (out/"PUBLIC_DAILY_INPUT_AUDIT.json").write_text(json.dumps(receipt,indent=2)+"\n"); print(json.dumps(receipt,indent=2))
if __name__=="__main__": main()
