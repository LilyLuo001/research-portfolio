# Gate 2 timing, endpoint, era, and seasonality findings

Status: **run complete and independently numerically validated; manuscript
presentation not yet validated**

SCC job `7490289` executed the frozen 34-model collection at commit
`4b298853f439fda1577a14f7dc598f7832f54466`. Scheduler status was
`failed=0`, `exit_status=0`, with 4,260 seconds wall time and 3.022 GB maximum
virtual memory. The result ID is
`yaxresult_v1_cc076af4f71d56d02f4944b07bc69e93db2c10f369512aa83641be1e71e659e4`.

Every model passed fresh A1 same-objective numerical certification. The
repository-side validator independently reconstructed the 34 model intervals,
47 paired comparisons, complete 34-by-34 covariance matrix, and both onset-grid
simultaneous intervals from the retained occupation influence matrix and common
9,999 multiplier draws. Its largest discrepancy was `1.07e-14`; all 17 checks
passed.

## Main timing comparisons

| specification | unconditioned coefficient (95% CI) | family-month coefficient (95% CI) |
|---|---:|---:|
| Full window | -0.1321 [-0.2206, -0.0437] | -0.0217 [-0.1620, 0.1186] |
| Through 2024 | -0.1110 [-0.1992, -0.0229] | -0.0120 [-0.1647, 0.1407] |
| 2025--2026 era | -0.1676 [-0.2738, -0.0615] | -0.0336 [-0.1984, 0.1313] |
| Full, excluding September and November 2025 | -0.1337 [-0.2221, -0.0453] | -0.0252 [-0.1661, 0.1157] |
| 2025--2026 era, excluding September and November 2025 | -0.1758 [-0.2845, -0.0670] | -0.0448 [-0.2130, 0.1234] |

The paired through-2024-minus-full movement is 0.0211 (95% CI -0.0073 to
0.0495) without family-month conditioning and 0.0097 (-0.0536 to 0.0730) with
it. The paired late-minus-early movement is -0.0566 (-0.1249 to 0.0118) and
-0.0216 (-0.1676 to 0.1244), respectively. These intervals do not detect a
change; they do not establish equality across windows.

Removing the two shutdown-adjacent observed months changes the full-window
coefficient by -0.0016 (-0.0074 to 0.0043) without family-month conditioning
and -0.0035 (-0.0131 to 0.0060) with it. For the late era, the corresponding
changes are -0.0082 (-0.0225 to 0.0061) and -0.0113 (-0.0331 to 0.0106).

## Onset and seasonality

Across the November 2022--June 2023 onset grid, unconditioned coefficients
range from -0.1324 to -0.1257. Every simultaneous onset-grid interval excludes
zero. Family-month coefficients range from -0.0251 to -0.0145, and every
simultaneous interval includes zero. Relative to January 2023, every paired
onset-change interval includes zero under both structures.

Adding quintile-by-month-of-year seasonality changes the unconditioned target
by -0.0005 (paired 95% CI -0.0042 to 0.0032) and the family-month target by
-0.0009 (-0.0066 to 0.0048). Occupation-by-month-of-year matching changes them
by -0.0003 (-0.0042 to 0.0037) and 0.0011 (-0.0061 to 0.0082). Thus neither
feasible seasonal specification explains the cross-structure movement.

Restricting to the coding-stable post-2020 window yields -0.1181
[-0.1941, -0.0420] without and -0.0304 [-0.1716, 0.1108] with family-month
conditioning. Relative to the full window, paired changes are 0.0140
[-0.0288, 0.0569] and -0.0087 [-0.1053, 0.0878]. The fixed treatment support
remains 468 occupations, but only 457 supply positive estimating rows in this
shorter window; the other 11 have aligned zero influence, with each model's own
finite-cluster correction retained.

## Interpretation boundary

The completed checks show that reasonable onset, endpoint, shutdown-adjacent,
coding-stable, and seasonal choices do not materially change the coefficient
*within* either conditioning structure at this design's precision. They do not
resolve the substantive difference between the two structures. The baseline
family-month-minus-unconditioned movement is 0.1104 (paired 95% CI 0.0097 to
0.2112); analogous movements remain about 0.088 to 0.134 across the declared
timing variants. These are descriptive projection comparisons, not proof that
the residual unconditioned association is caused by broad occupational
composition or that the conditioned remainder is a causal AI effect.
