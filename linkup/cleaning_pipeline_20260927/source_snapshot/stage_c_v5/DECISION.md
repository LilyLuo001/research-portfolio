# Stage C V5 bounded development freeze

Status: frozen after one bounded qualification-presence repair. V4 was not modified.

V5 separates applicant qualification presence from mandatory/preferred strength. `is_applicant_qualification_candidate=true` means a bounded rule found applicant qualification evidence. It does not mean required, preferred, or unconditional. `is_applicant_requirement=true` remains the narrower explicit-strength and locally unconditional flag. Generic `Qualifications`, `Position Specifications`, and education/experience field headings use `qualification_unspecified`; explicit `Position Requirements` retains required strength.

The frozen 24-ad independent-model diagnostic (education TP 8/FN 6; experience TP 11/FN 4) informed this repair and is now development evidence, not V5 validation. All 24 job hashes and normalized-text hashes, plus prior V4 development exclusions, are recorded in `development_exclusions_v5.json` for future validation exclusion/template screening.

Bounded additions cover smart-apostrophe degree forms, coordinated `Bachelor’s or Master’s degree`, `Associates Degree`, `H. S. Diploma`, an appropriate degree from an accredited institution, explicit domain-background wording, applicant-subject `experience and knowledge`, generic qualification scope, and adjacent list-item OR paths. Company/employer/duties/policy contexts, background checks, company history, negation, explicit no-experience statements, and unresolved alternatives remain nonpositive or unresolved as appropriate.

Verification:

- 61 unit/regression/exporter tests passed.
- Fixed 2,926-ad development fixture passed with zero parse, evidence-offset, qualification-scope-offset, source-fingerprint, and JSON-serialization errors.
- Fixture SHA-256: `d19a17c544b6dae9d985653453c620e7f8b8054be92b26f6bfd03535d9540a3a`.
- Parser SHA-256: `336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd`.
- Exporter SHA-256: `ef9e944bffe4c480427cb775c77df3b5489e55b9f60d6a3eab242fa604dc3d6f`.
- Validation report SHA-256: `0ef16816a678a977d689c103aad7b42c3cb9dfed27b953a5d8371cb53ec5a759`.

Four assertions changed because the old contract conflated generic-heading scope with strength: one generic-Qualifications context assertion and three observed real-fixture cases now assert qualification presence rather than a requirement. The exact tests/hashes and reasons are in `validation_report.json`. The unchanged V1–V4 regression suite otherwise remains in `test_v5.py`.

Limits: this is development integrity evidence, not independent semantic validation or a population accuracy estimate. The parser does not build a complete qualification/grade relationship graph. Cross-line OR handling is adjacent-list bounded, domain-background vocabulary is bounded, and unconventional flattened prose can remain unresolved. No full-corpus run, deployment, or new model was performed.
