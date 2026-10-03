# Frozen C1/C2 comparison input contract

The comparison builder consumes a joined, ad-level semantic narrow table. It aggregates existing flags only and never reads advertisement text or reruns parsing.

Required main-analysis columns are `usable`, `CREATED`, `OCCUPATION_MAJOR`, `CENSUS_REGION`; explicit role flags for generative AI use/develop and traditional-software use/develop; detected flags for generative, predictive, and unspecified AI; and `main`, `required`, and `broad` experience flags for `general_work`, `industry_domain`, and `specific_tool`. Missing occupation or Census region is excluded and reported as coverage loss; the program never guesses occupation. `occupation_task` is always unmeasured/NA under D10.

C1 arm A is explicit generative-AI use. C1 arm B is explicit traditional-software use with no detected generative, predictive, or unspecified AI. C2 applies the same rule to explicit develop roles. AI arms may also mention traditional software. Main rows require usable text and `CREATED` from 2018-01-01 through 2026-06-30 inclusive.

The common cell is occupation major × Census region × `CREATED` year. Both arms need at least 20 ads in a retained cell, each retained arm needs at least 200 ads overall, and support must cover at least five occupation majors. Unsupported comparisons are canceled without replacement. Both arms use the same pooled common-support record distribution as standardization weights. A retention rate below 70 percent changes status to limited; it does not change the sample rule.

Only the frozen sensitivities are implemented: S1 required-only and broader within-ad candidate co-occurrence; S2 same-company × occupation support and the 2016–2017 extension; S3 closed single-quarter observations and exclusion of intervals crossing 2022-11-30. The S2 company restriction requires `COMPANY_ID`, keeps pairs with at least one ad in each comparison arm, then reapplies every ordinary support threshold.

S3 requires upstream-verified `OBSERVATION_END`, `OBSERVATION_CLOSED`, `DATE_COMPLETE`, and the T4-consistent `CROSSES_2022_11_30`. The builder does not infer an endpoint from `DELETED`, `LAST_CHECKED`, or other dates. Closed single-quarter rows must have complete dates, a non-reversed interval, closure true, and `CREATED`/endpoint in the same calendar quarter. The crossing exclusion accepts only explicit false; missing is not false. Until these verified fields are connected, S3 outputs blocked rows. These intervals describe delivery observation risk, not text-effective dates.

For every measured Boolean used by a variant, eligible rows must contain a valid true or false. Nulls and invalid strings are unknown, never zero: they are excluded from that object's measurement denominator and counted explicitly. A support cell with no valid measurement in either arm blocks that object result. Valid false values remain in the denominator, preserving zero detections.

Outputs contain raw counts and proportions on the retained common-support sample, pooled-weight standardized proportions, differences A minus B, raw-minus-standardized differences, and support/retention counts. They also report raw summaries over all classifiable arm records before common-support trimming so trimming can be distinguished from standardization. Experience objects are multi-label. There are no p-values, wages, causal estimates, substitute groups, or ad-level minimum-years calculations.

For reproducibility, pass `--join-manifest` when a verified joined-input manifest exists; its SHA-256 is recorded. Otherwise the receipt records the complete input file inventory with size and nanosecond modification time and labels content hashing as not computed. The receipt always records the comparison script SHA-256.
