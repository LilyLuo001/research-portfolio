# Independent Stage-A result reproduction

Date: 2026-09-21. Disposition:
**`AGGREGATE_DIAGNOSTIC_REPRODUCED; PRIMARY_ANALYSIS_NOT_RELEASED`**.

This is an independent recomputation from the exported diagnostic JSON, not a
second read of raw DBN records. The file binds the reviewed code, manifest and
contract hashes exactly, reports 29/29 files processed, zero skipped files and
456 file-source cells. It exported no quote levels, sizes or returns.

I grouped cells by physical file, dataset, clock variant and ETF, required the
six targets `{baseline, 1, 5, 15, 30, 60}`, required the full baseline-to-target
range to lie in that file's header, and required every latest observed snapshot
to be noncrossed. At least one file-source satisfies that rule for 8 distinct
variant×ETF pairs:

```text
AAPL_FEB_WIRE       SPY
AAPL_AUG_WIRE       SPY
MSFT_APR_NOTICE_ONLY SPY
XOM_JAN_ISSUER_WIRE SPY, QQQ
XOM_JUL_ISSUER      SPY, QQQ
XOM_JUL_WIRE        SPY
```

The six unsupported pairs are both ETFs for UNH, QQQ for both Apple variants
and the Microsoft notice, and QQQ for the XOM July wire variant. The last pair
has a legacy file with six observed noncrossed snapshots but lacks full header
containment for the later wire window, so it correctly fails the decisive
criterion. Microsoft remains notice-only, not an original release anchor.

The 456 age cells independently recount as 265 unavailable, 104 at most one
second, 52 over one through 60 seconds, and 35 over 60 seconds. Of the 265
unavailable cells, 144 have no date-effective mapping and 121 have a mapping
but no observed state. All 191 observed states are noncrossed; zero are marked
ambiguous. The derived 70-row `QUOTE_SUPPORT_TABLE.csv` matches the independent
candidate-file, mapped-file, all-six-observed and all-six-in-header counts in
every row (zero discrepancies).

This establishes only observed file-source quote-state support. It does not
certify continuous live quotes, NBBO, missing-quote absence, a common ETF-plus-
basket sample, point-in-time holdings, clock validity, price responses,
covariance/calibration, or any economic effect. Primary results remain
`NOT_RUN`.

```text
6cc6059ff0c23ba4789f4fc00f8b78459ea9761fddd526621d1b6c47682e4285  data/QUOTE_SUPPORT_RESULTS.json
d7b050808328a72e04433e8d07d419e3194f9bbffb47b217b8a2d554eefb028a  QUOTE_SUPPORT_TABLE.csv
```
