# Year mention to original accepted experience object

`prepare_year_object.py` runs only in an actual SCNet Slurm job. Its six required
arguments are `--recovered`, `--input-manifest`, `--frozen-rule-dir`,
`--expected-rule-sha256`, `--expected-legacy-sha256`, and `--output`. Output must
not exist. The existing recovery manifest, contexts and original items are reused;
this script does not recover or amend them.

Optional `--analysis-frame` accepts only the root-approved parquet SHA256
`70ab7ed24697cf456e738497de4eec02531205294a626a0dab66bb779a0db1a6`.
It reads only normalized context hash, existing Pro technology group, and the
two experience-family status columns. `CONTEXT_STATES_PRIVATE.jsonl` receives
`reference_group` (`GA`, `GB`, `other`, `unknown`),
`reference_group_conflict`, `year_family_status`, `object_family_status`, and
`inventory_eligible` (both families `known` or `not_applicable`). All advertisement
rows sharing a complete context are collapsed without weighting or majority
choice; conflicting groups stay unknown. Without this optional file, checked
frozen-ledger statuses are used and its complete 70,000 family masks are required;
reference technology groups remain unknown. Inventory eligibility does not
require any positive year reference or compatible binding.

Conservative reference-known evaluation must use all predicted candidates in
eligible evaluation contexts as its precision-bound denominator, while confirming
only unique exact original-item links with the correct object. Unmatched candidate
predictions are possible false positives, not gold negatives. Recall uses all
original explicit numeric references, with `not_stated` separately counted.

The production function accepts only the frozen engine, complete text, complete
context hash and independently determined split. It enumerates the unchanged
frozen `YEARS` regular expression once over the complete normalized text. All
numeric spans are retained, including those without an old experience object.
The existing clause offsets and typed experience evidence are attached where
available. A fixed 192-character radius contains `[YEAR]` markers around the
original full numeric mention. No teacher evidence or class selects the span,
window, candidate count or input text. Production candidates are persisted before
the first original-item read.

Binding uses the accepted original year-family item, its exact evidence offsets,
all numeric bounds and original year relation. Unit conversion is the existing
frozen duration conversion, including months. A reference quote must contain the
entire frozen number/range/unit core; it may omit a prefix such as “at least”.
Explicit minimum, maximum, exact and range syntax must agree with the original
accepted relation. Bare scalar syntax can carry an accepted scalar relation only
when its number is conserved. The old predicted object never filters matches.

The same original source SHA, source record, context and item path must also have
an accepted `experience_object` row agreeing with the original year-family
object. Every year reference is retained individually, including `not_stated`,
unmatched, repeated, conflicting and unaccepted object-family bindings. Only one
reference to one candidate in both directions becomes compatible supervision.
Unlabeled and unknown candidates are never negatives; there is no gold
`no_relation` class. A `not_stated` item has no literal year to bind and remains
separately counted rather than a numeric-recall miss or a negative.

`CANDIDATES_PRIVATE.jsonl` is reference-independent production input.
`REFERENCE_COVERAGE_PRIVATE.jsonl` retains each original year item and its bound
source identity and masks. `CANDIDATE_SUPERVISION_PRIVATE.jsonl` retains every
candidate, including unlabeled and ambiguous candidates. Compatible train rows
are in `TRAIN_COMPATIBLE_PRIVATE.jsonl`; both final and legacy-reserved rows are
in `EVAL_COMPATIBLE_PRIVATE.jsonl`. Split names remain `train`,
`final_previously_exposed`, and `previous_holdout_reserved_not_final`.

`LABEL_DICTIONARY.json` preserves the four original core object classes plus every
other observed original object class. No observed rare class is merged or dropped.
Only the marked text is a model input; private supervision metadata and frozen
old object predictions are audit fields, not model features.

The sanitized `PREPARATION_PUBLIC.json` reports item counts, unique context
supports, all binding states, and support gates for every retained class. The
50-train/50-final floor is necessary and is not quality acceptance. It distinguishes
true absence of a frozen numeric candidate in evidence, incomplete literal
numeric/unit containment, numeric-bound disagreement, repeated reference quotes,
multiple candidate matches and multiple original-item matches. Unmatched numeric
references remain in numeric coverage denominators. It also records SHA256 hashes
of code, inputs, all private output files and sorted split membership. The exact
original final1331 and every legacy holdout stay excluded from training. The final
set was previously exposed and remains identified as such.
