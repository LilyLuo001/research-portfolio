"""Run a bounded, outcome-blind CRSP holdings unit-contract check on SCC.

Only aggregate diagnostics return locally.  No raw rows, identifiers, estimates,
returns, or quote data leave SCC.  This is deliberately not a weighted-network
calculation: it tests whether the ingredients have compatible documented fields
and dates before any L is attempted.
"""
import argparse
import json
import subprocess
from pathlib import Path


REMOTE = r'''import duckdb, glob, hashlib, json, os
root = "/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared"
hpaths = glob.glob(root + "/raw/rescue_remaining/crsp_holdings_etf_2022_b0001/*.parquet")
sp = root + "/raw/crsp_fund_summary2_2022.parquet"
hp = glob.glob(root + "/raw/rescue_remaining/crsp_fund_hdr_hist_full_max/*.parquet")
assert len(hpaths) == 1 and os.path.isfile(sp) and hp
con = duckdb.connect()
con.execute("SET threads=2")
con.execute("SET memory_limit='1GB'")
q = lambda paths: "read_parquet([" + ",".join("'" + p.replace("'", "''") + "'" for p in paths) + "])"
con.execute(f"""CREATE TEMP TABLE h AS
 SELECT crsp_portno, CAST(report_dt AS DATE) report_dt, security_rank,
        percent_tna, market_val
 FROM {q(hpaths)}
 WHERE CAST(report_dt AS DATE) BETWEEN DATE '2022-09-01' AND DATE '2022-12-30' """)
con.execute(f"""CREATE TEMP TABLE hdr AS
 SELECT crsp_portno, crsp_fundno, et_flag, CAST(chgdt AS DATE) chgdt,
        CAST(chgenddt AS DATE) chgenddt
 FROM {q(hp)} """)
con.execute(f"""CREATE TEMP TABLE s AS
 SELECT crsp_portno, crsp_fundno, CAST(caldt AS DATE) caldt,
        tna_latest, CAST(tna_latest_dt AS DATE) tna_latest_dt,
        CAST(asset_dt AS DATE) asset_dt, et_flag
 FROM {q([sp])} """)
con.execute("CREATE TEMP TABLE hd AS SELECT DISTINCT crsp_portno, report_dt FROM h")
con.execute("""CREATE TEMP TABLE hm AS SELECT hd.*, count(hdr.crsp_fundno) mapping_rows,
 count(DISTINCT hdr.crsp_fundno) class_count,
 count(DISTINCT CASE WHEN hdr.et_flag='F' THEN hdr.crsp_fundno END) etf_class_count
 FROM hd LEFT JOIN hdr ON hd.crsp_portno=hdr.crsp_portno AND hdr.chgdt<=hd.report_dt
 AND (hdr.chgenddt>=hd.report_dt OR hdr.chgenddt IS NULL) GROUP BY hd.crsp_portno,hd.report_dt""")
con.execute("""CREATE TEMP TABLE hs AS SELECT h.*, hm.class_count, hm.etf_class_count,
 count(s.crsp_fundno) same_date_summary_rows,
 count(DISTINCT s.crsp_fundno) same_date_summary_classes,
 count(DISTINCT CASE WHEN s.tna_latest IS NOT NULL AND s.tna_latest>0 THEN s.crsp_fundno END) positive_tna_classes,
 min(s.tna_latest) min_tna, max(s.tna_latest) max_tna,
 min(s.tna_latest_dt) min_tna_dt, max(s.tna_latest_dt) max_tna_dt,
 min(s.asset_dt) min_asset_dt, max(s.asset_dt) max_asset_dt
 FROM h LEFT JOIN hm USING(crsp_portno,report_dt) LEFT JOIN s ON h.crsp_portno=s.crsp_portno AND h.report_dt=s.caldt
 GROUP BY ALL""")
def one(sql): return con.execute(sql).fetchone()[0]
def groups(sql): return dict(con.execute(sql).fetchall())
out = {
      "status": "B0001_NEGATIVE_CONTROL_NOT_TARGET_REPRESENTATIVE",
 "scope": {"holdings_partition": "raw/rescue_remaining/crsp_holdings_etf_2022_b0001/part_00001.parquet", "report_date_window": "2022-09-01..2022-12-30", "outcome_fields_read": []},
 "source_manifest": {"holdings": [os.path.relpath(x,root) for x in hpaths], "fund_summary": os.path.relpath(sp,root), "fund_header_parts": [os.path.relpath(x,root) for x in hp],
   "sha256": {"holdings": hashlib.sha256(open(hpaths[0],"rb").read()).hexdigest(), "fund_summary": hashlib.sha256(open(sp,"rb").read()).hexdigest(), "header_paths": hashlib.sha256("\\n".join(hp).encode()).hexdigest()}},
 "holdings": {"rows": one("SELECT count(*) FROM h"), "portfolio_report_dates": one("SELECT count(*) FROM hd"),
  "positive_market_and_percent_rows": one("SELECT count(*) FROM h WHERE market_val>0 AND percent_tna>0"),
  "percent_tna_gt_100_rows": one("SELECT count(*) FROM h WHERE percent_tna>100"),
  "percent_tna_le_1_rows": one("SELECT count(*) FROM h WHERE percent_tna>0 AND percent_tna<=1"),
  "market_value_null_rows": one("SELECT count(*) FROM h WHERE market_val IS NULL"),
  "percent_tna_null_rows": one("SELECT count(*) FROM h WHERE percent_tna IS NULL")},
 "date_valid_class_mapping": {"by_class_count": groups("SELECT coalesce(CAST(class_count AS VARCHAR),'0'),count(*) FROM hm GROUP BY class_count"),
  "no_mapping": one("SELECT count(*) FROM hm WHERE coalesce(class_count,0)=0"), "multi_class": one("SELECT count(*) FROM hm WHERE class_count>1")},
 "same_report_date_summary_match": {"no_summary": one("SELECT count(*) FROM hs WHERE same_date_summary_classes=0"), "one_summary_class": one("SELECT count(*) FROM hs WHERE same_date_summary_classes=1"), "multi_summary_class": one("SELECT count(*) FROM hs WHERE same_date_summary_classes>1"),
  "positive_tna_available": one("SELECT count(*) FROM hs WHERE positive_tna_classes>0"),
  "same_date_tna_range_disagreement": one("SELECT count(*) FROM hs WHERE positive_tna_classes>1 AND min_tna<>max_tna"),
  "tna_date_not_report_date": one("SELECT count(*) FROM hs WHERE positive_tna_classes>0 AND (min_tna_dt<>report_dt OR max_tna_dt<>report_dt)"),
  "asset_date_not_report_date": one("SELECT count(*) FROM hs WHERE positive_tna_classes>0 AND (min_asset_dt<>report_dt OR max_asset_dt<>report_dt)")},
 "ratio_diagnostic": {"formula": "implied_denominator = market_val / (percent_tna / 100); only mathematical check, not a documented unit inference",
  "eligible_rows": one("SELECT count(*) FROM hs WHERE market_val>0 AND percent_tna>0 AND positive_tna_classes>0"),
  "class_tna_within_1pct_of_implied": one("SELECT count(*) FROM hs WHERE market_val>0 AND percent_tna>0 AND positive_tna_classes>0 AND min_tna>0 AND abs((market_val/(percent_tna/100))-min_tna)/min_tna<=.01"),
  "class_tna_within_1pct_of_implied_x1000": one("SELECT count(*) FROM hs WHERE market_val>0 AND percent_tna>0 AND positive_tna_classes>0 AND min_tna>0 AND abs((market_val/(percent_tna/100))-(min_tna*1000))/(min_tna*1000)<=.01"),
  "multi_class_tna_range_over_1pct": one("SELECT count(*) FROM hs WHERE market_val>0 AND percent_tna>0 AND positive_tna_classes>1 AND min_tna>0 AND (max_tna-min_tna)/min_tna>.01")},
 "decision": "NO_GLOBAL_WEIGHTED_L_INFERENCE_FROM_NONREPRESENTATIVE_NEGATIVE_CONTROL"
}
print(json.dumps(out, sort_keys=True))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    cmd = ["ssh", "-o", "BatchMode=yes", "scc1.bu.edu", "module load python3/3.12.4 && python3 -"]
    proc = subprocess.run(cmd, input=REMOTE, text=True, capture_output=True, check=True)
    data = json.loads(proc.stdout)
    args.out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
