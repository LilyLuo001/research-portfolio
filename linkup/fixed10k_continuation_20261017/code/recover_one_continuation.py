#!/usr/bin/env python3
"""One locator-bound source recovery; no search, new context, or ledger mutation."""
import argparse, datetime as dt, hashlib, importlib.util, json, os
from pathlib import Path
import pyarrow.parquet as pq

def rows(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]
def save(p, obj, lines=False):
    p=Path(p); p.parent.mkdir(parents=True, exist_ok=True); t=Path(str(p)+".tmp")
    with open(t,"w",encoding="utf-8") as f:
        if lines:
            for x in obj: f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")
        else: json.dump(obj,f,ensure_ascii=False,indent=2)
    os.chmod(str(t),0o600); os.replace(str(t),str(p))
def main():
    p=argparse.ArgumentParser()
    for n in ("record-id","manifest","packet","source-map","normalizer","register","receipt"):
        p.add_argument("--"+n,required=True)
    a=p.parse_args(); marker=Path(a.receipt+".started")
    if marker.exists() or Path(a.receipt).exists(): raise RuntimeError("single recovery already attempted")
    m=next(x for x in rows(a.manifest) if x["record_id"]==a.record_id)
    q=next(x for x in rows(a.packet) if x["record_id"]==a.record_id)
    if m["context_sha256"]!=q["context_sha256"]: raise RuntimeError("source binding mismatch")
    save(marker,{"attempts":1,"record_id":a.record_id,"utc":dt.datetime.now(dt.timezone.utc).isoformat()})
    key=m["representative_canonical_key"]; status="unrecoverable"; detail={}
    try:
        mapping={x["SOURCE_FILE"]:x["path"] for x in rows(a.source_map)}
        source=Path(mapping[str(key["SOURCE_FILE"])])
        if not source.is_file(): raise FileNotFoundError("frozen source locator unavailable")
        pf=pq.ParquetFile(source); index=int(key["SOURCE_ROW"]); offset=0; raw=None
        for rg in range(pf.metadata.num_row_groups):
            n=pf.metadata.row_group(rg).num_rows
            if offset<=index<offset+n:
                raw=pf.read_row_group(rg,columns=["JOB_HASH","DESCRIPTION"]).slice(index-offset,1).to_pylist()[0]; break
            offset+=n
        if raw is None or str(raw["JOB_HASH"])!=str(key["JOB_HASH"]): raise RuntimeError("source identity mismatch")
        spec=importlib.util.spec_from_file_location("frozen",a.normalizer); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        normalized=mod._normalize_with_flags(raw["DESCRIPTION"]); normalized=normalized[0] if isinstance(normalized,tuple) else normalized
        detail={"source_characters":len(normalized),"packet_characters":len(q["full_document"]),"same_context":hashlib.sha256(normalized.encode()).hexdigest()==q["context_sha256"]}
        if len(normalized)>len(q["full_document"]):
            status="recovery_candidate_requires_adjudication"
            save(a.receipt+".candidate.json",{"record_id":a.record_id,"source_text":normalized})
    except (FileNotFoundError,KeyError) as exc: detail={"reason":str(exc),"raw_row_read":False}
    receipt={"record_id":a.record_id,"status":status,"attempts":1,"comparison":detail,"utc":dt.datetime.now(dt.timezone.utc).isoformat()}
    if status=="unrecoverable":
        register=rows(a.register)
        if any(x["normalized_context_sha256"]==q["context_sha256"] for x in register): raise RuntimeError("already isolated")
        register.append({"record_id":a.record_id,"normalized_context_sha256":q["context_sha256"],"status":"source_truncated_unrecoverable","work_queue_excluded":True,"ledger_changed":False,"recovery_attempts":1,"isolation_batch":m["batch_number"]})
        save(a.register,register,True)
    save(a.receipt,receipt)
if __name__=="__main__": main()
