"""Refetch the DERA N-CEN structured data sets and flatten the four tables used.

N-CEN is the registrant's own annual census of its funds. Four tables carry the
whole of what this pipeline asks of it:

  SUBMISSION              which registrant filed, for which period
  FUND_REPORTED_INFO      one row per series per period: is it an ETF, what is
                          it called, is it present at all
  SECURITY_EXCHANGE       the listing venue, which is what distinguishes a real
                          ETF from a fund with "ETF" in its name
  TERMINATED_ORGANIZATION the registrant's own statement that a series ended,
                          dated to a month
  ADVISER                 needed for sponsor concentration, which the successor
                          registrant CIK only approximates

The quarterly zips are immutable once published, so a present zip is never
refetched. Only the flattening is redone, and it is deterministic given the zips.
"""
import io
import pickle
import sys
import zipfile

import pandas as pd

import fetchlib
from paths import CACHE, NCEN

BASE = "https://www.sec.gov/files/dera/data/form-n-cen-data-sets"
TABLES = ["SUBMISSION", "FUND_REPORTED_INFO", "SECURITY_EXCHANGE",
          "TERMINATED_ORGANIZATION", "ADVISER"]
# N-CEN's first filings land in 2019; the register runs to the 2026-08-29 cutoff
QUARTERS = [f"{y}q{q}" for y in range(2019, 2027) for q in (1, 2, 3, 4)]


def main():
    have, missing = [], []
    for qtr in QUARTERS:
        dest = NCEN / f"{qtr}_ncen.zip"
        p = fetchlib.get(f"{BASE}/{qtr}_ncen.zip", dest, kind="ncen_bulk")
        (have if p else missing).append(qtr)
        print(f"  {qtr} {'ok' if p else 'absent'}", flush=True)

    frames = {t: [] for t in TABLES}
    for qtr in have:
        with zipfile.ZipFile(NCEN / f"{qtr}_ncen.zip") as z:
            names = {n.split("/")[-1].upper(): n for n in z.namelist()}
            for t in TABLES:
                n = names.get(f"{t}.TSV")
                if not n:
                    continue
                with z.open(n) as fh:
                    df = pd.read_csv(io.BytesIO(fh.read()), sep="\t",
                                     dtype=str, low_memory=False)
                df["_quarter"] = qtr
                frames[t].append(df)

    tables = {t: pd.concat(v, ignore_index=True) for t, v in frames.items() if v}
    out = CACHE / "ncen_tables.pkl"
    with open(out, "wb") as fh:
        pickle.dump(tables, fh, protocol=4)
    fetchlib.record(out, kind="derived", parser="fetch_ncen_bulk.py",
                    extra={"lineage": sorted(have)})

    print(f"\nquarters fetched: {len(have)}  absent: {len(missing)}")
    for t in TABLES:
        print(f"  {t:<24}{len(tables.get(t, [])):>9,d} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
