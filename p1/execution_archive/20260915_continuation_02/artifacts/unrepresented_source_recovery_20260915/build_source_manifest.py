#!/usr/bin/env python3
import json
from pathlib import Path

ROOT="/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw"
years=list(range(2019,2027))
core_sizes=[481856,478470,527754,520665,513872,495363,477849,312800]
core_mtime=[1788333097,1788333097,1788333097,1788333098,1788333098,1788333098,1788333099,1788333099]
rescue_mtime=[1788335104,1788335105,1788335105,1788335105,1788335106,1788335106,1788335106,1788335107]
inputs=[{"path":"/projectnb/econdept/qluo/P1_Refraction_WRDS/unrepresented_source_recovery_20260915/inputs/candidates_v2.csv","verification":"sha256","sha256":"72a3c02d78458605716a23c2fce07f9a8611cb6dadd3d402c9c3d0babe1f42b3"},
{"path":ROOT+"/crsp_ibes_link_full.parquet","verification":"stat","size_bytes":606920,"mtime_epoch":1788337523,"upstream_sha256":"fd259ac817ab9ea64553e0cdacadc22fcd94de361d1f1851855f9e27ed87e326"}]
for y,s,m1,m2 in zip(years,core_sizes,core_mtime,rescue_mtime):
    inputs.append({"path":f"{ROOT}/ibes_actuals_eps_{y}.parquet","verification":"stat","size_bytes":s,"mtime_epoch":m1,"family":"CORE_IBES_ACTUALS_EPS"})
    inputs.append({"path":f"{ROOT}/rescue/ibes_allcols_actu_epsus_{y}.parquet","verification":"stat","size_bytes":s,"mtime_epoch":m2,"family":"RESCUE_ALLCOLS_ACTU_EPSUS"})
payload={"status":"PINNED_SOURCE_MANIFEST","authority":"UPDATED_ARCHIVE_MANUAL_PLUS_FINAL_SCC_MANIFEST","candidate_sha256":"72a3c02d78458605716a23c2fce07f9a8611cb6dadd3d402c9c3d0babe1f42b3","upstream_input_manifest_sha256":"54e4b8b943c5a8a8af173cf2dfaaa66590ad56d1e381f8157854cf11b6f4d9c9","upstream_full_receipt_sha256":"fa84cae932d64797e1a0b86ef8e7e94d3a5449ebe03fba8e9a435b74e9132a40","allowed_actual_columns":["ticker","cusip","pends","pdicity","anndats","anntims","actdats","acttims"],"allowed_link_columns":["permno","ncusip","sdate","edate","score"],"family_pooling":False,"inputs":inputs}
Path(__file__).with_name("source_manifest.json").write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
