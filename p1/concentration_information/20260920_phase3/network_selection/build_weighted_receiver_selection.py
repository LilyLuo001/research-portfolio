"""Build an outcome-blind reported-weight coholding network and freeze 20 receivers.

Designed for SCC. Licensed row-level and full-score outputs remain on SCC. The
local/Git exports are a 20-symbol configuration and aggregate diagnostics only.
No returns, event responses, quotes, EPS, forecasts, or post-event data are read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb
import numpy as np


CUTOFF = "2022-12-30"
LIQUIDITY_START = "2022-12-01"
LEVERAGE_NAME_PATTERN = r"lever|ultra|inverse|short|bear|2x|3x|-2x|-3x"


def q(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    manifest = root.parent / "_migration_meta/FINAL_SCC_MANIFEST.tsv"
    listed = [line.split("\t", 1)[1] for line in manifest.read_text().splitlines()]
    holding_paths = [
        root / rel
        for rel in listed
        if rel.startswith("raw/rescue_remaining/crsp_holdings_etf_2022_")
        and rel.endswith(".parquet")
    ]
    header_paths = [
        root / rel
        for rel in listed
        if rel.startswith("raw/rescue_remaining/crsp_fund_hdr_hist_full_max/")
        and rel.endswith(".parquet")
    ]
    membership = root / (
        "derived/p1_concentration_information/20260920/network/results/"
        "economic_date_only_membership.parquet"
    )
    roster = root / (
        "derived/p1_concentration_information/20260920/roster/"
        "private_top500_common_shareclasses.parquet"
    )
    dsf = root / "raw/crsp_dsf_2022.parquet"
    names = root / "raw/crsp_dsenames_full.parquet"
    required = holding_paths + header_paths + [membership, roster, dsf, names, manifest]
    assert holding_paths and header_paths and all(path.is_file() for path in required)

    def parquet_relation(paths: list[Path]) -> str:
        return "read_parquet([" + ",".join(q(path) for path in paths) + "])"

    con = duckdb.connect()
    con.execute("SET threads=2")
    con.execute("SET memory_limit='3GB'")

    con.execute(
        f"""
        CREATE TEMP TABLE membership AS
        SELECT DISTINCT CAST(crsp_portno AS BIGINT) crsp_portno,
               CAST(report_dt AS DATE) report_dt,
               CAST(permno AS BIGINT) permno
        FROM read_parquet({q(membership)})
        WHERE classification='ETF_ONLY_RECORDED_CLASSES' AND permno IS NOT NULL
        """
    )
    # DISTINCT removes nine identical physical repeats found in the bounded
    # diagnostic. Conflicting weights are counted and excluded below.
    con.execute(
        f"""
        CREATE TEMP TABLE holding_rows AS
        SELECT CAST(x.crsp_portno AS BIGINT) crsp_portno,
               CAST(x.report_dt AS DATE) report_dt,
               CAST(x.permno AS BIGINT) permno,
               x.percent_tna, x.market_val
        FROM {parquet_relation(holding_paths)} x
        JOIN membership m
          ON CAST(x.crsp_portno AS BIGINT)=m.crsp_portno
         AND CAST(x.report_dt AS DATE)=m.report_dt
         AND CAST(x.permno AS BIGINT)=m.permno
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE key_audit AS
        SELECT crsp_portno,report_dt,permno,count(*) physical_rows,
               count(DISTINCT percent_tna) distinct_percent_values,
               min(percent_tna) percent_tna
        FROM holding_rows GROUP BY ALL
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE holding_clean AS
        SELECT crsp_portno,report_dt,permno,percent_tna/100.0 reported_weight
        FROM key_audit
        WHERE distinct_percent_values=1 AND percent_tna>0 AND percent_tna<=100
        """
    )

    con.execute(
        f"""
        CREATE TEMP TABLE valid_classes AS
        SELECT DISTINCT CAST(crsp_portno AS BIGINT) crsp_portno,
               CAST(crsp_fundno AS BIGINT) crsp_fundno,
               index_fund_flag,coalesce(fund_name,'') fund_name
        FROM {parquet_relation(header_paths)}
        WHERE CAST(chgdt AS DATE)<=DATE {q(CUTOFF)}
          AND (CAST(chgenddt AS DATE)>=DATE {q(CUTOFF)} OR chgenddt IS NULL)
          AND et_flag='F'
        """
    )
    con.execute(
        f"""
        CREATE TEMP TABLE portfolio_contract AS
        SELECT crsp_portno,count(DISTINCT crsp_fundno) active_etf_classes,
               bool_and(coalesce(index_fund_flag='D',false)) pure_d,
               bool_and(coalesce(index_fund_flag IN ('B','D'),false)) index_bd,
               bool_or(regexp_matches(lower(fund_name),{q(LEVERAGE_NAME_PATTERN)}))
                   name_leverage_risk
        FROM valid_classes GROUP BY crsp_portno
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE portfolio_equity_proxy AS
        SELECT crsp_portno,sum(reported_weight) mapped_stock_weight
        FROM holding_clean GROUP BY crsp_portno
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE variants AS
        SELECT p.crsp_portno,'PURE_D' variant FROM portfolio_contract p
        JOIN portfolio_equity_proxy e USING(crsp_portno)
         WHERE p.pure_d AND NOT p.name_leverage_risk
           AND e.mapped_stock_weight BETWEEN 0.80 AND 1.20
        UNION ALL
        SELECT p.crsp_portno,'INDEX_BD' variant FROM portfolio_contract p
        JOIN portfolio_equity_proxy e USING(crsp_portno)
         WHERE p.index_bd AND NOT p.name_leverage_risk
           AND e.mapped_stock_weight BETWEEN 0.80 AND 1.20
        """
    )

    con.execute(
        f"""
        CREATE TEMP TABLE roster AS
        SELECT CAST(permno AS BIGINT) permno,CAST(permco AS BIGINT) permco,
               CAST(issuer_rank AS INTEGER) issuer_rank,market_cap_usd
        FROM read_parquet({q(roster)})
        """
    )
    con.execute(
        f"""
        CREATE TEMP TABLE historical_names AS
        SELECT CAST(permno AS BIGINT) permno,CAST(permco AS BIGINT) permco,
               ticker,comnam,siccd
        FROM read_parquet({q(names)})
        WHERE CAST(namedt AS DATE)<=DATE {q(CUTOFF)}
          AND (CAST(nameendt AS DATE)>=DATE {q(CUTOFF)} OR nameendt IS NULL)
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE company_identity AS WITH ranked AS (
          SELECT r.*,n.ticker,n.comnam,n.siccd,
                 row_number() OVER(PARTITION BY r.permco
                   ORDER BY r.market_cap_usd DESC,r.permno) rn
          FROM roster r LEFT JOIN historical_names n USING(permno,permco)
        )
        SELECT permco,sum(market_cap_usd) company_market_cap,
               max(CASE WHEN rn=1 THEN permno END) representative_permno,
               max(CASE WHEN rn=1 THEN ticker END) representative_ticker,
               max(CASE WHEN rn=1 THEN comnam END) company_name,
               max(CASE WHEN rn=1 THEN siccd END) siccd,
               min(issuer_rank) issuer_rank
        FROM ranked GROUP BY permco
        """
    )
    con.execute(
        f"""
        CREATE TEMP TABLE daily_liquidity AS
        SELECT CAST(d.permco AS BIGINT) permco,CAST(d.date AS DATE) date,
               sum(abs(d.prc)*d.vol) dollar_volume
        FROM read_parquet({q(dsf)}) d JOIN roster r
          ON CAST(d.permno AS BIGINT)=r.permno
        WHERE CAST(d.date AS DATE) BETWEEN DATE {q(LIQUIDITY_START)} AND DATE {q(CUTOFF)}
          AND d.prc IS NOT NULL AND d.vol IS NOT NULL AND d.vol>=0
        GROUP BY 1,2
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE liquidity AS
        SELECT permco,avg(dollar_volume) avg_daily_dollar_volume,
               count(*) liquidity_days
        FROM daily_liquidity GROUP BY permco
        """
    )

    # Company weights sum multiple common share classes within the same pooled
    # portfolio. The reported holding weights are unitless percent/100.
    con.execute(
        """
        CREATE TEMP TABLE company_weights_raw AS
        SELECT v.variant,h.crsp_portno,h.report_dt,r.permco,
               min(r.issuer_rank) issuer_rank,sum(h.reported_weight) company_weight
        FROM holding_clean h JOIN variants v USING(crsp_portno)
        JOIN roster r USING(permno)
        GROUP BY ALL
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE company_weights AS
        SELECT * FROM company_weights_raw WHERE company_weight>0 AND company_weight<=1
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE pair_scores AS
        SELECT i.variant,i.permco issuer_permco,r.permco receiver_permco,
               sum(i.company_weight*r.company_weight) pair_strength,
               count(DISTINCT struct_pack(portno:=i.crsp_portno,dt:=i.report_dt))
                   shared_portfolio_reports
        FROM company_weights i JOIN company_weights r
          USING(variant,crsp_portno,report_dt)
        WHERE i.issuer_rank<=8 AND r.issuer_rank<=500 AND r.issuer_rank>8
          AND i.permco<>r.permco
        GROUP BY ALL
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE receiver_total_weight AS
        SELECT variant,permco receiver_permco,sum(company_weight) receiver_weight_sum,
               count(DISTINCT struct_pack(portno:=crsp_portno,dt:=report_dt))
                   receiver_portfolio_reports
        FROM company_weights WHERE issuer_rank>8 AND issuer_rank<=500 GROUP BY ALL
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE receiver_scores AS
        SELECT p.variant,p.receiver_permco,sum(p.pair_strength) raw_strength,
               count(DISTINCT p.issuer_permco) connected_issuers,
               sum(p.shared_portfolio_reports) issuer_receiver_portfolio_memberships,
               t.receiver_weight_sum,t.receiver_portfolio_reports,
               sum(p.pair_strength)/nullif(t.receiver_weight_sum,0) normalized_strength
        FROM pair_scores p JOIN receiver_total_weight t USING(variant,receiver_permco)
        GROUP BY p.variant,p.receiver_permco,t.receiver_weight_sum,
                 t.receiver_portfolio_reports
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE scored_companies AS WITH issuer_industries AS (
          SELECT DISTINCT floor(siccd/100) sic2 FROM company_identity WHERE issuer_rank<=8
        )
        SELECT s.*,c.*,l.avg_daily_dollar_volume,l.liquidity_days,
               floor(c.siccd/100) sic2,
               floor(c.siccd/100) IN (SELECT sic2 FROM issuer_industries)
                   same_sic2_as_any_issuer
        FROM receiver_scores s JOIN company_identity c
          ON s.receiver_permco=c.permco
        LEFT JOIN liquidity l ON s.receiver_permco=l.permco
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE primary_bins AS
        SELECT *,ntile(5) OVER(ORDER BY company_market_cap,receiver_permco) size_quintile,
               ntile(5) OVER(ORDER BY avg_daily_dollar_volume,receiver_permco)
                   liquidity_quintile
        FROM scored_companies
        WHERE variant='PURE_D' AND representative_ticker IS NOT NULL
          AND avg_daily_dollar_volume>0 AND sic2 IS NOT NULL
        """
    )
    # Residualize log connection on PRE size, liquidity, and the same-industry
    # indicator, then nearest-neighbor match conditional-high and -low tails.
    # This is a design-stage ranking only; no response enters the calculation.
    frame = con.execute(
        """SELECT receiver_permco,raw_strength,company_market_cap,
                  avg_daily_dollar_volume,same_sic2_as_any_issuer
           FROM primary_bins ORDER BY receiver_permco"""
    ).fetchdf()
    log_size = np.log(frame["company_market_cap"].to_numpy(dtype=float))
    log_liq = np.log(frame["avg_daily_dollar_volume"].to_numpy(dtype=float))
    z_size = (log_size - log_size.mean()) / log_size.std()
    z_liq = (log_liq - log_liq.mean()) / log_liq.std()
    same = frame["same_sic2_as_any_issuer"].to_numpy(dtype=float)
    y = np.log(frame["raw_strength"].to_numpy(dtype=float))
    design = np.column_stack((np.ones(len(frame)), z_size, z_liq, same))
    residual = y - design @ np.linalg.lstsq(design, y, rcond=None)[0]
    frame["z_size"] = z_size
    frame["z_liq"] = z_liq
    frame["selection_residual"] = residual

    selected_ids = []
    for same_flag in (True, False):
        group = frame[frame["same_sic2_as_any_issuer"] == same_flag]
        low_cut = float(group["selection_residual"].quantile(0.30))
        high_cut = float(group["selection_residual"].quantile(0.70))
        highs = group[group["selection_residual"] >= high_cut]
        lows = group[group["selection_residual"] <= low_cut]
        candidates = []
        for high in highs.itertuples(index=False):
            for low in lows.itertuples(index=False):
                distance = (high.z_size - low.z_size) ** 2 + (high.z_liq - low.z_liq) ** 2
                residual_gap = high.selection_residual - low.selection_residual
                candidates.append((distance, -residual_gap, int(high.receiver_permco), int(low.receiver_permco), float(high.selection_residual), float(low.selection_residual)))
        used_high, used_low, chosen = set(), set(), []
        for distance, _, high_id, low_id, high_residual, low_residual in sorted(candidates):
            if high_id in used_high or low_id in used_low:
                continue
            used_high.add(high_id); used_low.add(low_id)
            chosen.append((high_id, low_id, high_residual, low_residual, float(distance)))
            if len(chosen) == 5:
                break
        assert len(chosen) == 5, (same_flag, len(chosen))
        for pair_rank, (high_id, low_id, high_residual, low_residual, distance) in enumerate(chosen, 1):
            selected_ids.extend([
                (high_id, "HIGH", pair_rank, high_residual, distance),
                (low_id, "LOW", pair_rank, low_residual, distance),
            ])
    con.execute(
        """CREATE TEMP TABLE selected_ids(
             receiver_permco BIGINT,connection_role VARCHAR,pair_rank INTEGER,
             selection_residual DOUBLE,covariate_distance DOUBLE)"""
    )
    con.executemany("INSERT INTO selected_ids VALUES (?,?,?,?,?)", selected_ids)
    con.execute(
        """
        CREATE TEMP TABLE selected_candidates AS
        SELECT b.*,s.connection_role,s.pair_rank AS stratum_rank,
               s.selection_residual,s.covariate_distance
        FROM primary_bins b JOIN selected_ids s USING(receiver_permco)
        """
    )
    selected_count = con.execute("SELECT count(*) FROM selected_candidates").fetchone()[0]
    same_count = con.execute(
        "SELECT count(*) FROM selected_candidates WHERE same_sic2_as_any_issuer"
    ).fetchone()[0]
    assert selected_count == 20 and same_count == 10, (selected_count, same_count)

    con.execute(
        f"COPY scored_companies TO {q(out / 'private_receiver_scores.parquet')} (FORMAT PARQUET)"
    )
    con.execute(
        f"COPY pair_scores TO {q(out / 'private_pair_scores.parquet')} (FORMAT PARQUET)"
    )
    con.execute(
        f"COPY selected_candidates TO {q(out / 'private_selected20.parquet')} (FORMAT PARQUET)"
    )
    con.execute(
        f"""
        COPY (SELECT
          (CASE WHEN same_sic2_as_any_issuer THEN 'S' ELSE 'C' END) ||
            lpad(CAST(stratum_rank AS VARCHAR),2,'0') || '_' || connection_role receiver_id,
          representative_ticker symbol,connection_role,
          same_sic2_as_any_issuer,size_quintile,liquidity_quintile
        FROM selected_candidates ORDER BY same_sic2_as_any_issuer DESC,
          stratum_rank,connection_role)
        TO {q(out / 'SELECTED20_PUBLIC_CONFIG.csv')} (HEADER,DELIMITER ',')
        """
    )

    physical_rows, duplicate_keys, conflict_keys = con.execute(
        """
        SELECT sum(physical_rows),sum(physical_rows>1),
               sum(distinct_percent_values>1) FROM key_audit
        """
    ).fetchone()
    variants_summary = {}
    for variant in ("PURE_D", "INDEX_BD"):
        portfolios = con.execute(
            "SELECT count(DISTINCT crsp_portno) FROM variants WHERE variant=?",
            [variant],
        ).fetchone()[0]
        receivers, pairs = con.execute(
            """SELECT count(DISTINCT receiver_permco),count(*)
               FROM pair_scores WHERE variant=?""",
            [variant],
        ).fetchone()
        variants_summary[variant] = {
            "portfolios": portfolios, "receivers": receivers,
            "issuer_receiver_pairs": pairs
        }
    selected_summary = con.execute(
        """
        SELECT count(*),sum(connection_role='HIGH'),sum(connection_role='LOW'),
               sum(same_sic2_as_any_issuer),count(DISTINCT size_quintile),
               count(DISTINCT liquidity_quintile),min(connected_issuers),
               max(connected_issuers)
        FROM selected_candidates
        """
    ).fetchone()
    summary = {
        "status": "SELECTED20_FROZEN_OUTCOME_BLIND_REPORTED_WEIGHT_NETWORK",
        "as_of": CUTOFF,
        "primary_network": "PURE_D",
        "sensitivity_network": "INDEX_BD",
        "network_formula": "sum_f (issuer percent_tna_f/100)*(receiver percent_tna_f/100)",
        "portfolio_contract": {
            "PURE_D": "all date-valid recorded ETF classes have index_fund_flag D; leverage-risk name tokens excluded; mapped-stock reported weight is 80%-120%",
            "INDEX_BD": "all date-valid recorded ETF classes have flag B or D; leverage-risk name tokens excluded; mapped-stock reported weight is 80%-120%",
            "excluded": "enhanced E, unflagged classes, name-flagged leverage/inverse/short products",
        },
        "holding_quality": {
            "physical_joined_rows": physical_rows,
            "duplicate_security_keys": duplicate_keys,
            "conflicting_percent_tna_keys_excluded": conflict_keys,
            "negative_percent_rows_excluded": con.execute(
                "SELECT count(*) FROM key_audit WHERE percent_tna<0"
            ).fetchone()[0],
            "percent_over_100_rows_excluded": con.execute(
                "SELECT count(*) FROM key_audit WHERE percent_tna>100"
            ).fetchone()[0],
            "invalid_company_weights_excluded": con.execute(
                "SELECT count(*) FROM company_weights_raw WHERE company_weight<=0 OR company_weight>1"
            ).fetchone()[0],
        },
        "network_variants": variants_summary,
        "selection_rule": (
            "Residualize log PURE_D strength on standardized log market cap, standardized "
            "December-2022 dollar volume, and same-SIC2-as-any-issuer. Within each industry "
            "status, define HIGH at/above the residual 70th percentile and LOW at/below the "
            "30th percentile; greedily select five nonreused nearest-covariate pairs by "
            "squared standardized size/liquidity distance, breaking ties by larger residual "
            "gap then PERMCO."
        ),
        "selection": {
            "receivers": selected_summary[0], "high": selected_summary[1],
            "low": selected_summary[2], "same_industry": selected_summary[3],
            "cross_industry": selected_summary[0] - selected_summary[3],
            "size_quintiles_represented": selected_summary[4],
            "liquidity_quintiles_represented": selected_summary[5],
            "connected_issuer_range": [selected_summary[6], selected_summary[7]],
        },
        "privacy": "full scores and licensed identifiers remain on SCC; public config exports 20 historical symbols and design strata only",
        "outcome_columns_read": [],
        "sources": {
            "manifest_sha256": sha256(manifest),
            "membership_sha256": sha256(membership),
            "roster_sha256": sha256(roster),
            "holdings_parts": len(holding_paths),
            "header_parts": len(header_paths),
            "dsf": "raw/crsp_dsf_2022.parquet; price and volume only for PRE liquidity",
            "names": "raw/crsp_dsenames_full.parquet; date-valid identity and SIC only",
        },
        "outputs": {
            "private_receiver_scores": str(out / "private_receiver_scores.parquet"),
            "private_pair_scores": str(out / "private_pair_scores.parquet"),
            "private_selected20": str(out / "private_selected20.parquet"),
            "public_config": str(out / "SELECTED20_PUBLIC_CONFIG.csv"),
        },
    }
    (out / "NETWORK_SELECTION_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
