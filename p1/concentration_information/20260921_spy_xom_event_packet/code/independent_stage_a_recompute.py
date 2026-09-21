#!/usr/bin/env python3
"""Independent SCC-only recomputation of decisive Stage-A metadata counts.

No forecast, actual EPS, quote price, quote size, or raw licensed row is read
or exported.  The queries are deliberately separate from stage_a_scc_probe.py.
"""
import glob
import json
from pathlib import Path

import duckdb


ROOT = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared")
OUT = Path("/scratch/qluo/spy_xom_event_packet_20260921/independent_stage_a_recompute.json")


def main():
    holdings = sorted(
        glob.glob(str(ROOT / "raw/rescue_remaining/crsp_holdings_etf_2022_*/part_*.parquet"))
        + glob.glob(str(ROOT / "raw/rescue_remaining/crsp_holdings_etf_2023_*/part_*.parquet"))
    )
    paths_sql = "[" + ",".join(repr(path) for path in holdings) + "]"
    con = duckdb.connect()
    con.execute(f"""CREATE VIEW h AS SELECT
      report_dt,eff_dt,crsp_portno,permno,nbr_shares
      FROM read_parquet({paths_sql})""")
    detail = ROOT / "raw/ibes_detu_eps_2023.parquet"
    actual = ROOT / "raw/ibes_actuals_eps_2023.parquet"
    con.execute(f"""CREATE VIEW d AS SELECT
      cusip,fpedats,measure,anndats,actdats,acttims,
      analys,estimator,fpi,curr
      FROM read_parquet({str(detail)!r})""")
    con.execute(f"""CREATE VIEW a AS SELECT
      cusip,pends,measure,pdicity,anndats
      FROM read_parquet({str(actual)!r})""")

    prior = con.execute("""
      SELECT max(CAST(report_dt AS DATE)) FROM h
      WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)<DATE '2023-01-31'
    """).fetchone()[0]
    snapshots = con.execute("""
      SELECT CAST(report_dt AS VARCHAR), CAST(min(eff_dt) AS VARCHAR),
        CAST(max(eff_dt) AS VARCHAR), count(*), count(DISTINCT permno),
        count(*) FILTER (WHERE permno IS NULL)
      FROM h WHERE crsp_portno=1021980
        AND CAST(report_dt AS DATE) IN (?, DATE '2023-01-31')
      GROUP BY report_dt ORDER BY report_dt
    """, [prior]).fetchall()
    identity_change = con.execute("""
      WITH p AS (SELECT DISTINCT permno FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)=? AND permno IS NOT NULL),
      s AS (SELECT DISTINCT permno FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)=DATE '2023-01-31' AND permno IS NOT NULL)
      SELECT
        (SELECT count(*) FROM (SELECT permno FROM p INTERSECT SELECT permno FROM s)),
        (SELECT count(*) FROM (SELECT permno FROM p EXCEPT SELECT permno FROM s)),
        (SELECT count(*) FROM (SELECT permno FROM s EXCEPT SELECT permno FROM p))
    """, [prior]).fetchone()
    ratios = con.execute("""
      WITH p AS (SELECT permno,sum(nbr_shares) shares FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)=? AND permno IS NOT NULL GROUP BY permno),
      s AS (SELECT permno,sum(nbr_shares) shares FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)=DATE '2023-01-31' AND permno IS NOT NULL GROUP BY permno)
      SELECT count(*), count(DISTINCT round(s.shares/p.shares,10))
      FROM p JOIN s USING (permno)
      WHERE p.shares IS NOT NULL AND s.shares IS NOT NULL AND p.shares<>0
    """, [prior]).fetchone()
    ibes = con.execute("""
      WITH ap AS (
        SELECT DISTINCT cusip,pends,measure FROM a
        WHERE upper(trim(cusip))='30231G10'
          AND CAST(anndats AS DATE)=DATE '2023-01-31'
          AND upper(trim(measure))='EPS' AND upper(trim(pdicity))='QTR'
      ), eligible AS (
        SELECT d.analys,d.estimator,d.fpi,d.curr
        FROM d JOIN ap ON upper(trim(d.cusip))=upper(trim(ap.cusip))
          AND d.fpedats=ap.pends AND upper(trim(d.measure))=upper(trim(ap.measure))
        WHERE CAST(d.anndats AS DATE) BETWEEN DATE '2022-11-02' AND DATE '2023-01-31'
          AND (CAST(d.actdats AS DATE)<DATE '2023-01-31'
            OR (CAST(d.actdats AS DATE)=DATE '2023-01-31' AND CAST(d.acttims AS TIME)<=TIME '06:30:00'))
      )
      SELECT
        (SELECT count(*) FROM a WHERE upper(trim(cusip))='30231G10' AND CAST(anndats AS DATE)=DATE '2023-01-31' AND upper(trim(measure))='EPS'),
        (SELECT count(*) FROM ap),
        (SELECT CAST(min(pends) AS VARCHAR) FROM ap),
        (SELECT CAST(max(pends) AS VARCHAR) FROM ap),
        count(*),
        count(DISTINCT analys || '|' || estimator), count(DISTINCT fpi),
        count(*) FILTER (WHERE curr IS NULL)
      FROM eligible
    """).fetchone()

    result = {
        "scope": "independent Stage-A aggregate-only recomputation; no values",
        "holdings_files": len(holdings),
        "latest_strictly_prior_report_dt": str(prior),
        "snapshots": [
            dict(zip(["report_dt", "min_eff_dt", "max_eff_dt", "rows", "valid_security_ids", "missing_security_id_rows"], row))
            for row in snapshots
        ],
        "valid_id_overlap_drop_add": dict(zip(["overlap", "dropped", "added"], identity_change)),
        "share_ratio_diagnostic": dict(zip(["comparable_pairs", "distinct_rounded_ratios"], ratios)),
        "ibes_exact_cusip_30231G10": dict(zip([
            "event_date_eps_actual_rows", "quarterly_actual_period_candidates",
            "candidate_period_min", "candidate_period_max",
            "nominal_pre_anchor_detail_records", "analyst_estimator_keys",
            "fpi_code_count", "currency_missing_records"
        ], ibes)),
        "prohibitions": {
            "forecast_values_read": False,
            "actual_values_read": False,
            "quote_values_read": False,
            "licensed_rows_exported": False,
        },
    }
    OUT.write_text(json.dumps(result, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
