#!/usr/bin/env python3
"""Apply the frozen six-event selection rule to the registered candidate pool.

The rule is `handoff/SELECTION_RULE.md`, committed before this file existed.
Nothing here may be tuned against its own output: outcome and treatment columns
are dropped and asserted absent before any filter or sort runs, so the draw
cannot condition on a realised return, a contribution, a surprise magnitude, or
an announcement-window market response.
"""
import hashlib
import sys

import pandas as pd

import ppw

SALT = "ppw-handoff-20260906-six-event-validation"

DROP_EARN = ["src_ret", "contribution_bps", "surprise_scaled", "date"]
DROP_FOMC = (["MP1", "MP2"] + [f"FF{i}" for i in range(1, 7)]
             + [f"ED{i}" for i in range(1, 9)] + ["OIS1Y", "OIS2Y"]
             + ["UST3M", "UST6M", "UST2Y", "UST5Y", "UST10Y", "UST30Y"]
             + ["TIPS5Y", "TIPS10Y", "TIPS30Y"]
             + ["SP500", "SPFUT", "DXY", "EURUSD", "USDJPY"])

# Published NYSE 13:00 ET early closes. Used only to *flag* a candidate whose
# session was short; it is an external calendar fact, not an archive extraction,
# so it is never allowed to silently admit anything.
EARLY_CLOSE = {
    "2019-07-03", "2019-11-29", "2019-12-24",
    "2020-11-27", "2020-12-24",
    "2021-11-26",
    "2022-11-25",
    "2023-07-03", "2023-11-24",
}


def trading_days():
    """NYSE session dates, taken from the CRSP daily market index."""
    d = pd.read_parquet(ppw.abspath("raw/crsp_dsi.parquet"), columns=["date"])
    return set(pd.to_datetime(d.date).dt.normalize())


def rank_of(key):
    return hashlib.sha256(f"{SALT}|{key}".encode()).hexdigest()


def strip_outcomes(d, cols, what):
    present = [c for c in cols if c in d.columns]
    d = d.drop(columns=present)
    leaked = [c for c in cols if c in d.columns]
    assert not leaked, f"{what}: outcome columns survived the drop: {leaked}"
    print(f"  {what}: dropped {len(present)} outcome/treatment columns "
          f"before any filter or sort")
    return d


def eligible_fomc(m, cal):
    m = strip_outcomes(m, DROP_FOMC, "FOMC candidates")
    m["Date"] = pd.to_datetime(m.Date).dt.normalize()
    n0 = len(m)
    step = []
    m = m[m.Unscheduled == 0];               step.append(("scheduled meeting", len(m)))
    m = m[m.date_time.notna()];              step.append(("statement clock recorded", len(m)))
    m = m[m.Date.isin(cal)];                 step.append(("NYSE trading day", len(m)))
    m["early_close"] = m.Date.dt.strftime("%Y-%m-%d").isin(EARLY_CLOSE)
    m = m[~m.early_close];                   step.append(("full session, not a 13:00 close", len(m)))
    print(f"\n  FOMC funnel from {n0}:")
    for lab, n in step:
        print(f"    {lab:<42s} {n:>4d}")
    m["key"] = "FOMC|" + m.Date.dt.strftime("%Y-%m-%d")
    m["rank"] = m.key.map(rank_of)
    m["year"] = m.Date.dt.year
    return m.sort_values(["rank", "key"])


def eligible_earn(e, cal):
    e = strip_outcomes(e, DROP_EARN, "earnings candidates")
    for c in ["event_date", "fpedats", "report_dt", "eff_dt",
              "reaction_date_session"]:
        e[c] = pd.to_datetime(e[c]).dt.normalize()
    # one event maps to one ETF and therefore one complete basket
    e = e.sort_values("etf").drop_duplicates(["permno", "fpedats"], keep="first")
    n0 = len(e)
    step = []
    e = e[e.session.isin(["BMO", "AMC"])];   step.append(("session verified BMO or AMC", len(e)))
    e = e[e.eff_before_event.astype(bool)];  step.append(("weights available before event", len(e)))
    e = e[e.report_age_days <= 120];         step.append(("report age <= 120 days", len(e)))
    e = e[e.prc_pre >= 5.0];                 step.append(("pre-event price >= $5", len(e)))
    e = e[e.event_date.isin(cal)];           step.append(("release date is a NYSE session", len(e)))
    e = e[e.reaction_date_session.isin(cal)];step.append(("reaction date is a NYSE session", len(e)))
    e["early_close"] = e.event_date.dt.strftime("%Y-%m-%d").isin(EARLY_CLOSE)
    e = e[~e.early_close];                   step.append(("full session, not a 13:00 close", len(e)))
    print(f"\n  earnings funnel from {n0} distinct (permno, fpedats):")
    for lab, n in step:
        print(f"    {lab:<42s} {n:>4d}")
    e["key"] = ("EARN|" + e.permno.astype(int).astype(str) + "|"
                + e.fpedats.dt.strftime("%Y-%m-%d") + "|" + e.etf)
    e["rank"] = e.key.map(rank_of)
    e["year"] = e.event_date.dt.year
    return e.sort_values(["rank", "key"])


