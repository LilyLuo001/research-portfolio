# Stage C V6 bounded freeze

Status: frozen after one concentrated education/experience repair. V5 was not modified.

V6 adds bounded structural recognition for `Required Skills`, `Job Specification`, and embedded minimum education/experience headings; a credential-plus-duration qualification line can be recovered from an inherited duties section only when credential and explicit duration share the same bounded AND/OR line. It recognizes `High School or Equivalent` and slash-separated graduate abbreviations in those qualification contexts. A current-year student phrase is retained only as an exploratory current-enrollment mention: it is not an attained degree, an unconditional education requirement, or a released positive qualification flag. Compensation eligibility phrased around a sign-on or relocation bonus is excluded from job-experience requirements. The Swedish diagnostic remains outside the English parser scope and no foreign-language phrase rule was added. Model-disagreement cases did not trigger an experience rule.

Rows whose V5 evidence was already truncated at the 100-item cap are not post-processed by V6. Their original totals, summaries, and module truncation flags are preserved, and `v6_candidate_incomplete=true` excludes them from semantic denominators. This avoids treating an unseen evidence tail as inspected.

Verification before freeze:

- Final parser SHA-256: `d8df533693cb9c01f169df51cac184f144888a1595bb28207deb82952ad2f744`.
- Frozen V5 base SHA-256: `336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd`.
- Seven focused V6 tests passed, including a greater-than-100-evidence truncation test.
- All 61 existing V5 parser/export regression tests passed.
- No diagnostic or advertisement identifiers occur in the parser.

The old 32-row diagnostic is development evidence, not a gold standard or an accuracy estimate. NEW48 was read only after the final parser freeze and did not trigger another parser cycle. Its model-reference results limit interpretation: education candidate detection was observed for 17 of 30 model-positive rows and experience detection for 32 of 35. Bulk education and joint tables are therefore measurement-audit candidate-detection tables, not true prevalence. Parser-detected no-experience phrases are candidates, not validated true absence.
