# ConvExp coverage audit — methods, caveats, file index

Read-side audit of the P1-T2 free-path ConvExp build
(`p1/t2_free/build_nport_convexp.py`, run on the BU SCC box). It recomputes
coverage/missingness from the **committed** pipeline outputs, scopes a conservative
denominator-recovery pass, and reports whether the dataset is ready for the P1-T2
kill-switch gate. **No number here is from memory or an LLM** — every figure is
derived from a pushed file (meta-rule 1).

## How to reproduce
```
python p1/output/convexp_coverage_audit/build_coverage_audit.py       # baseline (offline)
python p1/output/convexp_coverage_audit/recover_denominators.py       # recovery scope (offline)
# on the BOX (outbound HTTPS), to actually recover denominators:
export SEC_UA="Boston University research <email>"
python p1/t2_wrds/build_waves.py                 # regenerate waves + members
python p1/t2_free/build_nport_convexp.py         # now emits the shares_held sidecar
python p1/output/convexp_coverage_audit/recover_denominators.py --online \
       --shares-held p1/t2_free/dropped_cells_shares_held.csv
```
The two pipeline steps are new to this sequence: the sidecar only exists from a build
made after 2026-08-18. Step-by-step operator instructions, including what to check
before pushing, are in `ops/briefs/P1-T2-recovery-BOX.md`.
Both scripts are idempotent, logged, and take `--repo/--outdir`. They read only:
`p1/conv_exposure_free.parquet`, `p1/t2_free/NEED_HUMAN_stocks.csv`,
`p1/t2_free/NEED_HUMAN_funds.csv`, `p1/events_merged.csv`,
`p1/t2_wrds/waves_members.csv`, `p1/t2_free/build_nport_convexp.log`,
`ops/briefs/gate2_human_review_manifest.json`.

## Definitions
- **cell** = one `(stock_cusip × wave_id)` pair the pipeline tried to build a ConvExp
  for. **attempted = computed + dropped.** `ConvExp = Σ_funds shares_held / shares_outstanding`.
- **computed cell** = has a denominator → in `conv_exposure_free.parquet` (6,377).
- **dropped cell** = no denominator → in `NEED_HUMAN_stocks.csv` (5,929).
- **treated stock** = distinct stock with ConvExp ≥ threshold (0.25% / 0.5% / 1%).
- **DFA anchor** = wave W002, effective 2021-06-11 (the pre-registered anchor event).

## Three caveats a reviewer must know
1. **Value-weighting is not available FROM THE COMMITTED ARTIFACTS — fixed in the
   pipeline, lands with the next box build.** The build behind every number in this
   directory retained only `cusip/ticker/wave` on a dropped cell, so value-weighted
   *missingness* cannot be reconstructed from what is pushed today; everything here is
   exact **cell-count** coverage, and `shares_held` exists only for the 6,377 computed
   cells (+ the 18 stale cells, recovered from the log). As of 2026-08-18
   `build_nport_convexp.py` retains `shares_held`, `valusd` and `n_funds` on every drop
   (sidecar `p1/t2_free/dropped_cells_shares_held.csv`) and carries `valusd` on the
   computed rows, so the next box run makes both value-weighted coverage and
   post-recovery ConvExp computable. **Re-run this audit after that build** — until
   then, read the coverage numbers here as cell counts only.
2. **`p1/t2_wrds/waves.csv` WAS committed corrupt** (two concatenated schemas in one
   file, unparseable); the tables here derive wave attributes from the clean
   `waves_members.csv`. Root cause found 2026-08-18: `build_waves.py` itself held two
   concatenated modules, and the second — 7-col schema, and it never wrote
   `waves_members.csv` at all — shadowed the canonical one. Dead module removed; the
   repaired script reproduces the committed `waves.csv` byte-for-byte and is guarded by
   `p1/tests/test_t2_free_dropped_cells.py`.
1. **Value-weighting is NOT available *for this audit vintage*.** The pipeline
   aggregated `shares_held` across funds within a wave and, for *dropped* cells,
   retained only `cusip/ticker/wave` — no `shares_held` or `valUSD` — so value-weighted
   *missingness* cannot be reconstructed from the artifacts this audit read. The numbers
   in this directory are therefore exact **cell-count** coverage, and `shares_held`
   exists only for the 6,377 computed cells (+ the 18 stale cells, recovered from the
   log). **FIXED IN THE PIPELINE 2026-08-18 (not yet re-run):** `build_nport_convexp.py`
   now emits `val_usd` on every computed row and writes
   `p1/t2_free/dropped_cells_shares_held.csv` (cusip, wave_id, shares_held, val_usd, …)
   for every dropped cell. Value-weighted coverage becomes computable — and this caveat
   retires — on the next box run; nothing here can be recomputed before that.
