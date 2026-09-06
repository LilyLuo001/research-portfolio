# prepurchase_wrds

No-purchase empirical feasibility test for the ETF–stock price-discovery
question, run against the archived WRDS mirror on SCC. Bounded to instruments
SPY, XLK, XLF over 2019–2023, with pre-2019 history read only as regression
warm-up.

Nothing here can establish subminute leadership. The daily and weekly
quantities below are feasibility and precision inputs for deciding whether a
small intraday validation batch is worth buying — not evidence about the
ordering of price discovery within a day.

**The decision and all results are in [REPORT.md](REPORT.md).** Verdict:
`HOLD_PURCHASE_FOR_NAMED_INPUT`, on two named inputs — a written product
specification confirmation covering the extended session, and a decision on
basket-weight staleness.

## Running

Stages are ordered; each reads the previous stage's checkpoints from
`$PPW_WORK/out`. Run one at a time — one concurrent research job maximum.

```sh
source config/env.sh          # module load + PPW_ARCHIVE / PPW_WORK

python3 src/s7_00_write_test.py       # filesystem write test, before any compute
python3 src/s7_01_manifest_search.py  # the single manifest search
python3 src/s7_02_round_trips.py      # 8 raw-record round trips
python3 src/s7_03_selected_event.py   # holdings extract + one worked event

python3 src/s1_01_census.py           # event registry + ETF/security crosswalk
python3 src/s1_02_clock_and_macro.py  # clock validation, sessions, USMPD registry
python3 src/s2_01_portfolio.py        # basket tracking, report age, contributions
python3 src/s3_01_delay.py            # Hou-Moskowitz D1
python3 src/s3_02_response.py         # earnings-response curves
python3 src/s4_01_macro.py            # rate response + Rigobon relevance check
python3 src/s5_01_precision.py        # planning grid + acquisition manifest
MPLCONFIGDIR=$PPW_WORK/.mplcache python3 src/s6_00_figures.py
```

`MPLCONFIGDIR` must be redirected off `$HOME`, whose quota is exhausted.

Licensed rows stay under `$PPW_WORK/out` on SCC and are never committed. The
repository holds code, configuration, figures, and aggregate results only.

## Stage 7 findings that constrain everything after

**Archive integrity.** `FINAL_VERIFY_REPORT.txt` reports 12,100/12,100 files
matched, 0 missing, 0 wrong-size, `PATH_SIZE_CHECK = PASS`, and
`FINAL_CHECKSUM_DIFF.txt` is empty. No migration or checksum work was re-run.

**Primary daily source.** `raw/crsp_dsf_YYYY.parquet`. The `rescue/…_allcols_`
copy has identical keys and byte-identical `ret` on the 2021 overlap
(2,187,548 rows both, max |difference| = 0); it is a column superset, not new
data. CIZ `…_v2_` files begin in 2024 and fall outside the analysis window, so
no legacy/CIZ stacking arises.

**Market benchmark.** `raw/crsp_dsi.parquet` carries `vwretd` and `vwretx` over
2014-01-02 – 2024-12-31, decimal units, 13.95%/yr geometric mean 2019–2023. The
CRSP value-weighted return required by the Hou–Moskowitz first stage is
therefore verified locally; the original-style baseline is available and needs
no benchmark adaptation. SPY is never regressed on itself.

**ETF identifiers, resolved by date rather than by ticker.** `SPY` maps to
three PERMNOs across CRSP history — 33910 (Speedry Chemical, to 1966), 60716
(Spectra Physics, to 1987), and 84398 (SPDR Trust, 1993-01-29 onward). Only the
dated name interval separates them. XLK = 86457 and XLF = 86455, both from
1998-12-22. All three carry `SHRCD = 73`, so a `shrcd in (10,11)` universe
filter silently drops every instrument in this study; ETFs are extracted on a
separate path.

**Fund portfolios.** `et_flag = 'F'` in the CRSP fund header gives exactly one
`crsp_portno` per instrument: SPY 1021980, XLF 1026006, XLK 1026008.

**Holdings semantics.** The snapshot unit is
`(crsp_portno, report_dt, eff_dt)`, not `report_dt` alone — 21% of report dates
carry more than one `eff_dt`. `eff_dt` is later than `report_dt` on 100% of
46,068 extracted rows (median lag 19 days, range 5–54), so the two dates carry
genuinely different information and both labels are preserved: `report_dt` is
the economic as-of date, `eff_dt` a date-level availability proxy. Only
`eff_dt` before an event supports a knowable-before-the-event claim, and it is
read at date level, never as an intraday timestamp. The unique row key is
`(portno, report_dt, eff_dt, security_name, cusip)`; `security_rank` is not
unique and `permno` is not either (626 duplicate rows), so weights are
aggregated to PERMNO rather than assumed one-to-one. Snapshots are monthly
(71 report dates per instrument, median gap 31 days). `percent_tna` sums to a
median of 100 per snapshot, confirming `weight = percent_tna / 100`.

**Holdings coverage.** PERMNO-mapped share is 98.8% (SPY), 95.8% (XLF), 96.2%
(XLK). The pooled 33% figure seen across all ETF batches reflects bond and
money-market funds and does not describe these three. Unmapped rows are cash,
government money-market lines, and a residue of ordinary shares; none are
treated as cash or as zero-return assets, and the covered sleeve is reported
with its coverage rather than renormalised to 100%.

**Earnings records.** `ibes_actuals_eps_YYYY` supplies `measure`, `pdicity`,
`pends`, `curr_act`, and versioned duplicates that require explicit selection.
`ibes_statsum_eps_YYYY` carries the estimate and the matching actual on one row
under a shared `estflag` and `curcode`, which is the only construction that
guarantees expectation and actual share a split and adjustment basis.

**The clock is not resolved.** `anntims` is 100% populated, but the archive
manual records that its timezone was never verified. Under a naive read only
5.4% of stamps fall inside 09:00–15:59. This is not a session classification
and is not used as one. The single worked event shows why it matters: Microsoft
was 20.43% of XLK at the 2021-06-30 snapshot and announced on 2021-07-27 at a
stamp of 16:02, and the accounting contribution is −17.7 bps under a same-day
mapping against −2.3 bps under a next-day mapping. Both are reported; neither
is selected.

**Link quality.** The recovered CRSP–I/B/E/S link has the documented 37,662
rows and no inverted intervals. 702 of 25,074 I/B/E/S tickers map to more than
one PERMNO across history, so ticker-only matching is not used; applying the
`sdate`/`edate` interval on a test date left 5,093 live links and zero
remaining ambiguity.
