#!/usr/bin/env python3
"""SCC-only, metadata/holdings Stage-A probe for P1-2023-08-01.

It deliberately never projects forecast, actual EPS, or quote price/size fields.
It writes only a compact aggregate JSON on SCC; raw licensed rows never leave SCC.
"""
import glob, hashlib, json
from pathlib import Path
import duckdb

ROOT = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared")
OUT = Path("/scratch/qluo/spy_xom_event_packet_20260921")
DATE = "2023-01-31"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    holdings = sorted(glob.glob(str(ROOT / "raw/rescue_remaining/crsp_holdings_etf_2022_*/part_*.parquet")) + glob.glob(str(ROOT / "raw/rescue_remaining/crsp_holdings_etf_2023_*/part_*.parquet")))
    detail = ROOT / "raw/ibes_detu_eps_2023.parquet"
    actual = ROOT / "raw/ibes_actuals_eps_2023.parquet"
    con = duckdb.connect()
    # Holdings: no names/CUSIPs/position values are exported. 1021980 is the
    # established SPY CRSP portfolio number in the existing census.
    paths_sql = "[" + ",".join(repr(p) for p in holdings) + "]"
    con.execute(f"""CREATE VIEW h AS SELECT
      report_dt,eff_dt,crsp_portno,permno,ticker,nbr_shares,percent_tna
      FROM read_parquet({paths_sql})""")
    hcur = con.execute("""
      SELECT CAST(report_dt AS VARCHAR) report_dt,
        CAST(min(eff_dt) AS VARCHAR) min_eff_dt, CAST(max(eff_dt) AS VARCHAR) max_eff_dt,
        count(DISTINCT eff_dt) eff_dt_count,
        count(*) n_rows, count(DISTINCT permno) security_ids,
        count(*) FILTER (WHERE permno IS NULL) missing_security_id_rows,
        count(*) FILTER (WHERE nbr_shares IS NOT NULL) rows_with_shares,
        count(*) FILTER (WHERE percent_tna IS NOT NULL) rows_with_weight,
        count(*) FILTER (WHERE upper(ticker)='XOM') xom_rows,
        count(*) FILTER (WHERE upper(ticker)='XOM' AND nbr_shares IS NOT NULL AND percent_tna IS NOT NULL) xom_units_weight_present
      FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)=DATE '2023-01-31'
      GROUP BY 1
    """)
    hcols = [x[0] for x in hcur.description]
    hq = hcur.fetchall()
    # Snapshot comparison is aggregate only: no constituent rows, quantities or
    # weights are exported. It distinguishes latest strictly prior report from
    # same-calendar-date report and asks whether a common share multiplier can
    # be established without disclosing positions (it cannot when identity sets differ).
    prior = con.execute("SELECT max(CAST(report_dt AS DATE)) FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)<DATE '2023-01-31'").fetchone()[0]
    comp = con.execute("""
      WITH p0 AS (SELECT permno,nbr_shares FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)=?),
      s0 AS (SELECT permno,nbr_shares FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)=DATE '2023-01-31'),
      p AS (SELECT permno,sum(nbr_shares) nbr_shares FROM p0 WHERE permno IS NOT NULL GROUP BY permno),
      s AS (SELECT permno,sum(nbr_shares) nbr_shares FROM s0 WHERE permno IS NOT NULL GROUP BY permno),
      j AS (SELECT p.permno p_permno,s.permno s_permno,p.nbr_shares ps,s.nbr_shares ss FROM p FULL OUTER JOIN s ON p.permno=s.permno)
      SELECT
       (SELECT count(*) FROM p0) prior_rows,
       (SELECT count(*) FROM s0) same_day_rows,
       (SELECT count(*) FROM p) prior_valid_security_ids,
       (SELECT count(*) FROM s) same_day_valid_security_ids,
       count(*) FILTER(WHERE p_permno IS NOT NULL AND s_permno IS NOT NULL) overlap_valid_security_ids,
       count(*) FILTER(WHERE p_permno IS NOT NULL AND s_permno IS NULL) dropped_valid_security_ids,
       count(*) FILTER(WHERE p_permno IS NULL AND s_permno IS NOT NULL) added_valid_security_ids,
       (SELECT count(*) FROM p0 WHERE permno IS NULL) prior_missing_security_id_rows,
       (SELECT count(*) FROM s0 WHERE permno IS NULL) same_day_missing_security_id_rows,
       count(*) FILTER(WHERE p_permno IS NOT NULL AND s_permno IS NOT NULL AND ps IS NOT NULL AND ss IS NOT NULL AND ps<>0) comparable_share_pairs,
       count(DISTINCT round(ss/ps,10)) FILTER(WHERE p_permno IS NOT NULL AND s_permno IS NOT NULL AND ps IS NOT NULL AND ss IS NOT NULL AND ps<>0) distinct_rounded_share_ratios_diagnostic
      FROM j
    """, [prior]).fetchone()
    prior_meta = con.execute("""
      SELECT CAST(min(eff_dt) AS VARCHAR) min_eff_dt, CAST(max(eff_dt) AS VARCHAR) max_eff_dt,
        count(DISTINCT eff_dt) eff_dt_count, count(*) n_rows,
        count(DISTINCT permno) valid_security_ids,
        count(*) FILTER (WHERE permno IS NULL) missing_security_id_rows
      FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)=?
    """, [prior]).fetchone()
    # I/B/E/S: strict metadata projection. The event window is selected by
    # issuer identity plus announcement date; no value column is named.
    con.execute(f"""CREATE VIEW d AS SELECT
      cusip,fpedats,measure,anndats,anntims,actdats,acttims,curr,
      analys,estimator,fpi
      FROM read_parquet({str(detail)!r})""")
    con.execute(f"""CREATE VIEW a AS SELECT
      cusip,pends,measure,pdicity,anndats,anntims,actdats,acttims,curr_act
      FROM read_parquet({str(actual)!r})""")
    dq = con.execute("""
      SELECT count(*) records, count(DISTINCT fpedats) period_count,
        count(*) FILTER (WHERE actdats=anndats) same_date_activation,
        count(*) FILTER (WHERE actdats>anndats) later_date_activation,
        count(*) FILTER (WHERE actdats=anndats AND acttims>anntims) same_date_later_time,
        count(*) FILTER (WHERE curr IS NULL) currency_missing
      FROM d WHERE upper(trim(cusip))='30231G10' AND CAST(anndats AS DATE)=DATE '2023-01-31'
        AND upper(trim(measure))='EPS'
    """).fetchone()
    aq = con.execute("""
      SELECT count(*) records, count(DISTINCT pends) period_count,
        count(*) FILTER (WHERE actdats=anndats) same_date_activation,
        count(*) FILTER (WHERE actdats>anndats) later_date_activation,
        count(*) FILTER (WHERE actdats=anndats AND acttims>anntims) same_date_later_time,
        count(*) FILTER (WHERE upper(trim(curr_act))='USD') usd_actual_metadata,
        count(*) FILTER (WHERE upper(trim(pdicity))='QTR') quarterly_records
      FROM a WHERE upper(trim(cusip))='30231G10' AND CAST(anndats AS DATE)=DATE '2023-01-31'
        AND upper(trim(measure))='EPS'
    """).fetchone()
    # Candidate-period metadata only, then Detail history through the nominal
    # 06:30 cutoff. Exact CUSIP is retained on both sides of the join; ticker is
    # never used as an identity key. This does not certify the time-zone or
    # point-in-time semantics of I/B/E/S activation fields.
    match = con.execute("""
      WITH ap AS (SELECT DISTINCT cusip,pends,measure,pdicity FROM a
        WHERE upper(trim(cusip))='30231G10' AND CAST(anndats AS DATE)=DATE '2023-01-31' AND upper(trim(measure))='EPS' AND upper(trim(pdicity))='QTR'),
      dh AS (SELECT d.analys,d.estimator,d.fpi,d.curr,d.cusip FROM d JOIN ap ON upper(trim(d.cusip))=upper(trim(ap.cusip)) AND d.fpedats=ap.pends AND upper(trim(d.measure))=upper(trim(ap.measure))
        WHERE CAST(d.anndats AS DATE) BETWEEN DATE '2022-11-02' AND DATE '2023-01-31'
          AND (CAST(d.actdats AS DATE)<DATE '2023-01-31' OR (CAST(d.actdats AS DATE)=DATE '2023-01-31' AND CAST(d.acttims AS TIME)<=TIME '06:30:00')))
      SELECT (SELECT count(*) FROM ap) actual_period_candidates,
        (SELECT CAST(min(pends) AS VARCHAR) FROM ap) candidate_period_min,
        (SELECT CAST(max(pends) AS VARCHAR) FROM ap) candidate_period_max,
        count(*) detail_pre_anchor_records,
        count(DISTINCT analys || '|' || estimator) detail_analyst_estimator_keys,
        count(DISTINCT fpi) detail_fpi_code_count,
        count(*) FILTER(WHERE curr IS NULL) detail_currency_missing,
        count(*) FILTER(WHERE cusip IS NULL) detail_cusip_missing
      FROM dh
    """).fetchone()
    payload={
      "scope":"P1-2023-08-01 Stage A; no EPS/actual/quote values selected",
      "holdings_files":len(holdings), "holdings_glob":"raw/rescue_remaining/crsp_holdings_etf_2022_*/part_*.parquet + raw/rescue_remaining/crsp_holdings_etf_2023_*/part_*.parquet",
      "holdings_date_aggregate": [dict(zip(hcols, r)) for r in hq],
      "latest_strictly_prior_report_dt":str(prior),
      "latest_strictly_prior_snapshot_metadata":dict(zip(["min_eff_dt","max_eff_dt","eff_dt_count","n_rows","valid_security_ids","missing_security_id_rows"],prior_meta)),
      "prior_vs_same_day_snapshot_aggregate":dict(zip(["prior_rows","same_day_rows","prior_valid_security_ids","same_day_valid_security_ids","overlap_valid_security_ids","dropped_valid_security_ids","added_valid_security_ids","prior_missing_security_id_rows","same_day_missing_security_id_rows","comparable_share_pairs","distinct_rounded_share_ratios_diagnostic"],comp)),
      "ibes_sources":{"detail":{"path":str(detail),"sha256":sha(detail)},"actual":{"path":str(actual),"sha256":sha(actual)}},
      "detail_metadata":dict(zip(["records","period_count","same_date_activation","later_date_activation","same_date_later_time","currency_missing"],dq)),
      "actual_metadata":dict(zip(["records","period_count","same_date_activation","later_date_activation","same_date_later_time","usd_actual_metadata","quarterly_records"],aq)),
      "candidate_period_and_pre_anchor_detail_metadata":dict(zip(["actual_period_candidates","candidate_period_min","candidate_period_max","detail_pre_anchor_records","detail_analyst_estimator_keys","detail_fpi_code_count","detail_currency_missing","detail_cusip_missing"],match)),
      "prohibitions":{"forecast_values_read":False,"actual_values_read":False,"quote_values_read":False,"licensed_rows_exported":False}
    }
    (OUT / "stage_a_probe_aggregate.json").write_text(json.dumps(payload,indent=2,default=str)+"\n")

if __name__ == "__main__": main()
