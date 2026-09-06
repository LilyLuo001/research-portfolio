# V3 Gate 1 exact-target audit

Status: **PASS_EXACT_TARGET_AUDIT**. This module authenticates and describes the
aggregate estimating data; it does not estimate or reproduce a coefficient.

## Exact target

The criterion is evaluated on two continuous CPS-weighted employment stocks,
`N_y` for ages 22–25 and `N_o` for ages 26–65. For rows with
`T=N_y+N_o>0`, it is `N_y log(p) + N_o log(1-p)`, where
`logit(p)=log(mu_y/mu_o)`. The Q5 coefficient is therefore a Q5-versus-Q1
post-2023 change in a log ratio of conditional mean stocks. It is not an
observed log ratio, individual employment probability, or hiring rate.

## Authenticated static grid

- Occupations: 468
- Static months: 113
- Balanced static rows: 52884
- Positive-total estimating rows: 51891
- Retained one-sided zero rows: 12965
- Both-zero rows with no criterion contribution: 993

## Row and stock accounting

| stage | value | unit | criterion role |
|---|---:|---|---|
| source_rows_scanned | 9843021 | physical input rows | upstream only; includes rows later replaced or excluded |
| wide_source_rows_scanned | 9262480 | physical input rows | wide-source component of source_rows_scanned |
| repair_source_rows_scanned | 580541 | physical input rows | March-repair component of source_rows_scanned |
| eligible_employed_age_22_65_source_records | 5041595 | physical source records | exact target-age routing universe before occupation validity |
| wide_eligible_employed_age_22_65_source_records | 4801576 | physical source records | wide-source component of exact target-age eligibility |
| repair_eligible_employed_age_22_65_source_records | 240019 | physical source records | repair-source component of exact target-age eligibility |
| eligible_records_with_invalid_raw_occupation | 0 | physical source records | excluded before occupation routing |
| eligible_records_with_valid_raw_occupation | 5041595 | physical source records | partitioned into early and current source records |
| early_valid_source_records | 1854390 | physical source records | 2017–2019 valid records offered to the occupation bridge |
| current_valid_source_records | 3187205 | physical source records | 2020 onward valid records routed directly |
| early_matched_source_records | 1846744 | physical source records | early source records with a bridge route |
| early_unmatched_source_records | 7646 | physical source records | early source records excluded for no bridge route |
| wide_march_rows_explicitly_replaced | 621589 | physical input rows | wide-source March records removed before target eligibility |
| wide_march_positive_weight_rows_explicitly_replaced | 0 | physical input rows | positive-weight subset of explicitly replaced wide-source rows |
| early_expanded_route_descendants | 2696977 | in-memory bridge-contribution rows | not respondents; one matched early source record may have several descendants |
| early_fractional_route_contributions | 1224850 | in-memory bridge-contribution rows | strictly positive bridge allocation below one |
| early_unit_route_contributions | 1472127 | in-memory bridge-contribution rows | bridge allocation exactly one |
| early_zero_mass_route_contributions | 0 | in-memory bridge-contribution rows | bridge allocation exactly zero |
| current_direct_route_contributions | 3187205 | in-memory direct-contribution rows | one direct route for each valid current source record |
| all_routed_contribution_rows | 5884182 | in-memory route-contribution rows | early descendants plus current direct contributions |
| routed_age_level_aggregate_rows | 1411327 | grouped intermediate rows | pre-target aggregation |
| authenticated_aggregate_grid_rows | 53352 | occupation-month rows | 114-month transport grid including 2022-12 |
| canonical_static_grid_rows | 52884 | occupation-month rows | 113-month static grid after excluding 2022-12 |
| positive_total_estimating_rows | 51891 | occupation-month rows | rows with a nonzero grouped-binomial criterion contribution |
| one_sided_zero_rows_retained | 12965 | occupation-month rows | valid boundary stock observations retained |
| both_zero_rows | 993 | occupation-month rows | present on balanced grid; excluded because total stock is zero |
| young_stock | 1214266456.0190506 | CPS-weighted employed-person stock | continuous criterion numerator; not a row count |
| older_stock | 12380182137.007343 | CPS-weighted employed-person stock | continuous comparison stock; not a row count |

Physical row counts are integers. Employment stocks are real-valued survey-weighted
quantities and may be fractional. Route-expanded descendants are not unique people;
the aggregate schema cannot recover unique people or households.

## Weight rule

`WTFINL` enters routed stock exactly once. A pre-2020 bridge weight allocates that
stock across target occupations and is not a second survey weight. No weight is
applied when the routed stocks are collapsed to the audit grid.
