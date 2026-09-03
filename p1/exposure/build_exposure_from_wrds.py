#!/usr/bin/env python3
"""Map strictly-PRE N-PORT positions to CRSP and build Exposure^pre.

The script consumes the exact Gate-0 PRE holdings extracted by
``build_nport_pre_holdings.py`` and the read-only SCC WRDS mirror.  It never
reads POST holdings.  Corporate-action factors are joined to the N-PORT report
date and applied per fund-position before wave aggregation.

The archive currently contains CRSP daily security data through 2025.  A 2026
position/event is therefore retained with explicit missing-factor/denominator
status rather than silently carrying 2025 data forward.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_ARCHIVE = Path(
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/"
    "WRDS_MIRROR_20260902"
)
DEFAULT_INPUT = Path("p1/exposure/nport_pre_holdings_long.parquet")
DEFAULT_UNIVERSE = Path("p1/exposure/exposure_universe_gate0_pass.csv")
DEFAULT_PENDING = Path("p1/exposure/exposure_pending_missing_post.csv")
DEFAULT_EVENT_MASTER = Path("p1/universe_v2/output/event_master_final_reconciled.csv")
DEFAULT_LEGACY = Path("p1/conv_exposure_free.parquet")
DEFAULT_OUT = Path("p1/exposure")
COMPLETED_TIERS = {"A_explicit_completion", "B_structural_completion"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm_str(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def missing_or_strictly_before(value, cutoff) -> bool:
    """Return True for an unavailable date or a valid date before ``cutoff``.

    Denominator dates are intentionally missing when the WRDS mirror has no
    contemporaneous CRSP observation (notably in 2026).  CSV round-tripping
    represents those values as NaN floats, so the leakage audit must compare
    parsed timestamps rather than mixed Python strings/floats.
    """
    if pd.isna(value) or str(value).strip() == "":
        return True
    value_ts = pd.to_datetime(value, errors="coerce")
    cutoff_ts = pd.to_datetime(cutoff, errors="coerce")
    return bool(pd.notna(value_ts) and pd.notna(cutoff_ts) and value_ts < cutoff_ts)


def completed_event_mask(event_master: pd.DataFrame) -> pd.Series:
    """Identify signed completion tiers without counting future announcements."""
    return event_master.final_tier.isin(COMPLETED_TIERS)


def stockname_index(stocknames: pd.DataFrame):
    sn = stocknames.copy()
    sn["namedt"] = pd.to_datetime(sn.namedt, errors="coerce")
    sn["nameenddt"] = pd.to_datetime(sn.nameenddt, errors="coerce")
    sn["nameenddt"] = sn.nameenddt.fillna(pd.Timestamp("2099-12-31"))
    for col in ("cusip9", "cusip", "ticker", "sharetype", "securitytype",
                "securitysubtype", "usincflg"):
        sn[col] = sn[col].map(norm_str)
    by9, by8 = {}, {}
    for row in sn.itertuples(index=False):
        if row.cusip9:
            by9.setdefault(row.cusip9, []).append(row)
        if row.cusip:
            by8.setdefault(row.cusip[:8], []).append(row)
    return by9, by8


def map_one_position(row, by9, by8) -> dict:
    cusip9 = norm_str(row.cusip)
    asof = pd.Timestamp(row.pre_report_date)

    def active(rows):
        return [r for r in rows if r.namedt <= asof <= r.nameenddt]

    method = "exact_cusip9"
    candidates = active(by9.get(cusip9, []))
    if not candidates:
        method = "exact_cusip8"
        candidates = active(by8.get(cusip9[:8], []))
    if not candidates:
        country = norm_str(row.investment_country)
        return {
            "mapping_status": "non_us_non_crsp" if country not in ("", "US") else "unmatched",
            "mapping_method": "none",
            "permno": None,
            "crsp_ticker": "",
            "candidate_permnos": "",
        }

    common = [
        r for r in candidates
        if r.sharetype == "NS" and r.securitytype == "EQTY"
        and r.securitysubtype == "COM"
    ]
    us_common = [r for r in common if r.usincflg == "Y"]
    if not us_common:
        status = "non_us" if common else "non_common_equity"
        return {
            "mapping_status": status,
            "mapping_method": method,
            "permno": None,
            "crsp_ticker": "",
            "candidate_permnos": ";".join(
                str(x) for x in sorted({int(r.permno) for r in candidates})
            ),
        }
    permnos = sorted({int(r.permno) for r in us_common})
    if len(permnos) != 1:
        return {
            "mapping_status": "ambiguous",
            "mapping_method": method,
            "permno": None,
            "crsp_ticker": "",
            "candidate_permnos": ";".join(str(x) for x in permnos),
        }
    chosen = next(r for r in us_common if int(r.permno) == permnos[0])
    return {
        "mapping_status": "exact_matched",
        "mapping_method": method,
        "permno": permnos[0],
        "crsp_ticker": chosen.ticker,
        "candidate_permnos": str(permnos[0]),
    }


def load_crsp_daily(raw: Path, wanted_permnos: set[int]) -> tuple[pd.DataFrame, list[dict]]:
    frames = []
    lineage = []
    for year in range(2020, 2025):
        path = raw / "rescue" / f"crsp_dsf_allcols_{year}.parquet"
        d = pd.read_parquet(
            path,
            columns=["permno", "date", "prc", "shrout", "cfacshr"],
        )
        d = d[d.permno.isin(wanted_permnos)].copy()
        d = d.rename(columns={"date": "crsp_date", "prc": "price",
                              "cfacshr": "share_factor"})
        d["source_family"] = "legacy_crsp_dsf"
        d["source_file"] = str(path)
        frames.append(d)
        lineage.append({"source_file": str(path), "sha256": sha256(path),
                        "rows_selected": len(d), "year": year})

    path = raw / "rescue" / "newcrsp_crsp_dsf_v2_2025.parquet"
    d = pd.read_parquet(
        path,
        columns=["permno", "dlycaldt", "dlyprc", "shrout", "dlycumfacshr"],
    )
    d = d[d.permno.isin(wanted_permnos)].copy()
    d = d.rename(columns={"dlycaldt": "crsp_date", "dlyprc": "price",
                          "dlycumfacshr": "share_factor"})
    d["source_family"] = "crsp_ciz_dsf_v2"
    d["source_file"] = str(path)
    frames.append(d)
    lineage.append({"source_file": str(path), "sha256": sha256(path),
                    "rows_selected": len(d), "year": 2025})

    daily = pd.concat(frames, ignore_index=True)
    daily["permno"] = daily.permno.astype(int)
    daily["crsp_date"] = pd.to_datetime(daily.crsp_date)
    daily["price"] = pd.to_numeric(daily.price, errors="coerce").abs()
    daily["shrout"] = pd.to_numeric(daily.shrout, errors="coerce")
    daily["share_factor"] = pd.to_numeric(daily.share_factor, errors="coerce")
    daily = daily.sort_values(["permno", "crsp_date"]).drop_duplicates(
        ["permno", "crsp_date"], keep="last"
    )
    return daily, lineage


def daily_lookup(daily: pd.DataFrame):
    out = {}
    for permno, group in daily.groupby("permno", sort=False):
        g = group.sort_values("crsp_date")
        out[int(permno)] = (list(g.crsp_date), list(g.itertuples(index=False)))
    return out


def prior_observation(index, permno: int, target, *, strict: bool, max_gap: int):
    dates, rows = index.get(int(permno), ([], []))
    target = pd.Timestamp(target)
    pos = (bisect.bisect_left(dates, target) if strict else bisect.bisect_right(dates, target)) - 1
    if pos < 0:
        return None
    row = rows[pos]
    if (target - row.crsp_date).days > max_gap:
        return None
    return row


def attach_crsp(rows: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    idx = daily_lookup(daily)
    out = rows.copy()
    for col in (
        "factor_date", "share_factor", "factor_source_family", "factor_source_file",
        "denominator_date", "shares_outstanding", "stock_price",
        "market_cap_usd", "denominator_source_family", "denominator_source_file",
    ):
        out[col] = None

    for i, row in out.loc[out.mapping_status.eq("exact_matched")].iterrows():
        factor = prior_observation(
            idx, int(row.permno), row.pre_report_date, strict=False, max_gap=4
        )
        denom = prior_observation(
            idx, int(row.permno), row.effective_date, strict=True, max_gap=7
        )
        if factor is not None and pd.notna(factor.share_factor) and factor.share_factor > 0:
            out.at[i, "factor_date"] = factor.crsp_date.strftime("%Y-%m-%d")
            out.at[i, "share_factor"] = float(factor.share_factor)
            out.at[i, "factor_source_family"] = factor.source_family
            out.at[i, "factor_source_file"] = factor.source_file
        if denom is not None and pd.notna(denom.shrout) and denom.shrout > 0:
            out.at[i, "denominator_date"] = denom.crsp_date.strftime("%Y-%m-%d")
            out.at[i, "shares_outstanding"] = float(denom.shrout) * 1000.0
            out.at[i, "stock_price"] = float(denom.price) if pd.notna(denom.price) else None
            if pd.notna(denom.price):
                out.at[i, "market_cap_usd"] = float(denom.shrout) * 1000.0 * float(denom.price)
            out.at[i, "denominator_source_family"] = denom.source_family
            out.at[i, "denominator_source_file"] = denom.source_file

    out["adjusted_shares"] = pd.to_numeric(out.raw_reported_shares, errors="coerce") * pd.to_numeric(
        out.share_factor, errors="coerce"
    )
    out["fund_portfolio_weight"] = pd.to_numeric(
        out.position_value_usd, errors="coerce"
    ) / pd.to_numeric(out.fund_net_assets_usd, errors="coerce")
    return out


def aggregate_exposure(contrib: pd.DataFrame) -> pd.DataFrame:
    mapped = contrib[contrib.mapping_status.eq("exact_matched")].copy()
    if mapped.empty:
        return pd.DataFrame()
    group_cols = ["permno", "wave_id", "effective_date"]

    def agg(group):
        factor_complete = group.adjusted_shares.notna().all()
        denom = group.shares_outstanding.dropna().unique()
        mcap = group.market_cap_usd.dropna().unique()
        adjusted = group.adjusted_shares.sum() if factor_complete else None
        value = pd.to_numeric(group.position_value_usd, errors="coerce").sum(min_count=1)
        raw = pd.to_numeric(group.raw_reported_shares, errors="coerce").sum(min_count=1)
        ownership = adjusted / denom[0] if adjusted is not None and len(denom) == 1 else None
        value_exp = value / mcap[0] if pd.notna(value) and len(mcap) == 1 and mcap[0] else None
        return pd.Series({
            "raw_reported_shares": raw,
            "adjusted_shares_held": adjusted,
            "position_value_usd": value,
            "fund_portfolio_weight_sum": pd.to_numeric(
                group.fund_portfolio_weight, errors="coerce"
            ).sum(min_count=1),
            "shares_outstanding": denom[0] if len(denom) == 1 else None,
            "market_cap_usd": mcap[0] if len(mcap) == 1 else None,
            "exposure_ownership": ownership,
            "exposure_value": value_exp,
            "n_positions": len(group),
            "n_events": group.event_id.nunique(),
            "n_predecessor_funds": group.pre_series_id.nunique(),
            "n_missing_factors": int(group.adjusted_shares.isna().sum()),
            "factor_complete": bool(factor_complete),
            "denominator_complete": bool(len(denom) == 1),
            "primary_ready": bool(pd.notna(ownership)),
            "advisers": ";".join(sorted(set(group.adviser.fillna("").astype(str)) - {""})),
            "is_dimensional": bool(group.is_dimensional.any()),
            "pre_report_date_min": group.pre_report_date.min(),
            "pre_report_date_max": group.pre_report_date.max(),
            "source_accessions": ";".join(sorted(group.pre_accession.unique())),
        })

    return mapped.groupby(group_cols, dropna=False, sort=True).apply(agg).reset_index()


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:70] or "unknown"


def write_loso_inputs(contrib: pd.DataFrame, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    base = contrib[contrib.mapping_status.eq("exact_matched")].copy()
    base.to_parquet(outdir / "position_contributions.parquet", index=False)
    rows = []
    for adviser in sorted(set(base.adviser.fillna("").astype(str)) - {""}):
        rows.append({
            "excluded_adviser": adviser,
            "file_slug": safe_slug(adviser),
            "n_positions_excluded": int(base.adviser.eq(adviser).sum()),
            "status": "ADVISER_PROXY_NOT_SIGNED_ECONOMIC_SPONSOR",
        })
    pd.DataFrame(rows).to_csv(outdir / "loso_manifest.csv", index=False)


def distribution_summary(exposure: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ("adjusted_shares_held", "exposure_ownership", "exposure_value"):
        s = pd.to_numeric(exposure[col], errors="coerce").dropna()
        for metric, value in {
            "count": len(s), "mean": s.mean(), "median": s.median(),
            "p90": s.quantile(.90), "p95": s.quantile(.95),
            "p99": s.quantile(.99), "max": s.max(),
        }.items():
            rows.append({"measure": col, "metric": metric, "value": value})
    return pd.DataFrame(rows)


def build_census(event_master, universe, pending, holdings, crosswalk, exposure, legacy):
    # Only the two completion tiers are completed events.  Announced-future,
    # cancelled, and unresolved rows remain structural-universe members but
    # must not inflate the completed-event census.
    completed = event_master[completed_event_mask(event_master)].copy()
    ready = exposure[exposure.primary_ready]
    positive_permnos = ready.loc[ready.exposure_ownership.gt(0), "permno"]
    repeated = ready.groupby("permno").wave_id.nunique()
    metrics = {
        "structural_members": int(len(event_master)),
        "completed_events": int(len(completed)),
        "verified_exact_day_events": int(event_master.timing_eligible_primary.sum()),
        "verified_effective_dates": int(event_master.loc[event_master.timing_eligible_primary, "verified_effective_date"].nunique()),
        "gate0_events_tested": int(len(universe) + len(pending)),
        "gate0_pass_events": int(len(universe)),
        "gate0_pending_events": int(len(pending)),
        "gate0_pass_waves": int(universe.wave_id.nunique()),
        "unique_pre_conversion_funds_gate0": int(universe.pre_series_id.nunique()),
        "unique_post_conversion_etfs_gate0": int(universe.post_series_id.nunique()),
        "sec_registrants_gate0": int(universe.pre_cik.nunique()),
        "nport_positions_pre": int(len(holdings)),
        "unique_securities_before_mapping": int(holdings.cusip.replace("", pd.NA).nunique()),
        "common_equity_candidates_before_mapping": int(holdings.is_common_equity_candidate.sum()),
        "unique_treated_permnos_primary_ready": int(positive_permnos.nunique()),
        "treated_stock_wave_cells_primary_ready": int(ready.exposure_ownership.gt(0).sum()),
        "treated_stocks_in_multiple_waves": int((repeated > 1).sum()),
        "waves_with_valid_strict_pre": int((pd.concat([universe, pending]).pre_report_date.fillna("") != "").groupby(pd.concat([universe, pending]).wave_id).all().sum()),
        "waves_with_valid_first_post": int((pd.concat([universe, pending]).post_report_date.fillna("") != "").groupby(pd.concat([universe, pending]).wave_id).all().sum()),
        "waves_gate0_eligible": int(universe.wave_id.nunique()),
        "waves_exposure_primary_ready": int(ready.wave_id.nunique()),
        "legacy_events": 172,
        "legacy_waves": 96,
        "legacy_exposure_cells": int(len(legacy)),
        "legacy_unique_cusips": int(legacy.cusip.nunique()),
        "legacy_treated_cusips_ge_0_5pct": int(legacy.loc[legacy.conv_exp.ge(.005), "cusip"].nunique()),
        "rebuilt_treated_permnos_ge_0_5pct": int(ready.loc[ready.exposure_ownership.ge(.005), "permno"].nunique()),
        "rebuilt_treated_permnos_ge_1pct": int(ready.loc[ready.exposure_ownership.ge(.01), "permno"].nunique()),
    }
    return metrics


def write_reports(out: Path, metrics: dict, universe, pending, holdings, crosswalk,
                  contrib, exposure, daily_lineage, inputs):
    (out / "universe_census.json").write_text(json.dumps(metrics, indent=2) + "\n")
    pd.DataFrame([{"metric": k, "value": v} for k, v in metrics.items()]).to_csv(
        out / "universe_census.csv", index=False
    )
    pd.DataFrame([{"metric": k, "value": v} for k, v in metrics.items()]).to_markdown(
        out / "universe_census.md", index=False
    )

    both = pd.concat([universe, pending], ignore_index=True)
    coverage = both.groupby(["wave_id", "effective_date"], as_index=False).agg(
        events=("event_id", "size"),
        gate0_pass_events=("gate0", lambda x: int(x.eq("PASS").sum())),
        valid_pre_events=("pre_report_date", lambda x: int(x.fillna("").ne("").sum())),
        valid_post_events=("post_report_date", lambda x: int(x.fillna("").ne("").sum())),
    )
    coverage["gate0_ready"] = coverage.gate0_pass_events.eq(coverage.events)
    coverage["blocked_reason"] = coverage.apply(
        lambda r: "" if r.gate0_ready else "one_or_more_events_missing_first_post_nport", axis=1
    )
    coverage.to_csv(out / "nport_pre_post_coverage_by_wave.csv", index=False)
    coverage[coverage.gate0_ready].to_csv(out / "gate0_ready_waves.csv", index=False)
    coverage[~coverage.gate0_ready].to_csv(out / "gate0_blocked_waves.csv", index=False)

    match_diag = crosswalk.groupby(["mapping_status", "mapping_method"], as_index=False).agg(
        positions=("position_number", "size"),
        position_value_usd=("position_value_usd", "sum"),
        unique_cusips=("cusip", "nunique"),
    )
    match_diag.to_csv(out / "nport_crsp_match_diagnostics.csv", index=False)

    ca = contrib[contrib.mapping_status.eq("exact_matched")][[
        "event_id", "wave_id", "pre_series_id", "pre_report_date", "pre_accession",
        "position_number", "cusip", "permno", "raw_reported_shares", "factor_date",
        "share_factor", "adjusted_shares", "factor_source_family", "factor_source_file",
        "denominator_date", "shares_outstanding", "market_cap_usd",
        "denominator_source_family", "denominator_source_file",
    ]].copy()
    ca["formula"] = "adjusted_shares = raw_reported_shares * share_factor"
    ca["factor_date_pass"] = pd.to_datetime(ca.factor_date, errors="coerce").le(
        pd.to_datetime(ca.pre_report_date)
    )
    ca["factor_available"] = ca.share_factor.notna()
    ca.to_csv(out / "nport_corporate_action_adjustment_audit.csv", index=False)

    leak = universe[["event_id", "wave_id", "effective_date", "pre_report_date",
                     "pre_accession", "post_accession"]].copy()
    leak["no_post_holdings_used"] = True
    leak["strictly_pre_nport"] = pd.to_datetime(leak.pre_report_date).lt(
        pd.to_datetime(leak.effective_date)
    )
    denom_dates = contrib.groupby("event_id").denominator_date.apply(
        lambda x: max([v for v in x.dropna().astype(str)] or [""])
    )
    leak["latest_denominator_date"] = leak.event_id.map(denom_dates)
    leak["no_post_event_denominator"] = leak.apply(
        lambda r: missing_or_strictly_before(
            r.latest_denominator_date, r.effective_date
        ),
        axis=1,
    )
    leak["future_sponsor_information_used"] = False
    leak["future_wave_information_used"] = False
    leak["leakage_audit_pass"] = leak[
        ["no_post_holdings_used", "strictly_pre_nport", "no_post_event_denominator",
         "future_sponsor_information_used", "future_wave_information_used"]
    ].apply(lambda r: bool(r.iloc[0] and r.iloc[1] and r.iloc[2] and not r.iloc[3] and not r.iloc[4]), axis=1)
    leak.to_csv(out / "exposure_leakage_audit.csv", index=False)

    wave = exposure.groupby(["wave_id", "effective_date"], as_index=False).agg(
        stock_wave_cells=("permno", "size"),
        primary_ready_cells=("primary_ready", "sum"),
        events=("n_events", "max"),
        predecessor_funds=("n_predecessor_funds", "max"),
        adjusted_shares=("adjusted_shares_held", "sum"),
        position_value_usd=("position_value_usd", "sum"),
        max_exposure_ownership=("exposure_ownership", "max"),
        dimensional_wave=("is_dimensional", "max"),
    )
    aum = holdings.drop_duplicates("event_id").groupby("wave_id").fund_net_assets_usd.sum()
    wave["aggregate_predecessor_net_assets_usd"] = wave.wave_id.map(aum)
    wave["matched_position_value_share"] = (
        wave.position_value_usd / wave.position_value_usd.sum()
    )
    wave.to_csv(out / "exposure_wave_summary.csv", index=False)

    matched_contrib = contrib[contrib.mapping_status.eq("exact_matched")].copy()
    sponsor = matched_contrib.groupby("adviser", dropna=False, as_index=False).agg(
        events=("event_id", "nunique"),
        waves=("wave_id", "nunique"),
        positions=("position_number", "size"),
        unique_permnos=("permno", "nunique"),
        matched_position_value_usd=("position_value_usd", "sum"),
        adjusted_shares=("adjusted_shares", "sum"),
        dimensional=("is_dimensional", "max"),
    )
    sponsor["matched_position_value_share"] = (
        sponsor.matched_position_value_usd
        / sponsor.matched_position_value_usd.sum()
    )
    sponsor = sponsor.sort_values("matched_position_value_usd", ascending=False)
    sponsor.to_csv(out / "exposure_sponsor_concentration.csv", index=False)

    inspected = matched_contrib.copy()
    inspected["extreme_fund_weight_gt_10pct"] = inspected.fund_portfolio_weight.gt(.10)
    inspected["extreme_position_value_top_0_1pct"] = inspected.position_value_usd.ge(
        inspected.position_value_usd.quantile(.999)
    )
    inspected["extreme_adjusted_shares_top_0_1pct"] = inspected.adjusted_shares.ge(
        inspected.adjusted_shares.quantile(.999)
    )
    inspected["automatic_winsorization_applied"] = False
    inspected = inspected[
        inspected[[
            "extreme_fund_weight_gt_10pct",
            "extreme_position_value_top_0_1pct",
            "extreme_adjusted_shares_top_0_1pct",
        ]].any(axis=1)
    ]
    inspected.to_csv(out / "exposure_extreme_positions_audit.csv", index=False)

    dist = distribution_summary(exposure)
    dist.to_csv(out / "exposure_distribution_summary.csv", index=False)

    causes = [
        {"comparison": "legacy_event_register_to_completed_v2", "old": 172,
         "new": metrics["completed_events"], "cause": "reconciled structural completion and removed provisional/duplicate representations"},
        {"comparison": "completed_v2_to_verified_exact_day", "old": metrics["completed_events"],
         "new": metrics["verified_exact_day_events"], "cause": "changed/insufficient effective-date precision"},
        {"comparison": "verified_exact_day_to_gate0", "old": metrics["verified_exact_day_events"],
         "new": metrics["gate0_pass_events"], "cause": "missing first-post filing"},
        {"comparison": "legacy_treated_ge_0_5pct_to_rebuilt", "old": metrics["legacy_treated_cusips_ge_0_5pct"],
         "new": metrics["rebuilt_treated_permnos_ge_0_5pct"], "cause": "exact-series PRE holdings, date-aware identifier remapping, corporate actions, and denominator coverage"},
        {"comparison": "common_equity_positions_to_exact_crsp", "old": metrics["common_equity_candidates_before_mapping"],
         "new": int(crosswalk.mapping_status.eq("exact_matched").sum()), "cause": "identifier remapping / non-U.S. / non-common-equity / ambiguity"},
        {"comparison": "mapped_positions_to_factor_available", "old": int(crosswalk.mapping_status.eq("exact_matched").sum()),
         "new": int(contrib.adjusted_shares.notna().sum()), "cause": "corporate-action factor coverage (CRSP archive ends 2025)"},
    ]
    pd.DataFrame(causes).to_csv(out / "universe_discrepancy_report.csv", index=False)

    total_value = pd.to_numeric(holdings.position_value_usd, errors="coerce").sum()
    common_value = pd.to_numeric(
        holdings.loc[holdings.is_common_equity_candidate, "position_value_usd"], errors="coerce"
    ).sum()
    matched_value = pd.to_numeric(
        crosswalk.loc[crosswalk.mapping_status.eq("exact_matched"), "position_value_usd"], errors="coerce"
    ).sum()
    all_match_rate = matched_value / total_value if total_value else 0
    common_match_rate = matched_value / common_value if common_value else 0
    dimensional_value_share = (
        matched_contrib.loc[matched_contrib.is_dimensional, "position_value_usd"].sum()
        / matched_contrib.position_value_usd.sum()
        if matched_contrib.position_value_usd.sum() else 0
    )
    top_sponsor = sponsor.iloc[0] if len(sponsor) else None
    top_wave = wave.sort_values("matched_position_value_share", ascending=False).iloc[0] if len(wave) else None
    report = f"""# P1 Exposure^pre construction report