def take_fomc(m, need=2):
    out = []
    for _, r in m.iterrows():
        if len(out) >= need:
            break
        if r.year in {x.year for x in out}:
            continue
        out.append(r)
    return out


def take_earn(e, session, need, used_permnos):
    out = []
    for _, r in e[e.session == session].iterrows():
        if len(out) >= need:
            break
        if r.permno in used_permnos or r.year in {x.year for x in out}:
            continue
        out.append(r)
        used_permnos.add(r.permno)
    return out


def shortfall(name, got, need, pool):
    if got >= need:
        return None
    msg = (f"MISSING CATEGORY: {name} — needed {need}, found {got} "
           f"among {pool} eligible candidates under the frozen rule")
    print(f"\n  {msg}")
    return msg


def main():
    cal = trading_days()
    print(f"  NYSE session calendar from crsp_dsi: {len(cal)} dates")

    m = pd.read_parquet(ppw.OUT / "s5_batch_fomc.parquet")
    e = pd.read_parquet(ppw.OUT / "s5_batch_earnings.parquet")
    print(f"  registered pool: {len(m)} FOMC, {len(e)} earnings rows")

    m = eligible_fomc(m, cal)
    e = eligible_earn(e, cal)
    print(f"\n  eligible: {len(m)} FOMC, "
          f"{(e.session=='BMO').sum()} BMO, {(e.session=='AMC').sum()} AMC")

    fom = take_fomc(m, 2)
    used = set()
    bmo = take_earn(e, "BMO", 2, used)
    amc = take_earn(e, "AMC", 2, used)

    gaps = [g for g in [
        shortfall("FOMC", len(fom), 2, len(m)),
        shortfall("BMO earnings", len(bmo), 2, int((e.session == "BMO").sum())),
        shortfall("AMC earnings", len(amc), 2, int((e.session == "AMC").sum())),
    ] if g]

    rows = []
    for r in fom:
        rows.append({"slot": "FOMC", "key": r.key, "rank": r["rank"],
                     "event_date": r.Date, "clock_raw": str(r.date_time),
                     "etf": "ALL_THREE", "permno": pd.NA, "cname": "FOMC statement",
                     "ticker": pd.NA, "cusip": pd.NA, "session": "REGULAR",
                     "sep": bool(r.SEP), "press_conf": bool(r.PC),
                     "report_dt": pd.NaT, "eff_dt": pd.NaT, "weight": pd.NA,
                     "report_age_days": pd.NA,
                     "reaction_date_session": r.Date})
    for r in bmo + amc:
        rows.append({"slot": r.session, "key": r.key, "rank": r["rank"],
                     "event_date": r.event_date, "clock_raw": str(r.ann_time_raw),
                     "etf": r.etf, "permno": int(r.permno), "cname": r.cname,
                     "ticker": r.ticker, "cusip": r.cusip, "session": r.session,
                     "sep": pd.NA, "press_conf": pd.NA,
                     "report_dt": r.report_dt, "eff_dt": r.eff_dt,
                     "weight": float(r.weight),
                     "report_age_days": int(r.report_age_days),
                     "reaction_date_session": r.reaction_date_session})
    six = pd.DataFrame(rows)

    print("\n  === selected ===")
    for _, r in six.iterrows():
        w = "" if pd.isna(r.weight) else f"  w={r.weight:.4%} age={r.report_age_days}d"
        print(f"    {r.slot:<7s} {str(r.event_date)[:10]}  {str(r.cname)[:28]:<28s}"
              f"  {r.etf:<9s} clock={r.clock_raw:<10s}{w}")
        print(f"            rank={r['rank'][:16]}…  key={r.key}")

    six.to_parquet(ppw.OUT / "s8_six_events.parquet", index=False)
    ppw.provenance("s8_01_select_six",
                   [ppw.OUT / "s5_batch_fomc.parquet",
                    ppw.OUT / "s5_batch_earnings.parquet",
                    ppw.abspath("raw/crsp_dsi.parquet")],
                   {"salt": SALT, "selected": len(six), "missing_categories": gaps,
                    "rule": "handoff/SELECTION_RULE.md"})
    print(f"\n  wrote {ppw.OUT/'s8_six_events.parquet'}  ({len(six)} events)")
    if gaps:
        print("\n  NOT SILENTLY REPLACED — the above categories are reported short.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
