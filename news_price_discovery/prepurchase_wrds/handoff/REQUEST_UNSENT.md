# Unsent quote-and-weights specification request

**Status: DRAFTED, NOT SENT.** No vendor has been contacted, no account opened,
no quotation obtained, no purchase made. Nothing below is a vendor statement.
Every price, coverage claim, licence term and delivery format in the sample
request is a *question being asked*, never an assumption being carried.

Sending this requires the owner's specific authorization. Two things must be
settled first — see §5.

---

## 1. What is being asked for, in one paragraph

We need, for **six named announcement events**, the quote path of an ETF and of
every constituent of that ETF's governing portfolio, over short windows around
the release instant, on the event date and on three matched control dates. The
measurement is a difference between an ETF return and a complete-basket return
at horizons of one, five and fifteen minutes. That measurement is destroyed by
forward-filled samples, by trade-triggered observations, and by single-venue
quotes presented as consolidated. The purpose of this request is to establish,
*before any purchase*, whether a candidate product can supply a quote path with
the freshness semantics the measurement requires, on these specific historical
dates, for these specific identifiers.

## 2. The exact manifest

Deduplicated across events and securities. These are the totals, not an
estimate and not a superset:

| quantity | value |
|---|---|
| events | 6 |
| distinct securities | 532 |
| distinct calendar dates | 24 |
| security-days | 8,604 |
| merged security-day intervals | 8,604 |
| total quote-minutes requested | 645,300 |
| share of intervals outside 09:30–16:00 ET | 52.9% |

Windows per event, per security: an **event window** of T−5m to T+15m and a
**baseline window** of T−60m to T−5m, where overlapping intervals on the same
security-day have been merged so no minute is requested twice. The identical
window pair is requested on **three matched control dates** per event (the three
nearest prior NYSE sessions that are not themselves selected events).

The six events, their sessions and their window clocks:

| event | date | ET window (merged) | session |
|---|---|---|---|
| FOMC statement | 2021-09-22 | 13:00–14:15 | regular |
| FOMC statement | 2022-01-26 | 13:00–14:15 | regular |
| NDAQ earnings | 2022-04-20 | 06:00–07:15 | premarket |
| EMR earnings | 2023-02-08 | 05:57–07:12 | premarket |
| ESS earnings | 2022-10-26 | 15:15–16:30 | aftermarket |
| GL earnings | 2021-07-21 | 15:15–16:30 | aftermarket |

Control dates: FOMC 2021-09-22 → 09-17, 09-20, 09-21. FOMC 2022-01-26 → 01-21,
01-24, 01-25. NDAQ → 04-14, 04-18, 04-19. EMR → 02-03, 02-06, 02-07.
ESS → 10-21, 10-24, 10-25. GL → 07-16, 07-19, 07-20.

The full security-level manifest (identifiers per event-date-window) exists as
`out/s8_windows.parquet` and `out/s8_constituents.parquet` and is **not in this
repository** — see §5.2 on why transmitting it is itself a licence question.

## 3. Questions to the provider

Each of these is a question. None is an assertion about what the product does.

### 3.1 Coverage of these dates and identifiers

1. Does the product cover **2021-07-16 through 2023-02-08** for US equities and
   ETFs? Please confirm against the 24 specific dates listed, not against
   "history since YYYY."
2. A recent sample tests schema only. **Please confirm old-date availability
   explicitly** — a demonstration on last month's data does not answer this
   question and will not be treated as if it did.
3. Does coverage include the **extended session** — premarket from at least
   05:57 ET and aftermarket through at least 16:30 ET? 52.9% of the requested
   intervals lie outside regular hours. If extended-session quotes are absent,
   thin, or sourced differently from regular-session quotes, say so; that fact
   determines whether four of the six events are measurable at all.
4. Are all 532 securities present on their requested dates, including securities
   that were later delisted, renamed, or acquired?

### 3.2 The quote path itself

5. Is the delivered object an **event stream of quote updates** (one row per
   NBBO or venue quote change), or a **clock-sampled series** (one row per fixed
   interval)? If sampled, at what interval, and by what rule is the sample
   populated?
6. For a clock-sampled product: does each row carry a flag distinguishing a
   **fresh observation** in that interval from a **forward-filled carry** of an
   earlier quote? If the product cannot distinguish these, the measurement
   cannot distinguish a price response from a stale print, and the product is
   unsuitable regardless of price.
7. Does each row carry the **timestamp of the underlying quote** as distinct
   from the sampling instant? Please state the precision of each
   (milliseconds, microseconds, nanoseconds) and whether that precision is the
   native source precision or a re-stamp.
8. Where available, is there a **receipt / feed-arrival timestamp** separate
   from the exchange-side source timestamp? If both exist, please describe how
   they relate and which one is used for sequencing.
9. Is there a **quote age** or **update-count** field, or can it be derived
   without ambiguity from the delivered rows?
10. Are **condition codes** / quote condition flags delivered, with a
    documented code list valid for the 2021–2023 period (not only the current
    list)?
11. Are **bid and ask sizes** delivered where available?

### 3.3 Consolidation and venue semantics

12. Is the quote **consolidated (NBBO)** or **single-venue**? If consolidated,
    which SIP, and is the NBBO as-disseminated or recomputed by the vendor?
13. If recomputed, what inputs and what latency model? A vendor-recomputed NBBO
    and an as-disseminated NBBO are different objects and we need to know which
    one we would receive.
14. Are **odd-lot** and **round-lot** quotes handled the same way in the
    2021–2023 period as in current data?
