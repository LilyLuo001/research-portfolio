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

The three exposure definitions are distinct and must remain separate:
`aioe_admin_equal`, `aioe_ability_direct`, and
`aioe_oews2018_source_weighted`.

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

The direct 2020+ lookup emits all 570 official Census 2018 detailed codes,
including explicit zero-coverage rows. Nonmissing coverage is 545, 530, and
535 codes for the same three variants, respectively.

Exact input and output checksums are in
`CPS_OCCUPATION_EXPOSURE_LOOKUP_RECEIPT.json`.
