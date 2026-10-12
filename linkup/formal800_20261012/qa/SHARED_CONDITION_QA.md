# Shared-condition validator QA

Static review result: **PASS**. No findings require a code change.

- `validate_reviews.py` changes only the alternative-reference cross-field rule (plus the validator version string). A clause may now reference a declared qualification group with `alternative_branch: null`, correctly representing a condition shared by the real alternatives without inventing an additional branch.
- The revised rule still rejects an orphan branch, a reference to an undeclared group, and a reference to an undeclared branch. A branch is checked only after its group is confirmed as declared.
- The schema continues to require both `alternative_group` and `alternative_branch` fields and permits each to be either a string or `null`; no schema constraint was relaxed.
- The identity and packet binding, record completeness, schema validation, exact-quote resolution, reviewed-full nonmention rule, experience/entry/responsibility positive-support checks, technology inventory consistency, and year-bound checks are unchanged.
- `qa_shared_conditions.py` supplies every key accessed by `validate_cross_fields`. Its six independent cases exercise the three accepted forms (declared shared condition, declared single-branch condition, and unassociated clause) and the three rejected forms (orphan branch, undeclared shared group, and invented branch). The negative cases require exactly one matching error, so an unintended additional failure is also detected.

Per the QA constraint, these findings are from static inspection only; the script was not executed locally.
