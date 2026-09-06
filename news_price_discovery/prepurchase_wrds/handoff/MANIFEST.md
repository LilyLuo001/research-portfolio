# Six-event measurement-validation manifest, with clock and weight evidence

Selected by the rule frozen in `SELECTION_RULE.md`, which was committed
(`30dc8e6`) before the selection program (`6d6d56b`) existed. The rule is
deterministic: there is no seed and no sampling step, so every eligible
candidate has selection probability 0 or 1, and the ordering is the salted
SHA-256 tie-breaker recorded in that file. Re-running `src/s8_01_select_six.py`
must reproduce these six keys and ranks exactly.

**All six slots filled. No category came up short**, so nothing was substituted
and nothing is reported missing.

These six events test whether the measurement can be **built**. They are not a
powered test of the research question, and a null or opposite-sign result on
them would not be a technical failure.

---

## 1. The six events

| slot | event date | entity | ticker (IBES) | PERMNO | CUSIP | ETF and basket | release clock (ET) | rank prefix |
|---|---|---|---|---|---|---|---|---|
| FOMC | 2021-09-22 | FOMC statement + SEP + press conference | — | — | — | SPY, XLK, XLF (all three) | 14:00:00 | `68b55eee` |
| FOMC | 2022-01-26 | FOMC statement + press conference, no SEP | — | — | — | SPY, XLK, XLF (all three) | 14:00:00 | `3d3aedb4` |
| BMO | 2022-04-20 | Nasdaq, Inc. | NDAQ | 90601 | 63110310 | XLF | 07:00:00 | `03e73494` |
| BMO | 2023-02-08 | Emerson Electric Co. | EMR | 22103 | 29101110 | SPY | 06:57:00 | `05818d0d` |
| AMC | 2022-10-26 | Essex Property Trust, Inc. | ESS | 80681 | 29717810 | SPY | 16:15:00 | `00fbc56a` |
| AMC | 2021-07-21 | Globe Life Inc. | TMK | 62308 | 37959E10 | XLF | 16:15:00 | `3deb7750` |

Both FOMC events are scheduled meetings on full NYSE sessions in different
calendar years. The four earnings events span four distinct firms, four distinct
years, and two ETFs, with no firm repeated.

**Symbology warning, live in this manifest.** Globe Life carries I/B/E/S ticker
**TMK** (Torchmark) but had already traded as **GL** for roughly two years by
the 2021-07-21 event date. A vendor request keyed on `TMK` for that date will
return the wrong instrument or nothing. Every identifier in the table above must
be resolved **as of the event date**, not as of today; this is exactly the
historical-symbology handling the request in `REQUEST_UNSENT.md` asks the
provider to confirm.

---

## 2. Clock evidence — validated per event, not extrapolated

The twelve 2023 controls that resolved the archive-wide `anntims` timezone are
**not** carried over to these events. Each earnings release was checked
individually against a first-public-release filing.

| event | primary time (ET) | primary source | I/B/E/S `anntims` | SEC 8-K acceptance | source locator | items |
|---|---|---|---|---|---|---|
| NDAQ 2022-04-20 | 07:00:00 EDT | I/B/E/S (no earlier confirmed source) | 07:00:00 | 2022-04-20T11:44:10Z | `sec.gov/Archives/edgar/data/1120193/000119312522110289/d336569d8k.htm` | 2.02, 7.01, 8.01, 9.01 |
| **EMR 2023-02-08** | **06:55:00 EST** | **Company press release (wire) — see CLOCK_LEDGER.md §2** | 06:57:00 | 2023-02-08T11:54:31Z | `sec.gov/Archives/edgar/data/32604/000003260423000007/emr-20230208.htm` | 2.02, 9.01 |
| ESS 2022-10-26 | 16:15:00 EDT | I/B/E/S (no earlier confirmed source) | 16:15:00 | 2022-10-26T20:57:59Z | `sec.gov/Archives/edgar/data/920522/000114036122038510/brhc10043188_8k.htm` | 2.02, 9.01 |
| GL 2021-07-21 | 16:15:00 EDT | I/B/E/S (no earlier confirmed source) | 16:15:00 | 2021-07-21T20:58:32Z | `sec.gov/Archives/edgar/data/320335/000032033521000038/gl-20210721.htm` | 2.02, 9.01 |

