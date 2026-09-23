#!/usr/bin/env python3
"""Quote/download SCC-only earnings windows with no credential serialization.

Input requests must already have an official public clock and be de-duplicated
by dataset/date/UTC range.  The downloader refuses overwrite and writes a
receipt before each submission so a failed run cannot silently repurchase.
"""
import argparse, hashlib, json, os
from decimal import Decimal
from pathlib import Path
import databento as db
SOURCE_TICKER={"CMI":"CUM","CVS":"MES","EBAY":"EBY1","NWSA":"NWSV"}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p, x): Path(p).parent.mkdir(parents=True, exist_ok=True); Path(p).write_text(json.dumps(x, indent=2, sort_keys=True)+"\n")
def client():
    key=os.getenv("DATABENTO_API_KEY")
    if not key: raise RuntimeError("DATABENTO_API_KEY absent from authenticated SCC environment")
    return db.Historical(key)
def load(p):
    x=json.loads(Path(p).read_text()); rows=x.get("requests_detail", x.get("requests", []))
    if not isinstance(rows,list) or not rows:
        raise ValueError("manifest needs a nonempty requests_detail/request list")
    if x.get("clock_warning") or any(r.get("clock_status") not in (None,"OFFICIAL_PUBLIC_CLOCK_VERIFIED") for r in rows):
        raise ValueError("refusing quote until the manifest removes candidate-clock warning and records official public clocks")
    if any(r.get("schema") != "mbp-1" or r.get("dataset") not in {"XNAS.ITCH","ARCX.PILLAR","GLBX.MDP3"} for r in rows):
        raise ValueError("only native mbp-1 XNAS/ARCX/GLBX requests are permitted")
    for r in rows:
        r["start"] = r.get("start", r.get("start_utc")); r["end"] = r.get("end", r.get("end_utc"))
        if isinstance(r.get("symbols"),str): r["symbols"] = r["symbols"].split(";")
        if r["dataset"] in {"XNAS.ITCH","ARCX.PILLAR"}:
            r["symbols"]=[SOURCE_TICKER.get(s,s) for s in r["symbols"]]
    return rows
def quote(manifest, out):
    rows=load(manifest); c=client(); ans=[]
    for r in rows:
        spec={k:r[k] for k in ("dataset","schema","symbols","stype_in","start","end")}
        ans.append(dict(r, quoted_cost_usd=str(Decimal(str(c.metadata.get_cost(**spec)))), estimated_record_count=int(c.metadata.get_record_count(**spec))))
    put(out,{"status":"QUOTED_NO_DOWNLOAD","manifest_sha256":sha(manifest),"total_quoted_cost_usd":str(sum((Decimal(r["quoted_cost_usd"]) for r in ans),Decimal(0))),"requests":ans})
def download(manifest, quote_path, raw_root):
    q=json.loads(Path(quote_path).read_text())
    if q.get("manifest_sha256") != sha(manifest) or q.get("status") != "QUOTED_NO_DOWNLOAD": raise ValueError("matching quote receipt required")
    c=client(); done=[]; raw_root=Path(raw_root)
    for r in q["requests"]:
        target=raw_root/(r["request_id"]+".dbn.zst"); state={**r,"path":str(target)}
        if target.exists() and target.stat().st_size: state.update(status="REUSED_EXISTING_NATIVE_DBN_ON_SCC",bytes=target.stat().st_size,sha256=sha(target)); done.append(state); continue
        if target.exists(): raise RuntimeError(f"refusing overwrite/recharge risk: {target}")
        raw_root.mkdir(parents=True,exist_ok=True); state["status"]="SUBMISSION_STARTED_NO_RETRY"; done.append(state); put(raw_root/"DOWNLOAD_RECEIPT.json",{"status":"IN_PROGRESS","manifest_sha256":sha(manifest),"files":done})
        c.timeseries.get_range(dataset=r["dataset"],schema=r["schema"],symbols=r["symbols"],stype_in=r["stype_in"],start=r["start"],end=r["end"],path=target)
        state.update(status="DOWNLOADED_NATIVE_DBN_ON_SCC",bytes=target.stat().st_size,sha256=sha(target))
    put(raw_root/"DOWNLOAD_RECEIPT.json",{"status":"COMPLETE_NATIVE_DBN_ON_SCC","manifest_sha256":sha(manifest),"quote_sha256":sha(quote_path),"quoted_total_usd":q["total_quoted_cost_usd"],"files":done})
def main():
    p=argparse.ArgumentParser(); p.add_argument("mode",choices=("quote","download")); p.add_argument("--manifest",required=True); p.add_argument("--out"); p.add_argument("--quote-receipt"); p.add_argument("--raw-root"); a=p.parse_args()
    if a.mode=="quote":
        if not a.out: raise ValueError("quote needs --out")
        quote(a.manifest,a.out)
    else:
        if not a.quote_receipt or not a.raw_root: raise ValueError("download needs --quote-receipt and --raw-root")
        download(a.manifest,a.quote_receipt,a.raw_root)
if __name__ == "__main__": main()
