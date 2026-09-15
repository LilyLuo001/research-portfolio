# WRDS/LSEG clock-authority ledger

Scope: ibes.actu_epsus anndats and anntims only. No raw rows, financial values, prices, returns, quotes, or outcomes were read.

| Question | Evidence | Finding |
|---|---|---|
| Timezone and DST | Local archival finding: [CLOCK_EVIDENCE_V2.md](/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot/gate1_20260915/followup/clock_sources_v2/CLOCK_EVIDENCE_V2.md:7) records that the 2013 manufacturer Detail History guide says timestamps use season-dependent Eastern/daylight time. LSEG’s developer community separately says platform/API timestamps can differ and offers an origtimezone attribute for a different API field. [LSEG discussion](https://community.developers.lseg.com/discussion/78942) | No direct authority bridges the 2013 direct-delivery convention to the archived WRDS actu_epsus fields over the full frozen manifest coverage. |
| Announcement vs vendor activation/receipt | The local archival finding distinguishes announcement and activation time, and explicitly warns against replacing anntims with activation time. [CLOCK_EVIDENCE_V2.md](/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot/gate1_20260915/followup/clock_sources_v2/CLOCK_EVIDENCE_V2.md:7) | No provider source establishes that anndats/anntims is first-public dissemination rather than a vendor-recorded announcement attribute. |
| Precision, rounding, imputation | The existing archive states neither guide guarantees a first-public clock, seconds-level bound, or rounding/imputation rule. [CLOCK_EVIDENCE_V2.md](/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot/gate1_20260915/followup/clock_sources_v2/CLOCK_EVIDENCE_V2.md:15) | No decisive authority found. Minute display cannot be promoted to a five-minute eligibility clock. |
| Revision/correction | LSEG describes history products as versioned/history data and highlights revised estimates, but does not define correction behavior for these WRDS actuals fields. [LSEG I/B/E/S Estimates](https://www.lseg.com/en/data-analytics/financial-data/company-data/ibes-estimates) | No source-specific correction/revision semantics found for actu_epsus anndats/anntims. |

## Result

**NO_DECISIVE_WRDS_LSEG_BRIDGE_FOUND.** The existing manufacturer manual is relevant documentary context, not a certification for the third-party WRDS historical delivery. Clock/session classification therefore remains `UNKNOWN`.

## Four-question provider inquiry

1. For WRDS `ibes.actu_epsus` over the full frozen manifest coverage, do `anndats` and `anntims` preserve the I/B/E/S direct-delivery timezone convention, including season-dependent Eastern daylight time? If not, state the timezone and DST rule.
2. What operational event does anndats/anntims represent for actuals: issuer’s first public release, a source-document report time, I/B/E/S collection time, vendor activation/receipt, or another event?
3. What are the fields’ resolution and uncertainty rules: seconds retention, minute rounding/truncation, default/imputed times, and treatment of missing or midnight times?
4. When actuals are corrected or revised, are anndats/anntims overwritten, retained as original, or reassigned? Please identify the applicable WRDS delivery/version documentation.
