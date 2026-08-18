# P1-T2 — denominator recovery on the BOX (paste-and-run)

**Who runs this:** whoever has the box (outbound HTTPS to SEC / Yahoo / Stooq).
This sandbox is network-restricted — `curl https://www.sec.gov/...` returns 000 —
so the recovery pass cannot run here, only the code that makes it possible.

**Why it matters.** The free-path ConvExp drops 48.2% of cells (5,929 of 12,306).
Every one of those is a missing *denominator*, never a missing holding. The
coverage audit argues the drops are ~63% structurally non-US and therefore cannot
change the ≥0.5% treated set — and calls that "a strong expectation, not yet a
proof". This run turns it into a proof or refutes it. Until then the ConvExp
dataset is **feasibility-grade**: fine for T3/T4, not for the final estimation run.

## What changed 2026-08-18 (why the old command wouldn't have worked)
`recover_denominators.py --online` needs `shares_held` per dropped cell to
recompute ConvExp on a recovered denominator, and the pipeline was throwing it
away at drop time — without the sidecar every recovered row lands as
`PENDING_SHARES` and proves nothing. The pipeline now retains it. Also repaired:
`build_waves.py` was merge-corrupted into two modules and the wrong one was
winning, which would have rewritten `waves.csv` with a 7-column schema and left
`waves_members.csv` — the file the ConvExp pipeline actually reads — stale.

## Run

```bash
cd <repo>
git pull origin main
export SEC_UA="Boston University research <your-email>"   # SEC 403s without a real UA
export OPENFIGI_KEY=...                                   # optional, widens CUSIP->ticker

# 1. waves (cheap, no network). Must leave waves.csv byte-identical.
python p1/t2_wrds/build_waves.py
git diff --stat p1/t2_wrds/waves.csv        # expect: no change

# 2. rebuild ConvExp. Slow (EDGAR-rate-limited) but the cache under
#    p1/t2_free/cache/ makes reruns nearly free. Emits the new sidecar.
python p1/t2_free/build_nport_convexp.py
python ops/runner/contracts.py conv_exposure_free p1/conv_exposure_free.parquet

# 3. the actual recovery: SEC-renamed -> yfinance -> Stooq
python p1/output/convexp_coverage_audit/recover_denominators.py --online \
       --shares-held p1/t2_free/dropped_cells_shares_held.csv

# 4. re-run the audit so every table reflects the new build
python p1/output/convexp_coverage_audit/build_coverage_audit.py

# 5. tests + gate
python -m pytest -q
python ops/runner/selfcheck.py
```

## Check before pushing
- **Step 2 must produce `p1/t2_free/dropped_cells_shares_held.csv`** with roughly
  as many rows as `NEED_HUMAN_stocks.csv` (~5,929) and `shares_held > 0` on
  nearly all of them. If the file is missing or the column is empty, you are
  running a pre-2026-08-18 build — stop and re-pull.
- **`valusd` is now a column on the parquet.** Add
  `valusd: {min: 0}` to `ops/contracts/conv_exposure_free.yaml` in the same
  commit — it is deliberately undeclared today because the validator treats every
  declared column as must-exist and the committed parquet predates the change.
- **Compare treated counts, do not overwrite them.** The audit's claim is that
  `treated_stock_counts_by_threshold.csv` barely moves at ≥0.5% (389 pooled /
  361 DFA anchor). Report the before/after honestly whichever way it lands —
  meta-rule: report the first run, never specification-search.
- `recover_denominators.py` quarantines every recovered denominator with source +
  retrieval date + confidence and never overwrites baseline ConvExp. Check
  `suspicious_recovered_cells.csv` before believing any large ConvExp jump.

## Then
Update `p1/output/convexp_coverage_audit/coverage_audit_memo.md` (its numbers all
describe the pre-patch build) and note the outcome in `ops/decisions.md`. If the
≥0.5% treated set holds, the ConvExp dataset graduates from feasibility-grade and
P1-T5 can run on it.

## If recovery does NOT hold the treated set
That is a real finding, not a failure — it would mean the international sleeve is
doing more work than the audit expects. Say so, and escalate the sample-definition
question (memo item 5: document equity_intl as out of a US-listed event study, or
scope a separate non-US analysis). Do not tune the recovery to get the answer.
