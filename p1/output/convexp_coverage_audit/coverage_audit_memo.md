# P1-T2 ConvExp coverage audit — memo (seat C, 2026-07-19)

Audit of the box's free-path ConvExp build against the **committed** artifacts
(parquet + NEED_HUMAN files + log + manifest). Every number below is recomputed from
those files and **cross-checks exactly against the box manifest** (see
`coverage_manifest_crosscheck.csv`: funds, rows, dropped cells, ≥0.5%, ≥1% all OK).

## Headline
The "48% of cells dropped" is real but **almost entirely one thing: international-equity
conversions, dominated by a single fund.** The US-equity universe the study and the DFA
anchor depend on is well covered, the treated-stock set is intact and far above the
kill-switch floor, and the recoverable-for-free gap is modest. **Ready for the kill-switch
gate as a feasibility read; a short free recovery pass is worth doing before the final run.**

## Fund-level coverage
| | n |
|---|---|
| Total conversion funds | **131** |
| Equity funds resolved (ConvExp attempted) | **100** |
| Non-equity funds excluded (bond/commodity/derivative) | **31** |
| …of the 100, in ≥1 wave with a computed cell | 86 |
| …resolved funds whose waves computed **zero** cells | 13 |

The 31 excluded funds are correct (series located, held no common equity —
`reason_buckets: no_share_denominated_equity_in_matched_nport`). The **13 zero-cell
funds are also legitimate**: FundX Upgrader ×4 (funds-of-funds → hold other funds, not
stocks), Main BuyWrite / Soundwatch / Equable (options-overlay), Matthews Korea + abrdn
International Small Cap + JPMorgan International (foreign equity), Guggenheim/TCW (bond-ish).
None represent lost US common stock.

## Cell-level coverage (exact)
| metric | value |
|---|---|
| Attempted cells | **12,306** |
| Computed | **6,377** |
| Dropped | **5,929** |
| **Cell coverage** | **51.8%** |
| **Cell drop rate** | **48.2%** |
| Distinct stocks computed | 2,241 |
| ConvExp max / median | 0.261 / 0.000235 |
| **Value-weighted coverage** | **NOT AVAILABLE** — dropped cells retain no shares/value (see README caveat 1) |

## Drop reasons
| reason | count | % attempted | % dropped |
|---|---|---|---|
| `ticker_not_in_sec_map` | 4,914 | 39.9% | 82.9% |
| `no_xbrl_shares_outstanding` | 660 | 5.4% | 11.1% |
| `no_ticker` | 337 | 2.7% | 5.7% |
| `conv_exp>1` (stale denom) | 18 | 0.15% | 0.3% |

Every drop is a **missing denominator, not a missing holding** — the fund's position is
known; only shares-outstanding is absent because the free route (SEC XBRL via
`company_tickers.json`) covers only US-domestic SEC filers.

## Where the missingness actually lives (the real story)
**By asset class:** equity_US **65.8%** covered · equity_intl **8.8%** · mixed 74.6% ·
"other" 82.7% · fixed_income n/a (4 cells).

**By fund / wave — the dominant driver:**
- **Wave W020 — Mirae Asset Discovery (international equity), 2023-04-15: 3,015 attempted,
  88 computed = 2.9% coverage → 2,927 dropped cells = 49% of ALL 5,929 drops, from one
  fund.** It holds Korean/Asian equities with no US XBRL denominator.
- International-equity waves overall = **3,277 dropped = 55% of all drops.**

So roughly **half the total missingness is a single international fund, and the majority
is international equity generally.** Strip the international sleeve and US-equity coverage
is ~66%. This is a *sample-composition* fact, not a pipeline failure.

**By year:** 2023 is worst (31.7%) — that's the Mirae/international-heavy year; 2024–26 are
77–82%. **DFA vs non-DFA:** the DFA anchor W002 is the **best-covered** major wave at
**59.9%** (vs 49.7% non-anchor) — the pre-registered anchor is not the one that suffers.

## Severity: are important US common stocks missing? No.
Of 5,929 dropped cells: foreign-listing tickers 33.9% + foreign CINS CUSIPs 28.5% + ADR
0.8% = **~63% structurally non-US** (EUR-suffixed symbols like `ABMDEUR`, `ANGI1EUR`;
CINS CUSIPs). The 30.8% "US-recoverable" bucket is itself dominated by **delisted / renamed
/ acquired** names (ABC→Cencora, AAXN→AXON, ACC/ACIA acquired) that left the current SEC
map — a live US common stock that trades and tags XBRL today **was** captured. The 18
`conv_exp>1` are real US names (AMRX, FOX/FOXA, TRIP, RFL, CIA) with **dummy denominators**
(shares_out = 1/100/1000) the pipeline correctly quarantined.

