# Support reconciliation for the computerization design

## The three live counts

| count | what it counts | why it differs |
|---:|---|---|
| 490 | balanced two-age Census-2018 target clusters used by the power design | 492 raw target codes minus codes without positive 66-month support in both age groups |
| 445 | OCC2010 codes observed in the older 13-month moment artifact | current valid occupation for employed people or most recent prior valid occupation within 15 months for non-employed people |
| 442 | the 445 older-support OCC2010 codes carrying a Webb score | 445 minus the three Webb-unscored source occupations |

These are not three estimates of one population. The 490-cluster artifact uses harmonized Census-2018 target occupations and current employment in the two frozen age groups. The older 445-code artifact uses OCC2010 and can assign a recent occupation to a non-employed respondent. The 442 count is a measure-availability subset of that older support.

## Frozen support

The design pins the **66-month balanced Census-2018 target-occupation design cells**: 490 clusters, 66 months (2017-01-01 through 2022-11-01), lookup role `raw_occ_main_2020_plus`, cells SHA-256 `4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800`. OCC2010 is retained only as a sensitivity support.

The cells receipt still records the previously failed exposure-coverage gate. Pinning the file does not convert that failed gate into a pass.

## Thirteen- versus 66-month diagnostics

13m-to-66m changes combine horizon, occupation vintage, balance rule and weight definition; they are not a pure calendar-window experiment. The table therefore reports movements rather than attributing them to the additional months.

| AI measure | computerization | partial 13m | partial 66m | VIF 13m | VIF 66m | effective N 13m | effective N 66m |
|---|---|---:|---:|---:|---:|---:|---:|
| aioe_admin_equal | webb_pct_software | 0.968 | 0.949 | 1.03 | 1.05 | 62.3 | 72.2 |
| aioe_admin_equal | onet_computers_importance | 0.296 | 0.279 | 3.38 | 3.58 | 54.7 | 73.0 |
| aioe_admin_equal | onet_computers_level | 0.483 | 0.456 | 2.07 | 2.19 | 55.6 | 77.3 |
| aioe_admin_equal | rti_autor_dorn | 0.989 | 0.974 | 1.01 | 1.03 | 58.3 | 62.8 |
| aioe_admin_equal | frey_osborne_probability | 0.910 | 0.872 | 1.10 | 1.15 | 47.4 | 63.8 |
| aioe_ability_direct | webb_pct_software | 0.964 | 0.952 | 1.04 | 1.05 | 61.2 | 74.6 |
| aioe_ability_direct | onet_computers_importance | 0.308 | 0.283 | 3.25 | 3.53 | 35.1 | 77.8 |
| aioe_ability_direct | onet_computers_level | 0.464 | 0.435 | 2.16 | 2.30 | 42.0 | 82.2 |
| aioe_ability_direct | rti_autor_dorn | 0.987 | 0.977 | 1.01 | 1.02 | 60.3 | 68.2 |
| aioe_ability_direct | frey_osborne_probability | 0.890 | 0.861 | 1.12 | 1.16 | 41.2 | 59.3 |
| aioe_oews2018_source_weighted | webb_pct_software | 0.962 | 0.942 | 1.04 | 1.06 | 63.0 | 72.1 |
| aioe_oews2018_source_weighted | onet_computers_importance | 0.274 | 0.271 | 3.65 | 3.69 | 54.7 | 65.4 |
| aioe_oews2018_source_weighted | onet_computers_level | 0.461 | 0.452 | 2.17 | 2.21 | 57.0 | 70.3 |
| aioe_oews2018_source_weighted | rti_autor_dorn | 0.989 | 0.978 | 1.01 | 1.02 | 59.1 | 62.1 |
| aioe_oews2018_source_weighted | frey_osborne_probability | 0.899 | 0.864 | 1.11 | 1.16 | 46.7 | 62.8 |
| dv_rating_alpha | webb_pct_software | 0.974 | 0.983 | 1.03 | 1.02 | 14.0 | 17.4 |
| dv_rating_alpha | onet_computers_importance | 0.845 | 0.908 | 1.18 | 1.10 | 33.2 | 31.1 |
| dv_rating_alpha | onet_computers_level | 0.882 | 0.917 | 1.13 | 1.09 | 33.0 | 31.7 |
| dv_rating_alpha | rti_autor_dorn | 0.964 | 0.953 | 1.04 | 1.05 | 9.5 | 11.9 |
| dv_rating_alpha | frey_osborne_probability | 0.969 | 0.934 | 1.03 | 1.07 | 27.1 | 26.3 |
| dv_rating_beta | webb_pct_software | 1.000 | 0.997 | 1.00 | 1.00 | 44.4 | 53.3 |
| dv_rating_beta | onet_computers_importance | 0.357 | 0.365 | 2.80 | 2.74 | 50.2 | 63.2 |
| dv_rating_beta | onet_computers_level | 0.480 | 0.468 | 2.08 | 2.14 | 53.8 | 59.5 |
| dv_rating_beta | rti_autor_dorn | 0.985 | 0.971 | 1.02 | 1.03 | 41.1 | 51.7 |
| dv_rating_beta | frey_osborne_probability | 0.981 | 0.976 | 1.02 | 1.02 | 51.7 | 62.9 |
| dv_rating_gamma | webb_pct_software | 0.996 | 0.982 | 1.00 | 1.02 | 61.4 | 84.5 |
| dv_rating_gamma | onet_computers_importance | 0.317 | 0.306 | 3.15 | 3.27 | 34.9 | 44.4 |
| dv_rating_gamma | onet_computers_level | 0.443 | 0.425 | 2.26 | 2.36 | 49.5 | 72.2 |
| dv_rating_gamma | rti_autor_dorn | 0.995 | 0.988 | 1.00 | 1.01 | 58.3 | 77.5 |
| dv_rating_gamma | frey_osborne_probability | 0.943 | 0.913 | 1.06 | 1.10 | 48.0 | 74.0 |

## Reading the movement

The largest absolute partial-variance movement is 0.062; the largest VIF movement is 0.288. Those changes do not reverse the Y1b conclusion about which pairings are strongly versus weakly collinear. Effective-N moves more: the largest change is 42.6 occupations, so concentration must be reported on the pinned support rather than carried over from the 13-month receipt.
