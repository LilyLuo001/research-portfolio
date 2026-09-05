# HonestDiD dependency-receipt amendment

The successful official HonestDiD analysis in SCC job 7469301 used the pinned
project library created and verified by SCC job 7469287.  That library included
official CRAN `osqp` 1.0.0, as required by the pinned CVXR 1.8.2 dependency
stack.  The original machine-readable HonestDiD receipt recorded HonestDiD,
CVXR, and `highs`, but accidentally omitted the already-verified `osqp` version
and source fields.

`augment_honestdid_receipt.R` is a metadata-only correction.  It queries the
same project library, fails unless `osqp` is version 1.0.0, and adds
`osqp_version` and `osqp_source` to a copy of the completed receipt.  It does
not refit a model or modify event vectors, covariance matrices, intervals, or
other statistical artifacts.  The final dynamics self-check independently
revalidates every stored result hash against the amended receipt.

The later endpoint-grid extension does not change any event-study coefficient
or covariance: its four event-vector hashes and four covariance hashes match
those consumed by job 7469301 exactly.  A redundant full official-package
rerun was submitted in a separate result directory and was not used as a
substitute for this documented metadata correction.
