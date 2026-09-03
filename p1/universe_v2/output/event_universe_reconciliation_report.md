# P1 Fed/source-study event-universe reconciliation

**Audit date:** 2026-09-03  
**Decision state:** exposure construction paused; K2 suspended; no outcome data or
regression inspected.

## Bottom line

The concern was well founded, but the apparent `140+ -> 74` comparison mixes
different units. The Fed note does **not** use roughly 140 conversion events in
its empirical design. It reports an industry-wide aggregate of **125 mutual
funds converted by the end of 2024**, without publishing the underlying 125-row
list. Its empirical analysis uses exactly **four fund-to-ETF conversions**, all
completed by Dimensional on **2021-06-11** and all listed in Table 1.

All four published empirical events match P1 exactly. They are in P1's 156
completed conversions, in the 74 verified exact-day events, and in the 71
Gate0 PASS events (wave `W002`). The Fed note contains no additional publicly
identified exact conversion dates, so it supplies **zero upgrades** for P1's 82
completed but non-exact events.

This audit therefore does not trigger an event-master, wave, or Gate0 rebuild.
It also does **not** certify that P1 has captured the Fed's broader 125-event
descriptive universe. P1 has 95 completed predecessor funds dated through 2024,
leaving a 30-fund arithmetic gap to the Fed aggregate. Because the note does not
publish the 125 names, exact overlap and missing-event identities cannot be
measured. The 71-event set remains a valid, independently verified exact-date
subset, but it is **not declared the final global event universe**. Exposure and
K2 remain suspended pending access to the authors' or Morningstar/CRSP row-level
construction, or a separately completed universe audit.

## 1. What the source actually publishes

The official FEDS Note, Saglam and Tuzun (2025), makes two separate statements:

1. Introduction: 125 mutual funds had converted to ETFs as of end-2024. This is
   an aggregate descriptive count. The note gives no appendix, event table, or
   downloadable row-level replication file for those 125 funds.
2. Section 2 and Table 1: the empirical shock is four Dimensional conversions on
   June 11, 2021. Table 1 supplies the four predecessor names, successor ETF
   names, and assets. The analysis then measures stock ownership changes caused
   by this one conversion wave.

The accessible-data page contains descriptions/data for Figures 1 and 2 only.
Inspection of the official note's links found no CSV, XLSX, ZIP, appendix, or
supplementary event-list link. The only conversion-specific SEC link is the
Dimensional information statement covering the same four funds. That filing
said the reorganizations were expected on or about June 11, 2021; P1's four
successor filings independently state that each reorganization was consummated
after the close of business on June 11, 2021.

A read-only audit of the SCC mirror's final manifest and `meta/` schema
inventory found CRSP Mutual Funds tables (`fund_hdr`, `fund_hdr_hist`, names,
returns, TNA, holdings, and summaries), but no `wrds_mutualfund` schema or data
extract. The CRSP header schema has fund history, ETF, delisting, and merger
fields, but no explicit MF-to-ETF conversion flag or realized conversion-date
field. Consistent with the audit rule, those fields were not used to guess the
Fed list.

Source locators:

- FEDS Note: <https://www.federalreserve.gov/econres/notes/feds-notes/implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-conversions-20251119.html>
- Accessible data: <https://www.federalreserve.gov/econres/notes/feds-notes/implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-conversions-accessible-20251119.htm>
- SEC filing cited by the note: <https://www.sec.gov/Archives/edgar/data/1816125/000179420221000103/dimensionaletf497.htm>

## 2. Published empirical event crosswalk

| Fed event | Predecessor | Successor | Date | P1 event | P1 date evidence | 156 | 74 | Gate0 |
|---|---|---|---|---|---|---:|---:|---:|
| FED2025_T1_01 | DFA T.A. US Core Equity 2 | Dimensional US Core Equity 2 ETF | 2021-06-11 | P1E000016732 | 497K `0001193125-22-057393` | yes | yes | PASS |
| FED2025_T1_02 | DFA Tax-Managed US Equity | Dimensional US Equity ETF | 2021-06-11 | P1E000000972 | 497K `0001193125-22-057390` | yes | yes | PASS |
| FED2025_T1_03 | DFA Tax-Managed US Small Cap | Dimensional US Small Cap ETF | 2021-06-11 | P1E000000976 | 485BPOS `0001193125-22-057023` | yes | yes | PASS |
| FED2025_T1_04 | DFA Tax-Managed US Targeted Value | Dimensional US Targeted Value ETF | 2021-06-11 | P1E000000977 | 497K `0001193125-22-057394` | yes | yes | PASS |

The full machine-readable crosswalk preserves one row per predecessor fund. No
many-to-one relationship is collapsed.

## 3. Count reconciliation