**EMR timing discrepancy.** The company-issued press release (wire distribution)
carries 06:55 ET; I/B/E/S records 06:57 — a 2-minute gap. The SEC 8-K
acceptance at 06:54:31 EST (2023-02-08T11:54:31Z) is 29 seconds before the
press release time and is consistent with it. The primary event time is updated
to 06:55; the I/B/E/S value is retained. Detailed source analysis and
measurement consequences are in `CLOCK_LEDGER.md`. The EDGAR exhibit body
(EX-99.1) carries only "ST. LOUIS, February 8, 2023" without a time; the
06:55 source is the wire distribution, whose URL was not independently confirmed
in this session (Business Wire returned an edge block). The 1-minute horizon is
doubly marginal for EMR: the 2-minute source discrepancy spans the entire
horizon. **Do not infer the timezone from proximity to the I/B/E/S time or to
other earnings release times; the 06:55 is a separately sourced claim.**

Every one carries **Item 2.02, Results of Operations and Financial Condition** —
i.e. each is an earnings release, not a conference call, not a guidance update,
and not an unrelated 8-K.

**Timezone and DST interpretation.** US Eastern observed DST from 2021-03-14 to
2021-11-07, 2022-03-13 to 2022-11-06, and 2023-03-12 to 2023-11-05. So
2021-07-21, 2021-09-22, 2022-04-20 and 2022-10-26 are **EDT (UTC−4)**, and
2022-01-26 and 2023-02-08 are **EST (UTC−5)**.

| event | release, local ET | UTC | precision |
|---|---|---|---|
| FOMC 2021-09-22 | 14:00:00 EDT | 18:00:00Z | minute |
| FOMC 2022-01-26 | 14:00:00 EST | 19:00:00Z | minute |
| NDAQ 2022-04-20 | 07:00:00 EDT | 11:00:00Z | minute |
| EMR 2023-02-08 | **06:55:00 EST** (company press release; I/B/E/S: 06:57) | **11:55:00Z** | minute |
| ESS 2022-10-26 | 16:15:00 EDT | 20:15:00Z | minute |
| GL 2021-07-21 | 16:15:00 EDT | 20:15:00Z | minute |

**Two limits on this evidence, both binding.**

*First*, the EDGAR timestamps are read as **UTC**. That is the only reading under
which all four are simultaneously consistent with their assigned sessions and
with the I/B/E/S stamps — under an Eastern reading, EMR's earnings 8-K would be
accepted at 11:54 a.m. against a 06:57 release, and ESS's at 8:58 p.m. This
interpretation should be confirmed against SEC documentation before the
timestamps are used as anchors rather than as corroboration.

*Second, and more important*: an 8-K **acceptance** time is when the filing was
accepted, not when the newswire carried the release. NDAQ's filing lands 44
minutes after its I/B/E/S stamp; ESS's and GL's land about 43 minutes after
theirs. The two sources agree on the **session** for all four events, which is
what the selection rule required. They do **not** pin the release instant.

**Achieved clock resolution is therefore one minute**, set by `anntims`. This
directly gates the estimand: see `ESTIMAND.md`. Horizons finer than one minute
are marked unsupported until a wire-level timestamp is obtained.

**Session status.** All six event dates are full NYSE sessions — none is a
weekend, an exchange holiday, or a 13:00 early close, all verified against the
CRSP daily market index (2,768 session dates) and the published early-close
list. No release is routed from a non-trading day onto a later session, so no
event in this manifest is a weekend release relabelled as an immediate
release-time response. The two FOMC releases fall inside regular hours; the four
earnings releases fall outside them, which is the whole reason extended-session
coverage is the binding product requirement.

---

## 3. Weight evidence and complete constituent sets

Complete baskets throughout. An announcer-plus-ETF extract cannot produce the
ETF-minus-portfolio difference that is the registered outcome, so the full
constituent set of the governing snapshot is carried for every event.

The governing snapshot is the latest one **demonstrably available** before the
event — `eff_dt` strictly earlier than the event date, not merely `report_dt` —
subject to the registered 120-day age limit. Amendment cells are folded into
their report date, as established in the feasibility exercise.

