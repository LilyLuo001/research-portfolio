#!/usr/bin/env python3
"""Comparable-support one-second directional prediction and grid analysis."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


LAMBDAS = np.asarray([0.01, 0.1, 1.0, 10.0, 100.0])
QUOTE = ["ret_0_100ms", "ret_100ms_1s", "ret_1s_5s", "spread_bp",
         "bid_depth", "ask_depth", "mid_update_count_1s", "mid_update_age_ms"]
TRADE = [f"{stem}_{window}" for window in ("0_100ms", "100ms_1s", "1s_5s")
         for stem in ("known_signed_flow", "unknown_dollar_volume", "no_trade")]
TARGET = "y_1s_bp"
TIERS = ("high", "mid", "low")


def transform_values(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in ["bid_depth", "ask_depth", "mid_update_count_1s", "mid_update_age_ms"]:
        out[col] = np.log1p(out[col].clip(lower=0))
    for col in TRADE:
        if col.startswith("known_signed_flow"):
            x = out[col].to_numpy(float); out[col] = np.sign(x) * np.log1p(np.abs(x))
        elif col.startswith("unknown_dollar_volume"):
            out[col] = np.log1p(out[col].clip(lower=0))
    return out


def time_controls(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({f"minute_{k}": (frame["minute_bin_5m"].to_numpy(int) == k).astype(float)
                         for k in range(1, 6)}, index=frame.index)


def prepare_x(train: np.ndarray, arrays: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict]:
    with np.errstate(all="ignore"):
        median = np.nanmedian(train, axis=0)
    median[~np.isfinite(median)] = 0.0
    out, rates = {}, {}
    for name, raw in arrays.items():
        miss = ~np.isfinite(raw)
        out[name] = np.column_stack([np.where(miss, median, raw), miss.astype(float)])
        rates[name] = float(miss.mean())
    return out, {"missing_rates": rates}


def fit_ridge(x: np.ndarray, y: np.ndarray, mean: np.ndarray, scale: np.ndarray, lam: float):
    z = (x - mean) / scale; zbar = z.mean(axis=0); ybar = float(y.mean())
    zc = z - zbar; rhs = zc.T @ (y - ybar) / len(y)
    gram = zc.T @ zc / len(y) + lam * np.eye(z.shape[1])
    coef = np.linalg.solve(gram, rhs)
    return ybar - float(zbar @ coef), coef


def model_pair(frame: pd.DataFrame, base_cols: list[str], extra_cols: list[str], splits: dict[str, set[str]]):
    use = frame[np.isfinite(frame[TARGET].to_numpy(float))].copy()
    masks = {k: use.date.isin(v).to_numpy() for k, v in splits.items()}
    y = use[TARGET].to_numpy(float)
    xb_raw = use[base_cols].to_numpy(float); xf_raw = use[base_cols + extra_cols].to_numpy(float)
    xb, ib = prepare_x(xb_raw[masks["train"]], {k: xb_raw[m] for k, m in masks.items()})
    xf, iff = prepare_x(xf_raw[masks["train"]], {k: xf_raw[m] for k, m in masks.items()})

    def choose(x):
        mean=x["train"].mean(0); scale=x["train"].std(0); scale[(~np.isfinite(scale))|(scale==0)]=1
        trace=[]
        for lam in LAMBDAS:
            a,b=fit_ridge(x["train"],y[masks["train"]],mean,scale,float(lam))
            pred=a+(x["valid"]-mean)/scale@b
            trace.append((float(np.mean((y[masks["valid"]]-pred)**2)),float(lam)))
        return min(trace)[1],mean,scale
    lb,mb,sb=choose(xb); lf,mf,sf=choose(xf)
    fit_y=np.r_[y[masks["train"]],y[masks["valid"]]]
    fit_b=np.vstack([xb["train"],xb["valid"]]); fit_f=np.vstack([xf["train"],xf["valid"]])
    ab,bb=fit_ridge(fit_b,fit_y,mb,sb,lb); af,bf=fit_ridge(fit_f,fit_y,mf,sf,lf)
    pb=ab+(xb["test"]-mb)/sb@bb; pf=af+(xf["test"]-mf)/sf@bf
    yt=y[masks["test"]]; eb=(yt-pb)**2; ef=(yt-pf)**2
    detail=use.loc[masks["test"],["date","second_index","mid_update_count_1s","mid_update_age_ms"]].copy()
    detail["sse_baseline"]=eb; detail["sse_full"]=ef
    return {
        "lambda_baseline":lb,"lambda_full":lf,"n_train":int(masks["train"].sum()),
        "n_valid":int(masks["valid"].sum()),"n_test":int(masks["test"].sum()),
        "sse_baseline":float(eb.sum()),"sse_full":float(ef.sum()),
        "G":float(1-ef.sum()/eb.sum()),"absolute_loss_change":float(eb.sum()-ef.sum()),
        "baseline_missing_rate_test":ib["missing_rates"]["test"],
        "full_missing_rate_test":iff["missing_rates"]["test"],
    },detail


def day_ci(detail: pd.DataFrame, seed: int) -> tuple[float,float,int]:
    d=detail.groupby("date")[["sse_baseline","sse_full"]].sum(); rng=np.random.default_rng(seed)
    draws=[]
    for _ in range(1000):
        ix=rng.integers(0,len(d),len(d)); b=d.sse_baseline.to_numpy()[ix].sum(); f=d.sse_full.to_numpy()[ix].sum()
        draws.append(1-f/b)
    return float(np.quantile(draws,.025)),float(np.quantile(draws,.975)),int(((d.sse_baseline-d.sse_full)>0).sum())


def prefix(frame: pd.DataFrame, cols: list[str], name: str) -> pd.DataFrame:
    selected = ["date", "second_index", "minute_bin_5m", TARGET, *cols]
    return frame[selected].rename(columns={c:f"{name}__{c}" for c in selected if c not in ("date", "second_index")})


def pair_panels(f: pd.DataFrame, roster: pd.DataFrame, cols: list[str]):
    spy=f[f.symbol=="SPY"].copy(); stocks=f[f.symbol!="SPY"].copy(); out=[]
    weights = roster.set_index("symbol")["report_weight"].astype(float)
    stocks["report_weight"] = stocks.symbol.map(weights)
    keys = ["date", "second_index"]
    totals = {}
    for col in cols:
        valid = np.isfinite(stocks[col].to_numpy(float)); tmp = stocks[keys].copy()
        tmp["num"] = np.where(valid, stocks[col] * stocks.report_weight, 0.0)
        tmp["den"] = np.where(valid, stocks.report_weight, 0.0)
        totals[col] = tmp.groupby(keys)[["num", "den"]].sum()
    spy_p=prefix(spy,cols,"spy")
    for symbol in sorted(stocks.symbol.unique()):
        raw_one = stocks[stocks.symbol==symbol].copy(); one=prefix(raw_one,cols,"stock")
        p=one.merge(spy_p,on=["date","second_index"],validate="one_to_one")
        p["minute_bin_5m"] = p["stock__minute_bin_5m"]
        own_weight = float(weights.loc[symbol]); total_other_weight = float(weights.loc[stocks.symbol.unique()].sum() - own_weight)
        own = raw_one.set_index(keys)
        for col in cols:
            x = totals[col].join(own[[col]], how="left")
            valid = np.isfinite(x[col].to_numpy(float))
            num = x.num.to_numpy(float) - np.where(valid, x[col].to_numpy(float) * own_weight, 0.0)
            den = x.den.to_numpy(float) - np.where(valid, own_weight, 0.0)
            rest = pd.DataFrame({"date":[z[0] for z in x.index], "second_index":[z[1] for z in x.index],
                                 f"rest__{col}":np.where(den>0,num/den,np.nan),
                                 f"rest__coverage_{col}":den/total_other_weight})
            p = p.merge(rest, on=keys, how="left", validate="one_to_one")
        p["symbol"]=symbol
        p["report_weight"]=float(roster.set_index("symbol").loc[symbol,"report_weight"])
        p["weight_tier"]=roster.set_index("symbol").loc[symbol,"weight_tier"]
        out.append(p)
    return out


def weighted_tiers(f: pd.DataFrame, roster: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    keys=["date","second_index"] ; stocks=f[f.symbol!="SPY"].merge(roster[["symbol","report_weight","weight_tier"]],on="symbol")
    pieces=[]
    for tier in TIERS:
        x=stocks[stocks.weight_tier==tier].copy(); tw=float(x.drop_duplicates("symbol").report_weight.sum())
        base=x[keys].drop_duplicates().set_index(keys).sort_index(); z=pd.DataFrame(index=base.index)
        for col in cols:
            valid=np.isfinite(x[col].to_numpy(float)); tmp=x[keys].copy()
            tmp["num"]=np.where(valid,x[col]*x.report_weight,0.0); tmp["den"]=np.where(valid,x.report_weight,0.0)
            a=tmp.groupby(keys)[["num","den"]].sum(); z[f"{tier}__{col}"]=a.num/a.den.replace(0,np.nan); z[f"{tier}__coverage_{col}"]=a.den/tw
        pieces.append(z)
    return pd.concat(pieces,axis=1).reset_index()


def joint_panel(f: pd.DataFrame, roster: pd.DataFrame, cols: list[str], mode: str) -> tuple[pd.DataFrame,list[str]]:
    spy=f[f.symbol=="SPY"].copy(); base=prefix(spy,cols,"spy")
    base["minute_bin_5m"] = base["spy__minute_bin_5m"]
    if mode=="PER_STOCK":
        added=[]
        for symbol in sorted(x for x in f.symbol.unique() if x!="SPY"):
            x=f[f.symbol==symbol][["date","second_index",*cols]].rename(columns={c:f"{symbol}__{c}" for c in cols})
            base=base.merge(x,on=["date","second_index"],how="left",validate="one_to_one"); added += [f"{symbol}__{c}" for c in cols]
    else:
        x=weighted_tiers(f,roster,cols); base=base.merge(x,on=["date","second_index"],how="left",validate="one_to_one")
        added=[c for c in x.columns if c not in ("date","second_index")]
    return base,added


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--features",required=True);ap.add_argument("--roster",required=True);ap.add_argument("--dates",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
    raw=pd.read_parquet(a.features); roster=pd.read_csv(a.roster); dates=pd.read_csv(a.dates,dtype={"date":str}); raw.date=raw.date.astype(str)
    splits={k:set(dates.loc[dates.split==k,"date"]) for k in ("train","valid","test")}
    rows=[]; daily=[]; pair_details={}; grid_rows=[]
    for venue in sorted(raw.venue.unique()):
      for shift in (0,500):
       f=raw[(raw.venue==venue)&(raw.grid_shift_ms==shift)].copy()
       for symbol in f.symbol.unique():
        m=f.symbol==symbol; f.loc[m,QUOTE+TRADE]=transform_values(f.loc[m,QUOTE+TRADE])[QUOTE+TRADE]
       families=(("QUOTE_ONLY",QUOTE,False),("QUOTE_WITH_REST_BASKET",QUOTE,True),
                 ("QUOTE_PLUS_TRADE",QUOTE+TRADE,False),("QUOTE_TRADE_WITH_REST_BASKET",QUOTE+TRADE,True))
       for family,cols,use_rest in families:
        for p in pair_panels(f,roster,cols):
         tc=time_controls(p); p=pd.concat([p,tc],axis=1); tcols=list(tc.columns); symbol=p.symbol.iloc[0]
         for direction in ("ETF_TO_STOCK","STOCK_TO_ETF"):
          rest=([f"rest__{c}" for c in cols]+[f"rest__coverage_{c}" for c in cols]) if use_rest else []
          if direction=="ETF_TO_STOCK": target="stock__"+TARGET;base=["stock__"+c for c in cols]+rest+tcols;extra=["spy__"+c for c in cols];source="spy"
          else: target="spy__"+TARGET;base=["spy__"+c for c in cols]+rest+tcols;extra=["stock__"+c for c in cols];source="stock"
          q=p.rename(columns={target:TARGET}).copy()
          q["mid_update_count_1s"] = q[f"{source}__mid_update_count_1s"]
          q["mid_update_age_ms"] = q[f"{source}__mid_update_age_ms"]
          stat,det=model_pair(q,base,extra,splits); lo,hi,pos=day_ci(det,20260922+shift)
          meta={"venue":venue,"grid_shift_ms":shift,"family":family,"scope":"PAIRWISE","direction":direction,"symbol":symbol,
                "weight_tier":p.weight_tier.iloc[0],"report_weight":p.report_weight.iloc[0],**stat,"ci_low":lo,"ci_high":hi,"positive_test_dates":pos,"test_dates":8}
          rows.append(meta); det=det.assign(venue=venue,grid_shift_ms=shift,family=family,direction=direction,symbol=symbol)
          pair_details[(venue,shift,family,direction,symbol)]=det
          for date,g in det.groupby("date"):
           daily.append({"venue":venue,"grid_shift_ms":shift,"family":family,"scope":"PAIRWISE","direction":direction,"symbol":symbol,"date":date,
                         "n":len(g),"sse_baseline":g.sse_baseline.sum(),"sse_full":g.sse_full.sum()})
        # Joint stock panel -> ETF. Quote-only per-stock and tier; trade family tier is kept tractable and interpretable.
        if use_rest:
         continue
        modes=("PER_STOCK","TIER") if family=="QUOTE_ONLY" else ("TIER",)
        for mode in modes:
         p,extra=joint_panel(f,roster,cols,mode); tc=time_controls(p);p=pd.concat([p,tc],axis=1)
         q=p.rename(columns={"spy__"+TARGET:TARGET}).copy()
         q["mid_update_count_1s"] = q["spy__mid_update_count_1s"]
         q["mid_update_age_ms"] = q["spy__mid_update_age_ms"]
         base=["spy__"+c for c in cols]+list(tc.columns);stat,det=model_pair(q,base,extra,splits);lo,hi,pos=day_ci(det,20260922+shift)
         rows.append({"venue":venue,"grid_shift_ms":shift,"family":family,"scope":"JOINT_"+mode,"direction":"STOCK_PANEL_TO_ETF","symbol":"ALL_23",**stat,"ci_low":lo,"ci_high":hi,"positive_test_dates":pos,"test_dates":8})
         for date,g in det.groupby("date"):
          daily.append({"venue":venue,"grid_shift_ms":shift,"family":family,"scope":"JOINT_"+mode,"direction":"STOCK_PANEL_TO_ETF","symbol":"ALL_23","date":date,
                        "n":len(g),"sse_baseline":g.sse_baseline.sum(),"sse_full":g.sse_full.sum()})
         if mode=="TIER":
          for tier in TIERS:
           tier_extra=[c for c in extra if c.startswith(tier+"__")]; other=[c for c in extra if c not in tier_extra]
           stat_m,det_m=model_pair(q,base+other,tier_extra,splits);lo_m,hi_m,pos_m=day_ci(det_m,20260922+shift)
           rows.append({"venue":venue,"grid_shift_ms":shift,"family":family,"scope":"TIER_MARGINAL_"+tier,
                        "direction":"STOCK_TIER_TO_ETF","symbol":tier,**stat_m,"ci_low":lo_m,"ci_high":hi_m,
                        "positive_test_dates":pos_m,"test_dates":8})
           for date,g in det_m.groupby("date"):
            daily.append({"venue":venue,"grid_shift_ms":shift,"family":family,"scope":"TIER_MARGINAL_"+tier,
                          "direction":"STOCK_TIER_TO_ETF","symbol":tier,"date":date,"n":len(g),
                          "sse_baseline":g.sse_baseline.sum(),"sse_full":g.sse_full.sum()})
    # Natural and corresponding-second paired evaluation for pairwise directions.
    for venue in sorted(raw.venue.unique()):
     for family in ("QUOTE_ONLY","QUOTE_WITH_REST_BASKET","QUOTE_PLUS_TRADE","QUOTE_TRADE_WITH_REST_BASKET"):
      for direction in ("ETF_TO_STOCK","STOCK_TO_ETF"):
       for symbol in sorted(x for x in raw.symbol.unique() if x!="SPY"):
        a0=pair_details[(venue,0,family,direction,symbol)];a5=pair_details[(venue,500,family,direction,symbol)]
        common=a0.merge(a5,on=["date","second_index"],suffixes=("_0","_500"),validate="one_to_one")
        for shift,source in ((0,a0),(500,a5)):
         paired=common; sb=paired[f"sse_baseline_{shift}"].sum();sf=paired[f"sse_full_{shift}"].sum()
         natural=next(r for r in rows if r["venue"]==venue and r["grid_shift_ms"]==shift and r["family"]==family and r["scope"]=="PAIRWISE" and r["direction"]==direction and r["symbol"]==symbol)
         upd=source.mid_update_count_1s
         grid_rows.append({"venue":venue,"family":family,"direction":direction,"symbol":symbol,"grid_shift_ms":shift,
                           "natural_n":natural["n_test"],"natural_G":natural["G"],"paired_n":len(paired),"paired_G":1-sf/sb,
                           "source_update_positive_fraction":float((upd>0).mean()),"source_update_count_mean":float(upd.mean()),
                           "source_update_age_ms_median":float(source.mid_update_age_ms.median())})
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/"BIDIRECTIONAL_PREDICTION.csv",index=False)
    pd.DataFrame(daily).to_csv(out/"PREDICTION_DAILY.csv",index=False)
    pd.DataFrame(grid_rows).to_csv(out/"GRID_SHIFT_COMPARISON.csv",index=False)
    receipt={"status":"COMPLETE","feature_path":a.features,"prediction_rows":len(rows),"daily_rows":len(daily),"grid_rows":len(grid_rows),
             "families":["QUOTE_ONLY","QUOTE_WITH_REST_BASKET","QUOTE_PLUS_TRADE","QUOTE_TRADE_WITH_REST_BASKET"],
             "target":"future one-second midpoint log return bp","test_dates":8,
             "per_stock_joint_trade_extension":"NOT_RUN_DIMENSIONALITY_CONTROL; tier aggregate reported","raw_or_prediction_rows_exported_locally":False}
    (out/"MODEL_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))

if __name__=="__main__": main()
