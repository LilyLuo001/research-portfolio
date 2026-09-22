#!/usr/bin/env python3
"""Validate four model cells, concatenate safe losses, and summarize them."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--parts",required=True,type=Path);ap.add_argument("--out",required=True,type=Path);ap.add_argument("--summarizer",required=True,type=Path);a=ap.parse_args()
    expected={"XNAS.ITCH_0","XNAS.ITCH_500","ARCX.PILLAR_0","ARCX.PILLAR_500"}
    found={p.name for p in a.parts.iterdir() if p.is_dir() and (p/"MODEL_RECEIPT.json").exists()}
    if found != expected: raise RuntimeError(f"expected four model cells, found {sorted(found)}")
    daily=[];validation=[];receipts=[]
    for name in sorted(expected):
        root=a.parts/name;receipt=json.loads((root/"MODEL_RECEIPT.json").read_text())
        if receipt.get("status")!="COMPLETE_FOMC_MODELS_ON_SCC":raise RuntimeError(f"bad receipt {name}")
        daily.append(pd.read_csv(root/"DAILY_MODEL_SSE.csv"));validation.append(pd.read_csv(root/"VALIDATION_TRACE.csv"));receipts.append(receipt)
    a.out.mkdir(parents=True,exist_ok=True);daily_path=a.out/"DAILY_MODEL_SSE.csv"
    pd.concat(daily,ignore_index=True).to_csv(daily_path,index=False)
    pd.concat(validation,ignore_index=True).to_csv(a.out/"VALIDATION_TRACE.csv",index=False)
    subprocess.run([sys.executable,str(a.summarizer),"--daily-sse",str(daily_path),"--out",str(a.out)],check=True)
    (a.out/"CELL_RECEIPTS.json").write_text(json.dumps({"status":"COMPLETE_FOUR_CELLS","cells":receipts},indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
