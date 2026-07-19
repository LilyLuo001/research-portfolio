# EXEC BRIEF — P1-T2 FREE ConvExp (EDGAR N-PORT, no WRDS) [box]

_Paste below the line into a Claude Code seat on the BU SCC (has internet). This
replaces the WRDS holdings pipeline with 100%-free public sources — BU WRDS is no
longer active. It builds ConvExp for the kill-switch gate with zero paid data._

---

You are seat P1 executing **P1-T2 (free path)**. Read `CLAUDE.md`, `p1/CLAUDE.md`,
`docs/Project_1.md` §T2, `ops/briefs/WRDS-access-assessment.md`, and
`ops/contracts/conv_exposure_free.yaml`. Meta-rule 1 holds and is *satisfied by
design here*: every number carries an EDGAR/OpenFIGI locator — nothing hand-filled;
unmapped funds/stocks go to NEED_HUMAN files, never imputed.

Sources (all free): fund holdings = SEC EDGAR **NPORT-P**; CUSIP→ticker = N-PORT
identifiers + **OpenFIGI**; ticker→stock CIK = SEC `company_tickers.json`; shares
outstanding = SEC XBRL `dei:EntityCommonStockSharesOutstanding`.
`ConvExp = Σ_f (fund holding shares) / shares_outstanding`.

## Pre-flight
```
git pull
export SEC_UA="Boston University research <your-email>"   # SEC REQUIRES a real UA
# optional but recommended (raises OpenFIGI limit 10->100/req, ~25->250/min):
export OPENFIGI_KEY=<free key from openfigi.com/api>
python -c "import requests,pandas,pyarrow; print('deps ok')"   # pip install if missing
```
Confirm outbound HTTPS to `sec.gov` / `data.sec.gov` / `api.openfigi.com` works
(the box reached EDGAR fine for the earlier harvest).

## Run
```
python p1/t2_wrds/build_waves.py            # refresh waves.csv if events changed
python p1/t2_free/build_nport_convexp.py
```
It caches every raw pull under `p1/t2_free/cache/` (re-runs are free/auditable)
and writes:
- `p1/conv_exposure_free.parquet` (contract: conv_exposure_free)
- `p1/t2_free/cusip_ticker_cik_crosswalk.csv` (lets a later CRSP merge recover permno)
- `p1/t2_free/convexp_free_diagnostics.md` (kill-switch gate-2 numbers)
- `p1/t2_free/unresolved_funds.csv`, `unresolved_stocks.csv` (NEED_HUMAN)

## Fix the expected gaps (do not skip — this is the real work)
1. **Fund→series matching**: funds without a `mutual_fund_ticker` fall back to the
   trust CIK with an empty `series_id`, so `nport_holdings` reads the *trust's*
   latest NPORT-P without filtering to the converting series. For multi-series
   trusts this is wrong. Add series resolution: match the fund by name to the
   trust's series list (SEC series/class data, or the `<seriesId>`/`<seriesName>`
   in each NPORT-P header) and filter holdings to that series' filing. Re-run.
2. **`mcap_decile` is left blank** (needs a price). Add a free price join
   (`yfinance`/Stooq by ticker as of the pre-conversion date) → mcap = shares_out ×
   price → decile 1–10 within each wave's cross-section. Fill the column.
3. **`pre_etf_ownership`** stays blank at T2 (contract allows it); note it for the
   returns phase.
4. Anything in the two NEED_HUMAN files: resolve fund identity / stock CIK by hand
   where cheap; leave genuinely unmappable ones listed (never guess).

## Validate + land
```
python ops/runner/contracts.py conv_exposure_free p1/conv_exposure_free.parquet   # PASS
python ops/runner/lineage.py p1/conv_exposure_free.parquet p1/events_merged.csv p1/t2_wrds/waves.csv
git add p1/conv_exposure_free.parquet p1/t2_free/ p1/t2_wrds/waves.csv
git commit -m "P1-T2 free ConvExp (EDGAR N-PORT + OpenFIGI + XBRL)" && git push
```

## Report back
Rows, distinct stocks, #stocks ConvExp≥0.5% and ≥1%, the DFA anchor-wave share,
and the unresolved-fund / dropped-stock counts. Those feed **P1-T2-killswitch**
(human gate 2 — the owner reads the treated-stock counts and decides go/no-go).
Do NOT proceed to T4/T5 until the owner signs the kill-switch. Stop after pushing.
