#!/usr/bin/env python3
"""Materialize the first accepted Batch002 group on a scheduled cluster node."""
import argparse, hashlib, json
from pathlib import Path

def strict(path, expected):
    lines=path.read_text(encoding="utf-8").splitlines()
    if len(lines)!=expected or any(not x for x in lines): raise SystemExit(f"{path}: expected {expected} nonblank lines")
    return lines,[json.loads(x) for x in lines]
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source128",type=Path,required=True); ap.add_argument("--reference128",type=Path,required=True); ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args(); sl,sr=strict(a.source128,128); rl,rr=strict(a.reference128,128)
    if any(set(x)!={"record_id","original_text"} for x in sr): raise SystemExit("unexpected source shape")
    if any(not isinstance(x,dict) or not isinstance(x.get("objects"),list) for x in rr): raise SystemExit("reference is not an accepted field-candidate shape")
    for i,(s,r) in enumerate(zip(sr,rr),1):
        h=hashlib.sha256(s["original_text"].encode()).hexdigest()
        if str(r.get("record_id"))!=str(s["record_id"]) or r.get("source_text_sha256")!=h or r.get("processing_position_1based")!=i:
            raise SystemExit(f"reference binding mismatch at row {i}")
    a.output.mkdir(parents=True,exist_ok=False)
    source=a.output/"SOURCE32_PRIVATE.jsonl"; reference=a.output/"REFERENCE32_FINAL_CANDIDATES_PRIVATE.jsonl"
    source.write_text("\n".join(sl[:32])+"\n",encoding="utf-8"); reference.write_text("\n".join(rl[:32])+"\n",encoding="utf-8")
    (a.output/"PREPARE_RECEIPT_PRIVATE.json").write_text(json.dumps({"schema_version":"linkup-cpu-fixed32-prep-v1","selection":"Batch002 accepted processing positions 1-32, preserving order","source128_sha256":digest(a.source128),"reference128_sha256":digest(a.reference128),"source32_sha256":digest(source),"reference32_sha256":digest(reference),"records":32},indent=2,sort_keys=True)+"\n",encoding="utf-8")
if __name__=="__main__": main()
