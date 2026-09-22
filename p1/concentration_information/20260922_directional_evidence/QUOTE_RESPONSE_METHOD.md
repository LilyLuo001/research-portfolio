# Work C: venue-local quote-update response

All native DBN and all event/match rows were decoded and retained on SCC. The
three local CSVs are aggregates only, spanning the fixed 24 observed dates,
23 provider-resolved sampled stocks, SPY, and both source venues.

Source-event timestamps and matched-control grid centers are restricted to the
same analysis centers as the prediction design: `[request start + 60 seconds,
request end - 60 seconds)`, i.e. 10:00:00 inclusive through 10:30:00 exclusive
for each request. The 60-second native buffers remain available only to supply
strictly earlier baselines and post-center response endpoints.

An event is an endpoint-to-endpoint change in a valid best-bid/offer midpoint.
Invalid or reset endpoints are retained as invalid states: a later valid quote
begins a new validity epoch and cannot be classified as a change from a quote
before the invalid interval. The target baseline is its last valid midpoint
strictly before the source timestamp. A target midpoint update at the exact
same timestamp is marked order-uncertain. `*_simultaneous_excluded` removes
those observations; other variants retain them but report their count.

`nonoverlap` is prospective: retain a source midpoint change only if it is at
least 5 seconds after the last retained source event. It uses no response data.
For each 100ms, 500ms, 1s, 2s, and 5s horizon, signed response is source-event
sign times target log-midpoint change in bp. The named endpoint-alignment
probability has denominator **all usable source events** and additionally
requires at least one target midpoint update after the trigger through the
horizon. It is not a causal probability.
The prepath is the standard forward, sign-aligned path from `t-h` to the
strictly pre-trigger target baseline at `t-`; it is not the reverse return.

`MATCHED_CONTROL_RESPONSE_SUMMARY.csv` uses the nearest one-second grid center
in the same source date and 5-minute bin with absolute time separation from
the trigger strictly greater than 10 seconds. It is retained only on exact
tercile agreement of source BBO spread, absolute prior-five-second midpoint
movement, and prior-five-second midpoint-update count. The fixed separation
prevents a 1–5 second control window from mechanically containing its paired
trigger. **All three matching covariates are evaluated strictly before their
respective event or grid center**: source midpoint and spread use the final
valid quote before the center, and the five-second movement ends at that same
strictly pre-center quote. Candidate selection uses no future source/target
events or responses. Responses retain the source-event sign at both centers.
Equal-timestamp target updates remain in this matched-control table rather than
receiving a separate excluded variant; their counts are very small, and the raw
response table supplies the explicit `*_simultaneous_excluded` comparison.
Only aggregates leave SCC. This is a temporal control, not a causal identifying
design.
