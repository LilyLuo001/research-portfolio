# P1-T1 Pass 1 (date-recovery) — Root Cause Audit + Pass 1b / Pass 3 execution

**Date:** 2026-07-19  **Worker:** deepseek-v4-pro (channel A)
**Run cost (deepseek today):** ¥3.68 = Pass 1 ¥0.824 + Pass 1b ¥0.509 + Pass 3 ¥2.343
**Status:** Pass 1 + Pass 1b + Pass 3 complete, re-assembled, contract PASS; **not
committed/pushed** (held for owner review, per instruction).

## Execution outcome (owner-approved "honest middle path", 2026-07-19)

Following the accepted audit, three actions were run locally: a schema update (add
`effective_date_approx` + `date_precision`, keep `effective_date` strict/verbatim-only),
**Pass 1b** (subsequent-filing harvest), and **Pass 3** (no_event re-categorization).

| metric | before | after |
|---|---|---|
| `events_merged.csv` conversions | 124 | **131** (+7, all verbatim dates from Pass 1b) |
| `held_back` | 102 | **92** |
| held rows now carrying approx timing | 0 | **26** (22 quarter, 4 pending) |
| Pass 3 no_event→event flips | — | **0** (all 195 re-confirmed no_event) |

**Bottom line:** the count moved **124 → 131**, entirely from Pass 1b recovering *verbatim*
effective dates in post-close filings — **not** from re-categorization. Pass 3's full-text
re-read of the 195 most-likely-mislabeled no_event filings flipped **zero** to event,
confirming the original categorization. The brief's "~225" target is **not reachable** by
these mechanisms; §8–§10 detail why and what (if anything) remains. See §8 (Pass 1b),
§9 (Pass 3), §10 (final stats).

## 0. Headline

Pass 1 did **not** move the conversion count. `events_merged.csv` = **124 before → 124 after**.
Its actual effect was narrower: it back-filled effective dates on **27** already-counted
conversions and trimmed `held_back` 109 → 102. The brief's projection ("124 → ~225 from
Pass 1 alone") was based on a wrong mechanism — date recovery annotates existing events, it
does not add new ones. Any lift toward ~225 must come from **Pass 3 re-categorization**, not
from this pass.

## 1. Denominator reconciliation (109 vs 80)

| quantity | value |
|---|---|
| spec rows (`P1-T1-daterecover.yaml`) | 109 |
| **unique IDs** (source_accession) | **80** (17 IDs duplicated → 29 dup rows) |
| answers returned | 80 (0 missing, 0 lost) |
| ISO date recovered | **27 / 80 (34%)** |
| undated (failed) | **53 / 80 (66%)** |

No answers were dropped by chunk-merge; the "missing 29" are duplicate IDs collapsing in the
answer dict. Minor inefficiency only (see §3, rec 2).

## 2. Root Cause Analysis of the 53 failures

Every one of the 53 undated items returned `effective_date: NA` **and** `date_basis: NA`.
Mapping to the requested taxonomy:

