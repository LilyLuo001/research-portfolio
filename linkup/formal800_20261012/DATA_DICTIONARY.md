# Formal800 production data dictionary

Status: production output pending. This dictionary describes the frozen analysis contract; it contains no estimates and invents no numbers.

## Scope and common conventions

The main estimand is the post-exclusion eligible fixed10k advertisement frame. The approved sample is 800 ads representing 719 byte-identical complete review contexts. Advertisement-level counts, probabilities, weights, audit indicators, and uncertainty remain ad-level even when a context is read once for several ads.

The main design weight is `w3 = 1/pi3 = N_h/n_h`, within frozen arm-by-entry stratum `h`. `pi3` is the third-stage inclusion probability. `pi12` and `nested_design_weight` are retained as lineage fields only; missing upstream values remain null, are never imputed, and parent-frame inference is off for this release. Sampling intervals describe design uncertainty conditional on the reported semantic groups and support cells; they are not model-accuracy intervals.

Outcome fields use `1` (present/positive), `0` (not mentioned/negative), and `NA`/null (unknown, unresolved, or not defined). Unknowns are not majority-voted, propagated to unsampled ads, or silently coded as zero. Defined rates use the weighted known-outcome domain; unknown bounds use all weighted ads in the relevant group. Confidence intervals use stratified SRS delta-ratio linearization with the finite-population correction; a non-census stratum with `n_h < 2` has unavailable design variance.

## Production tables and files

| File | Purpose and principal fields |
|---|---|
| `T1_FORMAL_SAMPLE.csv` | Formal sample/accounting by `formal_arm`, `entry_stratum`: eligible `N_h`, sampled `n_h`, `pi3`, `w3`, audited ads, and unique review records. |
| `T1_OCCUPATION_SUPPORT.csv` | Sampled ads by `occupation_major` and semantic group; flags `in_common_support`. |
| `T2_EXPERIENCE_AND_OTHER_RATES.csv` | Weighted rates, coverage, unknown bounds, and design intervals for four experience dimensions, entry wording, and strict current-duty dimensions, by all-reviewed and support scopes. |
| `T2_CLAUSE_SUMMARY.csv` | Clause-level experience summaries by semantic group, object, strength, conditionality, years relation, alternative relation, and branch-conditioned status. Years are literal clause values, not a synthesized global minimum. |
| `T3_OLD_ARM_TO_SEMANTIC_TRANSITION.csv` | Cross-tab of frozen candidate arm to reviewed semantic technology group, with sampled and `w3`-weighted counts. |
| `T4_PRIOR_TABLE_REFERENCE.csv` | Reference to the accepted coverage/timing table and its receipt; no full-base rerun or historical-text claim. |
| `T5_EXPERIENCE_COMBINATIONS.csv` | Four-dimension experience combinations (`general_work`, `occupation_task`, `industry_domain`, `tool_specific`), including `unknown_any`. |
| `T5_ENTRY_BY_STRICT_DUTY.csv` | Co-occurrence of core entry wording and any strict current-duty wording, by comparison group and support scope. |
| `COMPARISON_1_EXPERIENCE.csv` | Main comparison of each experience dimension between `genai_use_with_or_without_software` and `traditional_software_use_no_ai`. |
| `COMPARISON_2_ENTRY_DUTY.csv` | Q2: strict current-duty wording conditional on explicit entrant wording, with entry definition, technology scope, rates/bounds, and support scope. |
| `SUPPLEMENT_TECH_GROUP_ENTRY_DUTY_DIFFERENCES.csv` | Supplementary unconditional technology-group differences; these do not answer Q2. |
| `T6_SENSITIVITY_AND_BOUNDS.csv` | Sensitivity rates, defined coverage, conditionality/unknown handling, and support/bound outputs. |
| `T6_COMMON_MAJOR_STANDARDIZED.csv` | Optional composition-standardized point estimates when a verified eligible occupation composition file is supplied; otherwise absent. |
| `ANALYSIS_RECEIPT.json` | Code/input/output hashes, counts, estimator and weight declarations, validator status, support rule, unknown policy, and claim boundary. |

## Private ad-level measures

`AD_LEVEL_MEASURES.parquet` is a private, unpublished 800-row linkage artifact. It contains no raw advertisement text or evidence. Its key identity/linkage fields are `JOB_HASH`, `SOURCE_FILE`, `SOURCE_ROW`, `RECORD_SOURCE_ROW`, `blind_context_id`, `blind_context_sha256`, `validated_nested_review_record_id`, `validated_nested_review_context_sha256`, and `validated_nested_review_jsonl_sha256`. The canonical ad key is the four `JOB_HASH`/source fields; context hashes bind the validated review.

Design and frame fields are `formal_arm`, `entry_stratum`, `N_h`, `n_h`, `pi12`, `pi3`, `nested_design_weight`, `w3`, `occupation_major`, and `audit_selected`. Technology fields are `semantic_technology_group` (detailed reviewed category) and `analysis_technology_group` (main comparison mapping). The main analysis groups are `genai_use_with_or_without_software` (GenAI use only or GenAI plus traditional software) and `traditional_software_use_no_ai`. Other reviewed states remain distinct: `predictive_ai_or_mixed`, `ai_develop_implement_other`, `background_only`, and `uncertain_technology`.

Measures include `experience_general_work`, `experience_occupation_task`, `experience_industry_domain`, and `experience_tool_specific`; `entry_explicit_no_experience`; `entry_explicit_new_graduate`; `entry_current_student_internship`; `entry_junior_or_entry_label`; `entry_core_including_conditional`; and `entry_core_unconditional`. Strict responsibility fields are `strict_current_duty_independent_judgment`, `strict_current_duty_client_ownership`, `strict_current_duty_people_supervision`, `strict_current_duty_training_mentoring`, and `strict_current_duty_any`. Strict duty is positive only for a complete, non-unknown review where the advertised worker has the current duty; required capability or prior experience alone does not qualify.

## Interpretation boundaries

`entry_core_including_conditional` and `entry_core_unconditional` are legacy names for broad no-experience-waiver-or-graduate wording, with supported conditionality separated by the accompanying fields. They do not mean proven entry eligibility and do not establish zero total experience. The explicit-new-graduate-only duty output is a separate, narrower wording sensitivity using the existing graduate field; it does not override contradictory requirements. Required and preferred language remain distinct.

The Q2 target is current advertised-worker duty wording among explicitly entrant-positive ads. It includes all technology categories in the primary eligible-frame description; clean software/GenAI groups are supplementary comparison strata. Unknown entrant membership is excluded from the conditional domain and its weighted mass is reported. Common support means at least five sampled ads in each main semantic group within an occupation major. It is coarse support for descriptive wording comparisons, not a firm-level, job-level, title-level, or fine-occupation fixed comparison.

All outputs describe the delivered current full text. They do not identify historical change, causal or technology effects, employer adoption, full-corpus prevalence, human-gold accuracy, or semantic correctness of unreviewed ads. Literal clause years remain clause-level and are not a global minimum; alternative branches retain their real relations. Final production remains pending accepted validator and scheduled execution receipts.
