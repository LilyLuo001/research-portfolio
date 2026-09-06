# Revised provider enquiry — UNSENT

**Status: DRAFTED, NOT SENT.** Prepared 2026-09-06. This is a new proposed
draft based on the owner's feedback; it is not a verbatim copy of `ENQUIRY.md`.
No message has been sent, no account has been opened, no purchase has been
authorized. Nothing below is a vendor statement.

Sending requires the owner's specific authorization. The five questions below
are the condensed form. A full 25-question technical specification exists in
`REQUEST_UNSENT.md`.

This draft adds explicit consolidation-semantics language, permits transparent
as-of quote sampling, and requests indicative pricing in the initial response
rather than deferring that question to a second round.

---

## Email — ready to send after owner authorization

**Subject:** Historical US equity/ETF quotes for six academic event windows —
suitability and indicative academic cost

---

Hello,

I am evaluating historical quote data for an academic study comparing ETF and
underlying-portfolio responses around six news announcements. Before purchasing
anything, I would appreciate confirmation of your product's suitability and an
indicative academic cost or minimum purchase requirement.

The equity/ETF request is provisionally about 530–535 distinct securities,
24 dates, 8,600 security-days, and 645,000 security-minutes. Approximately
53% of the requested intervals include time outside 09:30–16:00 US Eastern.
These are planning estimates, not a finalized security list, an exact quote
request, or an assumption about your billing method. Historical identifier
reconciliation is still being finalized.

The selected event and comparison dates are below. All times are US Eastern,
with the date-appropriate daylight-saving offset. The same clock window is
proposed for an event and its three listed comparison dates. Release-time
validation remains at displayed-minute precision; finer timing is not claimed
here.

| Event | Event date | Proposed window, US Eastern | Comparison dates |
|---|---|---|---|
| FOMC statement | 2021-09-22 | 13:00–14:15 EDT | 2021-09-17, 2021-09-20, 2021-09-21 |
| FOMC statement | 2022-01-26 | 13:00–14:15 EST | 2022-01-21, 2022-01-24, 2022-01-25 |
| Nasdaq earnings | 2022-04-20 | 06:00–07:15 EDT | 2022-04-14, 2022-04-18, 2022-04-19 |
| Emerson earnings | 2023-02-08 | 05:55–07:10 EST | 2023-02-03, 2023-02-06, 2023-02-07 |
| Essex earnings | 2022-10-26 | 15:15–16:30 EDT | 2022-10-21, 2022-10-24, 2022-10-25 |
| Globe Life earnings | 2021-07-21 | 15:15–16:30 EDT | 2021-07-16, 2021-07-19, 2021-07-20 |

The ETF universe is SPY, XLK, and XLF, with the relevant historical portfolio
requested for each selected event. The event issuers above are public
announcement references; no full constituent list or licensed portfolio weights
are attached.

Please address these five points:

**1. Historical dates and trading sessions.** Does your product cover US equities
and ETFs on these dates, including premarket observations from at least 05:55 ET
and aftermarket observations through 16:30 ET? Please distinguish historical
product availability from actual quote availability for individual securities. A
recent demonstration would establish format only, not the requested historical
coverage.

**2. Quote object and consolidation.** Please identify the exact dataset and
whether it provides an as-disseminated consolidated best bid/offer, a
vendor-reconstructed consolidated quote, or single-venue quotes. Does it provide
every quote update, or a clock-sampled bid/ask series at one second or finer?
Please explain extended-session consolidation and provide bid/ask size and
quote-condition/status fields where available. Trade-only bars and observations
sampled only when trades occur would not serve as substitutes for the required
quote path.

**3. Timestamps, carried observations, and initial state.** Can we recover the
actual underlying quote time, separately from a sampling time, and determine
quote age and whether a quote has been cancelled, replaced, or is otherwise
invalid? Please state timestamp precision and semantics. Transparent as-of
sampling is acceptable: we do not require every security to update every second,
but an old quote must not be re-stamped or represented as a fresh observation.
Can a short extract include the prevailing bid/ask state at its opening boundary,
or sufficient prior history to reconstruct that state? Please state how
one-sided, locked/crossed, and halted states are represented.

**4. Historical identifiers.** Which historical identifiers and crosswalks are
available? Our research identifiers include CUSIP and CRSP PERMNO, but we can
prepare a dated request in your supported identifier format. Please explain how
ticker changes and delisted securities are handled. For example, Globe Life's
July 2021 release concerns GL, while an upstream research record uses its former
TMK label. We are not asking you to certify coverage of an undisclosed
530-security list at this stage.

