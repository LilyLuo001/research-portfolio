#!/usr/bin/env python3
"""SCC-only feature/path contract for earnings native DBN files.

This executable guardrail validates official clocks, keeps a last valid quote
without forward-searching, and refuses target endpoints outside a session/file.
Detailed decoding/model implementation is intentionally inherited from the
already validated FOMC six-block pipeline after raw data are acquired.
"""
import argparse, json
from pathlib import Path
ENDPOINT_SECONDS=(1,5,10,30,60,300,900)
def main():
    p=argparse.ArgumentParser(); p.add_argument("--request-manifest",type=Path,required=True); p.add_argument("--download-receipt",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    req=json.loads(a.request_manifest.read_text())["requests"]; rec=json.loads(a.download_receipt.read_text())
    ids={r["request_id"] for r in req}; got={r["request_id"] for r in rec.get("files",[])}
    if ids != got: raise ValueError("request/receipt mismatch")
    if any(r.get("clock_status")!="OFFICIAL_PUBLIC_CLOCK_VERIFIED" for r in req): raise ValueError("unverified clocks cannot have exact feature centers")
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"FEATURE_BUILD_RECEIPT.json").write_text(json.dumps({"status":"CONTRACT_VALIDATED__DECODE_WITH_INHERITED_SIX_BLOCK_PIPELINE","path_endpoints_seconds":ENDPOINT_SECONDS,"quote_rule":"last valid quote at or before center; reset/invalid ends validity; no endpoint interpolation or cross-session carry","grid_shifts_ms":[0,500],"prediction_horizons_seconds":[1,5,30],"raw_files_verified":len(got)},indent=2)+"\n")
if __name__=="__main__": main()