## Does missingness change the treated-stock count at ≥0.5%? Almost certainly not.
Treated stocks (from computed cells): **pooled ≥0.25% = 761, ≥0.5% = 389, ≥1% = 24**;
DFA anchor W002 alone **≥0.5% = 361, ≥1% = 10.** These live in large US positions that
already have denominators. Dropped cells are small foreign/ADR positions (minor fund
allocations) — recovering them grows the low-exposure tail (≥0.25%), not the ≥0.5% treated
set. The 18 stale US names, once given real denominators, resolve to *tiny* exposures
(e.g. FOXA ~2×10⁵ shares against a multi-billion-share float) — none become treated.
**This is a strong expectation, not yet a proof:** confirming it requires recomputing
ConvExp on recovered denominators (needs the `shares_held` sidecar — box, see below).

## How much does recovery improve coverage?
Free, no-WRDS recovery ceiling (`coverage_before_after.csv`,
`coverage_post_recovery_summary.csv`):
- **Recoverable ceiling = 1,892 cells** (US-renamed 1,828 + ADR 46 + stale 18) →
  coverage **51.8% → ≤67.2%.**
- Remaining **3,698 (62% of drops) are foreign CINS / foreign listings** — outside the
  US/CRSP universe; even WRDS/CRSP would not place most of these in a US event study.
- 339 `no_ticker` need CUSIP→identity (mostly manual); 18 stale are a trivial priority fix.

So the achievable free gain is ~15 percentage points of cells, concentrated in
renamed/acquired US names and the stale fixes — useful for completeness, immaterial to the
≥0.5% treated set.

## Readiness verdict
**Ready for the kill-switch gate (Gate 2) as a feasibility read — recommend GO.**
The treated universe is **389 stocks ≥0.5% pooled and 361 in the DFA anchor alone**, versus
the P1-T2a power floor of **≥33 stocks on the smaller side**. Coverage clears the gate with
an order of magnitude to spare; the missingness is international/foreign by construction and
does not touch the treated set. This is a **preliminary/feasibility-grade** dataset, not yet
the final publishable one.

## Remaining data issues to fix before the *final* run (not blockers for the gate)
0. **Contract mismatch — RESOLVED 2026-07-20.** Root cause was NOT a parquet bug: the
   `conv_exposure_free.yaml` contract had been merge-corrupted into two concatenated YAML
   documents (a `cusip` block + a leftover `stock_cusip` scaffold block). `yaml.safe_load`
   silently kept the stray `stock_cusip` key, so the validator demanded a column the data
   never had. The box's *documented* design keys on `cusip`, and the parquet + crosswalk +
   NEED_HUMAN files all use `cusip`. Fix applied: repaired the contract to a single clean
   `cusip`-keyed document (nothing downstream consumes `stock_cusip`; the frozen
   `conv_exposure.yaml` stays `[permno, wave_id]`), and removed dead duplicate scaffold
   (an appended second `main()`/`_write()` using `stock_cusip`) from
   `build_nport_convexp.py` that would have mis-run on the next box execution.
   `contracts.py conv_exposure_free p1/conv_exposure_free.parquet` now **PASSES**
   (6,377 rows, 13 cols). No data mutation was needed.
1. **Fix the corrupt `p1/t2_wrds/waves.csv`** (double-schema; regenerate 4-col cleanly).
   *(Done in this audit — `waves.csv` regenerated from `waves_members.csv`; verify the
   pipeline's `build_waves.py` doesn't re-corrupt it.)*
2. **Retain `shares_held` on dropped cells** (1-line pipeline patch) so post-recovery
   ConvExp — and therefore post-recovery treated counts — can be computed. Emit a
   `dropped_cells_shares_held.csv` sidecar.
3. **Run `recover_denominators.py --online` on the box** (SEC-renamed → yfinance → Stooq):
   fixes the 18 stale, recovers ~1,800 renamed/acquired US names, and lets us *prove* the
   ≥0.5% treated set is unchanged.
4. **Add `valUSD`** to the pipeline output to enable value-weighted coverage (the one
   coverage view this audit could not produce).
5. Decide the **international sleeve's** treatment for the paper: document that
   equity_intl conversions (esp. Mirae W020) are largely out of a US-listed event study,
   or scope a separate non-US analysis. Either way it belongs in the sample-definition
   footnote, not treated as missing data.

_Numbers cross-checked against `ops/briefs/gate2_human_review_manifest.json`; full tables in
this directory; methods + caveats in README.md._
