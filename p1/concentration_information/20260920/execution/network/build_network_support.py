"""SCC-only, outcome-blind coholding support. This does NOT calculate weighted L.

Reads explicit identity/date fields; row-level licensed outputs remain on SCC.
Run with python3/3.12.4. No source writes, credentials, or network APIs.
"""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb


def quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--root", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--securities", help="Optional SCC roster CSV: permno, permco, company_rank")
    a.add_argument("--smoke", action="store_true", help="Only first holdings partition; NOT population counts")
    args = a.parse_args()
    root, out = Path(args.root), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = root.parent / "_migration_meta/FINAL_SCC_MANIFEST.tsv"
    listed = [line.split("\t", 1)[1] for line in manifest.read_text().splitlines()]
    paths = [root / p for p in listed if p.startswith("raw/rescue_remaining/crsp_holdings_etf_2022_") and p.endswith(".parquet")]
    headers = [root / p for p in listed if p.startswith("raw/rescue_remaining/crsp_fund_hdr_hist_full_max/") and p.endswith(".parquet")]
    assert paths and headers
    if args.smoke:
        paths = paths[:1]
    assert all(p.is_file() for p in paths + headers)
    con = duckdb.connect()
    con.execute("SET threads=2")
    con.execute("SET memory_limit='2GB'")
    def rel(ps):
        return "read_parquet([" + ",".join(quote(p) for p in ps) + "])"
    # Preserve raw physical row count; logical duplicates are removed only in projection.
    con.execute(f"""CREATE TEMP TABLE h AS SELECT crsp_portno,CAST(report_dt AS DATE) report_dt,CAST(eff_dt AS DATE) eff_dt,permno
      FROM {rel(paths)} WHERE CAST(report_dt AS DATE) BETWEEN DATE '2022-09-01' AND DATE '2022-12-30'""")
    con.execute(f"""CREATE TEMP TABLE cl AS SELECT DISTINCT crsp_portno,crsp_fundno,et_flag
      FROM {rel(headers)} WHERE CAST(chgdt AS DATE) <= DATE '2022-12-30'
      AND (CAST(chgenddt AS DATE) >= DATE '2022-12-30' OR chgenddt IS NULL)""")
    con.execute("""CREATE TEMP TABLE pc AS SELECT crsp_portno,
      count(DISTINCT crsp_fundno) class_count,
      count(DISTINCT CASE WHEN et_flag='F' THEN crsp_fundno END) etf_classes,
      count(DISTINCT CASE WHEN et_flag IS NULL OR et_flag<>'F' THEN crsp_fundno END) other_classes,
      CASE WHEN count(DISTINCT CASE WHEN et_flag='F' THEN crsp_fundno END)>0
        AND count(DISTINCT CASE WHEN et_flag IS NULL OR et_flag<>'F' THEN crsp_fundno END)=0
      THEN 'ETF_ONLY_RECORDED_CLASSES' WHEN count(DISTINCT CASE WHEN et_flag='F' THEN crsp_fundno END)>0
      THEN 'MIXED_RECORDED_CLASSES' ELSE 'NO_ETF_RECORDED_CLASS' END classification
      FROM cl GROUP BY crsp_portno""")
    summary = {
      "status": "IDENTITY_SUPPORT_ONLY_NOT_WEIGHTED_NETWORK",
      "smoke_only_not_population": args.smoke,
      "economic_cutoff": "2022-12-30", "max_report_age_calendar_days": 120,
      "selection": "Latest report per portfolio in bounded Sep01-Dec30 source window; no daily interpolation",
      "holdings_files": len(paths), "historical_header_files": len(headers),
      "holdings_file_bytes": sum(p.stat().st_size for p in paths),
      "source_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
      "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      "source_rows_in_date_window": con.execute("SELECT count(*) FROM h").fetchone()[0],
      "historical_classification": "Recorded classes only; completeness and historical leverage/asset-type not certified",
      "availability": "eff_dt is vendor acquisition date, NOT independently verified public disclosure timestamp",
      "weighted_L": "NOT_RUN_UNVERIFIED_UNITS_DENOMINATOR_CLASS_ALLOCATION",
      "outcome_columns_read": [], "cohorts": {},
      "sources": [str(p.relative_to(root)) for p in paths + headers],
    }
    for cohort, condition in [("economic_date_only", "TRUE"), ("vendor_observed_by_cutoff", "count(eff_dt)=count(*) AND max(eff_dt) <= DATE '2022-12-30'")]:
        con.execute(f"""CREATE OR REPLACE TEMP TABLE selected AS WITH eligible AS
          (SELECT crsp_portno,report_dt FROM h GROUP BY crsp_portno,report_dt HAVING {condition}), dates AS
          (SELECT crsp_portno,max(report_dt) report_dt FROM eligible GROUP BY crsp_portno)
          SELECT DISTINCT h.crsp_portno,h.report_dt,h.permno FROM h JOIN dates USING(crsp_portno,report_dt)
          """)
        con.execute("""CREATE OR REPLACE TEMP TABLE selected_class AS SELECT s.*,
          coalesce(pc.classification,'UNKNOWN_HEADER') classification FROM selected s LEFT JOIN pc USING(crsp_portno)""")
        d = {"portfolios": con.execute("SELECT count(DISTINCT crsp_portno) FROM selected").fetchone()[0],
             "portfolio_security_projection_rows": con.execute("SELECT count(*) FROM selected").fetchone()[0],
             "missing_permno_projection_rows": con.execute("SELECT count(*) FROM selected WHERE permno IS NULL").fetchone()[0],
             "portfolio_classification_counts": dict(con.execute("SELECT classification,count(DISTINCT crsp_portno) FROM selected_class GROUP BY classification").fetchall())}
        # Do not export held-security identifiers to local summaries.
        con.execute(f"COPY selected_class TO {quote(out / (cohort + '_membership.parquet'))} (FORMAT PARQUET)")
        if args.securities:
            con.execute(f"CREATE OR REPLACE TEMP TABLE roster AS SELECT DISTINCT permno,permco,company_rank FROM read_csv_auto({quote(args.securities)})")
            assert con.execute("SELECT count(*)=count(DISTINCT permno) FROM roster").fetchone()[0]
            con.execute("""CREATE OR REPLACE TEMP TABLE links AS SELECT DISTINCT s.crsp_portno,s.classification,r.permco,r.company_rank
              FROM selected_class s JOIN roster r USING(permno)""")
            con.execute("""CREATE OR REPLACE TEMP TABLE pairs AS SELECT a.permco issuer_permco,b.permco receiver_permco,a.classification,
              count(DISTINCT a.crsp_portno) shared_recorded_portfolios FROM links a JOIN links b USING(crsp_portno)
              WHERE a.company_rank<=8 AND b.company_rank<=500 AND a.permco<>b.permco
              GROUP BY a.permco,b.permco,a.classification""")
            d["roster_companies_held"] = con.execute("SELECT count(DISTINCT permco) FROM links").fetchone()[0]
            d["issuer_receiver_pairs_any_recorded_class"] = con.execute("SELECT count(*) FROM (SELECT DISTINCT issuer_permco,receiver_permco FROM pairs)").fetchone()[0]
            d["pairs_by_recorded_portfolio_class"] = dict(con.execute("SELECT classification,count(*) FROM pairs GROUP BY classification").fetchall())
            con.execute(f"COPY pairs TO {quote(out / (cohort + '_pair_support.parquet'))} (FORMAT PARQUET)")
        summary["cohorts"][cohort] = d
    if not args.securities:
        summary["roster_join"] = "PENDING_ROSTER_OUTPUT"
    else:
        summary["roster_join"] = "EXECUTED_IDENTITY_SUPPORT_NOT_ANALYSIS_ELIGIBILITY"
        summary["roster_input"] = args.securities
    (out / "NETWORK_SUPPORT.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k != "sources"}, indent=2))


if __name__ == "__main__":
    main()