| Bucket | Count | Notes |
|---|---|---|
| **Missing Anchors** (no date pattern in source `.htm`) | **53 (100%)** | the only real bucket |
| Parsing Failures (spec-window logic couldn't handle format) | **0** | every window parsed; every answer was valid JSON |
| Low Confidence (ambiguous / threshold) | **0** | no ambiguous matches |
| Technical Errors (exceptions, ISO-regex over-rejection) | **0** | no non-ISO date was wrongly rejected — deepseek honestly returned NA |

**The root cause is a DATA gap, not a code gap.** deepseek-v4-pro correctly extracted every
date that was present. The 53 source filings are overwhelmingly **N-14 merger proxies and
pre-effective 497s filed *before* the conversion closed**, so they carry only a shareholder-
meeting date, a blank-bracket placeholder (`[___]`), or an approximate future quarter — never
a specific `YYYY-MM-DD`.

### Recoverability sub-split of the 53

| Sub-bucket | Count | Recoverable? | Why |
|---|---|---|---|
| **FUTURE_PENDING** — "expected Q4 2026 / Q1 2027", quarter still ahead of today | 4 | **No (yet)** | conversion hasn't occurred; no date exists anywhere |
| **COMPLETED_ELSEWHERE** — expected quarter now past | 9 | **Yes** | actual date is in a *later* filing not in the held set |
| **MEETING_ONLY** — N-14 proxy, only the meeting date | 13 | **Yes (if completed)** | closing date is post-meeting, in a later filing |
| **NO_DATE_other** — residual (20 N-14, 4×497, 2 N-14/A, 1 COVER; 9 blank-bracket) | 27 | **Partial** | mostly pre-close proxies; recoverable only if a completion filing exists + is harvested |

## 3. Spot check (cik / accession)

1. **cik 1683471 · acc 0000894189-21-009051 · N-14 · filed 2021-12-21** — "No specific closing
   date provided; only shareholder meeting date [March 4, 2022]." → *Meeting-only proxy.* The
   close post-dates the meeting; date lives in a later 497/485BPOS not in scope.
2. **cik 1587982 · acc 0001398344-22-024759 · 497 · filed 2022-12-20** — "Reorganization is
   expected to take effect in the first quarter of 2023." → *Completed-elsewhere.* Q1-2023 is
   past; the actual date is in the acquirer's post-effective amendment.
3. **cik 1005942 · acc 0001193125-26-239660 · 497K · filed 2026-05-26** — "anticipated … in or
   around the first quarter of 2027." → *Future-pending.* Conversion not yet occurred; no date
   can exist. Should be flagged `pending`, not `failed`.
4. **cik 1845809 · acc 0001193125-25-151504 · N-14 · filed 2025-06-27** — "will not commence
   operations until the closing date of the Merger"; "Approximate date of Proposed Offering: As
   soon as practicable." → *No-date proxy* with blank-bracket placeholders; structurally dateless.
5. **cik 1464413 · acc 0001464413-20-000186 · 497 · filed 2020-10-29** — "Supplement approves
   reorganization but does not specify an effective date." → *No-date*; needs the follow-on
   completion sticker.

## 4. Strategic recommendations

1. **Pass 2 and Pass 3 will recover NONE of these 53.** Pass 2 confirms the *target type*
   (open-end MF) on the recheck queue — a different question, no dates. Pass 3 re-categorizes
   the dropped *no_event* pool (MENTION / MF_TO_MF) — a different population. Neither reads the
   later filings that hold the missing dates. Do not expect date recovery from them.

2. **`build_daterecover_spec.py` does NOT need a parsing/window change** — it is not the failure
   point; the dates are absent from the filings it was given. (Minor cleanup only: **dedupe items
   by ID** — 109 rows / 80 unique IDs wasted ~26% of the calls answering the same ID twice.)

3. **The real fix is a new "later-filing" harvest + recovery mini-pass (Pass 1b)** for the
   ~22 (COMPLETED + MEETING) and the recoverable slice of NO_DATE_other: for each conversion
   whose expected quarter is now past, harvest the **acquirer/family's *subsequent* EDGAR
   filings** — 485BPOS post-effective amendment, 497 sticker, N-CEN, or the retrospective
   "successor to the X Fund as a result of a reorganization on `<date>`" statement — via
   `p1/fetch_edgar_filings.py` (acquirer CIK + post-meeting date range), then re-run date
   recovery over those. This is a **harvest-widening**, not a spec-logic edit.

4. **Reclassify the 4 FUTURE_PENDING** as `effective_date = NA, status = pending,
   expected_quarter = <Qx YYYY>` and remove them from the failure denominator — they are
   correctly not-yet-datable, not errors.

5. **Correct the funnel narrative:** report the true Pass 1 result (124 → 124 conversions; +27
   dates; held_back 109 → 102). Re-anchor the "→225" expectation on Pass 3, and treat date
   completeness as a separate, later remediation track.

## 5. Staleness verification (2026-07-19, owner-requested)

Tested whether the data gap was caused by stale/truncated local `.htm`. Re-fetched 3 random
`date_basis: NA` samples directly from EDGAR (same accession/primary-doc URL) and diffed against
the local copies; also pulled each accession's `index.json` to check sibling documents.

| # | acc | form | local vs EDGAR | date in doc? | verdict |
|---|---|---|---|---|---|
| 1 | 0001829126-24-006799 | 497 | **byte-identical** (md5 match) | none — only "Q4 2024" | genuine gap; quarter past → Pass 1b |
| 2 | 0001999371-25-020449 | N-14 | **byte-identical** | only `[●], 2026` placeholder (+ unrelated historical dates) | genuine gap; deepseek correctly ignored the false dates |
| 3 | 0001213900-25-015352 | N-14 | **byte-identical** | "Mar 21 2025" = **Rule 488 reg-effective**; "Mar 13 2025" = **voting record date**; conversion only as "Q2 2025" | deepseek **correctly** rejected both false anchors |

**Conclusions:**
- **Staleness REJECTED.** All 3 local files are byte-for-byte identical to EDGAR — the local
  harvest is complete and current. A full re-harvest of the *same* accessions would recover nothing.
- **Windowing REJECTED.** Sample 3's 9,551-char window *contained* all candidate dates; deepseek
  saw them and correctly distinguished the conversion date (only "Q2 2025") from the registration-
  effective (Rule 488) and record dates. Not a spec-window coverage problem.
- **deepseek-v4-pro precision VALIDATED.** It does not mistake the many other dates in these
  proxies (registration-effective, record, meeting, fund-inception) for the conversion date.

The data gap is real: these pre-close N-14/497 filings do not state a specific effective date.
Confirms the remediation path is **Pass 1b (subsequent-filing harvest)**, not a re-harvest.

## 6. Logic audit — is the rejector too rigid? (2026-07-19, owner-requested)

Tested whether NA is caused by over-rigid parsing dropping valid non-standard dates.

**The rejector, exactly:**
- *Layer A — extraction prompt* (`build_daterecover_spec.py` RULES): rule (2) **"month- or
  quarter-only → NA; vague → NA"**; rule (4) **"never supplement from memory."** Output must be
  `YYYY-MM-DD` or `NA`.
- *Layer B — merge gate* (`merge_daterecover.py:53`): accepts only `^\d{4}-\d{2}-\d{2}$`.

These are **integrity gates, not format bugs.** They do not reject validly-formatted specific
dates; they reject text that gives no specific day.

**Relaxed re-extraction test** (same deepseek-v4-pro, same date-context windows, prompt changed
to "give your best concrete date, never NA", self-reporting `verbatim_in_text` + `date_precision`):

| ID | strict | relaxed | `verbatim_in_text` | precision | how the day was produced |
|---|---|---|---|---|---|
| 0001829126-24-006799 | NA | 2024-12-31 | **false** | quarter | mapped "Q4 2024" → year-end |
| 0001999371-25-020449 | NA | 2026-03-31 | **false** | inferred | source is a blank `[●], 2026` placeholder |
| 0001013762-25-002918 | NA | 2025-06-30 | **false** | quarter | mapped "Q2 2025" → quarter-end |

**Finding:** softer logic drops NA to 0/3 — but **every recovered day is fabricated**
(`verbatim_in_text=false` in all three, by the model's own admission). No specific date exists in
these filings; the relaxed prompt manufactures one by mapping a quarter to its end (or, for the
`[●]` placeholder, inventing a quarter). Recording these as `effective_date` would inject
non-existent event dates — a direct violation of meta-rule 1 (LLM ≠ source of facts) and rule 4
(never guess-fill). **The strict rejector was correct; it is not throwing away data.**

**Constructive middle path (no fabrication):** the *approximate* timing IS real data. Rather than
overwrite `effective_date` with a guessed day, add separate fields:
`effective_date_approx = "2025-Q2"`, `date_precision = quarter|month|pending`, leaving
`effective_date = NA` reserved for verbatim specific days. This preserves quarter-level timing for
any panel/quarterly analysis without fabricating a day. Whether quarter resolution is usable is the
owner's call (an event study needs the exact day → still requires Pass 1b).

## 7. Suggested next step

Date precision has two honest routes, not mutually exclusive:
- **Pass 1b (later-filing harvest)** — recovers the *actual* specific dates for the ~22
  completed-but-undated conversions from their post-close filings. Needed for event-study precision.
- **Approx-field capture** — records `YYYY-Qn` for the quarter-only cases now, zero new fetching,
  no fabrication. Useful if quarter resolution suffices.

For the conversion-count lift, **Pass 3 (re-categorization)** remains the lever; Pass 2 (recheck)
is orthogonal. Await owner decision before any commit/push.

---

## 8. Pass 1b — subsequent-filing harvest (executed 2026-07-19, ¥0.509)

**Mechanism.** For every held conversion with no Pass-1 date (**69** at the conversion level),
query the EDGAR *submissions* API (`data.sec.gov`, free, no LLM) for the registrant's filings
made **after** the announcement, keep the forms that carry a *completed* date — 485BPOS, 497,
N-CEN, N-8F (deregistration of the merged-away fund), 24F-2NT — and re-extract the date from
those. Scripts: `pass1b_harvest.py` → `pass1b_spec.py` → `merge_pass1b.py`.

- Candidates found: **307** subsequent filings across 68 conversions (1 conversion had no
  subsequent target filing → future-pending); **259** primary docs downloaded to
  `p1/edgar_filings_1b/`.
- Extraction (deepseek-v4-pro, 52 conversion-items, strict prompt anchored on the target fund
  name because a 485BPOS/N-CEN covers a whole trust): **6 items → 7 verbatim ISO dates**
  (one N-14 covered two funds twice: BBH Large+Mid Cap; Guggenheim Strategy II + Ultra Short).

| fund | recovered effective_date | basis |
|---|---|---|
| Thrivent Core Small Cap Value Fund | 2025-11-14 | expected |
| BBH Select Series — Large Cap Fund | 2025-11-17 | retrospective |
| BBH Select Series — Mid Cap Fund | 2025-11-17 | retrospective |
| BlackRock Securitized Income Fund | 2026-01-23 | expected |
| Guggenheim Strategy Fund II | 2026-04-30 | expected |
| Guggenheim Ultra Short Income Fund | 2026-04-30 | expected |
| Calamos Timpani SMID Growth Fund | 2026-09-18 | expected |

All seven carry a verbatim evidence quote and are now in `events_merged.csv`.

**Approx-field capture (no fabrication).** For the 46 conversions still NA after Pass 1b (plus
the 1 no-subsequent case), a **deterministic** parse (no LLM) of the *original* filings extracts
verbatim quarter/month timing — but only when a conversion-timing phrase ("expected to occur /
take effect / close", "on or about", "reorganization is") immediately precedes the period, which
excludes fund-inception, performance-drawdown and distribution dates. Result → `approx_dates.json`:
**26** conversions annotated (**22** quarter-precision, **4** `pending` future quarters); **month
precision fell to 0** after the anchor filter removed noise; **21** had no parseable conversion
timing (genuinely dateless / blank-bracket proxies). These stay in `held_back` with
`effective_date = NA`; the approx fields are advisory only and never enter the study key.

**Schema.** `events_merged.csv` gains two optional columns (`effective_date_approx`,
`date_precision`); contract `strict_columns: false` so this is non-breaking (verified PASS,
13 cols). Merged (ISO-dated) rows always show `NA` in these columns — approx is held-only.

## 9. Pass 3 — full-text re-categorization (executed 2026-07-19, ¥2.343)

Re-read the whole filing text (not the original excerpt windows) with deepseek-v4-pro under the
frozen v2 STEP rules, for the **195** no_event filings most likely to hide a real MF→ETF
conversion (reasons `MENTION` + `recheck_noevent`). Scripts: `build_recat_spec.py` →
`merge_recat.py`.

**Result: 0 flipped no_event→event; all 195 re-confirmed no_event.** Refined reasons on re-read:
121 MENTION, **64 reclassified MENTION→MF_TO_MF** (genuine fund-to-fund mergers), 7 SHARECLASS,
3 ETF_TO_ETF. The re-read *validated* the original categorization — the dropped pool contains no
hidden conversions. The conversion count therefore gains **nothing** from Pass 3.

Not run: the **MF_TO_MF** pool (445 filings) is out-of-scope by definition (a mutual fund merging
into another mutual fund is not a MF→ETF conversion; re-reading cannot change that structural
fact — indeed 64 MENTION items were just reclassified *into* MF_TO_MF). A confirmatory sweep is
available (`build_recat_spec.py --reasons MF_TO_MF`, ~¥5-6) but is expected to flip ≈0; left to
owner discretion rather than spent unprompted.

## 10. Final stats

| quantity | value |
|---|---|
| **conversions in `events_merged.csv`** | **131** (was 124; +7 via Pass 1b verbatim dates) |
| recovered verbatim dates total | 27 (Pass 1) + 6 items/7 rows (Pass 1b) |
| held conversions with approx timing | 26 (22 quarter, 4 pending) |
| held conversions with no date/approx | 66 (of 92 held; genuinely dateless pre-close proxies) |
| Pass 3 re-categorization flips | 0 / 195 |
| deepseek spend today | ¥3.68 (well under the ¥40 daily cap; no cap override used) |

**Honest conclusion on the "~225" target.** It is **not reachable** from these passes. Date
recovery (Pass 1/1b) *annotates* existing events and moved the count only because 7 conversions
had no resolvable date at all until their post-close filings were harvested. Re-categorization
(Pass 3) found **zero** mislabeled conversions in the highest-yield pool. **131 is the robust,
fully source-backed conversion count.** The gap to 225 in the original brief reflects a wrong
mechanism assumption, not recoverable data in the current harvest.

**New/changed files (all local, uncommitted):** `p1/events_merged.csv`, `p1/t1_events_final.json`
(Pass 3 provenance stamps), `p1/t1_arb/{recovered_dates,approx_dates,pass1b_candidates}.json`,
`p1/t1_arb/{assemble,pass1b_harvest,pass1b_spec,merge_pass1b}.py`, `p1/edgar_filings_1b/` (259
docs), `ops/l1/P1-T1-{pass1b,recat}.yaml`, `ops/l1/out/P1-T1-{pass1b,recat}.json`,
`p1/t1_arb/{arb_report,t1_full_audit.*}`.
