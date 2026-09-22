# Sample and dates — fixed engineering manifest

Status: `ROSTER_AND_MARKET_DATA_COMPLETE` (2026-09-22).

The roster uses the 2022-12-31 CRSP SPY holdings report for portfolio 1021980,
whose vendor `eff_dt` is 2023-01-09. It is a lagged-report retrospective weight
proxy, not an event-time PCF. Of 446 eligible ordinary common shares, seed
`20260922` selects 24, four per report-weight × 60-day-dollar-liquidity cell;
the safe tickers, permanent IDs, weights, and draw keys are in `SAFE_ROSTER.csv`.

Liquidity is mean `abs(CRSP prc) × vol` over the 60 trading sessions through
2022-12-30, from `raw/crsp_dsf_2022.parquet`; dated ordinary-common identity is
from `raw/crsp_dsenames_full.parquet`. `DATE_MANIFEST.csv` fixes the 24 NYSE
dates and chronological 12/4/8 train/validation/test split.

The exact plan was executed as 48 MBP-1 requests: SPY plus the provider-resolved
shares, 24 dates, and both XNAS.ITCH/ARCX.PILLAR venues, with 09:59--10:31 ET
request bounds. The authenticated quote was $5.823790758848 for approximately
65.14 million records. All 48 native DBN files remain on SCC. PERMNO 29946
(`BF`) did not resolve through Databento historical raw-symbol mapping, so the
fixed 24-stock roster remains the reporting denominator while the feature and
model samples contain SPY plus 23 stocks; no replacement was drawn.

Databento's authenticated dataset-condition metadata reports ARCX.PILLAR as
degraded on 2023-09-22, 2023-11-21, and 2023-12-07. Those dates are retained,
labeled in `COVERAGE.csv`,
and excluded only from the ARCX predeclared sensitivity summary; XNAS reports
`available` on those dates. Feature construction on SCC produced 4,147,200
security-second rows covering all 24 dates, both
venues, and both grid shifts. No raw DBN or security-time panel was copied to
the local worktree.
