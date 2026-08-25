# CPS occupation exposure lookup freeze

This is a measurement-only build. It does not read CPS microdata or outcomes.

## Frozen merge rule

Use `CPS_OCCUPATION_EXPOSURE_LOOKUP.csv` as follows:

- For 2017--2019, join raw IPUMS `OCC` to `occ_code` where
  `lookup_role == "raw_occ_main_2017_2019"`. These are Census 2010 codes
  bridged to Census 2018 with the Census Bureau's official total conversion
  rates.
- For 2020 onward, join raw IPUMS `OCC` to `occ_code` where
  `lookup_role == "raw_occ_main_2020_plus"`. Raw `OCC` is already Census 2018
  in these years, so this is a direct match with no bridge.
- Use `lookup_role == "occ2010_sensitivity_all_years"` only for the separately
  labelled harmonized-`OCC2010` sensitivity. It must not replace observed raw
  Census 2018 occupation after 2020.

The measures are distinct and must remain separate. The design's primary
treatment is GPT-4-model-rated `dv_rating_beta`; `dv_rating_alpha` and
`dv_rating_gamma` are required alternate definitions. The official Eloundou
CSV calls the upper-bound field `gamma`, while the published paper calls the
same E1+E2 construct Greek zeta. The lookup preserves the source field name and
records this translation in the receipt. `dingel_neiman_telework` is the
remote-feasibility control. The three AIOE construction variants remain
available as additional measurement checks.

Published O*NET detail rows are first averaged within six-digit SOC because no
official employment counts exist below six-digit SOC. Where one Census 2018
occupation contains multiple six-digit SOCs, the build uses May 2021 OEWS
target-SOC employment weights. The 22 Census occupations with at least one
missing OEWS component use an explicit equal-weight fallback. Target-component
coverage and partial sums are retained in `CENSUS2018_EXPOSURE_VARIANTS.csv`.

## Uncertainty and missingness

Every bridged 2010 code reports `n_routes`, `max_route_weight`,
`route_entropy`, and `ambiguity_status`. The row-level routing table is
`CENSUS_OCC2010_TO_2018_BRIDGE.csv`.

The aggregation rule is fail-closed. For each exposure definition,
`*_covered_route_mass` records how much official routing mass has a usable
target exposure and `*_partial_weighted_sum` records its unnormalized
contribution. The final exposure value is nonmissing only when covered route
mass is one. Missing children are never removed and the surviving weights are
never renormalized.

## Coverage from the frozen build

The main 2017--2019 lookup covers 503 Census 2010/IPUMS codes. Of these, 447
are one-to-one, 18 are one-to-many with a route carrying at least 90 percent,
and 38 are diffuse one-to-many conversions. Full-route coverage is 480 codes
for equal-administrative AIOE, 463 for direct-ability AIOE, and 472 for the
OEWS-2018 source-employment-weighted variant.

For all three GPT-4-rated Eloundou definitions, 443 pre-2020 codes have full
end-to-end coverage, 46 more have partial coverage, and 14 have none.
Dingel--Neiman has 392 full, 56 partial, and 55 zero-coverage codes. Partial
coverage is never promoted to a point exposure.

The direct 2020+ lookup emits all 570 official Census 2018 detailed codes,
including explicit zero-coverage rows. Nonmissing coverage is 545, 530, and
535 codes for the same three variants, respectively.

For 2020 onward, the three Eloundou definitions have 514 full, 33 partial, and
23 zero-coverage Census codes. Dingel--Neiman has 442 full, 42 partial, and 86
zero-coverage codes.

Exact input and output checksums are in
`CPS_OCCUPATION_EXPOSURE_LOOKUP_RECEIPT.json`.
