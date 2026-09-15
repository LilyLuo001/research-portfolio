# P1 current-data Gate 1 check — 2026-09-15

**Decision: HOLD_DATA + HOLD_DESIGN. Gate 1 is NOT PASSED.** This is not a finding of inadequate statistical power, nor a scientific NO_GO for all MF-to-ETF designs.

The currently supplied acquisition package does not literally define a numbered “Gate 1.” This report explicitly interprets the request as the post-download **measurement/data-readiness gate** in `evaluation_20260914/design/SUPPLEMENTAL_PULL_PLAN.md`, lines 56–59. It does not revive or certify the invalidated legacy exposure Gate 0/1. The user authorized checking current data and conditionally planning the pilot; no headline effect, empirical power simulation, new purchase, commit or push was run.

## What was actually checked

Connected to SCC and audited all 5,548 planned grouped jobs. For each downloaded file, checked existence, recorded byte size, DBN header decoding, dataset/schema/start/end/requested-symbol equality, and symbol-to-instrument mapping at the request's UTC start date. This is not a full-interval identity or endpoint check. Only metadata headers were decoded; no market-data records or POST response values were decoded. A local join then checked the actual 6,816 stock/SPY request legs and recomputed current source-metadata support. Existing local metadata CSV containers were hashed and parsed before column projection; some also contain previously computed liquidity/ownership columns, which were not analyzed or returned by the census. No raw EPS, forecast, quote, price or return source was opened.

| Check | Measured result | Meaning |
|---|---:|---|
| Selected jobs | 5,544 / 5,544 present, size matched, header contract matched | Selected acquisition is structurally accounted for |
| Original planned jobs | 5,544 / 5,548 downloaded | Four quote-query failures remain excluded, not silently complete |
| Requested job-symbol instances, all four feeds | 18,387 mapped; 191 NOT_FOUND; 14 UNKNOWN / 18,592 | Mapping counts, not live-quote counts |
| Core XNAS logical request legs | 6,766 / 6,816 header/mapping supported | 50 unresolved logical legs |
| Associations with all eight core request legs mapped | 839 / 852 | Structural prerequisite only; eight request legs are NOT six research horizons |
| Acquisition population | 71 PERMNOs, 71 stock-wave units, 5 waves | Acquisition union, not certified analysis sample |
| PRE / POST associations | 568 / 284 | 852 stock-period associations, not certified economic events |
| Source date-valid security mappings | 852 / 852 | CRSP/IBES mapping success does not guarantee Databento symbol resolution |
| One parseable announcement-time string | 852 / 852 | Timezone and publication-time precision remain uncertified |
| Announcement dates observed as sessions | 851 / 852 | Does not classify release session or RTH-60 |
| At least two analysts in the acquisition envelope | 659 / 852 | SUE compatibility/construction not certified |
| Compustat date cross-check | 828 unique, 24 missing; 809 agree with IBES | 19 unique dates disagree; do not silently resolve them |
| Corporate-action metadata | 10 distribution-flagged associations | Flags require endpoint adjustment policy |
| Holdings/denominator dates before recorded cutoff | 71 / 71 each | Date-order check passes; split basis remains provisional in every row |
| Final analysis eligibility | 71 / 71 NOT_CERTIFIED | No automatic promotion of retrieval/acquisition roster |

PRE dates are before the recorded announcement cutoff for all 568 PRE associations. All 284 POST dates meet their recorded 20-session threshold; this checks the saved threshold, not independently its exchange-calendar derivation. The 852 PERMNO/release-date keys are distinct, with 417 distinct announcement dates and no stock reused across waves in this union. This is not certification of economic-event deduplication, sponsor independence or effective sample size.

## Exact acquisition gaps

- All **191 NOT_FOUND** job-symbol instances are `CRD`: XNAS 48, XNYS 48, BATS 48, ARCX 47. This affects all 12 acquired CRD stock-period associations. Historical share-class symbology needs verification; never guess a suffix or substitute current ticker. ARCX has one additional unknown CRD instance in an excluded job.
- Core job `COREJOB_00366`, GDEN/SPY, 2021-03-11 date-wide slice: excluded after a quote `SSLError`. This affects one further association and two logical legs.
- Alternative jobs `ALTJOB_00186`, `ALTJOB_01420`, `ALTJOB_01748` remain excluded after SSL/proxy quote/count errors. These are transport/query failures, not demonstrated historical data absence.
- The three previously interrupted download jobs **are recovered**: `ALTJOB_00372`, `COREJOB_00623`, `COREJOB_00758`. They pass this header/size check. They are not the four outstanding quote exclusions.

See `core_mapping_gap_locators.csv` for exact affected associations/legs and `unresolved_symbol_summary.csv` for feed-level gaps. The large number of earlier warnings must not be treated as a missing-symbol count: many are ResourceWarning/unclosed-file notices. The direct header evidence above supersedes warning-based inference.

## Why measurement Gate 1 cannot pass

The existing measurement gate requires correctly parsed direct BBO fields, live two-sided **stock and SPY** support at 5m/15m/30m/60m/close/+1d-close, explicit initial-unknown/withdrawn/invalid states, and source sensitivity. No new enlarged-sample endpoint-quality result exists from this header audit. Unchanged live quotes must be carried as states, not treated as missing. Four single-venue feeds do not automatically become SIP NBBO.

The current manifest explicitly uses date-wide acquisition because `ANNTIMS` timezone is unverified. Parseability cannot certify a release instant, session or five-minute endpoint. It would be invalid to assume ET/UTC or use price movement to pick a clock. Thus RTH, RTH-60 and six-horizon common-mask counts remain **UNKNOWN**, not zero. This is a substantive missing verification, not a need to repeat the old exposure run.

User-disabled full DBN hashing was not restarted. Header/size success does not prove complete body decoding or checksum integrity. Hashes in receipts cover small control/code files only. The absence of full-file hashes is disclosed; it is not the scientific reason for HOLD.

## Separate design warning

Recomputed full-support-pool counts under the **proposed, unsigned** competing-conversion exclusion and all-12-events/two-analyst rule:

| Wave | HIGH | LOW |
|---|---:|---:|
| W002 | 10 | 165 |
| W013 | 0 | 0 |
| W016 (stress) | 2 | 1 |
| W021 | 0 | 0 |
| W025 | 2 | 2 |

These are full-pool support counts, not the acquired count or approved final population. The selected 15-stock-wave clean/analyst acquisition subset is capped by the intended up-to-four-per-tier selection; **15 is not the total full-pool eligible population**. W016 lacks two low stocks; W013/W021 are empty under this proposed exclusion. The original four-main-wave design therefore does not pass its stated design gate under that rule. Relaxing exclusions or adding W016 to the main estimand would be a visible scientific amendment, not a data-repair shortcut.

## One concrete next action

Execute one **outcome-blind clock-and-symbol repair packet** on the existing 71-stock/852-association manifest: verify historical CRD class identity, obtain authoritative `ANNTIMS` semantics and issuer release-time evidence (retain unknowns), and freeze release-time uncertainty plus historical-session rules. That packet must identify the exact supported event set before the SCC custodian computes six-horizon stock/SPY eligibility masks from already acquired data. Re-quote only the four named transport-failed jobs if needed; any newly charged repair must stay within separately verified remaining authority/balance. No broad re-download or new research population is warranted now.

`CONDITIONAL_PILOT_PLAN.md` specifies the staged identification/power work and economical agent routing. It is prepared, not launched past the failed gate. Independent bounded verification is in `REVIEW.md`; machine evidence is in `header_audit_receipt.json` and `readiness_receipt.json`.
