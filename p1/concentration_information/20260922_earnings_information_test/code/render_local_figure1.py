#!/usr/bin/env python3
"""Render the permitted aggregate replacement for Figure 1 locally."""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def main():
 p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
 x=pd.read_csv(a.input); x=x[(x.split=="TEST")&(x.sample_kind=="EVENT")&(x.venue=="XNAS.ITCH")&(x.instrument=="ISSUER")]
 fig,ax=plt.subplots(figsize=(8,5))
 for session,g in x.groupby("session"):
  g=g.sort_values("endpoint_seconds");ax.plot(g.endpoint_seconds,g.median_abs_bp,marker="o",label=session)
 ax.set_xscale("log");ax.set_xlabel("Endpoint seconds from candidate anchor (baseline t=-1s)");ax.set_ylabel("Median absolute issuer midpoint move (bp)");ax.set_title("2024 candidate-event issuer paths — XNAS (session medians)");ax.legend(title="Session",fontsize=8);fig.tight_layout();a.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.out,dpi=180);plt.close(fig)
if __name__=="__main__":main()
