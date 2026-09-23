#!/usr/bin/env python3
"""Receipt-backed SCC reuse audit for bounded earnings requests.

A same-date DBN filename is not sufficient to claim reuse.  A file is reusable
only when a prior receipt identifies the same dataset and a time span enclosing
the requested span.  Otherwise it is reported as a non-reusable lead, which
prevents both hidden gaps and duplicate paid submissions.
"""
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""): h.update(block)
    return h.hexdigest()
def timestamp(x): return datetime.fromisoformat(str(x).replace("Z","+00:00"))
def receipt_files(root):
    for p in Path(root).rglob("*.json"):
        try: data=json.loads(p.read_text())
        except Exception: continue
        files=data.get("files",[]) if isinstance(data,dict) else []
        if isinstance(files,list):
            for r in files:
                if isinstance(r,dict): yield p,r
def interval(row):
    start=row.get("start_utc",row.get("start")); end=row.get("end_utc",row.get("end"))
    return (timestamp(start),timestamp(end)) if start and end else (None,None)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",type=Path,required=True); ap.add_argument("--search-root",type=Path,required=True); ap.add_argument("--out",type=Path,required=True); a=ap.parse_args()
    m=json.loads(a.manifest.read_text()); req=m.get("requests_detail",m.get("requests",[]))
    if not isinstance(req,list): raise ValueError("manifest needs requests_detail list")
    prior=list(receipt_files(a.search_root)); result=[]
    for r in req:
        rs,re=interval(r); same_date=[]; reusable=[]
        for receipt, old in prior:
            if old.get("dataset") != r.get("dataset"): continue
            path=old.get("path")
            if path and Path(path).is_file() and str(r.get("date","")) in str(old.get("date",path)):
                same_date.append((receipt,old))
            os,oe=interval(old)
            if path and Path(path).is_file() and os and oe and os<=rs and oe>=re:
                reusable.append((receipt,old))
        if reusable:
            receipt,old=reusable[0]; state="REUSABLE_VERIFIED_BY_PRIOR_RECEIPT"; evidence={"receipt":str(receipt),"path":old["path"],"sha256":digest(old["path"])}
        elif same_date:
            state="EXISTING_SAME_DATE_FILE_UNVERIFIED_RANGE__DO_NOT_REUSE"; evidence={"same_date_file_count":len(same_date)}
        else:
            state="NO_PRIOR_RECEIPT_BACKED_FILE_FOUND"; evidence={}
        result.append({"request_id":r["request_id"],"dataset":r["dataset"],"date":r["date"],"status":state,"evidence":evidence})
    counts={}
    for x in result: counts[x["status"]]=counts.get(x["status"],0)+1
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps({"status":"COMPLETE","manifest_sha256":digest(a.manifest),"search_root":str(a.search_root),"request_count":len(result),"counts":counts,"requests":result,"rule":"reuse requires receipt-backed same-dataset enclosing UTC interval; filename/date alone is insufficient"},indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
