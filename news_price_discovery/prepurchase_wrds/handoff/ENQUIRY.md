# Vendor enquiry — ready to send after owner authorization

**Do not send without owner authorization.** This is the counts-only form
(option 1 of §5.1 in `REQUEST_UNSENT.md`): it transmits estimated window
structure and event dates only, without naming specific constituent securities.
The counts below are estimates from internal holdings records, not guarantees.

A longer technical specification with 25 detailed questions is in
`REQUEST_UNSENT.md`. This document is the condensed form suitable for an
initial product-suitability enquiry.

---

Subject: Historical intraday quote data — product-suitability enquiry for a
six-event academic study

---

We are a research group evaluating whether a quote data product can support a
feasibility pilot on six US announcement events (two FOMC statement releases in
2021–2023 regular session; two premarket earnings releases in 2022–2023; two
aftermarket earnings releases in 2021–2022). We are not yet purchasing anything.
We are asking whether your product can provide what the measurement requires
before we take any further steps.

**The manifest in brief.**

| dimension | estimate |
|---|---|
| events | 6 |
| distinct securities (ETFs + constituents, estimated from holdings records) | ~530–535 |
| calendar dates (event + 3 matched controls per event) | 24 |
| security-days | ~8,600 |
| quote-minutes | ~645,000 |
| share of intervals outside 09:30–16:00 ET | ~53% |

These counts are derived from internal CRSP mutual-fund holdings records and
may shift by a small number of securities once we resolve our identifier list
against your universe. We are not asking you to price exactly these numbers —
we are asking whether a dataset of this approximate scale and vintage is
something your product can deliver, and on what terms.

**The six event windows.** All windows are T−60m to T+15m where T is the
release time, on the event date and on three prior control dates.

| event | release date | release time (ET) | merged window (ET) | session |
|---|---|---|---|---|
| FOMC statement | 2021-09-22 | 14:00 EDT | 13:00–14:15 | regular |
| FOMC statement | 2022-01-26 | 14:00 EST | 13:00–14:15 | regular |
| NDAQ earnings | 2022-04-20 | 07:00 EDT | 06:00–07:15 | premarket |
| EMR earnings | 2023-02-08 | 06:55 EST | 05:55–07:10 | premarket |
| ESS earnings | 2022-10-26 | 16:15 EDT | 15:15–16:30 | aftermarket |
| GL earnings | 2021-07-21 | 16:15 EDT | 15:15–16:30 | aftermarket |

**Five questions we need answered before we can proceed.**

1. **Historical date coverage.** Does your product cover US equities and ETFs
   for the 24 specific dates spanning 2021-07-16 through 2023-02-08? A recent
   sample demonstrates format only; we need explicit confirmation of old-date
   availability, not an extrapolation from current coverage.

2. **Extended session.** Does your product include premarket quotes from at
   least 05:55 ET and aftermarket quotes through at least 16:30 ET on these
   dates? Four of the six events fall outside regular hours; without
   extended-session data those four events are unmeasurable.

3. **Quote freshness flag.** For each delivered quote observation (whether
   event-stream or clock-sampled), can we determine whether it is a fresh
   quote update or a forward-filled carry of an earlier quote? We also need the
   **original source timestamp** of the underlying quote, separate from any
   sampling clock. Without these two fields the measurement cannot distinguish
   a price response from a stale print, and the product is unsuitable
   regardless of price.

4. **Window boundary initial state.** The baseline window for each event opens
   60 minutes before the release. We need the prevailing bid and ask **at the
   instant the window opens**, not only changes within the window. Can your
   product provide an initial quote snapshot at a requested boundary, or
   sufficient pre-window history to reconstruct the prevailing quote
   unambiguously at that boundary?

5. **Historical symbology.** Our constituent list is keyed to CUSIP and CRSP
   PERMNO. For one event, Globe Life Inc traded as GL on the event date but
   appears in our upstream source as TMK (Torchmark, the legacy ticker). Does
   your product carry historical ticker crosswalks that would return the correct
   quote path under either identifier?

**What we are not asking for.** We are not asking for a quotation yet, a free
trial, or confirmation that you can cover each of our ~530 specific securities.
We understand that exact coverage depends on your universe for historical dates
and that gaps may exist for delisted or renamed names. What we need is an honest
characterisation of what your product does so we can determine whether it is
suitable before taking any further steps.

If there is a schema sample available, we would accept it as evidence about
format only and would not treat it as confirmation that the 2021–2023 dates are
covered.

If the product is suitable, our next step would be to request an itemized
quotation for approximately this manifest scale, academic-use terms, and export
and retention conditions. No purchase decision has been made.

---

*This enquiry was drafted on 2026-09-06. Owner authorization is required before
it is sent. The five questions above are a condensed form; a full 25-question
technical specification exists in `REQUEST_UNSENT.md` and covers consolidation
semantics, condition codes, halt representation, corrections, locked/crossed
quotes, and weight sourcing.*