| Object | Count | Unit | Interpretation |
|---|---:|---|---|
| Fed descriptive aggregate through 2024 | 125 | predecessor mutual funds | Published count; 121 rows are not publicly identified |
| Fed empirical event sample | 4 | predecessor mutual funds | Complete Table 1 list, all one date |
| P1 structural register | 247 | event candidates | Includes completed, future, unresolved, and cancelled rows through 2026 |
| P1 completed, all years | 156 | predecessor mutual funds | 74 Tier A + 82 Tier B |
| P1 completed through 2024 | 95 | predecessor mutual funds | Closest cutoff comparison to the Fed aggregate |
| P1 verified exact-day | 74 | predecessor mutual funds | Timing-eligible primary universe |
| P1 Gate0 PASS | 71 | predecessor mutual funds | Exact N-PORT PRE/POST filing coverage |
| P1 Gate0 PASS waves | 47 | conversion dates | Multiple funds on one date form one wave |
| Ownership-ready waves | 30 | waves | Positive, mapped U.S. common-stock exposure |

The public source permits four confirmed row-level matches. It does not permit
an exact statement that X of the aggregate 125 are in P1's 156, because 121
source identities are not published. The corresponding exact missing count is
also not identifiable. Under a same-unit/same-definition comparison, the
through-2024 arithmetic is `125 - 95 = 30`, but those 30 are not nameable from
the note and may also reflect a definition or dating difference.

`fed_source_event_universe.csv` therefore contains 125 rows without fabrication:
the four identified Table 1 events plus 121 rows explicitly marked
`unidentified_placeholder`. These placeholders preserve the published aggregate
denominator but are never assigned a guessed fund, date, sponsor, or P1 match.

## 4. Audit of the 82 completed non-exact P1 events

The excluded completed-event census reproduces exactly:

- 14 `proposed_exact_day_only`
- 57 `month_only`
- 9 `bounded_window`
- 2 `year_only`

Every row was checked against the public empirical list and the note's cited SEC
filing. None is one of the four Table 1 events. The broad 125 statement supplies
no names or dates, so it cannot upgrade any row. Result:

- source-study exact dates missed by P1 among published rows: **0**;
- excluded P1 events upgradeable from public Fed evidence: **0 of 82**.

This is a source-specific result. It does not convert the absence of a public
Fed date into proof that no exact SEC date exists elsewhere. The existing P1
SEC-recovery evidence and unresolved status remain unchanged row by row.

## 5. Why P1 has 74 timing-eligible events

P1's exact-day design needs a realized completion day. A proposed day can move,
a month-only termination date can misclassify the intraday event window, and a
bounded or year-only date cannot determine the treatment clock. Of the 156
completed conversions, 82 do not meet that evidentiary standard; only the 74
with a filing-supported realized day enter the primary timing universe.

That exclusion rule is economically and evidentially justified for an intraday
design. What is not yet justified is treating the 156 completed-event register
as demonstrably exhaustive relative to the Fed's unpublished 125-event
industry list. Exact-date validity and universe completeness are separate gates.

## 6. Required decisions

1. **How many completed conversions are actually in the source-study universe?**
   Four in the empirical event sample; 125 in the descriptive industry
   aggregate. The source does not publish a 125-row universe.
2. **How many are in P1's 156?** All four empirical events. For the aggregate
   125, four are confirmed and the other 121 are not row-identifiable; an exact
   overlap count cannot be claimed.
3. **Why only 74 timing-eligible?** The other 82 completed P1 events lack a
   filing-verified realized day: 14 proposed, 57 month, 9 bounded, and 2 year.
4. **Is the reduction justified?** Yes for exact-day identification. No claim of
   global source-universe completeness follows from that rule.
5. **Did the source contain exact dates P1 missed?** No among the publicly
   disclosed source rows. All four exact dates were already verified in P1.
6. **Does the 71-event Gate0 universe remain valid?** It remains internally
   valid as the current verified subset and does not require rebuilding from
   this evidence. It remains provisional, exposure construction stays paused,
   and K2 is not applied until the broader 125-event provenance gap is closed or
   explicitly accepted as an external-data limitation.

## 7. Deliverables and reproducibility

- `fed_source_event_universe.csv` — 125 aggregate units: four disclosed rows and
  121 transparent unidentified slots.
- `fed_to_p1_event_crosswalk.csv` — exact P1 reconciliation for the four
  disclosed rows; `UNKNOWN` rather than guessed matches for the other 121.
- `excluded_82_source_date_audit.csv` — one row for every completed non-exact P1
  event and the source-specific no-upgrade result.
- `event_universe_reconciliation_summary.csv` — machine-readable counts,
  statuses, units, and limitations.
- `audit_fed_source_universe.py` — deterministic generator with count and class
  assertions.

No event-master value, wave assignment, Gate0 result, exposure matrix, or
outcome file was changed by this audit.

The direct unblocker is a row-level author/replication extract (or the exact
Morningstar/other source table used to produce 125). If a live WRDS connection
later exposes `wrds_mutualfund`, its schema may be checked again, but only an
explicit conversion/reorganization field with a source date should be used;
fund-history inference alone is not an acceptable substitute.