15. Explicitly: **trade-only OHLC bars and trade-triggered quote snapshots are
    not substitutes** for the requested quote path. If the product is one of
    these, please say so rather than mapping our request onto it.

### 3.4 Edge conditions

16. **Halts and LULD pauses** — how are they represented? Is there an explicit
    halt indicator, or does the quote simply stop updating?
17. **One-sided quotes** (bid or ask absent) — are they delivered as-is, dropped,
    or filled? Absent-side handling changes a computed mid.
18. **Locked and crossed quotes** — delivered as-is, suppressed, or corrected?
19. **Corrections and cancellations** — is the product as-of-the-time or
    as-corrected? If corrections are applied retroactively, is the original
    print recoverable?
20. Are quotes present at all in the **market-closed interval** between the
    aftermarket close and the next premarket open, and how is that gap
    represented?

### 3.5 Historical symbology

21. What identifier does the product key on, and is there a documented
    historical crosswalk to CUSIP and to CRSP PERMNO for the 2021–2023 period?
22. Concretely: **Globe Life** appears in our upstream I/B/E/S source under the
    legacy ticker **TMK** (Torchmark) but traded as **GL** on the 2021-07-21
    event date. Which symbol would return the correct quote path for that date,
    and does the product resolve the change automatically or require the caller
    to know it? This is a real case in our manifest, not a hypothetical.
23. How are securities that changed ticker, CUSIP or listing venue *within* the
    2021–2023 window represented across that change?

## 4. Weights are a separate request

The quote product is not expected to carry portfolio weights. If it does not,
we need them from an appropriate historical holdings source, requested
separately, and the following distinctions matter:

- **Published benchmark weights**, **fund portfolio holdings**, and
  **exchanged AP creation baskets** are three different objects and are not
  interchangeable.
- What this project needs is the **portfolio value of the fund's actual
  holdings** at the event date — not a claim about which basket an authorized
  participant actually exchanged, and not the index's published weights.
- The weights currently in hand come from CRSP mutual-fund holdings at a
  **report date** with a separate **effective date** as the availability proxy.
  That is a date-level availability signal, never intraday. Reports governing
  the six events are 8 to 26 days stale relative to the event.
- **Missing constituent mass is named, not hidden.** In every snapshot
  governing a selected XLF event, 2.56–3.21% of reported net assets is carried
  by lines that do not map to a PERMNO. SPY snapshots carry 0.36–0.53% and XLK
  0.09–0.16%. A weights source that closes that gap for these dates would
  materially improve the measurement; one that does not, does not disqualify it,
  but the residual mass must then be reported as a bound.
- Any weights source must be usable as a **retrospective historical
  reconstruction**. We are not claiming it represents an investor-known
  information set at the event instant, and we will not backfill from holdings
  reported after the event.

## 5. Two things to settle before this is sent

### 5.1 Whether the security list may leave the licensed environment

The per-security manifest is derived from CRSP mutual-fund holdings. Sending a
vendor the full constituent list with weights for a named fund on a named date
is a disclosure of licensed holdings data to a third party. **This has not been
cleared.** Options, in increasing order of disclosure:

1. Send only the **counts and window structure** (§2 above) and the six ETF
   tickers, asking coverage and semantics questions without naming
   constituents. Sufficient to answer every question in §3.
2. Send the **date list and window clocks** plus a security count, still
   without names.
3. Send the **full identifier list**. Requires a licence determination first.

Option 1 answers the product-suitability question and is the recommended form
if this is authorized. Nothing beyond option 1 should be transmitted without a
specific licence review.

### 5.2 Cost and terms — to be requested, never assumed

The request should ask for:

- an **itemized quotation for exactly this manifest** — 8,604 security-days /
  645,300 quote-minutes / 24 dates — and separately for the smallest unit the
  provider will sell that covers it, if the manifest cannot be priced directly;
- whether pricing is by security-day, by row, by date, by subscription, or by
  flat historical extract;
- **academic-use terms**: whether an individual researcher at a university may
  purchase; whether an existing institutional subscription would cover it and
  under what conditions;
- **export and retention conditions**: whether derived aggregates may be
  published, whether raw rows may be retained after the project, whether
  co-authors at other institutions may access them;
- whether a **schema sample** is available, with the explicit statement that a
  schema sample will be treated as evidence about *format only* and never as
  evidence that the 2021–2023 dates are covered.

**No free sample, trial credit, institutional licence, current price, or
historical coverage is assumed here.** No figure appears in this document
because no figure has been obtained. Any number a vendor supplies gets recorded
with its date and source, and stale unit prices are not carried forward.

## 6. What a satisfactory answer looks like

The product is usable for this measurement if, on the 24 named dates:

1. quotes exist for the ETFs and for the great majority of constituents,
   **including in the extended session**;
2. fresh observations are distinguishable from forward-filled ones;
3. quote source timestamps are delivered at sub-second precision with
   documented semantics;
4. consolidation semantics are stated and stable across the period;
5. halts, one-sided quotes and corrections are represented explicitly rather
   than silently;
6. historical symbology resolves the TMK/GL case and its like.

If (2) fails, the product is unsuitable and the status becomes
`PRODUCT_UNSUITABLE_FOR_REQUESTED_MEASUREMENT` regardless of price. If (1) fails
only in the extended session, the two premarket and two aftermarket events are
unmeasurable and the pilot reduces to the two FOMC events — which would be
reported as a named shortfall, not silently absorbed.

Note that even a fully satisfactory answer here does not restore the 10-second
and 30-second horizons. Those are gated by the **announcement clock**, which is
minute-resolution, not by quote resolution. See `ESTIMAND.md` §3. A one-second
quote product does not fix a release time known only to the minute.
