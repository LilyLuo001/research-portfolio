"""Target-relevant, bounded CRSP holding/TNA diagnostic; returns aggregates only."""
import argparse, json, subprocess
from pathlib import Path

REMOTE = r'''import duckdb, glob, hashlib, json, os, re
r="/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared"
mem=r+"/derived/p1_concentration_information/20260920/network/results/economic_date_only_membership.parquet"
top500=r+"/derived/p1_concentration_information/20260920/roster/private_top500_common_shareclasses.parquet"
top8=r+"/derived/p1_concentration_information/20260920/roster/private_top8_permno_permco.parquet"
hdr=glob.glob(r+"/raw/rescue_remaining/crsp_fund_hdr_hist_full_max/*.parquet")
summary=r+"/raw/crsp_fund_summary2_2022.parquet"
con=duckdb.connect(); con.execute("SET threads=2"); con.execute("SET memory_limit='1GB'")
q=lambda ps: "read_parquet(["+",".join("'"+x.replace("'","''")+"'" for x in ps)+"])"
con.execute(f"CREATE TEMP TABLE m AS SELECT crsp_portno,CAST(report_dt AS DATE) report_dt,CAST(TRY_CAST(permno AS DOUBLE) AS BIGINT) permno,classification FROM read_parquet('{mem}')")
con.execute(f"CREATE TEMP TABLE r500 AS SELECT DISTINCT CAST(TRY_CAST(permno AS DOUBLE) AS BIGINT) permno FROM read_parquet('{top500}')")
con.execute(f"CREATE TEMP TABLE r8 AS SELECT DISTINCT CAST(TRY_CAST(permno AS DOUBLE) AS BIGINT) permno FROM read_parquet('{top8}')")
con.execute("""CREATE TEMP TABLE cand AS SELECT m.crsp_portno,m.report_dt,
 count(DISTINCT r500.permno) receiver_count,count(DISTINCT r8.permno) issuer_count
 FROM m LEFT JOIN r500 USING(permno) LEFT JOIN r8 USING(permno)
 WHERE classification='ETF_ONLY_RECORDED_CLASSES' GROUP BY 1,2
 HAVING count(DISTINCT r500.permno)>=100""")
chosen=con.execute("SELECT crsp_portno,report_dt,receiver_count,issuer_count FROM cand ORDER BY crsp_portno,report_dt LIMIT 3").fetchall()
assert chosen, "no target-relevant ETF-only portfolios meet deterministic rule"
ids={str(int(x[0])) for x in chosen}
parts=[]
for sql in glob.glob(r+"/raw/rescue_remaining/crsp_holdings_etf_2022_b*/QUERY.sql"):
    txt=open(sql).read()
    if any(re.search(r"(?<!\\d)"+re.escape(x)+r"(?!\\d)",txt) for x in ids): parts += glob.glob(os.path.dirname(sql)+"/*.parquet")
parts=sorted(set(parts))
assert parts
con.execute("CREATE TEMP TABLE chosen(crsp_portno DOUBLE,report_dt DATE)")
con.executemany("INSERT INTO chosen VALUES (?,?)",[(x[0],x[1]) for x in chosen])
con.execute(f"""CREATE TEMP TABLE h AS SELECT h.crsp_portno,CAST(h.report_dt AS DATE) report_dt,h.percent_tna,h.market_val
 FROM {q(parts)} h JOIN chosen c ON h.crsp_portno=c.crsp_portno AND CAST(h.report_dt AS DATE)=c.report_dt""")
con.execute(f"""CREATE TEMP TABLE hm AS SELECT c.*,count(DISTINCT x.crsp_fundno) valid_fund_ids
 FROM chosen c LEFT JOIN {q(hdr)} x ON c.crsp_portno=x.crsp_portno AND CAST(x.chgdt AS DATE)<=c.report_dt
 AND (CAST(x.chgenddt AS DATE)>=c.report_dt OR x.chgenddt IS NULL) GROUP BY ALL""")
con.execute(f"""CREATE TEMP TABLE sraw AS SELECT c.crsp_portno,c.report_dt,s.crsp_fundno,s.tna_latest,
 CAST(s.tna_latest_dt AS DATE) tna_latest_dt,CAST(s.asset_dt AS DATE) asset_dt
 FROM chosen c JOIN {q([summary])} s ON c.crsp_portno=s.crsp_portno AND CAST(s.caldt AS DATE)=c.report_dt""")
con.execute("""CREATE TEMP TABLE class_tna AS SELECT crsp_portno,report_dt,crsp_fundno,
 count(DISTINCT CASE WHEN tna_latest>0 THEN tna_latest END) positive_tna_value_count,
 CASE WHEN count(DISTINCT CASE WHEN tna_latest>0 THEN tna_latest END)=1 THEN max(CASE WHEN tna_latest>0 THEN tna_latest END) END class_tna,
 min(tna_latest_dt) min_tna_latest_dt,max(tna_latest_dt) max_tna_latest_dt,min(asset_dt) min_asset_dt,max(asset_dt) max_asset_dt
 FROM sraw GROUP BY ALL""")
con.execute("""CREATE TEMP TABLE sm AS SELECT c.crsp_portno,c.report_dt,count(ct.crsp_fundno) available_same_date_fund_ids,
 count(CASE WHEN ct.class_tna>0 THEN ct.crsp_fundno END) positive_tna_ids,
 count(CASE WHEN ct.positive_tna_value_count>1 THEN ct.crsp_fundno END) conflicting_tna_fund_ids,
 sum(ct.class_tna) available_class_tna_sum,min(ct.min_tna_latest_dt) min_tna_latest_dt,max(ct.max_tna_latest_dt) max_tna_latest_dt,
 min(ct.min_asset_dt) min_asset_dt,max(ct.max_asset_dt) max_asset_dt
 FROM chosen c LEFT JOIN class_tna ct USING(crsp_portno,report_dt) GROUP BY ALL""")
con.execute("CREATE TEMP TABLE d AS SELECT h.*,hm.valid_fund_ids,sm.* FROM h JOIN hm USING(crsp_portno,report_dt) JOIN sm USING(crsp_portno,report_dt)")
one=lambda sql:con.execute(sql).fetchone()[0]
out={"status":"TARGET_RELEVANT_DIAGNOSTIC_ONLY_NO_WEIGHTED_L","selection_rule":"ETF_ONLY_RECORDED_CLASSES; >=100 distinct frozen top500 securities (the top8 are a subset); sort crsp_portno,report_dt; first 3",
 "selected_portfolio_report_dates":len(chosen),"selected_receiver_security_count":sum(x[2] for x in chosen),"selected_issuer_security_count":sum(x[3] for x in chosen),
 "source_manifest":{"membership":os.path.relpath(mem,r),"top500":os.path.relpath(top500,r),"top8":os.path.relpath(top8,r),"holding_parts":[os.path.relpath(x,r) for x in parts],"fund_summary":os.path.relpath(summary,r),"header_parts":len(hdr),"holding_part_sha256":{os.path.relpath(x,r):hashlib.sha256(open(x,'rb').read()).hexdigest() for x in parts}},
 "holdings":{"rows":one("SELECT count(*) FROM h"),"positive_market_and_percent_rows":one("SELECT count(*) FROM h WHERE market_val>0 AND percent_tna>0"),"percent_tna_null_rows":one("SELECT count(*) FROM h WHERE percent_tna IS NULL"),"market_val_null_rows":one("SELECT count(*) FROM h WHERE market_val IS NULL"),"percent_tna_gt_100_rows":one("SELECT count(*) FROM h WHERE percent_tna>100")},
 "mapping_and_tna_coverage":{"all_date_valid_fund_ids":one("SELECT sum(valid_fund_ids) FROM hm"),"portfolio_dates_with_multiple_valid_fund_ids":one("SELECT count(*) FROM hm WHERE valid_fund_ids>1"),"same_date_available_fund_ids":one("SELECT sum(available_same_date_fund_ids) FROM sm"),"conflicting_tna_fund_ids":one("SELECT sum(conflicting_tna_fund_ids) FROM sm"),"portfolio_dates_with_no_same_date_tna":one("SELECT count(*) FROM sm WHERE positive_tna_ids=0"),"tna_latest_date_equals_report_date":one("SELECT count(*) FROM sm WHERE positive_tna_ids>0 AND min_tna_latest_dt=report_dt AND max_tna_latest_dt=report_dt"),"asset_date_equals_report_date":one("SELECT count(*) FROM sm WHERE positive_tna_ids>0 AND min_asset_dt=report_dt AND max_asset_dt=report_dt")},
 "available_class_sum_diagnostic":{"label":"NOT a portfolio TNA or documented complete-class sum","eligible_rows":one("SELECT count(*) FROM d WHERE market_val>0 AND percent_tna>0 AND available_class_tna_sum>0"),"within_1pct_unscaled":one("SELECT count(*) FROM d WHERE market_val>0 AND percent_tna>0 AND available_class_tna_sum>0 AND abs((market_val/(percent_tna/100))-available_class_tna_sum)/available_class_tna_sum<=.01")},
 "documented_contract":{"percent_tna":"Security percentage of total net assets (reported percent weight)","market_val":"Security market value as of report_dt","tna_latest":"Latest month-end TNA; mirror metadata has no portfolio-to-fund-class allocation or TNA-unit statement"},
 "decision":"percent_tna supports numerical holding weight; dollar weighted L remains pending documented TNA units/denominator and allocation"}
print(json.dumps(out,sort_keys=True))'''

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",required=True,type=Path); a=ap.parse_args()
    p=subprocess.run(["ssh","-o","BatchMode=yes","scc1.bu.edu","module load python3/3.12.4 && python3 -"],input=REMOTE,text=True,capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr)
    a.out.write_text(json.dumps(json.loads(p.stdout),indent=2,sort_keys=True)+"\n")
    print(p.stdout)
if __name__=="__main__": main()
