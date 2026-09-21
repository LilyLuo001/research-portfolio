#!/usr/bin/env python3
"""SCC-only daily nonmechanical and issuer-specific network analysis.

Private row-level outputs stay under SCC. Files prefixed PUBLIC_ contain only
aggregate counts, coefficients, intervals, hashes, and opaque block labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


DEV_START = pd.Timestamp("2023-01-01")
DEV_END = pd.Timestamp("2023-06-30")
EXPOSED = {pd.Timestamp("2023-01-31"), pd.Timestamp("2023-07-28")}
CONTROL_OFFSETS = (-28, -21, -14, 14, 21, 28)
BOOT_REPS = 1999
MIN_BLOCKS = 6


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compound(values) -> float:
    a = np.asarray(values, dtype=float)
    return float(np.prod(1.0 + a) - 1.0) if len(a) and np.isfinite(a).all() else np.nan


def window_has_calendar_date(start, end, dates, left_open=False) -> bool:
    return any((start < d if left_open else start <= d) and d <= end for d in dates)


def overlap_components(windows: dict[pd.Timestamp, tuple[pd.Timestamp, pd.Timestamp]]):
    keys = sorted(windows)
    adjacency = {k: set() for k in keys}
    sessions = {k: set(pd.date_range(v[0], v[1], freq="D")) for k, v in windows.items()}
    # Actual dependence is shared trading sessions; calendar range is harmless
    # here because endpoints are adjacent trading dates and overlap is checked
    # again against the explicit endpoint pair below in main.
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if sessions[a] & sessions[b]:
                adjacency[a].add(b); adjacency[b].add(a)
    out, seen, block = {}, set(), 0
    for k in keys:
        if k in seen:
            continue
        block += 1
        stack = [k]; seen.add(k)
        while stack:
            x = stack.pop(); out[x] = block
            for y in adjacency[x]:
                if y not in seen:
                    seen.add(y); stack.append(y)
    return out


def effective(mask_date, start, end):
    return (start.isna() | (start <= mask_date)) & (end.isna() | (end >= mask_date))


def fit_ols(frame: pd.DataFrame, outcome: str, controls: list[str]):
    use = frame[[outcome, "event_id", "x_std"] + controls].dropna().copy()
    if use.empty:
        return {"beta": np.nan, "n": 0, "rank": 0, "k": 0}
    cols = ["x_std"] + controls
    for c in [outcome] + cols:
        use[c + "_w"] = use[c] - use.groupby("event_id")[c].transform("mean")
    y = use[outcome + "_w"].to_numpy(float)
    X = use[[c + "_w" for c in cols]].to_numpy(float)
    rank = int(np.linalg.matrix_rank(X))
    if rank < X.shape[1]:
        return {"beta": np.nan, "n": len(use), "rank": rank, "k": X.shape[1]}
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    return {"beta": float(beta[0]), "n": len(use), "rank": rank, "k": X.shape[1]}


def block_bootstrap(frame, outcome, controls, rng):
    blocks = sorted(frame.block_id.unique())
    if len(blocks) < MIN_BLOCKS:
        return np.nan, np.nan, 0
    use = frame[[outcome, "event_id", "block_id", "x_std"] + controls].dropna().copy()
    cols = ["x_std"] + controls
    for c in [outcome] + cols:
        use[c + "_w"] = use[c] - use.groupby("event_id")[c].transform("mean")
    cross = {}
    for b,g in use.groupby("block_id"):
        X = g[[c + "_w" for c in cols]].to_numpy(float)
        y = g[outcome + "_w"].to_numpy(float)
        cross[b] = (X.T @ X, X.T @ y)
    vals = []
    for _ in range(BOOT_REPS):
        counts = pd.Series(rng.choice(blocks, len(blocks), replace=True)).value_counts()
        xtx = sum((int(n) * cross[b][0] for b,n in counts.items()), np.zeros((len(cols),len(cols))))
        xty = sum((int(n) * cross[b][1] for b,n in counts.items()), np.zeros(len(cols)))
        if np.linalg.matrix_rank(xtx) == len(cols):
            vals.append(float(np.linalg.solve(xtx, xty)[0]))
    if len(vals) < int(0.8 * BOOT_REPS):
        return np.nan, np.nan, len(vals)
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975)), len(vals)


def mean_block_ci(values, rng):
    a = np.asarray(values, float)
    if len(a) < MIN_BLOCKS:
        return np.nan, np.nan
    draws = np.array([rng.choice(a, len(a), replace=True).mean() for _ in range(BOOT_REPS)])
    return float(np.quantile(draws, .025)), float(np.quantile(draws, .975))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--macro", type=Path, required=True)
    ap.add_argument("--pilot-blocks", type=int, default=0)
    args = ap.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    private = out / "private"
    out.mkdir(parents=True, exist_ok=True); private.mkdir(parents=True, exist_ok=True)
    raw = root / "raw"
    roster_dir = root / "derived/p1_concentration_information/20260920/roster"
    network_dir = root / "derived/p1_concentration_information/20260920_phase3/network_selection/results"

    paths = {
        "dsf2022": raw / "crsp_dsf_2022.parquet",
        "dsf2023": raw / "crsp_dsf_2023.parquet",
        "names": raw / "crsp_dsenames_full.parquet",
        "links": raw / "crsp_ibes_link_full.parquet",
        "actuals": raw / "ibes_actuals_eps_2023.parquet",
        "delist": raw / "rescue/crsp_dsedelist_allcols_2023.parquet",
        "roster": roster_dir / "private_top500_permco_marketcap.parquet",
        "events": roster_dir / "private_2023_top8_earnings_release_group_candidates.parquet",
        "pairs": network_dir / "private_pair_scores.parquet",
        "receivers": network_dir / "private_receiver_scores.parquet",
    }
    if not all(p.is_file() for p in paths.values()):
        raise FileNotFoundError([str(p) for p in paths.values() if not p.is_file()])

    roster = pd.read_parquet(paths["roster"])
    roster_permcos = set(roster.permco.astype(int))
    top8 = set(roster.loc[roster.issuer_rank <= 8, "permco"].astype(int))
    events = pd.read_parquet(paths["events"])
    events["anndats"] = pd.to_datetime(events.anndats)
    events = events[["issuer_rank", "permco", "anndats"]].drop_duplicates()
    all_top8_dates = events[["permco", "anndats"]].drop_duplicates()
    events = events[(events.anndats >= DEV_START) & (events.anndats <= DEV_END) & ~events.anndats.isin(EXPOSED)].copy()

    dsf_parts = []
    for key in ("dsf2022", "dsf2023"):
        filters = [("date", "==", "2022-12-30")] if key == "dsf2022" else [("date", ">=", "2023-01-01"), ("date", "<=", "2023-06-30")]
        x = pd.read_parquet(paths[key], columns=["permno", "permco", "date", "ret", "prc", "shrout", "vol"], filters=filters)
        x["date"] = pd.to_datetime(x.date)
        x = x[x.permco.isin(roster_permcos)]
        dsf_parts.append(x)
    dsf = pd.concat(dsf_parts, ignore_index=True).drop_duplicates(["permno", "date"], keep=False)
    calendar_all = [pd.Timestamp(d) for d in sorted(dsf.loc[dsf.date <= DEV_END, "date"].unique())]
    calendar = sorted(dsf.loc[(dsf.date >= DEV_START) & (dsf.date <= DEV_END), "date"].unique())
    calendar = [pd.Timestamp(d) for d in calendar]
    cal_set = set(calendar)
    prior_trade = {d: calendar_all[calendar_all.index(d)-1] for d in calendar if calendar_all.index(d) > 0}

    def two_sessions(announcement_date):
        eligible = [d for d in calendar if d >= pd.Timestamp(announcement_date)]
        return (eligible[0], eligible[1]) if len(eligible) >= 2 and eligible[1] <= DEV_END else None

    event_windows = {d: two_sessions(d) for d in sorted(events.anndats.unique())}
    event_windows = {pd.Timestamp(k): v for k, v in event_windows.items() if v is not None}
    events = events[events.anndats.isin(event_windows)].copy()
    # Dependence components use actual shared endpoint trading sessions.
    keys = sorted(event_windows)
    adjacency = {k: set() for k in keys}
    for i, a in enumerate(keys):
        sa = set(event_windows[a])
        for b in keys[i + 1:]:
            if sa & set(event_windows[b]):
                adjacency[a].add(b); adjacency[b].add(a)
    block_map, seen, bi = {}, set(), 0
    for k in keys:
        if k in seen: continue
        bi += 1; stack = [k]; seen.add(k)
        while stack:
            z = stack.pop(); block_map[z] = bi
            for y in adjacency[z]:
                if y not in seen: seen.add(y); stack.append(y)
    if args.pilot_blocks:
        keep = set(sorted(set(block_map.values()))[:args.pilot_blocks])
        event_windows = {k:v for k,v in event_windows.items() if block_map[k] in keep}
        events = events[events.anndats.isin(event_windows)].copy()

    # Date-valid common-stock filter and company returns.
    names = pd.read_parquet(paths["names"], columns=["permno", "permco", "namedt", "nameendt", "shrcd", "siccd"])
    names["namedt"] = pd.to_datetime(names.namedt); names["nameendt"] = pd.to_datetime(names.nameendt)
    m = dsf.merge(names, on=["permno", "permco"], how="left")
    m = m[effective(m.date, m.namedt, m.nameendt) & m.shrcd.isin([10,11])].copy()
    m = m.sort_values(["permno", "date"])
    m["market_cap"] = m.prc.abs() * m.shrout * 1000.0
    # Preserve date-valid cutoff identity before the lagged-cap/return filter;
    # Dec-30 is the sole loaded 2022 row and therefore has no within-load lag.
    cutoff_identity = (m[m.date == pd.Timestamp("2022-12-30")]
                       .sort_values(["permco","market_cap"],ascending=[True,False])
                       .drop_duplicates("permco"))
    m["prior_market_cap"] = m.groupby("permno").market_cap.shift(1)
    dl = pd.read_parquet(paths["delist"], columns=["permno", "dlstdt", "dlret"],
                         filters=[("dlstdt", ">=", "2023-01-01"), ("dlstdt", "<=", "2023-06-30")])
    dl["date"] = pd.to_datetime(dl.dlstdt)
    dl = dl.dropna(subset=["date"]).drop_duplicates(["permno", "date"], keep=False)
    m = m.merge(dl[["permno", "date", "dlret"]], on=["permno", "date"], how="left")
    both = m.ret.notna() & m.dlret.notna()
    m["total_ret"] = m.ret
    m.loc[m.ret.isna() & m.dlret.notna(), "total_ret"] = m.loc[m.ret.isna() & m.dlret.notna(), "dlret"]
    m.loc[both, "total_ret"] = (1 + m.loc[both, "ret"]) * (1 + m.loc[both, "dlret"]) - 1
    m = m[m.total_ret.notna() & (m.prior_market_cap > 0)].copy()
    m["wr"] = m.total_ret * m.prior_market_cap
    company_daily = (m.groupby(["permco", "date"], as_index=False)
                     .agg(wr=("wr", "sum"), prior_market_cap=("prior_market_cap", "sum"),
                          shareclasses=("permno", "nunique")))
    company_daily["company_ret"] = company_daily.wr / company_daily.prior_market_cap
    dret = company_daily.set_index(["permco", "date"]).company_ret

    # Conservative all-top500 own-EPS announcement map via effective links.
    actual = pd.read_parquet(paths["actuals"], columns=["ticker", "anndats"], filters=[("anndats", ">=", "2023-01-01"), ("anndats", "<=", "2023-06-30")])
    actual["anndats"] = pd.to_datetime(actual.anndats); actual = actual.dropna().drop_duplicates()
    links = pd.read_parquet(paths["links"], columns=["ticker", "permno", "sdate", "edate"])
    links["sdate"] = pd.to_datetime(links.sdate); links["edate"] = pd.to_datetime(links.edate)
    own = actual.merge(links, on="ticker", how="inner")
    own = own[effective(own.anndats, own.sdate, own.edate)]
    hist = names[["permno", "permco", "namedt", "nameendt"]].drop_duplicates()
    own = own.merge(hist, on="permno", how="inner")
    own = own[effective(own.anndats, own.namedt, own.nameendt) & own.permco.isin(roster_permcos)]
    own_dates = own[["permco", "anndats"]].drop_duplicates()
    own_map = {int(k): set(v.anndats) for k,v in own_dates.groupby("permco")}

    # All H1 top8 windows identify overlapping announcers and contaminated controls.
    all_top8_windows = {}
    for d in sorted(all_top8_dates.anndats.unique()):
        if DEV_START <= d <= DEV_END:
            w = two_sessions(d)
            if w: all_top8_windows[pd.Timestamp(d)] = w
    top8_by_date = {d:set(g.permco.astype(int)) for d,g in all_top8_dates.groupby("anndats")}
    macro_obj = json.loads(args.macro.read_text())
    macro_sets = {k:set(pd.to_datetime(v)) for k,v in macro_obj["dates"].items()}
    all_macro = set().union(*macro_sets.values())

    def own_overlap(permco, w):
        return window_has_calendar_date(prior_trade[w[0]], w[1], own_map.get(int(permco), set()), left_open=True)

    def window_return(permco, w):
        vals = [dret.get((int(permco), d), np.nan) for d in w]
        return compound(vals)

    rows, control_records = [], []
    for event_date, ew in event_windows.items():
        overlapping_announcers = set()
        for d,w in all_top8_windows.items():
            if set(ew) & set(w): overlapping_announcers |= top8_by_date.get(d, set())
        event_macro = window_has_calendar_date(prior_trade[ew[0]], ew[1], all_macro, left_open=True)
        for permco in sorted(roster_permcos - overlapping_announcers):
            if own_overlap(permco, ew):
                continue
            er = window_return(permco, ew)
            if not np.isfinite(er):
                continue
            controls, used_control_windows, macro_controls = [], [], 0
            for off in CONTROL_OFFSETS:
                start = ew[0] + pd.Timedelta(days=off)
                if start not in cal_set:
                    continue
                ix = calendar.index(start)
                if ix + 1 >= len(calendar): continue
                cw = (calendar[ix], calendar[ix+1])
                if cw[1] > DEV_END: continue
                if any(set(cw) & set(w) for w in all_top8_windows.values()): continue
                if own_overlap(permco, cw): continue
                cr = window_return(permco, cw)
                if np.isfinite(cr):
                    controls.append(cr)
                    used_control_windows.append(cw)
                    macro_controls += int(window_has_calendar_date(prior_trade[cw[0]], cw[1], all_macro, left_open=True))
            if len(controls) < 2:
                continue
            control_records.extend({"event_date":event_date,"permco":int(permco),"control_start":cw[0],"control_end":cw[1]}
                                   for cw in used_control_windows)
            rows.append({"event_date":event_date,"block_id":block_map[event_date],"permco":int(permco),
                         "event_ret":er,"control_ret":float(np.mean(controls)),
                         "control_abs_ret":float(np.mean(np.abs(controls))),
                         "signed_diff":er-float(np.mean(controls)),
                         "abs_diff":abs(er)-float(np.mean(np.abs(controls))),
                         "n_controls":len(controls),"event_macro_overlap":event_macro,
                         "macro_control_windows":macro_controls})
    response = pd.DataFrame(rows)
    control_provenance = pd.DataFrame(control_records)
    response.to_parquet(private / "private_receiver_event_responses.parquet", index=False)
    control_provenance.to_parquet(private / "private_control_window_provenance.parquet", index=False)
    if response.empty: raise RuntimeError("No eligible receiver-event responses")

    # Aggregate one fact per overlap block after date-level portfolio formation.
    roster_w = roster.set_index("permco").market_cap_usd
    daily_rows = []
    for (event_date, block_id), g in response.groupby(["event_date", "block_id"]):
        for weighting in ("equal", "fixed_2022_12_30_market_cap"):
            w = np.ones(len(g)) if weighting == "equal" else g.permco.map(roster_w).to_numpy(float)
            w = w / w.sum()
            vals = {c:float(np.dot(w,g[c])) for c in ["event_ret","control_ret","signed_diff"]}
            vals["event_abs_ret"] = float(np.dot(w, np.abs(g.event_ret)))
            vals["control_abs_ret"] = float(np.dot(w, g.control_abs_ret))
            vals["abs_diff"] = float(np.dot(w, g.abs_diff))
            daily_rows.append({"event_date":event_date,"block_id":block_id,"weighting":weighting,
                               "receivers":len(g),"event_macro_overlap":bool(g.event_macro_overlap.iloc[0]),**vals})
    daily_date = pd.DataFrame(daily_rows)
    # If adjacent dates share an overlap block, average dates within block first.
    daily_block = daily_date.groupby(["block_id","weighting"], as_index=False).agg(
        event_ret=("event_ret","mean"),control_ret=("control_ret","mean"),signed_diff=("signed_diff","mean"),
        event_abs_ret=("event_abs_ret","mean"),control_abs_ret=("control_abs_ret","mean"),abs_diff=("abs_diff","mean"),
        receiver_date_rows=("receivers","sum"),event_dates=("event_date","nunique"),
        event_macro_overlap=("event_macro_overlap","max"))
    rng = np.random.default_rng(20260921)
    public_daily = []
    for weighting, g0 in daily_block.groupby("weighting"):
        for sample_name,g in [("all_development_blocks",g0),("exclude_named_macro_overlap_blocks",g0[~g0.event_macro_overlap])]:
            for outcome,ec,cc in [("signed_return","event_ret","control_ret"),("mean_stock_absolute_response","event_abs_ret","control_abs_ret")]:
                diff = g["signed_diff" if outcome=="signed_return" else "abs_diff"]
                lo,hi = mean_block_ci(diff,rng)
                public_daily.append({"population":"top500_broad_exclusions","weighting":weighting,"sample":sample_name,
                    "outcome":outcome,"event_mean":g[ec].mean(),"control_mean":g[cc].mean(),"event_minus_control":diff.mean(),
                    "ci_low":lo,"ci_high":hi,"unique_overlap_blocks":g.block_id.nunique(),
                    "unique_event_dates":int(g.event_dates.sum()),"receiver_date_rows":int(g.receiver_date_rows.sum())})
    pd.DataFrame(public_daily).to_csv(out / "PUBLIC_DAILY_NONMECHANICAL_RESULTS.csv", index=False)

    # Issuer-specific network rows. Missing pair records are left missing, never zero.
    pairs = pd.read_parquet(paths["pairs"])
    pairs = pairs[pairs.variant == "PURE_D"].copy()
    recv = pd.read_parquet(paths["receivers"])
    recv = recv[recv.variant == "PURE_D"][["receiver_permco","company_market_cap","avg_daily_dollar_volume","sic2"]]
    # Issuer SIC2 at cutoff: take the largest roster share class at 2022-12-30.
    issuer_sic = (cutoff_identity[cutoff_identity.permco.isin(top8)].set_index("permco").siccd // 100).to_dict()
    ev = events.rename(columns={"permco":"issuer_permco"})[["issuer_permco","anndats"]].drop_duplicates()
    net = ev.merge(pairs[["issuer_permco","receiver_permco","pair_strength"]],on="issuer_permco",how="inner")
    net = net.merge(response.rename(columns={"event_date":"anndats","permco":"receiver_permco"}),on=["anndats","receiver_permco"],how="inner")
    net = net.merge(recv,on="receiver_permco",how="left")
    net["issuer_sic2"] = net.issuer_permco.map(issuer_sic)
    net["same_focal_sic2"] = np.where(net.sic2.notna() & net.issuer_sic2.notna(), (net.sic2 == net.issuer_sic2).astype(float), np.nan)
    net["log_size"] = np.log(net.company_market_cap)
    net["log_liquidity"] = np.log(net.avg_daily_dollar_volume)
    net["log_pair_strength"] = np.log(net.pair_strength)
    xmean, xsd = float(net.log_pair_strength.mean()), float(net.log_pair_strength.std(ddof=1))
    net["x_std"] = (net.log_pair_strength - xmean) / xsd
    net["event_id"] = net.issuer_permco.astype(str) + "_" + net.anndats.dt.strftime("%Y%m%d")
    net.to_parquet(private / "private_issuer_receiver_analysis.parquet", index=False)

    specs = [("connection_event_fe",[]),("plus_pre_size_liquidity_focal_sic2",["log_size","log_liquidity","same_focal_sic2"])]
    outcomes = [("absolute_event_minus_control","abs_diff"),("signed_event_minus_control","signed_diff"),("raw_absolute_event_return","event_ret_abs")]
    net["event_ret_abs"] = net.event_ret.abs()
    public_net, loo_rows = [], []
    for sample_name,sample in [("all_observed_positive_pairs",net),("focal_same_sic2_only",net[net.same_focal_sic2==1])]:
        for spec,controls in specs:
            if sample_name == "focal_same_sic2_only" and "same_focal_sic2" in controls:
                controls = [c for c in controls if c != "same_focal_sic2"]
            for outname,col in outcomes:
                ans = fit_ols(sample,col,controls)
                lo,hi,nboot = block_bootstrap(sample,col,controls,rng)
                public_net.append({"sample":sample_name,"specification":spec,"outcome":outname,
                    "coefficient_per_1sd_log_pair_strength":ans["beta"],"ci_low":lo,"ci_high":hi,"successful_bootstrap_draws":nboot,
                    "rows":ans["n"],"unique_receivers":sample.receiver_permco.nunique(),"issuer_events":sample.event_id.nunique(),
                    "event_dates":sample.anndats.nunique(),"overlap_blocks":sample.block_id.nunique(),"design_rank":ans["rank"],"design_columns":ans["k"],
                    "log_pair_strength_mean":xmean,"log_pair_strength_sd":xsd})
                for block in sorted(sample.block_id.unique()):
                    la = fit_ols(sample[sample.block_id != block],col,controls)
                    loo_rows.append({"sample":sample_name,"specification":spec,"outcome":outname,
                                     "omitted_block":f"B{int(block):02d}","coefficient":la["beta"],"rows":la["n"]})
    pd.DataFrame(public_net).to_csv(out / "PUBLIC_ISSUER_RECEIVER_NETWORK_RESULTS.csv",index=False)
    pd.DataFrame(loo_rows).to_csv(out / "PUBLIC_LEAVE_ONE_BLOCK_OUT.csv",index=False)

    # Exact reuse and calendar-support dependence diagnostics. These do not
    # retroactively change the frozen event-overlap bootstrap.
    control_reuse = (control_provenance.groupby(["permco","control_start","control_end"])
                     .agg(focal_dates=("event_date","nunique"),rows=("event_date","size")).reset_index())
    shared_receiver_control_rows = int(control_reuse.loc[control_reuse.focal_dates > 1,"rows"].sum())
    date_support = {}
    for d in event_windows:
        support = set(event_windows[d])
        cp = control_provenance[control_provenance.event_date == d]
        support |= set(cp.control_start); support |= set(cp.control_end)
        date_support[d] = support
    dep_adj = {d:set() for d in date_support}
    dkeys = sorted(date_support)
    for i,a in enumerate(dkeys):
        for b in dkeys[i+1:]:
            if date_support[a] & date_support[b]:
                dep_adj[a].add(b); dep_adj[b].add(a)
    dep_seen, dep_sizes = set(), []
    for d in dkeys:
        if d in dep_seen: continue
        stack=[d]; dep_seen.add(d); n=0
        while stack:
            z=stack.pop(); n+=1
            for y in dep_adj[z]:
                if y not in dep_seen: dep_seen.add(y); stack.append(y)
        dep_sizes.append(n)
    dependency = {
      "unique_control_windows":int(control_provenance[["control_start","control_end"]].drop_duplicates().shape[0]),
      "receiver_control_window_keys":int(len(control_reuse)),
      "receiver_control_window_keys_reused_across_focal_dates":int((control_reuse.focal_dates>1).sum()),
      "rows_in_reused_receiver_control_window_keys":shared_receiver_control_rows,
      "event_plus_control_calendar_components":len(dep_sizes),
      "largest_component_event_dates":max(dep_sizes) if dep_sizes else 0,
      "event_overlap_bootstrap_fully_adjusts_shared_control_dependence":False,
      "precision_status":"HEURISTIC_NOT_FULLY_DEPENDENCE_ADJUSTED",
    }
    (out / "PUBLIC_CONTROL_REUSE_AND_DEPENDENCE.json").write_text(json.dumps(dependency,indent=2)+"\n")

    # Attrition, dependence and source receipt.
    attr = [
      {"stage":"fixed_top500_companies","count":len(roster),"unit":"company"},
      {"stage":"top8_calendar_release_groups_all_2023","count":len(pd.read_parquet(paths["events"])),"unit":"release_group"},
      {"stage":"development_issuer_dates_after_exposed_exclusion","count":len(events),"unit":"issuer_date"},
      {"stage":"development_unique_dates","count":events.anndats.nunique(),"unit":"date"},
      {"stage":"development_overlap_blocks","count":len(set(block_map[d] for d in event_windows)),"unit":"overlap_block"},
      {"stage":"broad_receiver_date_rows_with_event_and_2plus_controls","count":len(response),"unit":"receiver_date"},
      {"stage":"network_observed_positive_pair_analysis_rows","count":len(net),"unit":"issuer_receiver_event"},
      {"stage":"network_unique_receivers","count":net.receiver_permco.nunique(),"unit":"receiver_company"},
      {"stage":"network_missing_pairs_imputed_zero","count":0,"unit":"pair"},
    ]
    pd.DataFrame(attr).to_csv(out / "PUBLIC_SAMPLE_ATTRITION_AND_DEPENDENCE.csv",index=False)
    summary = {
      "status":"PILOT" if args.pilot_blocks else "FULL_DEVELOPMENT_EXECUTED",
      "privacy":"licensed identifiers, row-level returns and private pair data remain on SCC",
      "seal":{"return_dates_read_latest":str(max(company_daily.date).date()),"analysis_filter_latest":str(DEV_END.date()),
              "holdout_responses_used":False,"previously_exposed_dates_excluded":sorted(str(x.date()) for x in EXPOSED)},
      "counts":{"issuer_dates":int(len(events)),"unique_dates":int(events.anndats.nunique()),
                "overlap_blocks":int(len(set(block_map[d] for d in event_windows))),"broad_response_rows":int(len(response)),
                "network_rows":int(len(net)),"network_receivers":int(net.receiver_permco.nunique()),
                "macro_event_dates":int(daily_date[daily_date.event_macro_overlap].event_date.nunique())},
      "pair_scale":{"transform":"log positive observed PURE_D pair_strength, standardized on eligible primary rows",
                    "mean":xmean,"sd_ddof1":xsd,"missing_pair":"UNKNOWN_NOT_ZERO"},
      "control_dependence":dependency,
      "source_sha256":{k:sha256(v) for k,v in paths.items()},
      "macro_calendar_sha256":sha256(args.macro),
      "limits":["development-only descriptive estimates","small number of overlapping-window blocks; bootstrap intervals are heuristic",
                "limited macro calendar is not exhaustive","baseline holding reports may be stale relative to cutoff",
                "positive observed pair table does not distinguish absent from true zero"],
    }
    (out / "PUBLIC_RUN_SUMMARY.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({"status":summary["status"],"counts":summary["counts"]},indent=2))


if __name__ == "__main__":
    main()
