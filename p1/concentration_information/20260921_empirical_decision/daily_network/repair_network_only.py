#!/usr/bin/env python3
"""Finite issuer-SIC repair using the existing H1 response panel; no new outcomes."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

from run_daily_network import DEV_START, DEV_END, EXPOSED, block_bootstrap, fit_ols


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,required=True); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); root=a.root.resolve(); out=a.out.resolve(); private=out/"private"
    roster_dir=root/"derived/p1_concentration_information/20260920/roster"
    network_dir=root/"derived/p1_concentration_information/20260920_phase3/network_selection/results"
    response=pd.read_parquet(private/"private_receiver_event_responses.parquet")
    roster=pd.read_parquet(roster_dir/"private_top500_permco_marketcap.parquet")
    top8=set(roster.loc[roster.issuer_rank<=8,"permco"].astype(int))
    events=pd.read_parquet(roster_dir/"private_2023_top8_earnings_release_group_candidates.parquet")
    events["anndats"]=pd.to_datetime(events.anndats)
    events=events[(events.anndats>=DEV_START)&(events.anndats<=DEV_END)&~events.anndats.isin(EXPOSED)]
    events=events[["permco","anndats"]].drop_duplicates().rename(columns={"permco":"issuer_permco"})
    pairs=pd.read_parquet(network_dir/"private_pair_scores.parquet")
    pairs=pairs[pairs.variant=="PURE_D"]
    recv=pd.read_parquet(network_dir/"private_receiver_scores.parquet")
    recv=recv[recv.variant=="PURE_D"][["receiver_permco","company_market_cap","avg_daily_dollar_volume","sic2"]]

    dsf=pd.read_parquet(root/"raw/crsp_dsf_2022.parquet",columns=["permno","permco","date","prc","shrout"],filters=[("date","==","2022-12-30")])
    dsf["date"]=pd.to_datetime(dsf.date); dsf=dsf[dsf.permco.isin(top8)].drop_duplicates(["permno","date"],keep=False)
    names=pd.read_parquet(root/"raw/crsp_dsenames_full.parquet",columns=["permno","permco","namedt","nameendt","shrcd","siccd"])
    names["namedt"]=pd.to_datetime(names.namedt); names["nameendt"]=pd.to_datetime(names.nameendt)
    names=names[(names.namedt.isna()|(names.namedt<=pd.Timestamp("2022-12-30"))) &
                (names.nameendt.isna()|(names.nameendt>=pd.Timestamp("2022-12-30"))) & names.shrcd.isin([10,11])]
    names=names.drop_duplicates(["permno","permco","shrcd","siccd"])
    counts=names.groupby(["permno","permco"]).size(); valid=set(counts[counts==1].index)
    names=names[names.set_index(["permno","permco"]).index.isin(valid)]
    ident=dsf.merge(names,on=["permno","permco"],how="inner")
    ident["market_cap"]=ident.prc.abs()*ident.shrout*1000
    ident=ident.sort_values(["permco","market_cap"],ascending=[True,False]).drop_duplicates("permco")
    issuer_sic=(ident.set_index("permco").siccd//100).to_dict()
    coverage={"top8_expected":8,"top8_date_valid_sic_observed":len(issuer_sic),"ambiguous_active_name_security_keys_excluded":int((counts>1).sum())}
    if len(issuer_sic)!=8: raise RuntimeError(f"issuer SIC coverage failed: {coverage}")

    net=events.merge(pairs[["issuer_permco","receiver_permco","pair_strength"]],on="issuer_permco",how="inner")
    net=net.merge(response.rename(columns={"event_date":"anndats","permco":"receiver_permco"}),on=["anndats","receiver_permco"],how="inner")
    net=net.merge(recv,on="receiver_permco",how="left")
    net["issuer_sic2"]=net.issuer_permco.map(issuer_sic)
    net["same_focal_sic2"]=np.where(net.sic2.notna()&net.issuer_sic2.notna(),(net.sic2==net.issuer_sic2).astype(float),np.nan)
    net["log_size"]=np.log(net.company_market_cap); net["log_liquidity"]=np.log(net.avg_daily_dollar_volume)
    net["log_pair_strength"]=np.log(net.pair_strength)
    xmean=float(net.log_pair_strength.mean()); xsd=float(net.log_pair_strength.std(ddof=1)); net["x_std"]=(net.log_pair_strength-xmean)/xsd
    net["event_id"]=net.issuer_permco.astype(str)+"_"+net.anndats.dt.strftime("%Y%m%d"); net["event_ret_abs"]=net.event_ret.abs()
    net.to_parquet(private/"private_issuer_receiver_analysis.parquet",index=False)

    rng=np.random.default_rng(20260921); public=[]; loo=[]
    specs=[("connection_event_fe",[]),("plus_pre_size_liquidity_focal_sic2",["log_size","log_liquidity","same_focal_sic2"])]
    outcomes=[("absolute_event_minus_control","abs_diff"),("signed_event_minus_control","signed_diff"),("raw_absolute_event_return","event_ret_abs")]
    for sname,sample in [("all_observed_positive_pairs",net),("focal_same_sic2_only",net[net.same_focal_sic2==1])]:
      for spec,base_controls in specs:
       controls=[c for c in base_controls if not(sname=="focal_same_sic2_only" and c=="same_focal_sic2")]
       for oname,col in outcomes:
        ans=fit_ols(sample,col,controls); lo,hi,nb=block_bootstrap(sample,col,controls,rng)
        public.append({"sample":sname,"specification":spec,"outcome":oname,"coefficient_per_1sd_log_pair_strength":ans["beta"],
          "ci_low":lo,"ci_high":hi,"successful_bootstrap_draws":nb,"rows":ans["n"],"unique_receivers":sample.receiver_permco.nunique(),
          "issuer_events":sample.event_id.nunique(),"event_dates":sample.anndats.nunique(),"overlap_blocks":sample.block_id.nunique(),
          "design_rank":ans["rank"],"design_columns":ans["k"],"log_pair_strength_mean":xmean,"log_pair_strength_sd":xsd})
        for b in sorted(sample.block_id.unique()):
          la=fit_ols(sample[sample.block_id!=b],col,controls)
          loo.append({"sample":sname,"specification":spec,"outcome":oname,"omitted_block":f"B{int(b):02d}","coefficient":la["beta"],"rows":la["n"]})
    pd.DataFrame(public).to_csv(out/"PUBLIC_ISSUER_RECEIVER_NETWORK_RESULTS.csv",index=False)
    pd.DataFrame(loo).to_csv(out/"PUBLIC_LEAVE_ONE_BLOCK_OUT.csv",index=False)
    receipt={"status":"FINITE_NETWORK_REPAIR_COMPLETE","new_outcomes_read":False,"response_panel_rows":len(response),
      "issuer_sic_coverage":coverage,"same_focal_sic2_rows":int((net.same_focal_sic2==1).sum()),
      "same_focal_sic2_receivers":int(net.loc[net.same_focal_sic2==1,"receiver_permco"].nunique()),
      "adjusted_design_full_rank":bool(all((r["design_rank"]==r["design_columns"]) for r in public if r["sample"]=="all_observed_positive_pairs" and r["specification"].startswith("plus_"))),
      "precision":"event-overlap-block heuristic; not fully shared-control-dependence-adjusted"}
    (out/"PUBLIC_NETWORK_REPAIR_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))

if __name__=="__main__": main()
