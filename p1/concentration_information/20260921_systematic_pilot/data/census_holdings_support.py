#!/usr/bin/env python3
"""SCC-only aggregate CRSP holdings support census for the frozen clock roster."""
import argparse, csv, hashlib, json
from pathlib import Path
import duckdb

MAP = {
    "Apple Inc.": ("AAPL",), "Microsoft Corp.": ("MSFT",),
    "Alphabet Inc.": ("GOOG", "GOOGL"), "Amazon.com, Inc.": ("AMZN",),
    "Berkshire Hathaway Inc.": ("BRK",), "UnitedHealth Group Inc.": ("UNH",),
    "Johnson & Johnson": ("JNJ",), "Exxon Mobil Corp.": ("XOM",),
}
CLOCK_SHA = "267f9b679e9b61245268bf70a1026e1205576ffe611e4adf5cda998bd8e90dec"

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(paths): return "read_parquet([" + ",".join(repr(str(x)) for x in paths) + "])"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--clock",required=True,type=Path)
    ap.add_argument("--root",required=True,type=Path); ap.add_argument("--out",required=True,type=Path)
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    with a.clock.open(newline="",encoding="utf-8") as f: events=list(csv.DictReader(f))
    assert digest(a.clock)==CLOCK_SHA
    assert len(events)==32 and len({x["issuer"] for x in events})==8
    assert set(x["issuer"] for x in events)==set(MAP)
    assert all(sum(x["issuer"]==issuer for x in events)==4 for issuer in MAP)
    manifest=a.root.parent/"_migration_meta/FINAL_SCC_MANIFEST.tsv"
    listed=[x.split("\t",1)[1] for x in manifest.read_text().splitlines() if "\t" in x]
    hp=[a.root/x for x in listed if x.startswith("raw/rescue_remaining/crsp_holdings_etf_2022_") or x.startswith("raw/rescue_remaining/crsp_holdings_etf_2023_") if x.endswith(".parquet")]
    fp=[a.root/x for x in listed if x.startswith("raw/rescue_remaining/crsp_fund_hdr_hist_full_max/") and x.endswith(".parquet")]
    con=duckdb.connect(); con.from_parquet([str(x) for x in hp]).create_view("hold_all"); con.from_parquet([str(x) for x in fp]).create_view("fund_all")
    con.execute("CREATE TEMP TABLE hdr AS SELECT DISTINCT crsp_portno,upper(ticker) fund_ticker FROM fund_all WHERE upper(ticker) IN ('SPY','QQQ') AND CAST(chgdt AS DATE)<=DATE '2023-12-31' AND CAST(chgenddt AS DATE)>=DATE '2022-01-01'")
    con.execute("CREATE TEMP TABLE h AS SELECT crsp_portno,CAST(report_dt AS DATE) report_dt,CAST(eff_dt AS DATE) eff_dt,upper(ticker) security_ticker,permno,percent_tna,nbr_shares FROM hold_all WHERE crsp_portno IN (SELECT crsp_portno FROM hdr)")
    con.execute("CREATE TEMP TABLE e(event_id,issuer,event_date,security_group) AS SELECT * FROM (VALUES "+",".join("("+repr(x["event_id"])+","+repr(x["issuer"])+",DATE "+repr(x["event_date"])+","+repr("|".join(MAP[x["issuer"]]))+")" for x in events)+")")
    q="""WITH x AS (SELECT hd.fund_ticker,hd.crsp_portno,e.*,(SELECT max(report_dt) FROM h WHERE h.crsp_portno=hd.crsp_portno AND report_dt<=e.event_date) report_dt FROM hdr hd CROSS JOIN e), y AS (SELECT x.*,max(h.eff_dt) max_eff_dt,count(DISTINCT h.permno) n_security_ids,count(*) FILTER(WHERE h.nbr_shares IS NOT NULL AND h.percent_tna IS NOT NULL) positions_with_units_weight,bool_or(CASE WHEN x.issuer='Berkshire Hathaway Inc.' THEN h.security_ticker LIKE 'BRK%' ELSE contains(string_split(x.security_group,'|'),h.security_ticker) END) issuer_security_group_member FROM x LEFT JOIN h ON h.crsp_portno=x.crsp_portno AND h.report_dt=x.report_dt GROUP BY ALL) SELECT fund_ticker,count(*) event_groups,count(*) FILTER(WHERE report_dt IS NULL) no_prior_report,count(*) FILTER(WHERE report_dt=event_date) calendar_date_equal_report,count(*) FILTER(WHERE report_dt IS NOT NULL AND max_eff_dt<=event_date) vendor_observed_by_event,count(*) FILTER(WHERE report_dt IS NOT NULL AND max_eff_dt>event_date) vendor_not_observed_by_event,count(*) FILTER(WHERE report_dt IS NOT NULL AND issuer_security_group_member) issuer_security_group_member,count(*) FILTER(WHERE report_dt IS NOT NULL AND issuer_security_group_member IS FALSE) issuer_security_group_not_member,count(*) FILTER(WHERE report_dt IS NULL) issuer_security_group_unknown_no_report FROM y GROUP BY fund_ticker ORDER BY fund_ticker"""
    rows=con.execute(q).fetchall(); cols=[x[0] for x in con.description]
    detail=con.execute("""WITH x AS (SELECT hd.fund_ticker,hd.crsp_portno,e.*,(SELECT max(report_dt) FROM h WHERE h.crsp_portno=hd.crsp_portno AND report_dt<=e.event_date) report_dt FROM hdr hd CROSS JOIN e) SELECT fund_ticker,event_id,issuer,event_date,report_dt FROM x ORDER BY fund_ticker,event_id""").fetchall()
    payload={"status":"CORRECTED_AUTOMATIC_CENSUS","clock_sha256":digest(a.clock),"source_manifest_sha256":digest(manifest),"clock_rows":len(events),"issuers":sorted(MAP),"issuer_to_security_group_diagnostic":MAP,"source_paths":{"holdings_parquet_count":len(hp),"header_parquet_count":len(fp),"holdings_prefixes":["raw/rescue_remaining/crsp_holdings_etf_2022_","raw/rescue_remaining/crsp_holdings_etf_2023_"],"holdings_paths":sorted(str(x.relative_to(a.root)) for x in hp),"header_paths":sorted(str(x.relative_to(a.root)) for x in fp)},"aggregate":[dict(zip(cols,r)) for r in rows],"interpretation":{"calendar_date_equal_report":"calendar equality only; not pre-event availability","eff_dt":"vendor acquisition proxy; not first-public evidence","issuer_security_group":"security-ticker membership diagnostic, not issuer-level aggregation where multiple share classes exist"},"holdings_units_and_weights_accessed":True,"financial_response_values_read":False,"raw_rows_exported":False}
    (a.out/"holdings_census_aggregate.json").write_text(json.dumps(payload,indent=2,default=str)+"\n")
    (a.out/"holdings_census_receipt.json").write_text(json.dumps({"clock_sha256":digest(a.clock),"source_manifest_sha256":digest(manifest),"code_sha256":digest(__file__),"aggregate_output":"holdings_census_aggregate.json","detail_rows_kept_private":len(detail)},indent=2)+"\n")

if __name__=="__main__": main()
