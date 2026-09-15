"""Build outcome-blind seed rosters from evidence-manifest E007 only.

Does not read an earnings, return, quote, or IBES data record.  A point-in-time
PERMNO--IBES bridge is catalogued separately for a custodian; this code never
uses ticker or a static identifier mapping.
"""
import argparse, csv, hashlib, json
from pathlib import Path

E007="905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320"
E011="c0c0f817068609ff4c20ef4eb21958932d35a785390733d9b5c7993475aaff4a"
KEEP=["permno","wave_id","effective_date","primary_ready","pre_report_date_min","pre_report_date_max","source_accessions"]

def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def write_csv(path, fields, rows):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--exposure",type=Path,required=True); ap.add_argument("--lineage",type=Path,required=True); ap.add_argument("--out-dir",type=Path,required=True); a=ap.parse_args()
    if sha(a.exposure)!=E007 or sha(a.lineage)!=E011: raise ValueError("E007/E011 hash mismatch; refuse roster")
    a.out_dir.mkdir(parents=True,exist_ok=False)
    allrows=[]
    with a.exposure.open(newline="") as f:
        for n,r in enumerate(csv.DictReader(f),start=2):
            x={k:r[k] for k in KEEP}; x["source_row_locator"]=f"E007:exposure_stock_wave_all.csv:line:{n}"; x["source_version"]="E007_exposure_stock_wave_all.csv"; x["source_sha256"]=E007; x["source_membership_status"]="E007_PRIMARY_READY" if r["primary_ready"]=="True" else "E007_NOT_PRIMARY_READY"; x["announcement_eligibility_status"]="UNKNOWN_NOT_EVALUATED"; x["package_mapping_status"]="WAVE_ID_DIRECT_FROM_E007"; x["_exposure_ownership"]=r["exposure_ownership"]; allrows.append(x)
    if len({(r["permno"],r["wave_id"]) for r in allrows})!=len(allrows): raise ValueError("E007 key is not unique")
    eligible=[r for r in allrows if r["primary_ready"]=="True"]
    gaps=[{"gap_type":"NOT_PRIMARY_READY","permno":r["permno"],"wave_id":r["wave_id"],"source_row_locator":r["source_row_locator"],"detail":"Retained in E007 all-row provenance but excluded from seed roster."} for r in allrows if r["primary_ready"]!="True"]
    seed_fields=KEEP+["source_row_locator","source_version","source_sha256","source_membership_status","announcement_eligibility_status","package_mapping_status"]
    write_csv(a.out_dir/"seed_stock_wave.csv",seed_fields,eligible)
    by={}
    for r in eligible: by.setdefault(r["permno"],[]).append(r)
    securities=[]
    for permno,rs in sorted(by.items(),key=lambda z:float(z[0])):
        rs=sorted(rs,key=lambda x:(x["effective_date"],x["wave_id"]))
        securities.append({"permno":permno,"first_wave_id":rs[0]["wave_id"],"first_effective_date":rs[0]["effective_date"],"last_wave_id":rs[-1]["wave_id"],"last_effective_date":rs[-1]["effective_date"],"stock_wave_row_count":len(rs),"stock_wave_manifest_path":"seed_stock_wave.csv","source_version":"E007_exposure_stock_wave_all.csv","source_sha256":E007,"source_row_locators":";".join(r["source_row_locator"] for r in rs)})
    write_csv(a.out_dir/"seed_security.csv",list(securities[0]),securities)
    gaps.append({"gap_type":"PIT_PERMNO_IBES_BRIDGE_NOT_EXECUTED","permno":"","wave_id":"","source_row_locator":"archive catalog only","detail":"Custodian must apply ibcrsphist with sdate/edate and score; no ticker/static mapping used."})
    write_csv(a.out_dir/"roster_gaps.csv",["gap_type","permno","wave_id","source_row_locator","detail"],gaps)
    bridge={"status":"CATALOGGED_NOT_EXECUTED","source":"/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw/crsp_ibes_link_full.parquet","schema_source":"meta/schema__wrdsapps_link_crsp_ibes__ibcrsphist.csv","fields":["ticker","permno","ncusip","sdate","edate","score"],"rule":"Custodian must apply point-in-time sdate/edate validity and document score policy; no static ticker or CUSIP substitution."}
    (a.out_dir/"pit_bridge_catalog.json").write_text(json.dumps(bridge,indent=2)+"\n")
    outputs={p.name:sha(p) for p in sorted(a.out_dir.iterdir()) if p.is_file()}
    doses=[r['_exposure_ownership'] for r in allrows]
    def kind(v):
        try:
            z=float(v)
            return 'negative' if z<0 else ('zero' if z==0 else 'positive')
        except (TypeError,ValueError): return 'missing_or_nonfinite'
    dose_counts={k:sum(kind(v)==k for v in doses) for k in ['missing_or_nonfinite','negative','zero','positive']}
    receipt={"status":"SEED_ROSTER_COMPLETE_BRIDGE_PENDING","E007_sha256":E007,"E011_sha256":E011,"input_rows":len(allrows),"seed_stock_wave_rows":len(eligible),"seed_security_rows":len(securities),"gap_rows":len(gaps),"exposure_ownership_status_counts":dose_counts,"outcome_fields_read":False,"outputs":outputs}
    (a.out_dir/"ROSTER_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
if __name__=="__main__": main()
