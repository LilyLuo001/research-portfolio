# CHAR-03/CHAR-04 execution history

## SCC job 7469239 -- failed before data access

The first submitted job exited at module import before any CPS file was opened. The SCC Python environment exposes a minimal `scipy` namespace but not `scipy.stats`, so importing `chi2` raised `ModuleNotFoundError`. No estimate, support statistic, or other outcome was computed.

The repair removes the optional SciPy dependency and evaluates the chi-square upper-tail probability for the predeclared at-most-three-degree-of-freedom age equality test using the exact integer/half-integer incomplete-gamma recurrence in the Python standard library. The estimand, test statistic, degrees of freedom, support, and inference plan are unchanged. A unit test checks the implementation against the published chi-square(3) 95th-percentile checkpoint.
