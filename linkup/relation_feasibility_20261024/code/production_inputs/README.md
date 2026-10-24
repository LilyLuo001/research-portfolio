# Fixed non-oracle technology role inputs

This is preparation code for the existing bounded recovery, not a training or
corpus job. The scheduler wrapper creates a new `production_inputs_v1` directory;
an existing directory causes a stop. Frozen engine checksums must match the
unchanged accepted v1.2 code before any context processing.

The complete recovered normalized contexts enter `rule_engine.extract` without
reference fields. An output-normalization identity check rejects a changed
coordinate system. Each existing frozen technology evidence clause is rescanned
with its original `TECH[family]` compiled pattern only to recover the term offsets
omitted by the old evidence schema. The term sequence must match the frozen
engine output exactly. Each entity receives one fixed model string containing
192 Unicode characters on each side and literal `[TECH]`/`[/TECH]` markers. Do
not feed frozen role cues, reference names, family labels, quotes or compatibility
states into the model. All candidates, including negated ones, are retained.

`CANDIDATES_PRIVATE.jsonl` and `CONTEXT_STATES_PRIVATE.jsonl` are closed before the
teacher item file is opened. These are deployable candidate inputs. Teacher
references subsequently assess coverage and associate accepted supervision when
the candidate's literal term equals the accepted technology name under casefold
and its entity coordinates lie inside an original exact evidence occurrence.
No aliases or fuzzy matching are introduced. A reference with zero or multiple
compatible occurrences remains in the denominator and keeps its state. A
candidate linked to conflicting or multiple reference items is not fitted.
Unlabeled candidates do not become negatives.

`TRAIN_COMPATIBLE_PRIVATE.jsonl` is the only fitting input. It contains model
strings and original role labels for unique compatible train examples. Original
final1331 membership and every legacy holdout are independently recomputed from
the recovery freeze, checked against item splits, and excluded from this file.
The four output IDs in `LABEL_DICTIONARY.json` are fixed in their listed order.
Use `CANDIDATE_SUPERVISION_PRIVATE.jsonl` to identify the compatible evaluation
subset by ID, and use **all** `REFERENCE_COVERAGE_PRIVATE.jsonl` rows for candidate
recall and pipeline denominator accounting. Evaluate reserved holdouts separately
from the previously exposed final set. No random development subset is created.

`PREPARATION_PUBLIC.json` reports reference-item and deduplicated original-context
support by original split and role, candidate coverage, compatible support,
normalization refusals and ambiguity/conflict/unlabeled states. Before fitting,
root must inspect actual support and refusals. Coverage and classification here
refer to technology attributes within these recovered contexts; they do not
certify atomic entity pairs, the complete fixed frame or whole-corpus relations.

Local verification is syntax compilation only. Real context preparation must run
as a scheduled SCNet job. No fit, SSH, new labels or local advertisement processing
was performed in authoring these files.