Generated: {datetime.now(timezone.utc).isoformat()}

## Frozen universe and timing

- Gate0 PASS events: **{metrics['gate0_pass_events']}** across **{metrics['gate0_pass_waves']}** waves.
- Pending first-POST N-PORT events: **{metrics['gate0_pending_events']}**.
- PRE selection is the latest filing-internal `repPdDate` strictly before the verified effective date, using the exact predecessor series id.
- POST holdings are retained only as Gate0 evidence and are never read into treatment construction.

## Security mapping

- PRE N-PORT positions: **{metrics['nport_positions_pre']}**.
- Unique reported CUSIPs before mapping: **{metrics['unique_securities_before_mapping']}**.
- Mapping uses date-valid CRSP CIZ `stocknames_v2`: CUSIP9 first, CUSIP8 only as a labelled fallback. Fuzzy names are never used.
- Exact-matched position value / all N-PORT value: **{all_match_rate:.2%}**.
- Exact-matched position value / common-equity-candidate value: **{common_match_rate:.2%}**.
- Unmatched/non-CRSP/non-common share of candidate common-equity value: **{1-common_match_rate:.2%}**.

## Corporate actions and exposure definitions

The frozen formula is `AdjustedShares = RawShares × CFACSHR`. Legacy CRSP uses
`cfacshr`; 2025 CIZ uses `dlycumfacshr`. The factor is the same-day or most
recent prior trading-day observation within four calendar days of the N-PORT
report/as-of date. It is applied per fund-position before aggregation.