2. **`p1/t2_wrds/waves.csv` was committed CORRUPT — root cause found and fixed
   2026-08-18.** The file held two concatenated schemas (a 4-col header and a 7-col
   header) because `build_waves.py` itself held two complete programs, and the *second*
   `def main()` — a 7-column scaffold that never wrote `waves_members.csv` and skipped
   the sanity asserts — shadowed the real one. So the audit's hand-regenerated CSV would
   indeed have been re-corrupted on the next run, as this caveat suspected. The dead
   scaffold is removed, `waves.csv` is now regenerated BY THE PIPELINE (78 waves, 131
   members; content identical to the hand-regenerated file, line terminator now matching
   `waves_members.csv`), and `p1/tests/test_build_waves.py` pins both the single-`main()`
   invariant and the four-column schema. This audit's derivation of wave attributes from
   `waves_members.csv` remains valid either way.
3. **Post-recovery numbers are offline ceilings.** This sandbox is network-restricted
   (SEC/Yahoo/Stooq are policy-blocked); real denominator recovery must run `--online`
   on the box. Offline we scope the target list and an upper-bound coverage ceiling;
   `coverage_post_recovery_*` files are baseline mirrors (recovered=0) until the box runs.

## File index
| file | what |
|---|---|
| `coverage_baseline_summary.csv` | headline cell counts, coverage/drop rate, ConvExp stats |
| `coverage_baseline_fund_level.csv` | 131 funds → 100 equity / 31 excluded / zero-cell funds |
| `coverage_baseline_by_drop_reason.csv` | 4 drop reasons × count × % attempted × % dropped |
| `coverage_baseline_by_wave.csv` | per-wave computed/dropped/coverage (+year, anchor, labels) |
| `coverage_baseline_by_year.csv` | coverage by conversion year |
| `coverage_baseline_by_family.csv` | coverage by fund family (single-family waves; else MIXED) |
| `coverage_baseline_by_asset_class.csv` | coverage by asset class (equity_US / equity_intl / …) |
| `coverage_baseline_dfa_vs_nondfa.csv` | DFA anchor W002 vs the rest |
| `coverage_baseline_top_funds.csv` | top 20 cell-bearing waves (the cell-attribution unit) |
| `coverage_baseline_severity.csv` | dropped cells by severity (foreign / US-recoverable / …) |
| `coverage_baseline_severity_by_reason.csv` | severity × drop-reason cross-tab |
| `treated_stock_counts_by_threshold.csv` | treated stocks ≥0.25/0.5/1% (pooled / anchor / non-anchor) |
| `coverage_manifest_crosscheck.csv` | recomputed vs box manifest (all OK) |
| `coverage_recovery_attempts.csv` | every dropped cell + recovery tier + safeguards columns |
| `coverage_post_recovery_summary.csv` | recovery ceiling by tier |
| `coverage_post_recovery_by_drop_reason.csv` | recovery tiers (post-recovery drop view) |
| `coverage_post_recovery_by_{family,year,wave}.csv` | subgroup (offline=baseline; box overwrites) |
| `coverage_before_after.csv` | staged coverage: SEC baseline → +map → +yfinance → +stooq → final |
| `remaining_dropped_cells.csv` | all 5,929 dropped cells w/ bucket + severity |
| `suspicious_recovered_cells.csv` | the 18 ConvExp>1 stale-denominator cells (real shares from log) |
| `coverage_audit_memo.md` | the narrative answer to the gate questions |

## Recovery safeguards (recover_denominators.py)
Never accepts a recovered denominator blindly. For each it stores source, retrieval
date, original ticker/CUSIP, resolved ticker, shares-out, as-of date, confidence, and
re-flags: `conv_exp_gt_1_reject`, `conv_exp_ge_0.25pct_verify`, `small_denominator_review`,
`foreign_or_adr_outside_US_universe`. Baseline ConvExp is never overwritten; recovery
lands in new columns (`*_recovered`, `recovery_status`, `recovery_flag`).
