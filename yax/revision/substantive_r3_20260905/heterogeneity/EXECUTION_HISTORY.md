# CHAR-03/CHAR-04 execution history

## SCC job 7469239 -- failed before data access

The first submitted job exited at module import before any CPS file was opened. The SCC Python environment exposes a minimal `scipy` namespace but not `scipy.stats`, so importing `chi2` raised `ModuleNotFoundError`. No estimate, support statistic, or other outcome was computed.

The repair removes the optional SciPy dependency and evaluates the chi-square upper-tail probability for the predeclared at-most-three-degree-of-freedom age equality test using the exact integer/half-integer incomplete-gamma recurrence in the Python standard library. The estimand, test statistic, degrees of freedom, support, and inference plan are unchanged. A unit test checks the implementation against the published chi-square(3) 95th-percentile checkpoint.

## SCC job 7469259 -- successful complete estimation

The dependency-corrected job completed all twelve registered models and ten paired contrasts in 57 seconds, used at most 2.023 GB, and passed all 65 then-current self-checks. It reproduced BASE-03 at `-0.13210945079219039`. Its results are retained as the first complete numerical checkpoint.

Before final packaging, the reporting code was extended without changing a sample, regressor, estimate, or single-comparison interval. The final rerun adds explicit occupation/industry and occupation education/age membership files, stock-coverage ratios, and the already-registered simultaneous intervals for the four age-minus-pooled paired differences. These additions close traceability and multiplicity-reporting omissions found during review of job 7469259.

## SCC job 7469280 -- final reporting-complete execution

The final job ended with scheduler `failed=0`, `exit_status=0`, wall time 66 seconds, and maximum memory 2.034 GB. All model point estimates and pointwise/paired intervals are identical to job 7469259. The added simultaneous age-minus-pooled intervals all contain zero, including age 24 (`[-0.201416, 0.020235]`), so the final interpretation does not elevate the isolated pointwise age-24 difference. The final transfer passed 81/81 local checks.
