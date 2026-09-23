#!/usr/bin/env python3
"""Create safe SCC aggregate tables and three figures from corrected outputs."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser(); p.add_argument("--models",type=Path,required=True); p.add_argument("--paths",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    r=pd.read_csv(a.models/"PREDICTION_RESULTS.csv"); loo=pd.read_csv(a.models/"LOO.csv"); support=pd.read_csv(a.models/"DEPENDENCE_AND_SUPPORT.csv"); path=pd.read_csv(a.paths/"EVENT_PATH_SUMMARY.csv")
    primary=r[(r.comparison=="A2_TO_A5")&(r.split=="TEST")&(r.horizon_seconds==1)&(r.window=="POST_0_60S")].copy()
    lk=["venue","grid_shift_ms","horizon_seconds","fit_spec","window","sample_kind","session"]
    ls=loo.groupby(lk).G_equal_issuer_event.agg(loo_min="min",loo_max="max",loo_negative_count=lambda x:int((x<0).sum()),loo_positive_count=lambda x:int((x>0).sum()),loo_zero_count=lambda x:int((x==0).sum())).reset_index()
    primary=primary.merge(ls,on=lk,how="left",validate="one_to_one").rename(columns={"G_equal_issuer_event":"G_equal_issuer_event_fraction","G_pooled_sse":"G_pooled_sse_fraction"})
    primary.to_csv(a.out/"PRIMARY_TEST_SUMMARY.csv",index=False)
    support.to_csv(a.out/"DEPENDENCE_AND_SUPPORT_CORRECTED.csv",index=False)
    # Figure 1: event/control path magnitudes by endpoint and session.
    fig,ax=plt.subplots(figsize=(8,5))
    z=path[(path.split=="TEST")&(path.sample_kind=="EVENT")&(path.venue=="XNAS.ITCH")&(path.instrument=="ISSUER")]
    for session,g in z.groupby("session"): ax.plot(g.endpoint_seconds,g.median_abs_bp,marker="o",label=str(session))
    ax.set_xscale("log"); ax.set_xlabel("Endpoint seconds from candidate anchor (baseline t=-1s)"); ax.set_ylabel("Median absolute issuer midpoint move (bp)"); ax.set_title("2024 candidate-event issuer paths — XNAS (session medians)"); ax.legend(title="Session",fontsize=8); fig.tight_layout(); fig.savefig(a.out/"FIGURE_EVENT_PATHS.png",dpi=180); plt.close(fig)
    # Figure 2: issuer-level A2→A5 gain from paired TEST EVENT rows.
    paired=pd.read_csv(a.models/"PAIRED_MODEL_LOSSES.csv.gz")
    x=paired[(paired.comparison=="A2_TO_A5")&(paired.split=="TEST")&(paired.sample_kind=="EVENT")&(paired.horizon_seconds==1)&(paired.window=="POST_0_60S")&(paired.fit_spec=="OWN_LAMBDA")].copy()
    fig,axes=plt.subplots(2,2,figsize=(9,6),sharex=True)
    for ax,((venue,shift),g) in zip(axes.ravel(),x.groupby(["venue","grid_shift_ms"])):
        z=g.groupby("issuer")[["mean_loss_baseline","mean_loss_full"]].mean(); z["gain_pct"]=100*(1-z.mean_loss_full/z.mean_loss_baseline); z=z.sort_values("gain_pct")
        ax.barh(z.index,z.gain_pct); ax.axvline(0,color="black",lw=.8); ax.set_title(f"{venue}, {shift}ms"); ax.set_xlabel("A2→A5 MSE gain (%)")
    fig.suptitle("Conditional SPY increment by issuer: TEST EVENT, 1s, post 0–60s"); fig.tight_layout(); fig.savefig(a.out/"FIGURE_ISSUER_GAINS.png",dpi=180); plt.close(fig)
    # Figure 3: session/horizon sensitivity, each point is a fraction (not percent).
    z=r[(r.comparison=="A2_TO_A5")&(r.split=="TEST")&(r.sample_kind=="EVENT")&(r.window=="POST_0_60S")&(r.fit_spec=="OWN_LAMBDA")]
    fig,ax=plt.subplots(figsize=(8,5))
    for (venue,shift,session),g in z.groupby(["venue","grid_shift_ms","session"]):
        g=g.sort_values("horizon_seconds"); ax.plot(g.horizon_seconds,g.G_equal_issuer_event,marker="o",label=f"{venue} {shift}ms {session}")
    ax.axhline(0,color="black",lw=.8); ax.set_xscale("log"); ax.set_xlabel("Prediction horizon (seconds)"); ax.set_ylabel("Equal-issuer/event G (fraction)"); ax.set_title("Session and horizon sensitivity"); ax.legend(fontsize=7,ncol=2); fig.tight_layout(); fig.savefig(a.out/"FIGURE_SESSION_HORIZON.png",dpi=180); plt.close(fig)
if __name__=="__main__": main()
