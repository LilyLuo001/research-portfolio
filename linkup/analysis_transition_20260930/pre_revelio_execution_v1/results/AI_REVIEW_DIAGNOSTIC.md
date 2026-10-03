# AI review diagnostic

This is a **40-ad, stratified AI-review diagnostic**, not a human validation study or a full-corpus accuracy certification. The user replaced the planned human review with two blind GPT-5.6 Sol medium reviews; GPT-6 adjudicated the eight dual-review cases. Reviewers belong to the same model family, so their errors may be correlated.

## Raw dual-review agreement

Agreement below uses the eight untouched A/B labels, before B amendments and GPT-6 adjudication. It measures reviewer agreement, not accuracy.

| Item | Agree | Disagree |
|---|---:|---:|
| Experience presence | 8/8 | 0/8 |
| Experience-type exact set | 3/8 | 5/8 |
| Technology-class exact set | 6/8 | 2/8 |

## Candidate parser versus final review

The table reports exact 2×2 counts for the four measurable experience objects. `occupation_task` remains unavailable in the production measurement and is therefore NA rather than a negative. Review-uncertain object labels are excluded separately.

| Component | Object | Candidate+/review+ | Candidate+/review− | Candidate−/review+ | Candidate−/review− | Uncertain excluded | Agreement |
|---|---|---:|---:|---:|---:|---:|---:|
| core | general_work | 5 | 0 | 3 | 23 | 1 | 90.3% |
| core | industry_domain | 4 | 2 | 9 | 17 | 0 | 65.6% |
| core | specific_tool | 4 | 1 | 15 | 12 | 0 | 50.0% |
| core | object_unspecified | 1 | 22 | 1 | 8 | 0 | 28.1% |
| challenge | general_work | 2 | 0 | 1 | 5 | 0 | 87.5% |
| challenge | industry_domain | 2 | 0 | 6 | 0 | 0 | 25.0% |
| challenge | specific_tool | 0 | 0 | 2 | 6 | 0 | 75.0% |
| challenge | object_unspecified | 0 | 3 | 0 | 5 | 0 | 62.5% |

The core contains 32 stratified draws; the eight challenge ads were deliberately selected from broad-binding and exact-or-unspecified-duration boundary strata. Challenge results therefore should not be pooled into prevalence or accuracy estimates.

## Anonymized examples from observed disagreements

- A requirement framed as experience with a named business process was sometimes promoted to overall work experience; final review treated it as task or domain experience.
- A bare proficiency requirement for enterprise software did not by itself establish prior work experience with that tool.
- An education-substitution formula was not treated as a career-experience duration threshold.
- Work alongside generative-AI systems was distinguishable from developing the underlying model. Employer product descriptions and job duties were also distinguishable from applicant-experience requirements.
- Predictive-AI classification showed a structural boundary problem in this sample. It is reported as a diagnostic failure mode, not scored as accuracy.

Technology-role review is qualitative because the review form was not exhaustive for every complex role. Only clear quoted roles in applicant-requirement context were considered; unlabeled complex roles were not forced to zero. Duration claims were capped at six per ad and are non-exhaustive, so numeric-bound disagreements are diagnostic examples rather than precision or recall estimates.

## Interpretation

T2, T3, and T5 semantic results remain **candidate measurements**. This review identifies useful boundary failures but does not certify corpus-wide accuracy. The sample is strongly stratified, includes eight deliberately difficult challenge ads, uses same-family AI reviewers, and has unverified exclusion of the historical held-out set. The frozen baseline was rerun on these same 40 ads rather than recovered as an original saved row-level artifact; all 40 rerun sampling strata matched the saved strata.

The comparison is between the frozen dictionary-based production objects and conceptual review labels. Disagreement can reflect vocabulary coverage or object-definition differences, as well as extraction mistakes. It is not automatically a count of coding bugs, and these unweighted stratified counts must not be extrapolated to the corpus.
