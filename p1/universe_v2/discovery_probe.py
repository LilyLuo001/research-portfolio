"""Look for conversions the N-14 spine could not have seen, without using N-14.

Every recall check so far has been circular in one way or another. LEGACY_GOLD is
the output of the earlier discovery system, so agreeing with it cannot surface an
event both systems missed. The in-place rename test only sees funds that kept
their series id. The benchmark's own list is not published, so it cannot be
diffed. None of that licenses "discovery miss = 0".

This probe uses a different channel entirely: N-CEN's census of who exists.
A conversion leaves a shape there regardless of what was filed on N-14 -- a
listed ETF series starts appearing at about the moment a non-ETF series stops.
That shape is necessary for a conversion but not sufficient for one, so a hit is
a candidate to be read, not an event to be counted.

Two things make the shape usable rather than vacuous.

First, death is defined against the registrant's own panel, not against the
calendar. "Last seen before 2024" is not death: it is what a live fund looks like
whenever its next N-CEN has not been filed, or was filed late, or is missing from
the bulk data -- and at least one registrant here (CIK 1710607) is right-truncated
in exactly that way, which would otherwise have declared ten live Avantis funds
dead. A series is treated as dead only if its registrant filed a LATER N-CEN in
which the series does not appear. Absent a later filing, nothing is claimed.

Second, timing alone is not evidence. Every series in a trust shares the
registrant's fiscal year end, so "the ETF's first period equals the mutual fund's
last period" is true of every unrelated pair in the same trust and matches
thousands of them. So a candidate must show continuity as well as timing, on one
of two independent channels:

  succession  the ETF first appears in the same registrant in the very period
              that follows the mutual fund's disappearance from it
  name        the ETF's name matches the dead fund's, stripped of wrapper words,
              in any registrant -- which is the channel that can see a conversion
              that moved into a dedicated ETF trust

What the probe can establish is an upper bound: if no pair shows either shape
outside our register, then a missed conversion would have to be invisible to
N-14 and to N-CEN simultaneously, which is a much stronger claim than anything
LEGACY_GOLD supports.
"""
import difflib
import pickle
import re
import sys

import pandas as pd

from build_completion_evidence import STOP, flat
from paths import CACHE

CUTOFF = pd.Timestamp("2024-12-31")
NEAR = pd.Timedelta(days=400)
SIM = 0.85


def core(s):
    """A fund name reduced to the words that distinguish it from its neighbours."""
    return " ".join(w for w in flat(s).split() if w not in STOP)


def facts_table(t):
    s = t["SUBMISSION"]
    sub = s.assign(period_end=pd.to_datetime(
        s.REPORT_ENDING_PERIOD, format="%d-%b-%Y", errors="coerce"))
    if sub.period_end.isna().mean() > 0.5:
        sub["period_end"] = pd.to_datetime(s.REPORT_ENDING_PERIOD, errors="coerce")
    fri = t["FUND_REPORTED_INFO"].merge(
        sub[["ACCESSION_NUMBER", "CIK", "period_end"]], on="ACCESSION_NUMBER",
        how="left")
    fri = fri[fri.SERIES_ID.str.startswith("S0", na=False)].copy()
    fri["cik"] = fri.CIK.astype(str).str.lstrip("0")
    se = t["SECURITY_EXCHANGE"].drop_duplicates("FUND_ID").set_index("FUND_ID")
    fri["listed"] = fri.FUND_ID.map(se.FUND_EXCHANGE).notna()
    return fri


