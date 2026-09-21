# Independent result review

## Judgment

**Usable with stated restrictions; status remains `PATHS_AND_PROXY_COMPUTED`.** I independently rebuilt the decisive XNAS SPY/XOM states and the requested basket aggregates from the licensed SCC DBN/CRSP files. The released endpoint values match the independent reconstruction. The SPY/XOM exhibit is usable as a descriptive, venue-specific observed-price-path demonstration. It is not evidence of price discovery, causal response, or information share. The six-stock and ex-XOM series are low-coverage, sparse-quote diagnostics and are not usable as SPY holdings, NAV, PCF, or a broad constituent-response measure.

One interpretation issue was corrected in `RESULTS.md`: the plotted ex-XOM dip at +46/+47 minutes is a transient, very wide XNAS BSX quote, not a broad five-stock move. I also replaced an ambiguous `percent_tna` sentence with the actual report sums. No endpoint, path, or figure values required correction or rerunning.

## Independent raw reconstruction

I used a separate one-off decoder on SCC rather than reading `ENDPOINTS.csv` as the source of truth. It read the two raw `bbo-1s` DBNs directly, selected date-valid instrument IDs from each file's metadata, retained valid positive two-sided BBOs, and selected the latest `ts_recv` state at or before each target without interpolation. The XNAS metadata IDs were SPY 9880 and XOM 11563; the ARCX IDs were SPY 15144 and XOM 17709. DBN fixed prices were converted from nanodollars by dividing by 1,000,000,000.

On 2023-01-31 New York was on EST (UTC-5), so 06:30 ET is 11:30 UTC. The baseline target is 06:25 ET / 11:25 UTC; the endpoints are 11:31, 11:35, 11:45, 12:00, and 12:30 UTC. This conversion and the delivered anchor metadata are correct.

### Decisive XNAS reconstruction

| Object | Target | Selected `ts_recv` UTC | Bid | Ask | Mid | Age (s) | Change from baseline (bp) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| SPY | baseline | 11:24:59 | 398.59 | 398.65 | 398.620 | 1 | 0.00 |
| SPY | +1 | 11:30:58 | 398.39 | 398.42 | 398.405 | 2 | -5.3936 |
| SPY | +5 | 11:34:57 | 398.24 | 398.31 | 398.275 | 3 | -8.6549 |
| SPY | +15 | 11:44:58 | 399.19 | 399.25 | 399.220 | 2 | +15.0519 |
| SPY | +30 | 12:00:00 | 399.23 | 399.30 | 399.265 | 0 | +16.1808 |
| SPY | +60 | 12:29:59 | 399.70 | 399.73 | 399.715 | 1 | +27.4698 |
| XOM | baseline | 11:24:14 | 112.20 | 112.52 | 112.360 | 46 | 0.00 |
| XOM | +1 | 11:30:57 | 110.60 | 111.60 | 111.100 | 3 | -112.1396 |
| XOM | +5 | 11:35:00 | 109.30 | 110.00 | 109.650 | 0 | -241.1890 |
| XOM | +15 | 11:44:49 | 109.94 | 110.30 | 110.120 | 11 | -199.3592 |
| XOM | +30 | 11:59:59 | 110.33 | 110.63 | 110.480 | 1 | -167.3193 |
| XOM | +60 | 12:29:38 | 111.83 | 111.90 | 111.865 | 22 | -44.0548 |

The reconstructed quote fields and ages equal the delivered rows; across XNAS and ARCX the largest floating-point difference in a reported change was 2.3e-12 bp.

### ARCX direction check

| Object | +1 bp | +5 bp | +15 bp | +30 bp | +60 bp |
| --- | ---: | ---: | ---: | ---: | ---: |
| SPY, XNAS | -5.39 | -8.65 | +15.05 | +16.18 | +27.47 |
| SPY, ARCX | -5.64 | -9.03 | +14.80 | +16.31 | +27.34 |
| XOM, XNAS | -112.14 | -241.19 | -199.36 | -167.32 | -44.05 |
| XOM, ARCX | -111.75 | -222.17 | -200.80 | -150.93 | -40.96 |

