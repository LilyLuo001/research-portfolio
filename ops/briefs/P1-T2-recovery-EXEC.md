# EXEC BRIEF — P1-T2 ConvExp denominator recovery (box, online) [optional pre-final pass]

_Paste below the line into a Claude Code seat on the BU SCC (has internet). This is the
online half of the coverage audit in `p1/output/convexp_coverage_audit/`. It is NOT a
gate blocker — the kill-switch can be read now — but it lifts free coverage ~51.8% → ≤67%,
fixes the 18 stale cells, and lets us PROVE the ≥0.5% treated set is unchanged._

---

You are seat P1 running the **P1-T2 ConvExp denominator-recovery** pass. Read `CLAUDE.md`,
`p1/output/convexp_coverage_audit/README.md`, and `coverage_audit_memo.md`. Meta-rule 1
holds: every recovered denominator carries a source + retrieval date + confidence and is
re-flagged if it yields a suspicious ConvExp. Never overwrite baseline ConvExp.

## Step 1 — emit the shares_held sidecar (1-line pipeline patch, required for treated counts)
The current pipeline discards `shares_held` on dropped cells, so post-recovery ConvExp
can't be recomputed. Patch `p1/t2_free/build_nport_convexp.py`: at the point a cell is
sent to NEED_HUMAN_stocks, also write `cusip,wave_id,shares_held` to
`p1/t2_free/dropped_cells_shares_held.csv`. (You already have `shares_held` in scope at the
aggregation step — it's `d["shares"]` per `(cusip, wave_id)`.) Re-run the build, or just
re-emit the sidecar from the cached holdings — do NOT alter the existing parquet.

## Step 2 — run the online recovery
```
git pull
export SEC_UA="Boston University research <your-email>"
python p1/output/convexp_coverage_audit/recover_denominators.py --online \
       --shares-held p1/t2_free/dropped_cells_shares_held.csv
```
Priority order per target (already coded): SEC `company_tickers.json` renamed-ticker →
current-CIK XBRL; then yfinance `sharesOutstanding`; Stooq is price-only (no denom).
It caches every raw pull under `p1/output/convexp_coverage_audit/recovery_cache/` and
overwrites `coverage_recovery_attempts.csv`, `coverage_before_after.csv`,
`coverage_post_recovery_*` with real recovered numbers.

## Step 3 — priority fixes (small, high-value)
1. **The 18 `conv_exp>1` stale cells** (`suspicious_recovered_cells.csv`): AMRX, FOX, FOXA,
   TRIP, RFL, CIA — real US common with dummy shares_out (1/100/1000). The online pass
   refetches a fresh point-in-time denominator; verify each recomputed ConvExp is < 1 and
   sane before any inclusion.
2. **~1,828 `tier1_us_renamed`**: delisted/renamed/acquired US names (ABC→Cencora,
   AAXN→AXON, …). yfinance keeps delisted history — expect a high hit rate.
3. **Foreign/CINS (~3,698, `tier3_foreign`)**: recover only to DOCUMENT them; keep the
   `foreign_or_adr_outside_US_universe` flag — they stay OUT of the US-listed event study.

## Step 4 — the one question that matters
After recompute, report **treated stocks ≥0.5% and ≥1% pooled + DFA anchor, before vs after
recovery**. Expectation (state whether it holds): recovery adds to the ≥0.25% tail but the
≥0.5% treated set is ~unchanged. If any recovered cell lands ≥0.5%, list it for review
(could be a bad denominator).

## Validate + land
```
python ops/runner/contracts.py conv_exposure_free p1/conv_exposure_free.parquet   # still PASS
git add p1/output/convexp_coverage_audit/ p1/t2_free/dropped_cells_shares_held.csv
git commit -m "P1-T2 ConvExp denominator recovery (online): stale fixes + renamed-US map" && git push
```

## Report back
Baseline vs post-recovery cell coverage, US-only coverage, treated ≥0.5%/≥1% before/after,
recovered-cell count by tier, and the residual foreign/CINS count. These finalize the
P1-T2 dataset for the returns phase. Do NOT proceed to T4/T5 until the owner signs the
kill-switch. Stop after pushing.
