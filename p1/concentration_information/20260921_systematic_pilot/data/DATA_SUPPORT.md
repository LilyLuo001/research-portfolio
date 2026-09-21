# SUPERSEDED — SCC data support (aggregate only)

The 32-event issuer mapping in this first support note was incorrectly
hand-transcribed as a different top-eight set. Do not use its event-membership,
event-date, or I/B/E/S target counts. The source-path/schema facts remain
provisional only; the corrected, roster-hash-bound aggregate is pending.

SCC BatchMode login is confirmed. `DATABENTO_API_KEY` is absent in the SCC
process environment (presence boolean only); no purchase, balance check, quote,
price, return, EPS, or forecast value was read.

## Holdings

2023 CRSP holdings files exist at
`raw/rescue_remaining/crsp_holdings_etf_2023_b####/part_*.parquet`. Confirmed
fields are `crsp_portno`, `report_dt`, `eff_dt`, `percent_tna`, `nbr_shares`,
`security_name`, `cusip`, `permno`, and `ticker`. Active 2023 fund identities
are QQQ/1026023 and SPY/1021980, both ETF class `F`.

Each has twelve month-end snapshots, 2023-01-31 through 2023-12-31. QQQ has
101 distinct security identifiers/report; SPY has 500--501. Every inspected
2023 position has non-null shares and `percent_tna`. This is genuine
per-security holdings support, but not an event-date actual basket: neither
fund has an exact report on any existing event date. `eff_dt` is vendor
acquisition metadata, not a publication-time assertion. Latest prior reports
are stale/proxy candidates unless that policy is frozen.

The former 32-event membership figures in this document were calculated with
the wrong issuer roster and are invalidated. The only authoritative replacement
is the hash-bound automatic census script in this directory; until it executes,
event-level membership remains unknown. In no case does this establish
REST/common quote support.

## I/B/E/S and quotes

Direct actuals/detail 2023 source files contain all eight issuer identifiers
(Alphabet `GOOGL`, Berkshire `BRK.B`), EPS and USD metadata, with actual,
activation, announcement, revision, fiscal-period, and currency fields. The
PIT activation/version and same-day ordering rules remain unfrozen.

The existing nine DBNs cover only the two old XOM technical anchors, not the
six-clock candidate set. They are venue-specific `bbo-1s`, not REST/TOP or
NBBO evidence. Any later diagnostic must use `ts_recv`, report aggregate
positive/noncrossed observed snapshot counts only, and make no live-continuity
claim.
