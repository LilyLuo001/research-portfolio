# P1 continuation 09 — event-clock adjudication

Date: 2026-09-15

Decision: **HOLD_DATA**

Execution state: **STOPPED AT THE CORRECT EARLY-STOP BOUNDARY**

This checkpoint tests the remaining event-clock prerequisite for the frozen
RTH/RTH-60 pilot. It does not open response outcomes, estimate an effect, run
empirical power, select a new session, or order more market data.

## Result

The repaired W021 roster has 1,082 release keys. Their source display clock is
parseable, but the delivered `anndats`/`anntims` projection still lacks an
authoritative bridge for timezone, first-public meaning, precision and revision
handling. The source-safe projection therefore leaves every key's RTH and
RTH-60 status `UNKNOWN`.

A complete versioned XNYS calendar was then used for explicitly hypothetical
clock interpretations. Counts below require at least two analysts for each
release key.

| Hypothetical interpretation | High stocks with >=1 PRE and >=1 POST RTH-60 | Low stocks with >=1 PRE and >=1 POST RTH-60 | Necessary Stage-A support |
|---|---:|---:|---|
| Display clock is America/New_York | 0 | 0 | FAIL |
| Display clock is fixed UTC-05 | 0 | 0 | FAIL |
| Display clock is UTC | 7 | 7 | PASS_NECESSARY_ONLY |
| Eastern; first-public time may be 0–60 minutes before receipt | 0 | 0 | FAIL |

Under the UTC hypothesis, 6 high and 7 low stocks also meet the stronger
illustrative threshold of at least 8 PRE and 4 POST keys. This does not certify
UTC or establish identification; it shows that the unresolved clock contract
is decision-relevant.

One bounded issuer/public-source rescue covered 24 boundary-sensitive keys.
It found only two directional scheduling statements and zero certified exact
first-public timestamps; all 24 remain unresolved. Conference-call or planned
release direction was not substituted for an actual release timestamp.

## Decision rule

- If the data owner/provider documents that the delivered display time is
  America/New_York (with sufficiently tight first-public semantics and
  uncertainty), the currently frozen RTH-only W021 comparison fails its
  necessary support gate. Reclassify that specification as **HOLD_DESIGN**;
  do not buy more quotes or run power to rescue it.
- If the data owner/provider documents that it is UTC and supplies adequate
  first-public/precision/revision semantics, continue to competing-conversion,
  common-calendar and control-support checks before opening quotes or running
  power.
- Until that bridge is documented, retain **HOLD_DATA**. The analysis may not
  choose the clock interpretation that happens to pass.

## Single next action

Obtain one authoritative, versioned statement covering the full frozen manifest
for the harvested `ibes.actu_epsus.anndats/anntims` records, specifying:
timezone/DST convention, whether the clock is first public release or vendor
receipt/activation, precision/rounding/imputation, and revision/correction
behavior. Apply that statement to the already frozen 1,082-key projection and
rerun this exact classification. No further quote purchase is justified before
that answer.

Details and evidence: [decision](artifacts/w021_clock_adjudication_20260915/DECISION.md).