| event | ETF | `report_dt` (economic) | `avail_dt` (`eff_dt`, availability) | age | lines | mapped PERMNOs | equity mapped | cash | **missing mass** | filed sum |
|---|---|---|---|---|---|---|---|---|---|---|
| FOMC 2021-09-22 | SPY | 2021-08-31 | 2021-09-07 | 22d | 508 | 504 | 99.42% | 0.12% | **0.53%** | 100.07% |
| FOMC 2021-09-22 | XLK | 2021-08-31 | 2021-09-07 | 22d | 77 | 73 | 99.72% | 0.18% | **0.09%** | 99.99% |
| FOMC 2021-09-22 | XLF | 2021-08-31 | 2021-09-07 | 22d | 67 | 64 | 96.68% | 0.09% | **3.21%** | 99.98% |
| FOMC 2022-01-26 | SPY | 2021-12-31 | 2022-01-24 | 26d | 507 | 504 | 99.72% | 0.27% | **0.40%** | 100.39% |
| FOMC 2022-01-26 | XLK | 2021-12-31 | 2022-01-24 | 26d | 79 | 76 | 99.82% | 0.13% | **0.16%** | 100.11% |
| FOMC 2022-01-26 | XLF | 2021-12-31 | 2022-01-24 | 26d | 68 | 66 | 96.76% | 0.14% | **3.03%** | 99.93% |
| NDAQ 2022-04-20 | XLF | 2022-03-31 | 2022-04-07 | 20d | 69 | 66 | 97.22% | 0.16% | **2.56%** | 99.94% |
| EMR 2023-02-08 | SPY | 2023-01-31 | 2023-02-07 | 8d | 505 | 501 | 99.46% | 0.05% | **0.42%** | 99.93% |
| ESS 2022-10-26 | SPY | 2022-09-30 | 2022-10-07 | 26d | 507 | 502 | 99.56% | 0.41% | **0.36%** | 100.33% |
| GL 2021-07-21 | XLF | 2021-06-30 | 2021-07-07 | 21d | 67 | 64 | 96.78% | 0.16% | **3.08%** | 100.02% |

**Provenance and its limits.** These are CRSP mutual-fund holdings for the three
fund `crsp_portno` values (SPY 1021980, XLF 1026006, XLK 1026008), filed
monthly. `report_dt` is the economic as-of date; `eff_dt` is a **date-level**
availability proxy and is never read as an intraday timestamp. Snapshot ages at
these six events run 8–26 days, all inside the registered limit.

**Retrospective reconstruction is not an investor-known information set.** The
weight vector used here is what a researcher can rebuild after the fact from
filed holdings. It is not what a market participant knew at 16:15 on the event
day. Both labels are preserved and they are not interchangeable. No weight is
backfilled from a later filing and no snapshot is interpolated.

**Unmapped lines — categorized in `MAPPING_OUTCOMES.md`.** XLF carries roughly
**2.6–3.2%** of TNA in lines that do not map to a CRSP PERMNO, in every
snapshot governing a selected event. SPY carries 0.36–0.53% and XLK 0.09–0.16%.
These lines divide into two distinct categories:

- **Category A — known equity, PERMNO crosswalk absent** (dominant): BlackRock
  Inc (CUSIP 09290D10) accounts for 2.56–3.12% in every XLF snapshot and
  0.28–0.35% in SPY. LabCorp Holdings (50492210, 0.06–0.08% SPY) and Federal
  Realty Investment Trust (31374720, 0.02% SPY) also fall here. These are
  identifiable, exchange-traded equities whose returns are observable. The gap
  is in the MFDB-to-DSF PERMNO crosswalk, not in the securities' observability.
  Adding these three securities to the quote manifest by CUSIP resolves most of
  the unmapped mass. **This weight is not a return bound.**

- **Category B — non-equity / non-quotable** (small): balance-sheet netting
  entries labelled "OTHER ASSETS" (0–0.10%) and apparent futures or
  cash-equitization instruments in XLK labelled "ES&P TE SIF SP21/MR22"
  (0.16–0.23%). These carry no CUSIP and have no equity return to compute.
  They are the only lines for which "return unknown" is literally correct.

The covered sleeve is reported as a sleeve and is never renormalised to 100%.
Category A lines are a crosswalk gap — a gap in the **automated pipeline**,
not in the quote data or in the securities' existence. Category B lines are a
genuine exclusion; their weight (at most 0.23% in XLK) is the only portion
that propagates directly into basket-return uncertainty with no remedy from
additional quote data.

