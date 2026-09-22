#!/usr/bin/env python3
"""Adapt validated SCC feature builders to the 32-date FOMC design.

Raw DBN and generated row-level parquet are deliberately SCC-only.  This
wrapper supplies a compact equity receipt to the existing directional builder
and a compact futures receipt to the existing ES builder.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
import pandas as pd
def put(p,x): Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def event_clock(path, receipt, label):
    """The reused builders index their interior window from 13:45.

    Shift it so 14:00 is fixed index 600: index zero now represents 13:50,
    which is the requested beginning of the analysis panel.  Retain only
    13:50--14:10 rather than exporting the initialization tail.
    """
    data=pd.read_parquet(path)
    data["second_index"]=data["second_index"].astype(int)-300
    data=data.loc[(data.second_index>=0)&(data.second_index<1200)].copy()
    if label == "equity":
        keys=["date","venue","symbol","grid_shift_ms","second_index"]
        expected=32*2*24*2*1200
    else:
        keys=["date","grid_shift_ms","second_index"]
        expected=32*2*1200
    if len(data)!=expected or data.duplicated(keys).any(): raise RuntimeError(f"bad {label} event-clock panel")
    data.to_parquet(path,index=False)
    meta=json.loads(Path(receipt).read_text());meta.update({"feature_sha256":digest(path),"rows":len(data),"event_clock_definition":"second_index=600 is 14:00 ET; retained [13:50,14:10)","event_clock_shift_from_reused_builder_seconds":300});put(receipt,meta)
def main():
    a=argparse.ArgumentParser();a.add_argument("--download-receipt",required=True,type=Path);a.add_argument("--equity-builder",required=True,type=Path);a.add_argument("--base-code",required=True,type=Path);a.add_argument("--es-builder",required=True,type=Path);a.add_argument("--equity-out",required=True,type=Path);a.add_argument("--es-out",required=True,type=Path);a.add_argument("--equity-receipt",required=True,type=Path);a.add_argument("--es-receipt",required=True,type=Path);x=a.parse_args()
    d=json.loads(x.download_receipt.read_text()); files=d.get("files",[]); eq=[r for r in files if r["dataset"] in {"XNAS.ITCH","ARCX.PILLAR"}]; es=[r for r in files if r["dataset"]=="GLBX.MDP3"]
    if d.get("status")!="COMPLETE_NATIVE_DBN_ON_SCC" or len(files)!=96 or len(eq)!=64 or len(es)!=32: raise RuntimeError("complete fixed FOMC 96-request receipt required")
    eq_requests=[]
    for r in eq:
        q=dict(r);q["symbols"]=list(r.get("resolved_symbols") or r["symbols"].split(";"));eq_requests.append(q)
    eq_receipt=x.equity_receipt.parent/"_FOMC_EQUITY_DOWNLOAD_RECEIPT.json"; es_receipt=x.es_receipt.parent/"_FOMC_ES_DOWNLOAD_RECEIPT.json"
    put(eq_receipt,{"status":"COMPLETE_NATIVE_DBN_ON_SCC","selected_variant":{"requests":eq_requests},"files":eq})
    put(es_receipt,{"status":"COMPLETE_NATIVE_DBN_ON_SCC","files":es})
    subprocess.run([sys.executable,str(x.equity_builder),"--base-code",str(x.base_code),"--download-receipt",str(eq_receipt),"--out",str(x.equity_out),"--receipt",str(x.equity_receipt)],check=True)
    subprocess.run([sys.executable,str(x.es_builder),"--download-receipt",str(es_receipt),"--out",str(x.es_out),"--receipt",str(x.es_receipt)],check=True)
    event_clock(x.equity_out,x.equity_receipt,"equity")
    event_clock(x.es_out,x.es_receipt,"ES")
if __name__=="__main__": main()
