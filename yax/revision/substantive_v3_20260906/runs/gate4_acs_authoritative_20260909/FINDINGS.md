# Gate 4 annual ACS findings

Status: post-outcome exploratory. The v1.1 confirmatory CPS design is unchanged.

## Public benchmark analogue

Every row below is an independent public reconstruction, not an exact BCC replication, because BCC's complete occupation membership is unavailable.

| definition | population | Q5-Q1 growth | ACS SDR 95% interval | unweighted analogue |
|---|---|---:|---:|---:|
| `BCC_analogue_primary_equal` | `all_employed` | -0.0859 | [-0.1238, -0.0480] | -0.0935 |
| `BCC_analogue_primary_equal` | `full_time_civilian_wage_salary` | -0.0834 | [-0.1272, -0.0396] | -0.0900 |
| `YAX_primary_fixed` | `all_employed` | -0.0949 | [-0.1307, -0.0591] | -0.1030 |
| `YAX_primary_fixed` | `full_time_civilian_wage_salary` | -0.1004 | [-0.1435, -0.0574] | -0.1113 |
| `BCC_analogue_broader_equal` | `all_employed` | -0.0796 | [-0.1162, -0.0431] | -0.0897 |
| `BCC_analogue_broader_equal` | `full_time_civilian_wage_salary` | -0.0766 | [-0.1188, -0.0344] | -0.0856 |

BCC's published comparison targets are -0.022 for all employed and -0.019 for full-time civilian wage-and-salary workers. A gap here combines any sampling difference with the unavailable BCC occupation membership.

## Young-relative annual extension

| definition | population | calendar | pooled | family-year |
|---|---|---|---:|---:|
| `YAX_primary_fixed` | `all_employed` | `full_2017_2019_2021_2023_2024` | -0.1089 [-0.1310, -0.0869] | -0.0474 [-0.0885, -0.0063] |
| `YAX_primary_fixed` | `all_employed` | `nonreuse_2017_2021_2023_2024` | -0.0951 [-0.1204, -0.0698] | -0.0220 [-0.0705, 0.0264] |
| `YAX_primary_fixed` | `full_time_civilian_wage_salary` | `full_2017_2019_2021_2023_2024` | -0.1196 [-0.1456, -0.0936] | -0.0691 [-0.1193, -0.0188] |
| `YAX_primary_fixed` | `full_time_civilian_wage_salary` | `nonreuse_2017_2021_2023_2024` | -0.1063 [-0.1361, -0.0764] | -0.0467 [-0.1057, 0.0122] |
| `BCC_analogue_broader_equal` | `all_employed` | `full_2017_2019_2021_2023_2024` | -0.0830 [-0.1053, -0.0607] | -0.0151 [-0.0559, 0.0257] |
| `BCC_analogue_broader_equal` | `all_employed` | `nonreuse_2017_2021_2023_2024` | -0.0723 [-0.0979, -0.0467] | -0.0056 [-0.0535, 0.0424] |
| `BCC_analogue_broader_equal` | `full_time_civilian_wage_salary` | `full_2017_2019_2021_2023_2024` | -0.0933 [-0.1203, -0.0664] | -0.0292 [-0.0790, 0.0205] |
| `BCC_analogue_broader_equal` | `full_time_civilian_wage_salary` | `nonreuse_2017_2021_2023_2024` | -0.0828 [-0.1137, -0.0520] | -0.0291 [-0.0875, 0.0293] |

## Interpretation boundary

The ACS intervals above measure person-sampling uncertainty under the stated year-block approximation. Occupation- and family-shock intervals are reported separately in the machine-readable tables. Larger respondent counts do not repair missing family-by-quintile comparisons, and neither interval identifies a causal AI effect.

There are 8 paired pooled-minus-family-year rows. A paired interval containing zero is described only as failure to detect a difference, never as equivalence.