**Cash and non-equity.** Cash and money-market lines run 0.05–0.41% of TNA and
are identified by name pattern, held separately, and excluded from the equity
constituent request. They are not quote-bearing instruments and are not part of
the quote manifest.

**Corporate actions**, detected as a change in CRSP `cfacpr` or `cfacshr` within
five sessions either side of each event date:

| event date | constituents checked | with an action | which |
|---|---|---|---|
| 2021-07-21 | 525 | 1 | NVIDIA (PERMNO 86580) |
| 2021-09-22 | 525 | 1 | Raymond James Financial (69649) |
| 2022-01-26 | 524 | 0 | — |
| 2022-04-20 | 522 | 0 | — |
| 2022-10-26 | 518 | 0 | — |
| 2023-02-08 | 517 | 1 | PACCAR (60506) |

Three events each contain exactly one constituent whose price basis changes
inside the window. Quotes for those names must be requested on the **as-traded**
basis with the adjustment factor supplied separately, or the basket return will
carry a spurious jump. This is flagged in the product request.

---

## 4. Quote windows

Windows are defined relative to the release clock **T**, in event-local ET:

- **baseline** `[T − 60m, T − 5m]`
- **event** `[T − 5m, T + 15m]`
- **matched control** the same two clock windows on the three nearest prior NYSE
  sessions that are not themselves event dates in this manifest

Baseline and event windows are contiguous, so after the union they form one
75-minute interval per security-day. Overlaps are counted once; nothing is
purchased twice.

| event | dates (3 control + 1 event) | merged window, ET | extended session |
|---|---|---|---|
| FOMC 2021-09-22 | 09-17, 09-20, 09-21, **09-22** | 13:00 – 14:15 | no |
| FOMC 2022-01-26 | 01-21, 01-24, 01-25, **01-26** | 13:00 – 14:15 | no |
| NDAQ 2022-04-20 | 04-14, 04-18, 04-19, **04-20** | 06:00 – 07:15 | yes |
| EMR 2023-02-08 | 02-03, 02-06, 02-07, **02-08** | 05:57 – 07:12 | yes |
| ESS 2022-10-26 | 10-21, 10-24, 10-25, **10-26** | 15:15 – 16:30 | yes (crosses the 16:00 close) |
| GL 2021-07-21 | 07-16, 07-19, 07-20, **07-21** | 15:15 – 16:30 | yes (crosses the 16:00 close) |

**Totals after deduplication and overlap merge:**

| quantity | value |
|---|---|
| raw security-window rows | 19,440 |
| **merged intervals (what would be purchased)** | **8,604** |
| distinct securities | 532 |
| distinct dates | 24 |
| security-days | 8,604 |
| intervals needing extended-hours coverage | 4,548 (52.9%) |
| total quote-minutes requested | 645,300 |

By role, before the cross-event merge: SPY-basket events request ~500 constituents
each, XLF events ~65, and the two FOMC events request the union of all three
baskets (504 distinct securities, since XLF and XLK are largely subsets of SPY).
The announcing stock and the ETF itself are requested on the same windows.

For scale: this is **8,604 security-days against 49,863** in the full
feasibility manifest — about **17%** of it, and the reduction comes from cutting
the event count from 72 to 6, not from thinning any basket.

---

## 5. Machine-readable files

In this directory (aggregates only):

| file | contents |
|---|---|
| `s8_six_events.csv` | the six events with keys, ranks, clocks, snapshot pointers |
| `s8_coverage.csv` | per event-ETF weight provenance and coverage |
| `s8_constituent_counts.csv` | constituent counts and summed weight per event-ETF |
| `s8_windows_summary.csv` | interval, security, date and quote-minute counts by event and role |
| `s8_corp_actions.csv` | corporate-action scan results |

Held privately on SCC under `$PPW_WORK/out`, **not** exported to the repository:

| file | why it stays |
|---|---|
| `s8_constituents.parquet` | the actual per-security holdings and weights — a licensed CRSP holdings extract, not an aggregate |
| `s8_windows.parquet` | the full 8,604-row interval list, keyed to those constituents |

The complete constituent lists must be transmitted to a provider to obtain a
quotation. That is a disclosure of licensed holdings data to a third party and
requires a licence check before it happens; it is named as a gating step in
`REQUEST_UNSENT.md` rather than assumed.