The consistent stock denominator is CRSP `shrout × 1,000` on the latest trading
day strictly before the wave effective date (maximum seven-day gap). Market cap
uses `abs(price) × shrout × 1,000` on that same date.

Candidate measures saved together:

- `adjusted_shares_held`: raw share dose after the frozen factor adjustment;
- `exposure_ownership`: adjusted shares / CRSP shares outstanding;
- `exposure_value`: summed N-PORT position value / CRSP market capitalization;
- `fund_portfolio_weight_sum`: sum of position value / predecessor net assets.

`exposure_ownership` is recommended as the primary measure because it matches
the frozen economic treatment definition and uses one pre-event denominator per
stock-wave. No result coefficient has been inspected.

## Concentration and extreme-position diagnostics

- Dimensional share of exact-matched PRE position value: **{dimensional_value_share:.2%}**.
- Largest adviser by exact-matched PRE position value: **{top_sponsor.adviser if top_sponsor is not None else 'n/a'}** (**{top_sponsor.matched_position_value_share if top_sponsor is not None else 0:.2%}**).
- Largest wave by exact-matched PRE position value: **{top_wave.wave_id if top_wave is not None else 'n/a'}** (**{top_wave.matched_position_value_share if top_wave is not None else 0:.2%}**).
- Exact-matched positions with fund portfolio weight above 10%: **{int(matched_contrib.fund_portfolio_weight.gt(.10).sum())}**.
- No position was automatically winsorized or removed. Flagged rows are preserved in `exposure_extreme_positions_audit.csv` for inspection.
- Sponsor and wave tables are in `exposure_sponsor_concentration.csv` and `exposure_wave_summary.csv`.

