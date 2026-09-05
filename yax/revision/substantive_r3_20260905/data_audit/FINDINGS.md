# Corrected-calendar data, support, and cell audit

Status: post-outcome descriptive audit; not part of the frozen YAX v1.1 confirmatory design.

## Result

The corrected source calendar contains 114 of 115 expected months from January
2017 through July 2026. October 2025 is absent because the CPS was not collected;
it is never interpolated. December 2022 is observed but excluded from the static
pre/post specification by the signed transition-month rule, leaving 113 analysis
months.

The fully enumerated primary grid has 52,884 occupation-month cells (468
occupations by 113 months). Of those cells, 51,891 have positive fitted totals,
12,965 contain a valid one-sided zero and remain in the likelihood, and 993 have
both age-group counts equal to zero and therefore make no likelihood
contribution. The reconstruction scans 9,843,021 source rows, retains 5,322,047
eligible employed records with positive `WTFINL`, and expands them to 6,188,956
fractional routed descendants before aggregation.

Young-worker cells are sparse. Among the 52,884 cells, 26.25 percent have zero
respondent-equivalent young records and 69.83 percent have fewer than five. The
corresponding older-worker shares are 2.02 and 11.01 percent. These are
fractional route-equivalent counts before 2020 and exact record counts from 2020
onward; they are not distinct-respondent counts or effective sample sizes.

## Support and exclusions

The common beta/Webb support contains 468 occupations and 87.19 percent of the
preperiod stock represented in the audited candidate universe. Seventy-three
occupations are excluded: 41 only for a nonfinite Rule-A beta exposure, 22 only
for a nonfinite Webb software score, eight for both, and two for nonpositive
young preperiod stock. The full named support and exclusion list is preserved in
`results/SUPPORT_AND_EXCLUSIONS.csv`; it must accompany any model whose support
uses these joint requirements.

## Reconstruction and weights

Before 2020, the bridge contains 503 source codes and 568 target codes; 56 source
codes route one-to-many and the maximum multiplicity is seven. Source `WTFINL`
enters stock once and route shares partition that stock. The early and current
relative conservation gaps are below 2e-16 in absolute value. The explicitly
superseded wide-file March rows contribute no eligible positive-weight record;
the separately hashed March repair contributes 252,862 eligible records across
March 2017--2021. No source month is silently duplicated.

## Interpretation

This audit establishes the calendar, route conservation, named support, sample
flow, and sparse/boundary-cell accounting used by the corrected analyses. It
does not validate the CPS as a design-based sample under the grouped-binomial
likelihood, and it does not turn respondent-equivalent cell counts into
independent observations. Survey-design and finite-sample sensitivities remain
separate registered analyses.

## Reproduction

SCC job `7469159` completed with exit status 0 in 44 seconds and peak memory
1.825 GB. All 17 artifact/hash/self-check conditions pass locally after transfer.
The immutable inputs and generated-output hashes are recorded in
`results/EXECUTION_RECEIPT.json`.