**5. Indicative cost and academic terms.** For a historical request of roughly
this scale, what is your pricing basis, minimum extract or subscription, and
indicative academic charge or range? Please distinguish optional estimates from a
firm quote and identify exchange, access, delivery, or other mandatory fees. What
academic-use, retention, publication-of-derived-results, and coauthor-access
conditions apply? If exact pricing requires a final identifier list or
cost-estimation job, please explain that step rather than assuming the present
estimates are final. This enquiry does not authorize a purchase, subscription,
paid estimation job, or billable account activation.

Historical portfolio composition is being handled separately; we do not assume
that a quote product provides ETF holdings or that an index or AP basket is
interchangeable with the fund's portfolio. If a schema example or field
dictionary is available, please provide it, without initiating a paid service.
Please state any material limitation directly.

Thank you.

---

## Internal provenance notes — not part of the email

These notes document the sources behind the claims in the email above. They are
for internal research records only and are not transmitted to any vendor.

**Counts and window derivation.** The approximate counts (530–535 securities,
24 dates, 8,600 security-days, 645,000 security-minutes, 53% extended session)
and the revised Emerson window (05:55–07:10 EST) come from committed output
`205479c` in this repository. The three comparison dates per event are preserved
from `MANIFEST.md` and `REQUEST_UNSENT.md`. These counts were not independently
reproduced in this chat session; they are accepted as the committed feasibility
result.

**Release-time wire sources — confirmed.** The displayed release minutes were
independently checked against company-issued press releases:

| event | confirmed time | source | URL |
|---|---|---|---|
| Nasdaq 2022-04-20 | 07:00 EDT | GlobeNewswire | https://www.globenewswire.com/news-release/2022/04/20/2425307/6948/en/Nasdaq-Reports-First-Quarter-2022-Results-Delivers-Strong-Growth-in-Solutions-Segments-Revenue.html |
| Emerson 2023-02-08 | 06:55 EST | PR Newswire | https://www.prnewswire.com/news-releases/emerson-reports-first-quarter-2023-results-updates-2023-outlook-301741483.html |
| Essex 2022-10-26 | 16:15 EDT | Business Wire (via Nasdaq) | https://www.nasdaq.com/press-release/essex-announces-third-quarter-2022-results-2022-10-26 |
| Globe Life 2021-07-21 | 16:15 EDT | PR Newswire | https://www.prnewswire.com/news-releases/globe-life-inc-reports-second-quarter-2021-results-301338894.html |

These wire confirmations establish minute-level release times from the company's
own distribution. They do not establish an exact first-public-dissemination
second or certify the SEC 8-K acceptance timestamp timezone conversion. The
EDGAR UTC interpretation is internally consistent with all session assignments
but has not been confirmed against SEC documentation.

**PERMNO crosswalk resolution (Category A unmapped lines).** The three Category A
securities identified in `MAPPING_OUTCOMES.md` were searched in CRSP DSF/MSF
for their historical PERMNOs. Results:

| security | CUSIP | resolved PERMNO | source |
|---|---|---|---|
| BlackRock Inc | 09290D10 | **87267** | crsp_msf_full.parquet |
| LabCorp Holdings | 50492210 | **12062** | crsp_msf_full.parquet |
| Federal Realty Investment Trust | 31374720 | **not found** | searched crsp_dsf + crsp_msf_full; REIT, possible CUSIP format mismatch |

Adding BLK (PERMNO 87267) and LH (PERMNO 12062) to the quote manifest repairs
the primary source of unmapped equity weight. FRT (0.02% weight, two snapshots)
remains unresolved and must be carried as an explicit exclusion if not resolved
before the quote request is submitted. Full before/after coverage numbers are
in `MAPPING_OUTCOMES.md`.

**XLK futures identification.** The XLK snapshot lines labelled "ES&P TE SIF
SP21" (2021-08-31) and "ES&P TE SIF MR22" (2021-12-31) are identified as CME
E-mini Technology Select Sector futures (CME root symbol XAK):

| label | contract | expiry | direction | units | economic exposure |
|---|---|---|---|---|---|
| ES&P TE SIF SP21 | XAK U1 (XAKU1) | September 2021 | LONG (cash-equitization) | ~67,100 | ~$107M (~0.23% TNA) |
| ES&P TE SIF MR22 | XAK H2 (XAKH2) | March 2022 | LONG (cash-equitization) | ~47,400 | ~$83M (~0.16% TNA) |

These positions must not be excluded from the economic exposure merely because
they lack a stock PERMNO. They represent cash-equitization overlay and carry
genuine beta exposure to the XLK basket. There is no equity quote to request for
these lines, but the ~0.16–0.23% weight is Category B (non-quotable) and must
be reported as an exclusion, not silently dropped from the basket return.

**Restrictions.** Full constituent lists and portfolio weights are derived from
licensed CRSP mutual-fund holdings and have not been cleared for third-party
disclosure. This enquiry transmits only estimated counts and window structure,
consistent with option 1 of §5.1 in `REQUEST_UNSENT.md`. No purchase, paid
trial, or billable account activation is authorized at this stage.
