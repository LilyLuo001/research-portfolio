#!/usr/bin/env python3
"""Build the frozen H2 response panel on SCC after the independent gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from replication_statistics import sha256, verify_opening_gate

H2_START = pd.Timestamp("2023-07-01")
H2_END = pd.Timestamp("2023-12-31")
PRE_DATE = pd.Timestamp("2023-06-30")


def compound(a) -> float:
    x = np.asarray(a, float)
    return float(np.prod(1.0 + x) - 1.0) if len(x) == 2 and np.isfinite(x).all() else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--design", type=Path, required=True)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--bind", type=Path, nargs="+", required=True,
                    help="Metadata/control files named in the approved pre-outcome hash set")
    ap.add_argument("--private-out", type=Path, required=True)
    ap.add_argument("--public-receipt", type=Path, required=True)
    args = ap.parse_args()

    root, stage = args.root.resolve(), args.stage.resolve()
    bound = [p.resolve() for p in args.bind]
    if args.design.resolve() not in bound or args.controls.resolve() not in bound:
        raise PermissionError("the exact --design and --controls paths must both be in --bind")
    gate = verify_opening_gate(stage, bound)
    # The first response-bearing read occurs only below this successful guard.
    design = pd.read_parquet(args.design)
    controls = pd.read_parquet(args.controls)
    if design.duplicated(["event_id", "receiver_id"]).any():
        raise ValueError("duplicate event/receiver design keys")
    if controls.duplicated(["event_id", "receiver_id", "control_start", "control_end"]).any():
        raise ValueError("duplicate receiver-control keys")
    for df, cols in ((design, ["event_start", "event_end"]),
                     (controls, ["control_start", "control_end"])):
        for c in cols:
            df[c] = pd.to_datetime(df[c])
            if not df[c].between(H2_START, H2_END).all():
                raise ValueError(f"{c} crosses approved H2 response boundary")

    raw = root / "raw"
    dsf_path = raw / "crsp_dsf_2023.parquet"
    delist_path = raw / "rescue/crsp_dsedelist_allcols_2023.parquet"
    names_path = raw / "crsp_dsenames_full.parquet"
    receiver_ids = set(design.receiver_id.astype(int))

    calendar = pd.read_parquet(dsf_path, columns=["date"])
    dates = sorted(pd.to_datetime(calendar.date).dropna().unique())
    previous = {pd.Timestamp(dates[i]): pd.Timestamp(dates[i - 1]) for i in range(1, len(dates))}
    required_dates = set(design.event_start) | set(design.event_end) | set(controls.control_start) | set(controls.control_end)
    cap_dates = required_dates | {previous[d] for d in required_dates if d in previous}
    required_iso = sorted(str(pd.Timestamp(d).date()) for d in required_dates)
    cap_iso = sorted(str(pd.Timestamp(d).date()) for d in cap_dates)
    receiver_list = sorted(receiver_ids)
    # Cap fields are projected only for required dates and their immediately
    # preceding trading dates. RET is separately projected only on required H2 dates.
    cap = pd.read_parquet(dsf_path, columns=["permno", "permco", "date", "prc", "shrout"],
                          filters=[("date", "in", cap_iso), ("permco", "in", receiver_list)])
    ret = pd.read_parquet(dsf_path, columns=["permno", "permco", "date", "ret"],
                          filters=[("date", "in", required_iso), ("permco", "in", receiver_list)])
    for df in (cap, ret):
        df["date"] = pd.to_datetime(df.date)
    dup_cap = int(cap.duplicated(["permno", "date"], keep=False).sum())
    dup_ret = int(ret.duplicated(["permno", "date"], keep=False).sum())
    cap = cap.drop_duplicates(["permno", "date"], keep=False)
    ret = ret.drop_duplicates(["permno", "date"], keep=False)
    dsf = cap.merge(ret, on=["permno", "permco", "date"], how="left")
    dsf["is_h2_response"] = dsf.date.isin(required_dates)

    names = pd.read_parquet(names_path, columns=["permno", "permco", "namedt", "nameendt", "shrcd"])
    names["namedt"] = pd.to_datetime(names.namedt)
    names["nameendt"] = pd.to_datetime(names.nameendt)
    x = dsf.merge(names, on=["permno", "permco"], how="left")
    active = ((x.namedt.isna() | (x.namedt <= x.date)) &
              (x.nameendt.isna() | (x.nameendt >= x.date)))
    x = x[active].copy()
    # Conflicting simultaneous share codes are identity-ambiguous and excluded.
    sh = (x.groupby(["permno", "permco", "date"], as_index=False)
          .agg(shrcd_values=("shrcd", lambda z: tuple(sorted(set(z.dropna().astype(int)))))))
    sh["shrcd"] = sh.shrcd_values.map(lambda z: z[0] if len(z) == 1 else np.nan)
    base = dsf.merge(sh[["permno", "permco", "date", "shrcd"]],
                     on=["permno", "permco", "date"], how="left")
    base = base[base.shrcd.isin([10, 11])].sort_values(["permno", "date"]).copy()
    base["market_cap"] = base.prc.abs() * base.shrout * 1000.0
    base["lag_date"] = base.groupby("permno").date.shift(1)
    base["prior_market_cap"] = base.groupby("permno").market_cap.shift(1)
    base["expected_lag_date"] = base.date.map(previous)
    base["adjacent_lag"] = base.lag_date.eq(base.expected_lag_date)

    selected_permnos = sorted(set(base.permno.astype(int)))
    dl = pd.read_parquet(delist_path, columns=["permno", "dlstdt", "dlret"],
                         filters=[("dlstdt", "in", required_iso), ("permno", "in", selected_permnos)])
    dl["date"] = pd.to_datetime(dl.dlstdt)
    dup_dl = int(dl.duplicated(["permno", "date"], keep=False).sum())
    dl = dl.dropna(subset=["date"]).drop_duplicates(["permno", "date"], keep=False)
    base = base.merge(dl[["permno", "date", "dlret"]], on=["permno", "date"], how="left")
    both = base.ret.notna() & base.dlret.notna()
    base["total_ret"] = base.ret
    base.loc[base.ret.isna() & base.dlret.notna(), "total_ret"] = base.loc[base.ret.isna() & base.dlret.notna(), "dlret"]
    base.loc[both, "total_ret"] = (1 + base.loc[both, "ret"]) * (1 + base.loc[both, "dlret"]) - 1
    base["weight_eligible"] = base.adjacent_lag & (base.prior_market_cap > 0)
    base["contributes"] = base.weight_eligible & base.total_ret.notna()
    base["denom_cap"] = np.where(base.weight_eligible, base.prior_market_cap, 0.0)
    base["contrib_cap"] = np.where(base.contributes, base.prior_market_cap, 0.0)
    base["weighted_ret"] = np.where(base.contributes, base.prior_market_cap * base.total_ret, 0.0)
    daily = (base[base.is_h2_response].groupby(["permco", "date"], as_index=False)
             .agg(weighted_ret=("weighted_ret", "sum"), denom_cap=("denom_cap", "sum"),
                  contrib_cap=("contrib_cap", "sum"), eligible_classes=("weight_eligible", "sum"),
                  contributing_classes=("contributes", "sum")))
    daily["company_ret"] = daily.weighted_ret / daily.contrib_cap.replace(0, np.nan)
    daily["lagged_cap_weight_coverage"] = daily.contrib_cap / daily.denom_cap.replace(0, np.nan)
    daily["missing_return_classes"] = daily.eligible_classes - daily.contributing_classes
    required_base = base[base.is_h2_response]
    invalid_lag_class_dates = int((~required_base.adjacent_lag | ~(required_base.prior_market_cap > 0)).sum())
    adjacent_missing_return_class_dates = int((required_base.weight_eligible & required_base.total_ret.isna()).sum())
    dret = daily.set_index(["permco", "date"]).company_ret
    dcov = daily.set_index(["permco", "date"]).lagged_cap_weight_coverage
    dmiss = daily.set_index(["permco", "date"]).missing_return_classes

    ctl_group = {k: g for k, g in controls.groupby(["event_id", "receiver_id"])}
    rows = []
    missing_event, insufficient_control = 0, 0
    coverage_values, missing_class_total = [], 0
    for r in design.itertuples(index=False):
        key = (r.event_id, int(r.receiver_id))
        event_vals = [dret.get((int(r.receiver_id), r.event_start), np.nan),
                      dret.get((int(r.receiver_id), r.event_end), np.nan)]
        event_ret = compound(event_vals)
        if not np.isfinite(event_ret):
            missing_event += 1
            continue
        er_cov = [dcov.get((int(r.receiver_id), r.event_start), np.nan),
                  dcov.get((int(r.receiver_id), r.event_end), np.nan)]
        cr, cr_cov, cr_miss = [], [], []
        for c in ctl_group.get(key, pd.DataFrame()).itertuples(index=False):
            vals = [dret.get((int(r.receiver_id), c.control_start), np.nan),
                    dret.get((int(r.receiver_id), c.control_end), np.nan)]
            z = compound(vals)
            if np.isfinite(z):
                cr.append(z)
                cr_cov.extend([dcov.get((int(r.receiver_id), c.control_start), np.nan),
                               dcov.get((int(r.receiver_id), c.control_end), np.nan)])
                cr_miss.extend([dmiss.get((int(r.receiver_id), c.control_start), 0),
                                dmiss.get((int(r.receiver_id), c.control_end), 0)])
        if len(cr) < 2:
            insufficient_control += 1
            continue
        coverage_values.extend(er_cov + cr_cov)
        missing_class_total += int(sum(dmiss.get((int(r.receiver_id), d), 0)
                                       for d in (r.event_start, r.event_end)) + sum(cr_miss))
        z = r._asdict()
        z.update(outcome=abs(event_ret) - float(np.mean(np.abs(cr))), event_ret=event_ret,
                 mean_abs_control_ret=float(np.mean(np.abs(cr))), n_controls=len(cr),
                 minimum_lagged_cap_weight_coverage=float(np.nanmin(er_cov + cr_cov)))
        rows.append(z)
    panel_columns = list(design.columns) + ["outcome", "event_ret", "mean_abs_control_ret",
                                             "minimum_lagged_cap_weight_coverage"]
    panel = pd.DataFrame(rows, columns=list(dict.fromkeys(panel_columns)))
    args.private_out.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.private_out, index=False)
    finite_cov = np.asarray([v for v in coverage_values if np.isfinite(v)], float)
    receipt = {
        "status": "PRIVATE_RESPONSE_PANEL_BUILT_PENDING_ESTIMATION",
        "gate_status": gate["status"], "gate_sha256": sha256(stage / "PREOUTCOME_REVIEW.json"),
        "approved_h2_response_range": [str(H2_START.date()), str(H2_END.date())],
        "source_predicates": {"RET": "date IN exact frozen event/control response dates AND permco IN frozen receivers",
                              "DLRET": "dlstdt IN exact frozen response dates AND permno IN selected receiver share classes",
                              "cap_fields": "exact response dates plus their immediately preceding trading dates; RET omitted"},
        "counts": {"metadata_design_rows": int(len(design)), "response_panel_rows": int(len(panel)),
                   "missing_event_response_rows": missing_event,
                   "fewer_than_two_valid_control_response_rows": insufficient_control,
                   "duplicate_dsf_cap_source_rows_excluded": dup_cap,
                   "duplicate_dsf_ret_source_rows_excluded": dup_ret,
                   "duplicate_delist_source_rows_excluded": dup_dl,
                   "required_class_dates_with_nonadjacent_or_nonpositive_lag_cap": invalid_lag_class_dates,
                   "required_adjacent_positive_lag_class_dates_missing_ret_and_dlret": adjacent_missing_return_class_dates,
                   "analysis_window_missing_return_shareclass_uses": missing_class_total},
        "lagged_cap_weight_coverage": {"minimum": float(finite_cov.min()) if len(finite_cov) else None,
                                       "mean": float(finite_cov.mean()) if len(finite_cov) else None,
                                       "scope": "CONDITIONAL_ON_OBSERVED_ADJACENT_POSITIVE_LAG_CLASSES_NOT_COMPLETE_COMPANY_WEIGHT"},
        "private_panel_sha256": sha256(args.private_out),
        "private_panel_not_exported": True,
        "sample_refilled_after_response": False,
    }
    args.public_receipt.parent.mkdir(parents=True, exist_ok=True)
    args.public_receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
