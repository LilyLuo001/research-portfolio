# R3 public BCC-grouping bridge findings

Status: post-outcome exploratory; approximate CPS stock bridge, not an ADP replication.

## Static corrected-calendar estimates

Both constructions use the same 468 occupations and March-restored January 2017--July 2026 CPS stock calendar. The only grouping difference is the weight used to form GPT-4 beta quintile cutoffs.

| grouping | no SOC2 conditioning | SOC2 x post | SOC2 x month |
|---|---:|---:|---:|
| `historical_YAX_employment_weighted_approximation` | -0.0750 [-0.1254, -0.0246] | -0.0266 [-0.0945, 0.0413] | -0.0267 [-0.0934, 0.0400] |
| `public_dashboard_equal_occupation_approximation` | -0.0720 [-0.1218, -0.0222] | -0.0148 [-0.0796, 0.0501] | -0.0168 [-0.0810, 0.0474] |

## Membership

- `historical_YAX_employment_weighted_approximation` assigns 155 of 468 occupations to Q4--Q5, representing 39.70% of corrected-calendar stock.
- `public_dashboard_equal_occupation_approximation` assigns 184 of 468 occupations to Q4--Q5, representing 45.91% of corrected-calendar stock.

## Paired grouping-rule changes

- occupation_plus_calendar_month_FE: equal-occupation minus historical employment-weighted = 0.0030 [-0.0147, 0.0206].
- SOC2_x_post: equal-occupation minus historical employment-weighted = 0.0118 [-0.0304, 0.0541].
- SOC2_x_calendar_month: equal-occupation minus historical employment-weighted = 0.0099 [-0.0321, 0.0519].

These comparisons do not establish BCC membership concordance. The official dashboard documents equal occupation weights, but the complete occupation universe, cutoff/tie implementation, and membership file remain unavailable.

## Dynamics and failures

The quarterly companion produced 152 path rows. 0 model failures were retained in `MODEL_FAILURES.json`.

Intervals containing zero are described as nondetection, never as economic equivalence.
