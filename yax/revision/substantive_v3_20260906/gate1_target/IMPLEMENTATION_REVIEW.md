# T01 implementation review before empirical execution

Status: source-code and contract review only; no protected aggregate outcome
file or raw CPS microdata was read for this review.

## Inspected implementation

The Gate-1 target router and its historical reference sources are separately
content-locked in `TARGET_AUDIT_SPEC.json`. Inspection establishes the
following operations:

- `build_six_field_target_cells` asks pandas to read only `YEAR`, `MONTH`,
  `AGE`, `EMPSTAT`, `OCC`, and `WTFINL` from each raw source.
- It removes the five wide-file March samples that the dedicated repair source
  replaces, then keeps only ages 22–65, `EMPSTAT` 10 or 12, and finite positive
  `WTFINL`. The repair source is required to contain exactly those five March
  months.
- It rejects a raw occupation unless `OCC` is an integer from 0000 through
  9999. For 2017–2019 it maps raw Census-2010 `OCC` through the fixed bridge and
  sets `stock = WTFINL * bridge_weight`; from 2020 onward it takes raw
  Census-2018 `OCC` directly and sets `stock = WTFINL`.
- It constructs no respondent-equivalent field. The old general-purpose R3
  modules and their inherited helper columns are byte-locked reference inputs
  for parity tests only; the production target router does not import them.
- It groups routed stock to occupation-month-age-route cells. The downstream
  target construction sums the same routed stock into ages 22–25 and 26–65,
  completes the occupation-month grid with zeros, and applies no new weight.
- The rebuilt treatment contract uses young-plus-older stock for those exact
  ages over January 2017–November 2022.
- The static design creates Q2–Q5-by-post columns and a Webb-z-by-post column,
  with Q1 omitted and post beginning in January 2023.
- The frozen model sets `total = young + older`; the engine removes only rows
  with zero total before fitting. It does not remove a one-sided row merely
  because young or older stock is zero.

The grouped-binomial score for a positive-total row is
`young - total*p`. It follows from the two-stock conditional Poisson algebra
that the linear predictor parameterizes `log(mu_y/mu_o)`. Nothing in the
observed-data schema constructs `log(young/older)`, and such a quantity would
be undefined for retained one-sided cells.

## Contract reconciliation

The canonical V2 contract says the outcome stocks use ages 22–25 and 26–65,
the final survey weight is `WTFINL`, the static model excludes December 2022,
the treatment starts in January 2023, and the target is Q5-by-post relative to
Q1 under occupation, month, and Webb-z-by-post conditioning. The target runner
encodes exact JSON-pointer assertions for these clauses and for the sanctioned
aggregate schema. A changed prose contract cannot pass merely because a file
retains a familiar name or a restamped identifier.

The target runner separately authenticates the cell-builder receipt and checks
the cell file hash, support hash, exact assignment fingerprint, calendar,
balanced grid, stock sums, and weight-once identity. It also requires the exact
two source identifiers; reconciles physical-row and eligible-record totals to
their by-source components; confirms that repair eligibility equals the repair
component; validates replacement, invalid-occupation, routed-descendant, and
routed-aggregate counts as nonnegative integers; and requires the exact
six-field raw universe. This division matters: code inspection establishes the
transformation, while the receipt and aggregate checks establish that the
executed product descended from that transformation.

The producer boundary is fail-closed. The audit compares the complete canonical
source registry to the receipt, separately requires the exact authenticated
subset and the single unread historical source, and checks all three
authorization subchecks. It validates the one-file runtime-code map, the exact
historical-reference map, the builder hash, the explicitly empty transitive
runtime map, and the committed-path hash map. It also binds the full SCC runtime
payload and checks the nested observed-runtime fields for internal consistency.
No load-bearing comparison accepts two absent values as agreement.

Git provenance is resolved rather than self-attested: the receipt commit must
exist, its derived tree must equal the recorded tree, the required ancestor
must be in its history, and the blobs at all four declared paths must reproduce
the specification hashes. The checkout executing T01 must remain at that exact
HEAD and tree with no tracked or untracked changes.

For route accounting, the runner reconstructs every total and by-source record
identity and every reported stock gap from primitive receipt components. It
requires the exact five repair months and verifies that the repair eligible
count is the repair-source component. It accepts neither a standalone passing
Boolean nor a rounded narrative total when the underlying components disagree.

## Scientific precision and remaining ambiguity

The corrected target router now filters to ages 22–65 before routing, so its
eligible-record count and the canonical target-age universe align. The total
and by-source counts are physical input records, not unique longitudinal
people: the same CPS person can appear in more than one monthly record, and the
sanctioned aggregate has no person or household identifier. Route-expanded
descendants are also not respondents, because a pre-2020 source record can map
to several target occupations.

Calling the objective a grouped-binomial “likelihood” is algebraic
shorthand. With continuous CPS-weighted stocks, its transparent description is
a frequency-weighted grouped-binomial estimating criterion (or the conditional
criterion associated with two-age PPML), not a literal sampling likelihood for
independent persons. A conditional-mean-ratio interpretation depends on the
mean specification; it does not by itself supply a causal interpretation.

Finally, a noninteger final stock demonstrates that row counts and weighted
stocks are different quantities, but the final aggregate alone cannot allocate
the fractional part between released survey-weight precision and bridge
routing. T01 needs only the exact distinction and the verified one-time
weight/allocation rule.

## Completion boundary

The code and synthetic tests can establish implementation correctness without
protected outcomes. T01 remains empirically unrun until the target runner
consumes a fresh authenticated Gate-1 aggregate leaf on SCC. Manuscript and
table-note acceptance also remains separate; this source review does not claim
those edits have occurred.

Output publication checks both the unresolved and resolved destination with
`os.path.lexists`, including immediately before atomic publication. A dangling
symlink is therefore treated as an existing destination and is refused.
