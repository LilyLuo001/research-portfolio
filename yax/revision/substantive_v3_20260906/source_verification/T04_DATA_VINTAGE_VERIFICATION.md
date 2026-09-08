# T04 CPS extract and production-vintage verification

Date verified: 2026-09-08

## Bottom line

The current stock analysis uses authenticated IPUMS CPS extract 9 plus the
authenticated March Basic repair. Extract 9 was submitted on August 25, 2026,
after IPUMS had processed the reissued January 2026 file (April 10), revised
household identifiers (July 13), and the later November-2025--March-2026
`CPSIDP` corrections (August 14). The extract therefore uses the then-current
IPUMS production database rather than a pre-correction snapshot. Its data and
DDI bytes are pinned below.

This timing verification does not construct unavailable age-by-occupation
counterfactual weights. January 2025 and January 2026 remain documented
population-control breaks, and October 2025 remains an uncollected month.

## Actual extract receipts

Extract 9:

- submitted `2026-08-25T13:38:31Z`, completed `2026-08-25T13:42:35Z`;
- 114 requested samples, January 2017--July 2026, with October 2025 removed as
  unavailable;
- data: 267,021,345 bytes, SHA-256
  `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9`;
- DDI: 242,931 bytes, SHA-256
  `5933bc48ed736a00fa70547ef503f571c6f1f9c03aef7d24ce511af3550fb319`;
- 9,262,480 rows and 114 distinct observed months in the structural validation;
- requested fields include `WTFINL`, `CPSID`, `CPSIDP`, `CPSIDV`, `MISH`,
  occupation, age, enrollment, and earnings variables.

The original five March 2017--2021 selections in that wide extract are ASEC,
not Basic Monthly samples. The authenticated repair file is extract 11, data
SHA-256 `a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911`
and DDI SHA-256
`e29c6c30a397357b927692af371b3fa77176f3d020f513343237d651bf3d3b03`.
The replacement audit finds zero positive-`WTFINL`, analysis-eligible records
from the superseded wide-file March rows and 252,862 from the Basic Monthly
repair. The current protected calibration re-authenticates both data hashes,
rebuilds the 113-month static cells, and passes with a maximum relative
aggregate gap of `3.15e-15`.

## Official production changes governing interpretation

The retained official-source audit establishes:

1. Census corrected an April 2025 Basic Monthly weighting error, which IPUMS
   processed in June 2025.
2. BLS introduced Vintage-2024 population controls in January 2025 without
   revising preceding official months to the new basis.
3. October 2025 CPS data were not collected during the federal funding lapse.
   November used delayed/extended collection and modified weighting; the gap is
   preserved rather than interpolated.
4. Initial January 2026 estimates used earlier projections. BLS reissued the
   January file with Vintage-2025 controls on March 6, and IPUMS processed it on
   April 10.
5. IPUMS processed revised `HRHHID2` values on July 13 and a small number of
   corrected `CPSIDP` values for November 2025--March 2026 on August 14.

The stock analysis uses the post-August-14 extract-9 vintage. Flow analyses use
separately authenticated extracts and must retain their own hashes and linkage
rules; this stock-vintage finding is not silently transferred to a different
file.

## Prohibited correction

BLS publishes selected aggregate experimental adjustments, not counterfactual
age-by-occupation factors. YAX therefore does not multiply its cells by an
aggregate adjustment and does not claim to recover a constant-control-vintage
subgroup series. Production breaks are disclosed and assessed with endpoint or
month-exclusion sensitivities.

## Evidence hashes

- extract-9 submission receipt:
  `d63879c84c1b8ce5c4b61fa90c1d0bd709bdaa8043d328a6c7b8c7dd4bf9cfa7`;
- extract-9 download receipt:
  `3a5eef306d791ef608577b5ad07435cda9ce2c3ee1b2bf69b501aace88c89f9e`;
- extract-9 structural validation:
  `4c43b92a912b0c3e965fe5e2bb2dea8f690e2e81d266eb63ef60cf683b548d14`;
- March replacement audit:
  `359a861956cdbf05441e4e15243a7cd1f6859cf144eb281d2b103c9548995921`;
- current protected-calibration receipt:
  `9d0851fac65db630373060e28e076871a964c71363170feaec3cfa6fe254cfae`;
- official CPS/IPUMS documentation audit:
  `0da4c6fcd95f2b0a46e53c6a5c7a5f5ef83ee27132e16a401d57ae3a4d7c9e26`.