ARCX agrees on direction at every requested endpoint: SPY is down at +1/+5 and up at +15/+30/+60; XOM is below baseline throughout. The venue levels and magnitudes are not identical, especially for wide premarket XOM quotes, so this is corroboration of the descriptive direction rather than a merged NBBO or evidence about which security incorporated information first.

## Fixed CRSP subset and company actions

The Dec-31 report contains 505 raw rows and 504 non-null ticker candidates. `percent_tna` sums to 100.3799701482 across all rows and 99.9699703008 across ticker-identified rows. Independently intersecting all ticker candidates with date-valid XNAS mappings and requiring a state by the 06:30 baseline and each fixed endpoint reproduces exactly AIG, BSX, CMI, EA, LHX, and XOM. The row-level licensed holdings and identifiers used for this check remain on SCC and are not reproduced here.

The six fields sum to 2.0999996066 `percent_tna` points, which is 2.0920504% of the all-row report sum. Marking the reported quantities at the XNAS baseline gives XOM a 0.6761872619 share of the six-stock baseline value, exactly matching `QUALITY_SUMMARY.json`. Removing XOM but keeping the other five quantities fixed gives a +5 endpoint of 99.8435698893, or **-15.6430111 bp**, exactly matching `ENDPOINTS.csv`.

On SCC I checked the CRSP daily share adjustment factors and distribution file for all six securities. Each name's share and price adjustment factors are 1.0 throughout the checked Dec-29-to-Jan-31 daily interval, and there is no distribution record with a share factor and ex-date from Dec-31 through Jan-31. Therefore no Dec-31-to-event split/share adjustment is required; using the reported relative quantities is correct. Their units are also internally consistent with the report's market-value fields and contemporaneous prices, and a common quantity scale cancels after baseline normalization.

## Ex-XOM +46/+47-minute dip

The apparent sharp dip is an observed-state artifact, not a calculation or interpolation error. XNAS BSX changed from 45.64/46.52 at 12:14:24 UTC to **41.66/46.61** at 12:15:01, making its midpoint fall from 46.08 to 44.135 while its spread widened to about **1,122 bp**. That one state is 59 seconds old at the +46 minute mark and 119 seconds old at +47. The next XNAS BSX updates beginning at 12:17:10 return the midpoint to about 46.04–46.10, and the five-stock index returns from 98.84 to 100.05 by +48.

At the same 12:15:01 timestamp ARCX BSX was 45.73/46.13 (mid 45.93) and had no analogous drop. Thus the XNAS state is real under the stated latest-valid-state rule, but the plotted movement is caused by one sparse name and an unusually wide venue quote. It cannot support a spillover interpretation. More generally, several proxy states are old even at the declared +5 endpoint (AIG 114 seconds, BSX 92, and EA 208), which reinforces the proxy's limited time-local meaning.

## Code and interpretation audit

- Instrument mapping is metadata-based and date-valid; there is no ticker-to-ID guess in the price decoder.
- Price scaling, midpoint, basis-point, spread, and baseline-value formulas have the correct units. The fixed set does not change by horizon or response direction.
- Endpoint state selection uses `ts_recv <= target` and does not linearly interpolate or substitute zero returns. Its carry-forward behavior is intentional but can preserve stale or wide venue states, as the BSX diagnostic shows.
- Separate venue files remain separate; the output does not claim SIP NBBO.
- `RESULTS.md` describes different-cash-flow paths and explicitly rejects information-share and causal interpretations. With the added BSX caveat, it does not overstate the proxy or price discovery.

The empirical content supports only this narrow statement: on the selected XNAS and ARCX venue feeds, XOM's midpoint was materially below its pre-anchor baseline at all requested post-anchor endpoints, while SPY's smaller path changed sign later in the hour. It does not establish that XOM led SPY, that either path was caused by the earnings release, or where/when the market discovered fundamental value.

## Routing

Requested reviewer routing was not visible in model telemetry. Actual routing: **`NOT_OBSERVED`**. This did not block the raw-data review.
