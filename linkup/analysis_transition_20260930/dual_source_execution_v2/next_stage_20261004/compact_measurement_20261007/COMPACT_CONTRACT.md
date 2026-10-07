# Compact three-object extraction contract v1.0

This capped test measures three applicant-facing experience concepts only:

- `general_work`: unrestricted total work or employment experience. A role, function, task, sector, market, client type, or tool restriction excludes the mention from this object.
- `occupation_task`: experience in a role, occupation, function, or task, including broad alternatives such as experience in A, B, or C roles.
- `industry_domain`: experience in an industry, sector, domain, market, client population, or subject area.

Tool-specific experience and all technology-role or AI classification are outside this test. Earlier arm assignments remain candidate labels; this test does not validate them.

The model returns one small JSON object containing exactly one finding per object. It does not return record IDs, hashes, span IDs, or offsets. Deterministic code binds each output to its source row by position, supplies the record ID and exact source hash, and expands each unique exact quote to zero-based, end-exclusive offsets.

Each finding has one state:

- `positive`: one or more applicant conditions are present.
- `no_experience`: the text explicitly says experience in this object is not needed.
- `not_mentioned`: no applicant condition for this object appears.
- `unknown`: relevant wording exists, but the object or polarity cannot be resolved.

Every positive mention labels:

- `condition_mode`: `prior_experience`, `knowledge_proficiency`, or `unknown`.
- `strength`: `required`, `preferred`, or `unknown`, based on local wording and the active section.
- `qualification_scope`: `unconditional`, `education_substitution`, `other_conditional`, or `unknown`.
- `quote`: the shortest exact source substring that still proves the applicant condition, object, strength, scope, and duration. The quote must occur exactly once. If a short quote repeats, expand it until it is unique.
- `duration`: null when there is no supported explicit year amount. Supported forms are `minimum`, `range`, `exact`, and `stated_unspecified`. Maximum-only, non-year, malformed, or unresolved amounts are not converted to a supported duration.

Education substitutions remain conditional. A degree-or-years branch is `education_substitution`, not an unconditional minimum. Preferred experience remains `unconditional` when every applicant faces the same preference; preferred is strength, not qualification scope.

Knowledge, understanding, familiarity, and proficiency are `knowledge_proficiency` unless the wording actually describes prior work, use, or experience. A numeric tenure condition belongs only to `prior_experience`.

Validation is strict about deterministic structure and source support. Missing quotes, non-exact quotes, repeated quotes without a unique longer anchor, unsupported duration shapes, duration values absent from the quoted text, reversed ranges, duplicate objects, and contradictory state/mention shapes fail the record. Whether a reader should have emitted a duration is assessed during semantic review; the validator does not manufacture a duration from unrelated numbers or education alternatives. The validator never deletes or overwrites a conflicting label and performs no semantic repair.
