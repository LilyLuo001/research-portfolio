# Corrected-calendar architecture audit results

Status: **post-outcome exploratory; not part of confirmatory YAX v1.1**.

## Lambda construction continuum

| lambda | Q5-Q1 coefficient | 95% occupation wild-score interval | fixed-beta-scale continuous coefficient | restandardized continuous coefficient |
|---:|---:|---:|---:|---:|
| 0.00 | -0.102791 | [-0.176852, -0.028730] | -0.039693 | -0.030923 |
| 0.25 | -0.100732 | [-0.178939, -0.022524] | -0.046463 | -0.037839 |
| 0.50 | -0.132109 | [-0.219789, -0.044429] | -0.038514 | -0.038514 |
| 0.75 | -0.142765 | [-0.228077, -0.057453] | -0.029559 | -0.037591 |
| 1.00 | -0.155621 | [-0.238247, -0.072995] | -0.023005 | -0.036483 |

Lambda 0.5 reproduces literal Rule-A beta and the BASE-03 categorical coefficient to the declared tolerance (maximum raw identity gap `7e-13`). All pairwise intervals and MDEs are in `LAMBDA_PAIRED_DIFFERENCES.csv`; a null-containing interval is not an equivalence result.

## Focused characteristic conditioning at lambda 0.5

| model | Q5-Q1 coefficient | 95% interval |
|---|---:|---:|
| beta_plus_Webb | -0.107041 | [-0.187934, -0.026149] |
| beta_plus_Webb_plus_computer | -0.212433 | [-0.330977, -0.093889] |
| beta_plus_Webb_plus_remote | -0.115544 | [-0.202801, -0.028287] |
| beta_plus_Webb_plus_computer_plus_remote | -0.211958 | [-0.328715, -0.095202] |

These 408-occupation models hold support fixed. Computer use and remotability are static occupational characteristics, not realized adoption; conditioning does not purify a causal AI effect.

## Webb conditioning versus Webb availability

On the fixed 468 support, adding Webb changes the point estimate from -0.133785 to -0.132109. The common-draw paired difference and interval are reported separately. Removing the Webb availability requirement expands support to 490 occupations and yields -0.134845; that support-changing comparison is descriptive and has no paired CI.

## Primitive model and exclusions

The direct D/S model is reported in raw and standardized units with its full covariance and common draws. The two presentations span the same fitted column space. Historical F/G and A/E rotations remain archived provenance only, mobility/rematching is not reopened, and age-specific bridge shares remain blocked absent genuine validation data.
