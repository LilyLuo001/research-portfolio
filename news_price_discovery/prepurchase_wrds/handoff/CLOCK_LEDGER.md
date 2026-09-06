# Clock ledger — six measurement-validation events

Corrected record. Supersedes the clock table in `MANIFEST.md` §2 for the EMR
entry; all other entries are unchanged. Original MANIFEST.md is preserved.

The EMR correction is documented in §2 below. The SEC acceptance timestamps
are read as UTC throughout; that interpretation is consistent with all four
events' session assignments and is noted in `MANIFEST.md` §2 as requiring
confirmation against SEC documentation.

---

## 1. Full corrected clock table

| event | primary source | primary time (ET) | I/B/E/S `anntims` | SEC 8-K acceptance (UTC) | EST equivalent | discrepancy | precision | status |
|---|---|---|---|---|---|---|---|---|
| FOMC 2021-09-22 | FRB published statement schedule | 14:00:00 EDT | 14:00:00 | — | — | none | minute | **supported (5m, 15m); marginal (1m)** |
| FOMC 2022-01-26 | FRB published statement schedule | 14:00:00 EST | 14:00:00 | — | — | none | minute | **supported (5m, 15m); marginal (1m)** |
| NDAQ 2022-04-20 | I/B/E/S (primary; no earlier confirmed source) | 07:00:00 EDT | 07:00:00 | 2022-04-20T11:44:10Z | 07:44:10 EDT | 44m acceptance lag | minute | **supported (5m, 15m); marginal (1m)** |
| EMR 2023-02-08 | **Company-issued press release (wire)** | **06:55:00 EST** | 06:57:00 | 2023-02-08T11:54:31Z | **06:54:31 EST** | **2m vs I/B/E/S; 29s vs acceptance** | minute | **supported (5m, 15m); 1m marginal; 10s/30s unsupported** |
| ESS 2022-10-26 | I/B/E/S (primary; no earlier confirmed source) | 16:15:00 EDT | 16:15:00 | 2022-10-26T20:57:59Z | 16:57:59 EDT | 43m acceptance lag | minute | **supported (5m, 15m); marginal (1m)** |
| GL 2021-07-21 | I/B/E/S (primary; no earlier confirmed source) | 16:15:00 EDT | 16:15:00 | 2021-07-21T20:58:32Z | 16:58:32 EDT | 43m acceptance lag | minute | **supported (5m, 15m); marginal (1m)** |

---

## 2. The EMR correction

**What changed.** The primary event time for EMR 2023-02-08 is updated from
06:57 (I/B/E/S) to **06:55 ET** (company-issued press release). The I/B/E/S
value of 06:57 is retained in the ledger as a conflicting source; it is not
dropped.

**Sources in hand.**

| source | value | format | what it times |
|---|---|---|---|
| Company-issued press release (wire distribution) | 06:55:00 EST | minute | **first public release — the event time** |
| SEC 8-K acceptance timestamp | 2023-02-08T11:54:31Z = 06:54:31 EST | second | 8-K accepted by EDGAR; times the filing, not the wire |
| I/B/E/S `anntims` | 06:57:00 | minute | I/B/E/S data-vendor recording time |
| EDGAR exhibit body (EX-99.1, `a2023q1release_ex991.htm`) | "ST. LOUIS, February 8, 2023" | date only | press release dateline — no time in the exhibit HTML |

**Consistency.** The SEC acceptance at 06:54:31 EST is 29 seconds before the
company press-release time of 06:55. That ordering is consistent with standard
practice: companies typically file the 8-K within seconds of or simultaneously
with the wire distribution, and EDGAR sometimes accepts before the wire
timestamp rounds up. The two are therefore not in conflict; the acceptance
corroborates that the release occurred before 06:55, not after.

I/B/E/S records 06:57, two minutes after the company-issued time. A two-minute
recording lag is plausible for a data vendor monitoring the wire.

**Wire source locator.** The user-supplied 06:55 time originates from the
company-issued wire distribution. The Business Wire page for this release
returned an Akamai edge block and could not be independently read. The primary
source claim is accepted as provided; the source URL should be recorded when
the document is finalized.

**What this changes for the measurement.** Using 06:55 as T rather than 06:57:

- The 5-minute and 15-minute horizons are unaffected — the 2-minute shift is
  small relative to these windows.
- The 1-minute horizon (already marginal at minute-precision clock resolution)
  is more sensitive: at 06:55 the first full minute after release is
  06:56:00–06:57:00, which overlaps the I/B/E/S stamp. Any return computed at
  h=1m is therefore uncertain over a 2-minute band, not a 1-minute band, making
  this horizon doubly marginal for EMR specifically.
- The 10-second and 30-second horizons remain unsupported for the same
  reason as all other events: the release time is minute-precision at best.

**Baseline window implication.** With T=06:55, the event window opens at
T−5m = 06:50 and the baseline runs 05:55–06:50. The 06:50 window open is
demonstrably pre-release under both the press-release time (06:55) and the
I/B/E/S time (06:57). No ambiguity crosses into the event window.

---

## 3. Unresolved event-time claims

| event | what is unresolved |
|---|---|
| FOMC 2021-09-22 | No independent sub-minute evidence; minute precision accepted for 14:00:00 |
| FOMC 2022-01-26 | Same |
| NDAQ 2022-04-20 | No source earlier than I/B/E/S 07:00; press-release exhibit not yet read for a wire time |
| **EMR 2023-02-08** | **Wire source URL not confirmed; the 06:55 claim is accepted as user-provided. Business Wire page blocked.** |
| ESS 2022-10-26 | No source earlier than I/B/E/S 16:15; press-release exhibit not yet read for a wire time |
| GL 2021-07-21 | No source earlier than I/B/E/S 16:15; press-release exhibit not yet read for a wire time |

For NDAQ, ESS and GL: the EDGAR exhibit EX-99.1 for each was not read in this
session for a wire timestamp. Reading those three exhibits and comparing against
I/B/E/S is the same cheap non-vendor task applied here for EMR, and should be
done before finalizing T for any sub-5-minute measurement.

**The timezone interpretation for EDGAR acceptance times has not been confirmed
against SEC documentation.** The UTC reading is internally consistent with all
four events' session assignments, but this should be formally verified.