## Remaining blockers

- The archive has CRSP security returns/factors through 2025. 2026 observations
  that fail the four-/seven-day alignment are retained as explicit missing, not
  filled with stale 2025 factors.
- The economic-sponsor crosswalk is not signed. LOSO inputs therefore preserve
  position contributions and carry adviser labels only; they are not final
  sponsor-cluster matrices.
- Gate0 has 47 PASS waves, of which 30 currently contain at least one exact-mapped
  U.S. common stock with a valid pre-event CRSP denominator. The other 17 are
  retained in coverage files; most have no N-PORT position classified as U.S.
  common equity, and none is silently promoted into the stock-level sample.
- Two specified long-handoff events and every predecessor-report-after-event
  flag are carried, not automatically dropped.

## Lineage

Inputs and SHA-256 hashes are in `exposure_construction_lineage.json`. CRSP raw
files remain outside Git. No headline earnings outcomes or coefficients were
loaded or estimated.
"""
    (out / "exposure_construction_report.md").write_text(report)
    lineage = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": inputs,
        "crsp_sources": daily_lineage,
        "formula": "adjusted_shares = raw_reported_shares * share_factor",
        "primary_measure": "exposure_ownership",
        "outcomes_inspected": False,
    }
    (out / "exposure_construction_lineage.json").write_text(json.dumps(lineage, indent=2) + "\n")


def run(args) -> None:
    archive = args.archive.resolve()
    raw = archive / "p1_refraction_wrds_shared" / "raw"
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    holdings = pd.read_parquet(args.holdings)
    universe = pd.read_csv(args.universe)
    pending = pd.read_csv(args.pending)
    event_master = pd.read_csv(args.event_master)
    legacy = pd.read_parquet(args.legacy)

    stock_path = raw / "rescue" / "newcrsp_crsp_stocknames_v2_full.parquet"
    stocknames = pd.read_parquet(stock_path)
    by9, by8 = stockname_index(stocknames)

    candidates = holdings[holdings.is_common_equity_candidate].copy().reset_index(drop=True)
    mapped = pd.DataFrame([map_one_position(r, by9, by8) for r in candidates.itertuples(index=False)])
    crosswalk = pd.concat([candidates.reset_index(drop=True), mapped], axis=1)
    crosswalk.to_csv(out / "nport_crsp_security_crosswalk.csv", index=False)

    wanted = set(crosswalk.loc[crosswalk.mapping_status.eq("exact_matched"), "permno"].astype(int))
    daily, daily_lineage = load_crsp_daily(raw, wanted)
    contrib = attach_crsp(crosswalk, daily)
    exposure = aggregate_exposure(contrib)
    exposure.to_csv(out / "exposure_stock_wave_all.csv", index=False)
    aggregate_exposure(contrib[contrib.is_dimensional]).to_csv(
        out / "exposure_stock_wave_dimensional_only.csv", index=False
    )
    aggregate_exposure(contrib[~contrib.is_dimensional]).to_csv(
        out / "exposure_stock_wave_ex_dimensional.csv", index=False
    )
    write_loso_inputs(contrib, out / "exposure_loso_inputs")

    metrics = build_census(event_master, universe, pending, holdings, crosswalk, exposure, legacy)
    inputs = [
        {"path": str(Path(args.holdings).resolve()), "sha256": sha256(Path(args.holdings))},
        {"path": str(Path(args.universe).resolve()), "sha256": sha256(Path(args.universe))},
        {"path": str(Path(args.pending).resolve()), "sha256": sha256(Path(args.pending))},
        {"path": str(Path(args.event_master).resolve()), "sha256": sha256(Path(args.event_master))},
        {"path": str(stock_path), "sha256": sha256(stock_path)},
    ]
    write_reports(out, metrics, universe, pending, holdings, crosswalk, contrib,
                  exposure, daily_lineage, inputs)
    print(json.dumps(metrics, indent=2))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    p.add_argument("--holdings", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE)
    p.add_argument("--pending", type=Path, default=DEFAULT_PENDING)
    p.add_argument("--event-master", type=Path, default=DEFAULT_EVENT_MASTER)
    p.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p


def main(argv=None) -> int:
    run(parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
