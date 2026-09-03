"""Project the audited v2 universe into the legacy events_merged schema.

The legacy file is a hand-curated candidate list. This writes its replacement in
the same 13 columns so that anything reading it does not need to change, but the
replacement is derived: every row is a completed pair from
events_master_v2_stage3.csv, and rerunning this script on the same stage3 file
reproduces the output byte for byte.

Columns the legacy file carried by hand and that no v2 channel can supply --
family, etf_ticker, asset_class, AUM_at_conversion_USD, source_url -- are written
as NA rather than guessed. Two of those are recoverable and one is not:

  family      N-CEN ADVISER, whose bulk cache was lost to the /tmp purge
  source_url  needs the filer CIK for the source accession, which lived in
              submissions_flat.parquet, also purged
  asset_class no SEC channel supplies it; it was analyst judgement in the legacy
              file and must stay that way

Writes events_derived_v2.csv here. It does not touch events_merged.csv; promoting
it into the research repo is a separate decision.
"""
import sys

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
COLS = ["fund_name", "family", "mutual_fund_ticker", "etf_ticker", "announce_date",
        "effective_date", "asset_class", "AUM_at_conversion_USD", "source_accession",
        "source_url", "confidence", "effective_date_approx", "date_precision"]
DAY = ["verified_exact_day", "proposed_exact_day_only"]
# how much of a date claim each precision really is, in the legacy H/M/L vocabulary
CONF = {"verified_exact_day": "H", "proposed_exact_day_only": "M", "month_only": "M",
        "year_only": "L", "bounded_window": "L"}


def main():
    ev = pd.read_csv(HERE / "events_master_v2_stage3.csv")
    d = ev[ev.final_tier.str.startswith(("A_", "B_"), na=False)].copy()
    day = d.final_precision.isin(DAY)

    out = pd.DataFrame({
        "fund_name": d.pre_series_name,
        "family": "NA",
        "mutual_fund_ticker": d.pre_tickers.fillna("NA").replace("", "NA"),
        "etf_ticker": "NA",
        "announce_date": pd.to_datetime(d.n14_first_filed, errors="coerce")
                           .dt.strftime("%Y-%m-%d").fillna("NA"),
        # only a day-level claim may occupy the exact-date column; anything weaker
        # goes to effective_date_approx, which is what that column is for
        "effective_date": d.final_effective_date.where(day).fillna("NA"),
        "asset_class": "NA",
        "AUM_at_conversion_USD": "NA",
        "source_accession": d.final_source_accession.fillna("NA"),
        "source_url": "NA",
        "confidence": d.final_precision.map(CONF).fillna("L"),
        "effective_date_approx": d.final_effective_date.where(~day).fillna("NA"),
        "date_precision": d.final_precision,
    })[COLS]
    out = out.sort_values(["fund_name", "source_accession"], kind="mergesort") \
             .reset_index(drop=True)
    out.to_csv(HERE / "events_derived_v2.csv", index=False)

    assert len(out) == len(d)
    assert (out.effective_date == "NA").sum() == int((~day).sum())
    assert not ((out.effective_date != "NA") & (out.effective_date_approx != "NA")).any()

    print(f"events_derived_v2.csv : {len(out)} completed pairs "
          f"(legacy events_merged.csv: 131, untouched)")
    print(f"  exact effective date : {int((out.effective_date != 'NA').sum())}")
    print(f"  approximate only     : {int((out.effective_date_approx != 'NA').sum())}")
    print("\nconfidence:")
    print(out.confidence.value_counts().to_string())
    print("\ncolumns written NA for want of a channel: "
          "family, etf_ticker, asset_class, AUM_at_conversion_USD, source_url")
    return 0


if __name__ == "__main__":
    sys.exit(main())
