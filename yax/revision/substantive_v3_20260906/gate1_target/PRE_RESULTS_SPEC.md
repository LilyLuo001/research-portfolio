# V3 Gate 1 exact-target audit: pre-results specification

Status: written before this module reads the authenticated V3 aggregate-cell
product. This is a post-outcome, referee-led verification of a previously
estimated target, not a preregistration. Adding this module does not establish
that its empirical checks have run.

## Purpose

Requirement T01 asks what is actually observed, what the grouped-binomial
criterion is evaluated on, and what its coefficient parameterizes. The audit
must prevent three category errors: calling a cell's observed outcome a log
ratio when either stock can be zero; treating continuous survey-weighted
stocks as literal independent Bernoulli trials; and interpreting the target as
an individual's employment probability or an employer's hiring rate.

The empirical runner accepts only the sanitized aggregate product emitted by
the authenticated Gate-1 cell builder. It has no arguments for row-level CPS
microdata and does not invoke an estimator. It authenticates the aggregate
file through the colocated cell-builder receipt, then writes a new atomic
audit leaf outside the repository.

## Observed estimating data

For Census-2018 detailed occupation \(o\) and observed calendar month \(t\),
the cell builder supplies two real-valued quantities:

\[
N_{y,ot}=\sum_{i\in(o,t),\,22\leq AGE_i\leq25} WTFINL_i a_{io},
\qquad
N_{o,ot}=\sum_{i\in(o,t),\,26\leq AGE_i\leq65} WTFINL_i a_{io},
\]

where \(a_{io}=1\) on the direct Census-2018 route and is the fixed bridge
allocation share on a pre-2020 Census-2010-to-2018 route. `WTFINL` enters once;
the bridge share allocates that stock and is not a second survey weight.
The target router reads only `YEAR`, `MONTH`, `AGE`, `EMPSTAT`, `OCC`, and
`WTFINL`, applies the 22–65 and employed-status restrictions before occupation
routing, and does not import the historical general-purpose builder at runtime.

The transport product is a balanced 468-occupation by 114-observed-month
grid. The static target excludes the observed December 2022 transition month,
leaving 113 months and 52,884 grid rows. October 2025 is genuinely absent and
is not interpolated. The empirical audit must recompute these facts rather
than accept the arithmetic alone.

Rows with \(T_{ot}=N_{y,ot}+N_{o,ot}>0\) contribute to the criterion. A row
with one stock equal to zero remains a valid boundary contribution. A
both-zero row remains visible in balanced-grid accounting but has no criterion
contribution.

## Criterion and exact parameter

For a positive-total row, define the conditional mean share

\[
p_{ot}=\frac{\mu_{y,ot}}{\mu_{y,ot}+\mu_{o,ot}}.
\]

The frequency-weighted grouped-binomial criterion contribution is

\[
\ell_{ot}=N_{y,ot}\log p_{ot}+N_{o,ot}\log(1-p_{ot}),
\]

with

\[
\operatorname{logit}(p_{ot})
=\log\!\left(\frac{\mu_{y,ot}}{\mu_{o,ot}}\right)
=\alpha_o+\lambda_t
+\sum_{q=2}^{5}\beta_q\mathbf 1\{Q_o=q\}\mathbf 1\{t\geq 2023\text{-}01\}
+\theta\,WebbZ_o\mathbf 1\{t\geq 2023\text{-}01\}.
\]

The headline \(\beta_5\) is the Q5-versus-Q1 post-2023 change in the log ratio
of conditional mean employment stocks under the declared occupation and month
nuisance restrictions and Webb-software interaction. Its unit is log points.
`100[exp(beta_5)-1]` is a ratio-percent transformation only when labeled with
that denominator and comparison. It is not a percentage-point change in an
individual employment probability.

The word “likelihood” is used only as shorthand for the algebraic
grouped-binomial criterion. Because the inputs are continuous survey-weighted
stocks, the audit does not claim a literal binomial sampling model of
independent people.

## Row-count reconciliation

The audit keeps the following objects distinct and enforces the identities its
input receipt can actually support:

