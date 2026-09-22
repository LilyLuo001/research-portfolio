#!/usr/bin/env python3
"""Create aggregate inference tables and the three directional-evidence figures."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def bootstrap_group(group: pd.DataFrame, weights: dict[str, float], seed: int, reps: int = 2000) -> dict:
    dates = sorted(group.date.unique()); symbols = sorted(group.symbol.unique()); rng = np.random.default_rng(seed)
    sb=group.pivot(index="symbol",columns="date",values="sse_baseline").reindex(index=symbols,columns=dates).to_numpy(float)
    sf=group.pivot(index="symbol",columns="date",values="sse_full").reindex(index=symbols,columns=dates).to_numpy(float)
    w=np.asarray([weights[s] for s in symbols],float);w/=w.sum(); gain=1-sf.sum(1)/sb.sum(1)
    point=(float(gain.mean()),float(gain@w))
    ix=rng.integers(0,len(dates),size=(reps,len(dates)))
    b=np.stack([sb[:,draw].sum(1) for draw in ix]);f=np.stack([sf[:,draw].sum(1) for draw in ix]);g=1-f/b
    a=np.column_stack([g.mean(1),g@w])
    return {"equal_stock_G":point[0],"equal_ci_low":float(np.quantile(a[:,0],.025)),"equal_ci_high":float(np.quantile(a[:,0],.975)),
            "report_weight_G":point[1],"weighted_ci_low":float(np.quantile(a[:,1],.025)),"weighted_ci_high":float(np.quantile(a[:,1],.975))}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",required=True);a=ap.parse_args();root=Path(a.root)
    pred=pd.read_csv(root/"BIDIRECTIONAL_PREDICTION.csv");daily=pd.read_csv(root/"PREDICTION_DAILY.csv")
    grid=pd.read_csv(root/"GRID_SHIFT_COMPARISON.csv");resp=pd.read_csv(root/"MATCHED_CONTROL_RESPONSE_SUMMARY.csv")
    roster=pd.read_csv(root.parent/"20260922_bidirectional_information/results/SAFE_ROSTER.csv")
    weights=roster.set_index("symbol").report_weight.to_dict(); pair=daily[daily.scope=="PAIRWISE"]
    rows=[]
    keys=["venue","grid_shift_ms","family","direction"]
    for i,(key,g) in enumerate(pair.groupby(keys)):
        meta=pred[(pred.scope=="PAIRWISE")]
        for col,val in zip(keys,key):meta=meta[meta[col]==val]
        b=bootstrap_group(g,weights,20260922+i)
        rows.append(dict(zip(keys,key),stocks=int(g.symbol.nunique()),test_dates=int(g.date.nunique()),
                         mean_test_centers_per_stock=float(meta.n_test.mean()),positive_stocks=int((meta.G>0).sum()),
                         median_stock_G=float(meta.G.median()),**b))
    agg=pd.DataFrame(rows);agg.to_csv(root/"BIDIRECTIONAL_AGGREGATES.csv",index=False)
    c=pred[(pred.scope=="PAIRWISE")&(pred.family=="QUOTE_WITH_REST_BASKET")&(pred.direction=="ETF_TO_STOCK")]
    correlations=[]
    for (venue,shift),g in c.groupby(["venue","grid_shift_ms"]):
        correlations.append({"venue":venue,"grid_shift_ms":shift,"stocks":len(g),
                             "pearson_weight_G":float(g.report_weight.corr(g.G)),
                             "spearman_weight_G":float(g.report_weight.rank().corr(g.G.rank()))})
    pd.DataFrame(correlations).to_csv(root/"CONCENTRATION_DIAGNOSTIC.csv",index=False)

    # Figure 1: rest-basket-controlled prediction, the most discriminating specification.
    x=agg[agg.family.isin(["QUOTE_WITH_REST_BASKET","QUOTE_TRADE_WITH_REST_BASKET"])].copy()
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,(family,title) in zip(axes,[("QUOTE_WITH_REST_BASKET","Quotes"),("QUOTE_TRADE_WITH_REST_BASKET","Quotes + separated trades")]):
        z=x[x.family==family]; labels=[];vals=[];lo=[];hi=[]
        for venue in ["XNAS.ITCH","ARCX.PILLAR"]:
            for shift in [0,500]:
                for direction in ["ETF_TO_STOCK","STOCK_TO_ETF"]:
                    r=z[(z.venue==venue)&(z.grid_shift_ms==shift)&(z.direction==direction)].iloc[0]
                    labels.append(f"{venue.split('.')[0]}\n{shift}ms\n{'ETF→S' if direction=='ETF_TO_STOCK' else 'S→ETF'}")
                    vals.append(r.equal_stock_G);lo.append(r.equal_stock_G-r.equal_ci_low);hi.append(r.equal_ci_high-r.equal_stock_G)
        pos=np.arange(len(vals));ax.errorbar(pos,vals,yerr=[lo,hi],fmt='o',capsize=3);ax.axhline(0,color='black',lw=.8);ax.set_xticks(pos,labels,rotation=45,ha='right',fontsize=7);ax.set_title(title);ax.set_ylabel("Out-of-sample G")
    fig.tight_layout();fig.savefig(root/"FIG1_BIDIRECTIONAL_PREDICTION.png",dpi=180);plt.close(fig)

    # Figure 2: natural and paired-grid comparisons.
    z=grid[grid.family=="QUOTE_WITH_REST_BASKET"].groupby(["venue","direction","grid_shift_ms"])[["natural_G","paired_G"]].mean().reset_index()
    fig,ax=plt.subplots(figsize=(9,4));labels=[];vals=[]
    for _,r in z.iterrows():
        labels.append(f"{r.venue.split('.')[0]} {int(r.grid_shift_ms)}ms {'ETF→S' if r.direction=='ETF_TO_STOCK' else 'S→ETF'}")
        vals.append(r.paired_G)
    colors=['#2b6cb0' if v>0 else '#c53030' for v in vals];ax.bar(np.arange(len(vals)),vals,color=colors);ax.axhline(0,color='black',lw=.8);ax.set_xticks(np.arange(len(vals)),labels,rotation=35,ha='right');ax.set_ylabel("Mean paired-support G");ax.set_title("One-second grid translated by 500ms")
    fig.tight_layout();fig.savefig(root/"FIG2_GRID_SHIFT_COMPARISON.png",dpi=180);plt.close(fig)

    # Figure 3: matched-control quote response.
    z=resp[resp['sample']=='nonoverlap'];fig,ax=plt.subplots(figsize=(8,4.5))
    for (venue,direction),g in z.groupby(["venue","direction"]):
        g=g.sort_values("window_ms");lab=f"{venue.split('.')[0]} {'ETF→S' if direction=='ETF_TO_STOCK' else 'S→ETF'}"
        ax.plot(g.window_ms,g.mean_event_minus_control_bp,marker='o',label=lab)
    ax.axhline(0,color='black',lw=.8);ax.set_xscale('log');ax.set_xticks([100,500,1000,2000,5000],["100ms","500ms","1s","2s","5s"]);ax.set_xlabel("Post-trigger horizon");ax.set_ylabel("Signed event − matched control (bp)");ax.legend(frameon=False,ncol=2);ax.set_title("Nonoverlapping midpoint-update response")
    fig.tight_layout();fig.savefig(root/"FIG3_QUOTE_RESPONSE.png",dpi=180);plt.close(fig)
    print({"aggregate_rows":len(agg),"concentration_rows":len(correlations),"figures":3})

if __name__=="__main__":main()
