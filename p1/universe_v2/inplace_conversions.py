"""Find conversions the N-14 spine cannot see, by watching series rename themselves.

The discovery spine is the N-14 MERGER block, which only exists when the
conversion is structured as a reorganization of one series into another. A fund
can also convert *in place*: the same SERIES_ID stops calling itself a Fund and
starts calling itself an ETF, with no target->acquirer pair to find. Nothing in
the N-14 channel would ever surface that, so it is the natural home of a
discovery miss and has to be measured rather than assumed away.

The test is deliberately name-based rather than IS_ETF-based. The IS_ETF flag
flips for reporting corrections on funds that were already ETFs, which is noise;
a registrant renaming a series from "Fund" to "ETF" is making a claim about what
the series now is.
"""
import re
import sys

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
# a fund that *is* an ETF ends its name with one; one that merely holds ETFs
# carries the word mid-name and ends with Fund
TAIL = re.compile(r"(?:\bETFs?|exchange[-\s]traded\s+fund)\s*$", re.I)


def main():
    fri = pd.read_pickle(HERE / "fri_flat.pkl").sort_values("period_end")
    rows = []
    for sid, g in fri.groupby("SERIES_ID"):
        nm = g.FUND_NAME.astype(str).str.strip()
        is_etf = nm.apply(lambda s: bool(TAIL.search(s))).values
        if not (is_etf.any() and (~is_etf).any()):
            continue
        first_etf = g[is_etf].iloc[0]
        last_mf = g[~is_etf].iloc[-1]
        # only a forward transition counts; the reverse is a renaming artefact
        if last_mf.period_end >= first_etf.period_end:
            continue
        # a fund already reporting IS_ETF=Y under its old name was always an ETF
        # and merely put the word into its title ("ALPS Sector Dividend Dogs" ->
        # "ALPS Sector Dividend Dogs ETF"). That is a rename, not a conversion.
        if str(last_mf.IS_ETF).upper().startswith("Y"):
            continue
        rows.append({
            "series_id": sid, "cik": int(str(last_mf.CIK).lstrip("0")),
            "mf_name": last_mf.FUND_NAME, "mf_last_period": last_mf.period_end,
            "etf_name": first_etf.FUND_NAME, "etf_first_period": first_etf.period_end,
        })

    d = pd.DataFrame(rows)
    print(f"series renamed from non-ETF to ETF in place: {len(d):,d}")
    if d.empty:
        return 0

    ev = pd.read_csv(HERE / "events_master_v2_stage3.csv")
    known = set(ev.pre_series_id.dropna()) | set(ev.post_series_id.dropna())
    d["in_n14_universe"] = d.series_id.isin(known)
    d.to_csv(HERE / "inplace_conversions.csv", index=False)

    n_new = int((~d.in_n14_universe).sum())
    print(f"  already in the N-14 universe : {int(d.in_n14_universe.sum()):,d}")
    print(f"  NOT in the N-14 universe     : {n_new:,d}")
    if n_new:
        new = d[~d.in_n14_universe].copy()
        # the rename is bracketed between the last MF period and the first ETF one
        new["year_if_unambiguous"] = [
            a.year if a.year == b.year else None
            for a, b in zip(new.mf_last_period, new.etf_first_period)]
        print("\ncandidate discovery misses:")
        print(new[["series_id", "mf_name", "mf_last_period", "etf_name",
                   "etf_first_period"]].to_string(index=False))
        print("\nby first-ETF-period year:")
        print(new.etf_first_period.dt.year.value_counts().sort_index().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