- source-file rows are physical integer rows read from the wide and March-repair
  inputs; the two by-source counts must sum to the reported total;
- eligible employed ages-22–65 source records are physical integer records after
  the March replacement and all age, employment, and positive-weight rules; the
  two by-source counts must sum to the reported total, and the repair-specific
  count must equal the repair by-source component;
- invalid raw-occupation records are an integer subset of those eligible source
  records and are excluded before routing;
- wide-file March rows removed under the replacement rule, and their
  positive-weight subset, are reported separately as physical input-row counts;
- route-expanded descendants are physical integer in-memory rows, but are not
  distinct respondents because one source row can have several descendants;
- intermediate routed age-level aggregates and final occupation-month rows are
  integer row counts at their respective aggregation levels;
- `young` and `older` are real-valued weighted stocks, not row counts; they can
  be fractional because of released survey weights and bridge allocation;
- the six-field target router does not construct “respondent equivalents,” and
  the audit never substitutes them for a physical record count; and
- unique longitudinal people and households cannot be recovered from this
  aggregate product and therefore are not reported by this module.

The empirical audit will verify the total/by-source identities above, that every
receipt field labeled as a physical row count is a nonnegative integer, that
the raw-field universe is exactly the canonical six fields, independently
classify static rows, count noninteger stock values, and reconcile aggregate
stock sums to the upstream weight-once receipt. It will not equate any of these
quantities.

The route receipt is not accepted at face value. The audit recomputes, in total
and by source, the invalid/valid, early/current, matched/unmatched,
bridge-descendant, allocation-class, direct-route, and total-contribution
identities. It also reconstructs each reported stock-conservation gap from its
components, requires exact repair-month membership, and verifies that the
bridge mass is one. A passing Boolean with inconsistent components fails.

## Authentication and failure rules

`TARGET_AUDIT_SPEC.json` binds the canonical V2 contract, the final Gate-1
cell-build contract, this runner, and the inspected R3 cell/estimator source by
content hash. The runner fails closed on a changed identifier, byte hash,
equation-relevant semantic assertion, receipt status, source hash format,
authorization chain, cell hash, schema, assignment fingerprint, support,
calendar, age labels, weight-once receipt, route conservation result, or row
partition.

Producer authentication is exact rather than presence-based. The complete
canonical source-hash map, the exact authenticated subset, the one declared
unread historical source, every authorization subcheck, runtime and historical
code maps, builder and empty-transitive hashes, clean committed-Git fields, and
runtime payload must all equal their bound contracts. Missing values cannot
pass through a `None == None` comparison. The bound SCC payload is CPython
3.13.8 on x86-64/glibc 2.28 with NumPy 2.5.1, pandas 3.0.3, pytest 9.1.1, and
SciPy 1.16.2; the compute-node kernel release is recorded in the producer
receipt but is intentionally nonbinding across SCC patch-level variation.
The Git check resolves the receipt commit as an actual commit object, derives
its tree, verifies required ancestry, hashes every declared blob at that
commit, and requires the consuming checkout's HEAD/tree to be that producer
commit with an empty porcelain status. Forty hexadecimal characters alone are
not accepted as provenance.

The assignment check reads decimal floats with round-trip parsing and hashes
the exact binary `webb_z` value through `float.hex`; a parser-induced last-bit
change therefore cannot silently alter or falsely reject the assignment lock.

The output destination must be a new leaf outside both the Git repository and
the authenticated input leaf. The runner writes only a sanitized target audit,
row-accounting table, human-readable report, and execution receipt. It stores
no resolved private path, credential, row-level record, or coefficient.
Both the unresolved destination and its post-resolution target are checked with
`lexists`, so a dangling symlink cannot masquerade as a new output leaf.

## Acceptance

The T01 runner can support an empirical `VERIFIED` state only after a passing
receipt exists and is separately reviewed and integrated into the project
ledger and manuscript/table notes. Until then, code and tests are
`IMPLEMENTED_UNRUN`; this document alone is not empirical evidence.