def main():
    with open(CACHE / "ncen_tables.pkl", "rb") as fh:
        t = pickle.load(fh)
    fri = facts_table(t)

    # the registrant's own reporting panel: a period the registrant filed for
    periods = {c: sorted(v.period_end.unique())
               for c, v in fri.groupby("cik")}
    present = set(zip(fri.cik, fri.SERIES_ID, fri.period_end))

    g = fri.groupby("SERIES_ID")
    facts = pd.DataFrame({
        "cik": g.cik.last(),
        "fund_name": g.FUND_NAME.last(),
        "first_seen": g.period_end.min(),
        "last_seen": g.period_end.max(),
        "ever_etf": g.IS_ETF.apply(lambda x: x.eq("Y").any()),
        "ever_listed": g.listed.any(),
    }).reset_index()

    # death against the registrant's own panel, never against the calendar
    def next_period(cik, p):
        ps = periods.get(cik, [])
        later = [x for x in ps if x > p]
        return later[0] if later else None

    facts["next_period"] = [next_period(c, p)
                            for c, p in zip(facts.cik, facts.last_seen)]
    facts["died"] = facts.next_period.notna()

    born = facts[facts.ever_etf & facts.ever_listed
                 & (facts.first_seen <= CUTOFF)].copy()
    died = facts[~facts.ever_etf & facts.died
                 & (facts.last_seen <= CUTOFF)].copy()

    ev = pd.read_csv(CACHE / "events_master_v2_stage3.csv")
    known = set(ev.pre_series_id) | set(ev.post_series_id)
    born = born[~born.SERIES_ID.isin(known)]
    died = died[~died.SERIES_ID.isin(known)]

    rows = []

    # ---- channel 1: succession inside one registrant -----------------------
    b_by_cik = {c: v for c, v in born.groupby("cik")}
    for d in died.itertuples(index=False):
        cand = b_by_cik.get(d.cik)
        if cand is None:
            continue
        # the ETF must first appear in the very period the fund's absence began
        hit = cand[cand.first_seen == d.next_period]
        for b in hit.itertuples(index=False):
            rows.append({"channel": "succession", "cik": d.cik,
                         "mf_series_id": d.SERIES_ID, "mf_name": d.fund_name,
                         "mf_last_ncen": d.last_seen,
                         "etf_series_id": b.SERIES_ID, "etf_name": b.fund_name,
                         "etf_first_ncen": b.first_seen,
                         "gap_days": abs((b.first_seen - d.last_seen).days),
                         "name_sim": difflib.SequenceMatcher(
                             None, core(d.fund_name), core(b.fund_name)).ratio()})

    # ---- channel 2: name continuity across any registrant ------------------
    born["core"] = born.fund_name.map(core)
    bl = [(x.SERIES_ID, x.fund_name, x.cik, x.first_seen, x.core)
          for x in born.itertuples(index=False) if x.core]
    for d in died.itertuples(index=False):
        dc = core(d.fund_name)
        if not dc:
            continue
        for sid, nm, cik, first, bc in bl:
            if abs((first - d.last_seen).days) > NEAR.days:
                continue
            r = difflib.SequenceMatcher(None, dc, bc).ratio()
            if r < SIM:
                continue
            rows.append({"channel": "name", "cik": d.cik,
                         "mf_series_id": d.SERIES_ID, "mf_name": d.fund_name,
                         "mf_last_ncen": d.last_seen,
                         "etf_series_id": sid, "etf_name": nm,
                         "etf_first_ncen": first,
                         "gap_days": abs((first - d.last_seen).days),
                         "name_sim": r})

    d = pd.DataFrame(rows)
    if len(d):
        d = (d.sort_values(["name_sim", "gap_days"], ascending=[False, True])
             .drop_duplicates(["mf_series_id", "etf_series_id"]))
    out = CACHE / "discovery_probe_candidates.csv"
    d.to_csv(out, index=False)

    print("=" * 74)
    print(f"INDEPENDENT DISCOVERY PROBE (N-CEN only, through {CUTOFF.date()})")
    print("=" * 74)
    print(f"  {int(facts.ever_etf.sum() and len(born)):>5d}   listed ETF series first "
          f"reporting by {CUTOFF.date()}, not already in the register")
    print(f"  {len(died):>5d}   non-ETF series whose registrant filed again "
          f"without them, by {CUTOFF.date()}")
    print(f"  {len(d):>5d}   candidate pairs")
    if len(d):
        print(f"  {d.etf_series_id.nunique():>5d}   distinct ETFs implicated")
        print(f"\n  by channel:")
        print(d.channel.value_counts().to_string().replace("\n", "\n    "))
        print(f"\n  strongest 20 by name continuity:")
        for r in d.head(20).itertuples(index=False):
            print(f"    {r.name_sim:.2f} {r.gap_days:>4d}d {r.channel[:10]:<10} "
                  f"{str(r.mf_name)[:32]:<32} -> {str(r.etf_name)[:32]}")
    print(f"\n  written: {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
