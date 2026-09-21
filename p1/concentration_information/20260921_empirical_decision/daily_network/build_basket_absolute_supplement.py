#!/usr/bin/env python3
"""Secondary same-mask aggregated-basket absolute response; H1 only, no CI."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from run_daily_network import compound, effective

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,required=True); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); root=a.root; out=a.out; private=out/"private"
    roster=pd.read_parquet(root/"derived/p1_concentration_information/20260920/roster/private_top500_permco_marketcap.parquet")
    pop=set(roster.permco.astype(int)); fixed=roster.set_index("permco").market_cap_usd
    parts=[]
    for year,flt in [(2022,[("date","==","2022-12-30")]),(2023,[("date",">=","2023-01-01"),("date","<=","2023-06-30")])]:
        x=pd.read_parquet(root/f"raw/crsp_dsf_{year}.parquet",columns=["permno","permco","date","ret","prc","shrout"],filters=flt)
        x["date"]=pd.to_datetime(x.date); parts.append(x[x.permco.isin(pop)])
    dsf=pd.concat(parts,ignore_index=True).drop_duplicates(["permno","date"],keep=False)
    names=pd.read_parquet(root/"raw/crsp_dsenames_full.parquet",columns=["permno","permco","namedt","nameendt","shrcd"])
    names["namedt"]=pd.to_datetime(names.namedt); names["nameendt"]=pd.to_datetime(names.nameendt)
    m=dsf.merge(names,on=["permno","permco"],how="left")
    m=m[effective(m.date,m.namedt,m.nameendt)&m.shrcd.isin([10,11])].sort_values(["permno","date"]).copy()
    m["market_cap"]=m.prc.abs()*m.shrout*1000; m["prior_market_cap"]=m.groupby("permno").market_cap.shift(1)
    dl=pd.read_parquet(root/"raw/rescue/crsp_dsedelist_allcols_2023.parquet",columns=["permno","dlstdt","dlret"],
                       filters=[("dlstdt",">=","2023-01-01"),("dlstdt","<=","2023-06-30")])
    dl["date"]=pd.to_datetime(dl.dlstdt); dl=dl.drop_duplicates(["permno","date"],keep=False)
    m=m.merge(dl[["permno","date","dlret"]],on=["permno","date"],how="left")
    both=m.ret.notna()&m.dlret.notna(); m["total_ret"]=m.ret
    m.loc[m.ret.isna()&m.dlret.notna(),"total_ret"]=m.loc[m.ret.isna()&m.dlret.notna(),"dlret"]
    m.loc[both,"total_ret"]=(1+m.loc[both,"ret"])*(1+m.loc[both,"dlret"])-1
    m=m[m.total_ret.notna()&(m.prior_market_cap>0)]; m["wr"]=m.total_ret*m.prior_market_cap
    cd=m.groupby(["permco","date"],as_index=False).agg(wr=("wr","sum"),cap=("prior_market_cap","sum")); cd["r"]=cd.wr/cd.cap
    dret=cd.set_index(["permco","date"]).r

    response=pd.read_parquet(private/"private_receiver_event_responses.parquet",columns=["event_date","block_id","permco","event_ret"])
    cp=pd.read_parquet(private/"private_control_window_provenance.parquet")
    z=cp.merge(response,on=["event_date","permco"],how="inner")
    z["control_ret"]=[compound([dret.get((int(r.permco),r.control_start),np.nan),dret.get((int(r.permco),r.control_end),np.nan)]) for r in z.itertuples(index=False)]
    z=z[np.isfinite(z.control_ret)]
    comps=[]
    for (d,b,cs,ce),g in z.groupby(["event_date","block_id","control_start","control_end"]):
      for weighting in ("equal","fixed_2022_12_30_market_cap"):
        w=np.ones(len(g)) if weighting=="equal" else g.permco.map(fixed).to_numpy(float); w=w/w.sum()
        er=float(np.dot(w,g.event_ret)); cr=float(np.dot(w,g.control_ret))
        comps.append({"event_date":d,"block_id":b,"control_start":cs,"control_end":ce,"weighting":weighting,
                      "receivers":len(g),"event_basket_return":er,"control_basket_return":cr,
                      "event_abs_basket_return":abs(er),"control_abs_basket_return":abs(cr),"abs_basket_difference":abs(er)-abs(cr)})
    comps=pd.DataFrame(comps); comps.to_parquet(private/"private_matched_basket_absolute_comparisons.parquet",index=False)
    bydate=comps.groupby(["event_date","block_id","weighting"],as_index=False).agg(
      event_abs_basket_return=("event_abs_basket_return","mean"),control_abs_basket_return=("control_abs_basket_return","mean"),
      abs_basket_difference=("abs_basket_difference","mean"),matched_control_windows=("control_start","nunique"),
      min_same_mask_receivers=("receivers","min"),max_same_mask_receivers=("receivers","max"))
    byblock=bydate.groupby(["block_id","weighting"],as_index=False).agg(
      event_abs_basket_return=("event_abs_basket_return","mean"),control_abs_basket_return=("control_abs_basket_return","mean"),
      abs_basket_difference=("abs_basket_difference","mean"),event_dates=("event_date","nunique"),
      matched_control_windows=("matched_control_windows","sum"),min_same_mask_receivers=("min_same_mask_receivers","min"),max_same_mask_receivers=("max_same_mask_receivers","max"))
    public=[]
    for weighting,g in byblock.groupby("weighting"):
      public.append({"status":"SECONDARY_AFTER_PILOT_NO_CI","weighting":weighting,
        "event_abs_basket_return":g.event_abs_basket_return.mean(),"control_abs_basket_return":g.control_abs_basket_return.mean(),
        "event_minus_control_abs_basket":g.abs_basket_difference.mean(),"overlap_blocks":g.block_id.nunique(),
        "event_dates":int(g.event_dates.sum()),"matched_event_control_comparisons":int(g.matched_control_windows.sum()),
        "min_same_mask_receivers":int(g.min_same_mask_receivers.min()),"max_same_mask_receivers":int(g.max_same_mask_receivers.max()),
        "interval":"NOT_ESTIMATED_SHARED_CONTROL_DEPENDENCE"})
    pd.DataFrame(public).to_csv(out/"PUBLIC_MATCHED_BASKET_ABSOLUTE_SUPPLEMENT.csv",index=False)
    receipt={"status":"SECONDARY_MEASUREMENT_SUPPLEMENT_COMPLETE","h2_response_values_read":False,
      "same_receiver_mask_and_weights_within_each_event_control_comparison":True,"changes_primary_specification":False,
      "comparisons":int(len(comps)//2),"unique_control_windows":int(comps[["control_start","control_end"]].drop_duplicates().shape[0]),
      "precision":"NO_CI; shared-control dependence unresolved"}
    (out/"PUBLIC_MATCHED_BASKET_SUPPLEMENT_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n"); print(json.dumps(receipt,indent=2))
if __name__=="__main__": main()
