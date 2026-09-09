# Gate 4 public benchmark and population-alignment findings

Status: post-outcome exploratory; the frozen v1.1 design is unchanged.

## Public stock benchmarks

These are independent CPS analogues using equal-occupation Rule-A beta quintiles on the fixed YAX support. They are not exact BCC occupation memberships, an ADP replication, or CPS design-based estimates.

| population | endpoint | contrast | estimate | occupation-linearized 95% interval |
|---|---|---|---:|---:|
| `all_employed` | `annual_mean_2022_to_2024` | `Q5_vs_Q1_growth_factor_difference` | -0.0346 | [-0.1455, 0.0763] |
| `all_employed` | `annual_mean_2022_to_2024` | `top_two_vs_bottom_three_kept_pace` | -0.0269 | [-0.0972, 0.0435] |
| `full_time_civilian_wage_salary` | `annual_mean_2022_to_2024` | `Q5_vs_Q1_growth_factor_difference` | -0.0306 | [-0.1366, 0.0755] |
| `full_time_civilian_wage_salary` | `annual_mean_2022_to_2024` | `top_two_vs_bottom_three_kept_pace` | -0.0093 | [-0.0852, 0.0666] |
| `all_employed` | `November_2022_to_June_2026` | `Q5_vs_Q1_growth_factor_difference` | -0.2312 | [-0.4660, 0.0036] |
| `all_employed` | `November_2022_to_June_2026` | `top_two_vs_bottom_three_kept_pace` | -0.1007 | [-0.2380, 0.0367] |
| `full_time_civilian_wage_salary` | `November_2022_to_June_2026` | `Q5_vs_Q1_growth_factor_difference` | -0.1332 | [-0.4047, 0.1382] |
| `full_time_civilian_wage_salary` | `November_2022_to_June_2026` | `top_two_vs_bottom_three_kept_pace` | -0.0544 | [-0.2231, 0.1142] |

The annual CPS comparison averages all twelve months of 2022 and all twelve months of 2024. December 2022 remains excluded from the separately defined YAX post models.

## Occupation long differences

The no-control occupation regressions use baseline employment-stock weights and HC1 heteroskedastic-robust standard errors, matching the public regression form as far as CPS and the reconstructed membership permit.

| population | endpoint | Q5-Q1 estimate | HC1 95% interval | occupations |
|---|---|---:|---:|---:|
| `all_employed` | `annual_mean_2022_to_2024` | -0.0318 | [-0.1447, 0.0811] | 439 |
| `full_time_civilian_wage_salary` | `annual_mean_2022_to_2024` | -0.0260 | [-0.1324, 0.0804] | 429 |
| `all_employed` | `November_2022_to_June_2026` | -0.2466 | [-0.4771, -0.0160] | 330 |
| `full_time_civilian_wage_salary` | `November_2022_to_June_2026` | -0.1553 | [-0.4069, 0.0963] | 306 |

## Separately defined young-relative CPS extension

All conditional rows use one common support of 468 occupations and identical exposure labels. The no-Webb rows are shown separately from the historical YAX Webb-control extension.

| population | contrast | Webb rule | pooled | family-post | family-month |
|---|---|---|---:|---:|---:|
| `all_employed` | `Q5_vs_Q1` | `no_Webb_public_benchmark` | -0.1146 [-0.2057, -0.0236] | -0.0118 [-0.1440, 0.1203] | -0.0124 [-0.1446, 0.1197] |
| `all_employed` | `Q5_vs_Q1` | `with_Webb_YAX_extension` | -0.1117 [-0.2056, -0.0178] | -0.0072 [-0.1420, 0.1276] | -0.0080 [-0.1428, 0.1267] |
| `all_employed` | `top_two_vs_bottom_three` | `no_Webb_public_benchmark` | -0.0712 [-0.1216, -0.0208] | -0.0142 [-0.0776, 0.0493] | -0.0162 [-0.0792, 0.0468] |
| `all_employed` | `top_two_vs_bottom_three` | `with_Webb_YAX_extension` | -0.0720 [-0.1223, -0.0218] | -0.0148 [-0.0792, 0.0497] | -0.0168 [-0.0808, 0.0473] |
| `full_time_civilian_wage_salary` | `Q5_vs_Q1` | `no_Webb_public_benchmark` | -0.1364 [-0.2354, -0.0374] | -0.0426 [-0.1814, 0.0963] | -0.0429 [-0.1823, 0.0965] |
| `full_time_civilian_wage_salary` | `Q5_vs_Q1` | `with_Webb_YAX_extension` | -0.1310 [-0.2298, -0.0323] | -0.0408 [-0.1808, 0.0992] | -0.0412 [-0.1818, 0.0995] |
| `full_time_civilian_wage_salary` | `top_two_vs_bottom_three` | `no_Webb_public_benchmark` | -0.0836 [-0.1417, -0.0255] | -0.0453 [-0.1206, 0.0299] | -0.0473 [-0.1232, 0.0285] |
| `full_time_civilian_wage_salary` | `top_two_vs_bottom_three` | `with_Webb_YAX_extension` | -0.0836 [-0.1415, -0.0258] | -0.0457 [-0.1231, 0.0316] | -0.0477 [-0.1258, 0.0304] |

The top-two/bottom-three movement has its own paired influence distribution and intervals. No Q5-Q1 rejection or precision statement is transferred to that grouping.

## Interpretation boundary

Family conditioning, sample alignment, and the Webb control change descriptive estimands. A confidence interval containing zero means only that this design does not detect a difference; it does not establish equivalence. None of these comparisons reproduces unavailable BCC firm controls or identifies a causal AI effect.

The run retained 4 population/Webb-specific paired family-month-minus-pooled comparisons for the binary BCC-style grouping.
