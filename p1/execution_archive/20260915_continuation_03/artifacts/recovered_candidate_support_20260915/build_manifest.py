#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

ap=argparse.ArgumentParser(); ap.add_argument("--config",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
c=json.load(open(a.config)); inputs=[]
p=Path(c["protected_recovery_paths"]); inputs.append({"path":str(p),"verification":"sha256","sha256":sha(p),"size_bytes":p.stat().st_size,"mtime_epoch":int(p.stat().st_mtime)})
for y in c["forecast_years"]:
    p=Path(c["forecast_path_template"].format(year=y)); inputs.append({"path":str(p),"verification":"stat","size_bytes":p.stat().st_size,"mtime_epoch":int(p.stat().st_mtime)})
m={"status":"PINNED_RECOVERED99_SUPPORT_MANIFEST","authority":"USER_AUTHORIZED_SCC_ONLY_CENSUS_USING_EXISTING_CUSTODIAN_METADATA","source_primary":c["source_family_primary"],"source_comparison_not_pooled":c["source_family_comparison"],"allowed_forecast_columns":c["forecast_columns"],"inputs":inputs,"upstream_recovery_full_receipt_sha256":"29d4dd4e58407117effed7aaa840fd9ab2dd6d2a0affdfde3b8ebabded594092","upstream_recovery_code_sha256":"63a34f0819feb610877d3c6c9465cc887a18b4a36ba416ef11c08f3e1f6cdc87"}
Path(a.out).write_text(json.dumps(m,indent=2,sort_keys=True)+"\n")
