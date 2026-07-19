# P1-T2 (free path) — box execution brief

You are seat **P1** executing **P1-T2 free path**. WRDS is gone; ConvExp is
rebuilt from EDGAR N-PORT + OpenFIGI + XBRL. Read `CLAUDE.md`, `p1/CLAUDE.md`,
`docs/Project_1.md` §T2, `ops/briefs/WRDS-access-assessment.md`, and
`ops/contracts/conv_exposure_free.yaml`. Meta-rule 1 holds and is satisfied by
design — every number carries an EDGAR/OpenFIGI locator; unmapped funds/stocks
go to `p1/t2_free/NEED_HUMAN_*.csv`, never imputed.

## Pre-flight
Default `python3` on the box is 3.6 without pandas — **use the seat venv**
(`.venv/bin/python`, 3.10.5). `pyarrow` was already pip-installed there.
```
git pull
export SEC_UA="Boston University research <your-email>"   # SEC REQUIRES a real UA
export OPENFIGI_KEY=<free key from openfigi.com/api>       # optional, raises limits
.venv/bin/python -c "import requests,pandas,pyarrow; print('deps ok')"
```
Confirm outbound HTTPS to data.sec.gov / www.sec.gov / api.openfigi.com /
stooq.com. (All four verified reachable from the login node.)

## Run
```
.venv/bin/python p1/t2_wrds/build_waves.py          # stdlib only, 3.6 ok too
.venv/bin/python p1/t2_free/build_nport_convexp.py  # needs the venv
```
Smoke-tested on one fund end-to-end (Guinness Atkinson Asia Pacific →
NPORT-P series match 1.00 → 37 holdings → AFL→CIK 4977→688.6M shares). Expect
~131 funds × several SEC calls each on the first run; the cache makes reruns
instant.
Everything is cached under `p1/t2_free/cache/` (immutable) — reruns are free and
hit zero network. Delete a cache file to force a refetch.

## Then feed the diagnostics back
The pipeline runs the happy path out of the box and writes a full trail to
`p1/t2_free/build_nport_convexp.log` + `p1/t2_free/diagnostics.md`. Two matching
problems are implemented **best-effort** and need a live-EDGAR eyeball — grep the
log and report:

1. **G1 fund→series match** (multi-series trusts): `grep SERIES_MATCH …log`.
   Report funds with `NO_series_match_used_newest` or low scores, plus the
   `NEED_HUMAN_funds.csv` rows. I'll tune the matcher / add series-ID resolution.
2. **H2 mcap_decile price join**: `grep -c MCAP_MISS …log` and how many rows have
   `mcap_decile` filled (see diagnostics.md). Report missing tickers.
3. **shares-out sanity**: `grep XBRL_MULTICLASS` and `grep CONVEXP_GT1` (the
   latter are dropped as likely stale shares-outstanding — report the tickers).

## Validate
```
python ops/runner/contracts.py conv_exposure_free p1/conv_exposure_free.parquet   # expect PASS
python ops/runner/lineage.py p1/conv_exposure_free.parquet \
       p1/events_merged.csv p1/t2_wrds/waves.csv
```

## Report back (these numbers feed P1-T2-killswitch, Gate 2)
- rows, distinct stocks;
- #cells ConvExp ≥ 0.5% and ≥ 1% (overall + by wave, from diagnostics.md);
- DFA anchor-wave (2021-06-11) share of cells;
- NEED_HUMAN fund count and dropped-stock count with reasons.

Do **not** proceed to T4/T5 until you sign the kill-switch. When you've run it,
paste the log tail + diagnostics.md back and I'll resolve the matching problems,
then we land the parquet + lineage with:
```
git add p1/conv_exposure_free.parquet p1/conv_exposure_free.parquet.lineage.json \
        p1/t2_free/ p1/t2_wrds/ ops/contracts/conv_exposure_free.yaml \
        ops/briefs/P1-T2-free-EXEC.md ops/briefs/WRDS-access-assessment.md
git commit -m "P1-T2 free ConvExp (EDGAR N-PORT + OpenFIGI + XBRL)" && git push
```
(The `cache/` dir and the parquet are large — confirm `.gitignore` covers
`p1/t2_free/cache/` before committing.)
