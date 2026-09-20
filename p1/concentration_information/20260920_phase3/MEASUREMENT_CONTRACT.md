# P1 quotation measurement contract — frozen before response access

Frozen on 2026-09-20 for the six-event technical/development pilot. This file
does not authorize or report treatment-effect estimation.

## Measurement object

The existing files are venue-specific `bbo-1s`, not a SIP NBBO. Each dataset is
kept separate: `XNAS.ITCH`, `BATS.PITCH`, `ARCX.PILLAR`, and `XNYS.PILLAR`.
They must not be pooled and relabeled as a national composite. A second venue is
a measurement-sensitivity check, not an independent economic observation.

Databento documents `bbo-1s` as the last BBO and sale on a one-second interval.
No row is printed when neither a BBO update nor trade occurs. In this schema,
`ts_recv` is the interval-end timestamp clamped to the second boundary, while
`ts_event` is the timestamp of the last trade and can be undefined. Therefore:

- endpoint alignment uses UTC `ts_recv`, never `ts_event`;
- absence of a row does not by itself mean that a live quote is missing;
- BBO state may be carried forward only within the same documented session;
- every session is reset, and no future observation initializes an earlier time.

Official schema documentation:

- <https://databento.com/docs/knowledge-base>
- <https://databento.com/docs/venues-and-datasets>

## Event and sample rules

- Population stays the frozen 32 top-eight issuer release groups in 2023.
- Six development events are chosen without response data: earliest eligible
  events within verified PRE_OPEN and AFTER_CLOSE strata, with winter/summer
  coverage where the evidence permits. Ties use issuer rank, date, then opaque
  event ID.
- The other eligible events remain validation events. Date-only or boundary-
  crossing publication-time evidence is excluded from minute endpoints and may
  enter only a separately defined daily fact.
- Receiver securities are the outcome-blind 20-symbol configuration produced by
  `network_selection/build_weighted_receiver_selection.py`. QQQ and SPY are
  additional measurement objects, not untreated controls.
- No event, receiver, venue, or horizon may be added or removed based on a
  realized price response.

## Window and quote-state rules

- Requested window: publication time minus 15 minutes through plus 75 minutes.
- Baseline target: publication time minus 5 minutes.
- Post targets: +1, +5, +15, +30, and +60 minutes. The primary endpoint is +15;
  +60 is the persistence endpoint.
- Also retain the pre-response from -5 minutes through the publication boundary.
- A usable state requires defined positive bid and ask, positive sizes, and
  `ask >= bid`. Locked quotes are retained and flagged; crossed quotes are
  invalid. Midpoint is `(bid + ask)/2`.
- At a target, use the last valid state whose interval end is no later than the
  target. Never interpolate in both directions or use a future row. There is no
  arbitrary staleness cutoff: an unchanged valid order is not missing. If the
  downloaded pre-window cannot initialize the state, mark the endpoint UNKNOWN.
- Do not carry state across the core/extended-session boundary, a halt, or a
  documented session reset. If the available schema cannot identify a halt or
  withdrawal state reliably, mark the affected endpoint UNKNOWN rather than
  treating the prior state as live.
- A horizon is reported on a common mask for the exact objects compared. Missing
  quote state is not zero return.

## Derived measurements

For a usable object and horizon, simple midpoint response is
`midpoint_h / midpoint_baseline - 1`. This is a venue-specific response, not a
price-discovery share. No early/final-return ratio is allowed.

Development output may contain endpoint coverage, response paths, and
pre-specified strong-minus-weak receiver baskets. The validation set stays
sealed until the development code, common masks, event blocks, and inference
plan are frozen and recorded on final hashes.

## Required checks before reading a development response

1. Synthetic no-movement, one-sided withdrawal, locked, crossed, sparse-update,
   session-reset, and asynchronous-venue fixtures pass.
2. The exact request matrix is reconciled against the SCC manifest by dataset,
   schema, historical symbol, and UTC interval.
3. At least 20 endpoint observations are traced to raw DBN records without
   inspecting validation events.
4. Any source-clock amendment regenerates the six-event selection and request
   matrix before response access.

