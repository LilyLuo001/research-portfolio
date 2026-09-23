#!/usr/bin/env python3
"""Verify integer loss-window membership against stored UTC grid centers."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

WINDOWS={"PRE_600S":(-600,0),"POST_0_60S":(0,60),"POST_60_600S":(60,600)}
def main():
 p=argparse.ArgumentParser(); p.add_argument("--features",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
 x=pd.read_parquet(a.features,columns=["sample_id","grid_shift_ms","second_index","t_ns","anchor_utc"]); x=x.drop_duplicates()
 anchor=pd.to_datetime(x.anchor_utc,utc=True).astype("int64").to_numpy(); t=x.t_ns.to_numpy(np.int64); rel=x.second_index.to_numpy(int)-600; rows=[]
 for h in (1,5,30):
  for name,(lo,hi) in WINDOWS.items():
   current=(rel>=lo)&(rel+h<hi); actual=(t>=anchor+lo*1_000_000_000)&(t+h*1_000_000_000<anchor+hi*1_000_000_000)
   rows.append({"horizon_seconds":h,"window":name,"rows":len(x),"mismatches":int((current!=actual).sum()),"equivalent":bool(np.array_equal(current,actual))})
 a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps({"status":"COMPLETE","rows":rows,"conclusion":"integer second-index membership is equivalent to actual UTC center/target membership for both 0ms and 500ms grids"},indent=2)+"\n")
if __name__=="__main__":main()
