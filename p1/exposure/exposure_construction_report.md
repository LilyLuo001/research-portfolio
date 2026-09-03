# P1 Exposure^pre construction report

Generated: 2026-09-03T05:17:26.268682+00:00

## Frozen universe and timing

- Gate0 PASS events: **71** across **47** waves.
- Pending first-POST N-PORT events: **3**.
- PRE selection is the latest filing-internal `repPdDate` strictly before the verified effective date, using the exact predecessor series id.
- POST holdings are retained only as Gate0 evidence and are never read into treatment construction.

## Security mapping

- PRE N-PORT positions: **26399**.
- Unique reported CUSIPs before mapping: **11962**.
- Mapping uses date-valid CRSP CIZ `stocknames_v2`: CUSIP9 first, CUSIP8 only as a labelled fallback. Fuzzy names are never used.
- Exact-matched position value / all N-PORT value: **67.23%**.
- Exact-matched position value / common-equity-candidate value: **96.49%**.
- Unmatched/non-CRSP/non-common share of candidate common-equity value: **3.51%**.

## Corporate actions and exposure definitions

The frozen formula is `AdjustedShares = RawShares × CFACSHR`. Legacy CRSP uses
`cfacshr`; 2025 CIZ uses `dlycumfacshr`. The factor is the same-day or most
recent prior trading-day observation within four calendar days of the N-PORT
report/as-of date. It is applied per fund-position before aggregation.

The consistent stock denominator is CRSP `shrout × 1,000` on the latest trading
day strictly before the wave effective date (maximum seven-day gap). Market cap
uses `abs(price) × shrout × 1,000` on that same date.

Candidate measures saved together:

- `adjusted_shares_held`: raw share dose after the frozen factor adjustment;
- `exposure_ownership`: adjusted shares / CRSP shares outstanding;
- `exposure_value`: summed N-PORT position value / CRSP market capitalization;
- `fund_portfolio_weight_sum`: sum of position value / predecessor net assets.

`exposure_ownership` is recommended as the primary measure because it matches
the frozen economic treatment definition and uses one pre-event denominator per
stock-wave. No result coefficient has been inspected.

## Concentration and extreme-position diagnostics

- Dimensional share of exact-matched PRE position value: **64.15%**.
- Largest adviser by exact-matched PRE position value: **Dimensional Fund Advisors LP** (**64.15%**).
- Largest wave by exact-matched PRE position value: **W002** (**50.26%**).
- Exact-matched positions with fund portfolio weight above 10%: **5**.
- No position was automatically winsorized or removed. Flagged rows are preserved in `exposure_extreme_positions_audit.csv` for inspection.
- Sponsor and wave tables are in `exposure_sponsor_concentration.csv` and `exposure_wave_summary.csv`.

## Remaining blockers

- The archive has CRSP security returns/factors through 2025. 2026 observations
  that fail the four-/seven-day alignment are retained as explicit missing, not
  filled with stale 2025 factors.
- The economic-sponsor crosswalk is not signed. LOSO inputs therefore preserve
  position contributions and carry adviser labels only; they are not final
  sponsor-cluster matrices.
- Gate0 has 47 PASS waves, of which 30 currently contain at least one exact-mapped
  U.S. common stock with a valid pre-event CRSP denominator. The other 17 are
  retained in coverage files; most have no N-PORT position classified as U.S.
  common equity, and none is silently promoted into the stock-level sample.
- Two specified long-handoff events and every predecessor-report-after-event
  flag are carried, not automatically dropped.

## Lineage

Inputs and SHA-256 hashes are in `exposure_construction_lineage.json`. CRSP raw
files remain outside Git. No headline earnings outcomes or coefficients were
loaded or estimated.
