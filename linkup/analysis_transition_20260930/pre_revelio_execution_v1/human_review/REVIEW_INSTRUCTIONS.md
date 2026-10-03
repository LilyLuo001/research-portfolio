# Blind human review instructions

Status: ready for authorized human reviewers after a full canonical frame and heldout-key manifest pass the generator gates.

Review each advertisement from its supplied original text. Do not consult extractor output, model judgments, predicted spans, or aggregate results before the initial labels are locked. The first-observation stratum describes the record's cohort in this delivery; it does not prove that the displayed text was the historical text at that date.

For each explicit experience statement, mark presence, experience object, duration bounds and unit, requirement strength, applicant context, binding, and a short evidence quote. Use `unknown` or `insufficient_text` when the text does not support a decision. Absence of a detected phrase is not automatically a negative label. Multiple experience objects may apply.

Experience objects follow the frozen common measurement categories: `general_work`, `occupation_task`, `industry_domain`, `specific_tool`, and `object_unspecified`. Occupational/task experience remains unavailable in the frozen main extractor under Decision Register D10, but human reviewers should still label it diagnostically when the text supports it. That extractor missingness must later be reported as unmeasured/NA, never as zero.

Technology class and role use the reviewer schema enums. Copy only the minimum text needed to support the judgment into `human_evidence_quote`. Put ambiguity, alternatives, or broken text in `human_uncertainty_note`.

The coordinator assigns all ads to reviewer slot A and the eight prespecified core ads flagged for duplicate review to an independent reviewer slot B. Reviewers must lock their files independently before any comparison. Conflicts are retained and adjudicated once; unresolved cases stay unresolved. Challenge ads are reported separately and never enter probability-weighted prevalence or accuracy estimates.

After return, report assigned, returned, duplicate-reviewed, adjudicated, and unresolved counts. Do not fill missing human labels with model output. The later comparison must be called model-versus-human; a model is never a human reviewer.
