# Formal800 methods and estimands

Date: 2026-10-12. This document fixes the analysis before semantic results are available. Real-data execution is restricted to a scheduled SCNet job.

## Scope and units

The probability unit is an advertisement in the post-exclusion eligible fixed10k frame. Historical development, review, and locked-evaluation exact-context groups are excluded before third-stage sampling. The resulting target is therefore the eligible finite fixed10k candidate frame, not the original fixed10k without exclusions, the parent 40,300 candidate design, the full LinkUp corpus, or all jobs in supported occupations.

The semantic reading unit is a byte-identical complete context. Identical contexts selected for several advertisements may be read once, but the validated decision maps only to sampled ads. Advertisement counts, probabilities, weights, audit indicators, and uncertainty calculations remain ad-level.

The main analysis weight is `w3 = 1/pi3 = N_h/n_h`, where `h` is the frozen arm-by-entry stratum after exclusions. This estimates finite eligible fixed10k quantities. `nested_design_weight/pi3` belongs to an optional parent candidate-frame estimand and is excluded from all main tables unless upstream probability lineage is separately verified. Pooled-cell standardization weights remain a separate estimand and are never mixed with design weights. In the actual frozen input, upstream weights are missing for2,000 C-arm ads. Root decision12 therefore disables parent-frame inference for this release; no upstream weight is imputed.

Analysis accepts only a validated-context JSONL whose validator receipt has `status=pass` and whose recorded SHA-256 matches the submitted file. It joins that JSONL to the private selected-ad map on the frozen opaque record ID and exact normalized-context hash. The map retains `N_h`, `n_h`, `pi3`, arm, frozen entry stratum, occupation major, ad-level audit flag, canonical ad key, and the raw exact-text hash; it contains one row per sampled ad even when several sampled ads share a context. A root resolution, if any, is an explicit, complete validator-produced replacement record bound by record ID and context hash in a private overlay. Analysis never infers a resolution from audit agreement, copies a decision to an unsampled ad, or fills missing fields.

## Frozen semantic derivations

The four experience outcomes are coded `present=1`, `not_mentioned=0`, and `unknown=NA`. Explicitly waived clauses are retained separately and do not create an experience positive. Strength, conditionality, alternative branches, and literal years remain clause-level. No minimum or maximum is synthesized into a unique job-level experience requirement.

Core entry wording is explicit no-experience wording or explicit new-graduate eligibility. Internship/student wording and junior/entry labels are separate. The primary core-entry indicator includes supported conditional and unconditional mentions; sensitivity outputs separate unconditional mentions. Contradictory experience evidence remains present and is never collapsed into an entry-positive interpretation.

A strict responsibility positive requires `subject=advertised_worker` and `relation=current_duty`. A strict zero requires a complete review, a non-unknown responsibility outcome, and no applicable current-duty item for that dimension. Partial reviews and unknown responsibility fields remain unknown. Required capability and prior experience may support the broader reviewed outcome but do not count as strict current duty.

Technology groups are derived only from validated explicit inventory:

- `genai_use_only`: generative-AI use for work, without traditional-software-use overlap, predictive-AI activity, AI development/implementation, or unresolved family/role.
- `traditional_software_use_no_ai`: traditional-software use for work and no generative/predictive AI use, development, or implementation, without unresolved family/role.
- `genai_traditional_overlap`, `predictive_ai_or_mixed`, `ai_develop_implement_other`, `background_only`, and `uncertain_technology` remain separate. A nonempty inventory is not itself work-technology evidence.

The main technology comparison is `genai_use_with_or_without_software` (combining `genai_use_only` and `genai_traditional_overlap`) versus `traditional_software_use_no_ai`. This implements prereview root decision10; exclusive GenAI use remains a separate inventory/sensitivity category. Frozen old candidate arms are reported separately, with an old-arm-to-semantic-group transition matrix. Uncertain technology is excluded from the main comparison with its weighted and unweighted coverage reported. Labels are never changed after viewing outcomes.

## Support and reported statistics

The coarse support rule is fixed at five sampled ads in each main semantic group within an occupation major. Common-support occupation majors satisfy the threshold for both groups. Retained ads and design-weight mass are reported. No title-, firm-, or fine-occupation claim is produced.

For each semantic group and supported scope, outcomes report the design-weighted rate among defined values, defined coverage, and worst-case unknown bounds. If `P`, `Z`, and `U` are weighted positive, defined, and unknown totals, the defined rate is `P/Z`, the lower bound is `P/(Z+U)`, and the upper bound is `(P+U)/(Z+U)`. These bounds address field-level missing or unresolved semantic values only; they do not bound undetected model error.

The release includes weighted four-dimension experience combinations, clause-level years/strength/conditionality/alternative summaries, core-entry by strict-current-duty combinations, old-arm transitions, and two main comparison files. Disagreements not root-adjudicated within the cap become field-level unknown. There is no majority vote and no propagation to unreviewed ads.

Experience-combination and entry-by-duty tables carry a common-support scope label; their common-support rows use only occupation majors meeting the fixed five-per-group rule. Rates retain the all-reviewed scope as a descriptive eligible-frame output and always disclose their support scope. Unknown lower and upper bounds use all weighted ads in the relevant semantic group as their denominator; the defined-value rate instead uses its weighted known-outcome domain denominator. Missing/unresolved is reported separately from a coded zero.

## Variance and confidence intervals

Main confidence intervals use stratified simple-random-sampling delta-ratio linearization with `pi3=n_h/N_h` and the finite-population correction. For a ratio `R=Y/X`, define sampled linearized values `z_hi = y_hi - R x_hi`. The estimated variance is

`sum_h N_h^2 (1-n_h/N_h) s_h^2(z) / n_h / X_hat^2`.

A stratum sampled as a census contributes zero. A non-census stratum with fewer than two sampled ads cannot supply a design variance; the corresponding confidence interval is reported as unavailable rather than replaced with a binomial or model-based interval. Intervals are descriptive design-uncertainty intervals and exclude semantic model error.

Cell-specific conditional estimates use the same rule only when their design variance is identified. Otherwise the estimate is retained and its standard error and confidence limits are `NA`.

If a verified eligible-fixed10k occupation composition file is supplied, common-support pooled comparisons may standardize both groups to that fixed composition. Without it, outputs are limited to within-major estimates and a common-support restricted pooled description whose observed group composition may differ; the receipt states this caveat.

## Table boundaries

- T1: formal sample, exclusions, review coverage, weights, and support accounting.
- T2: four experience dimensions plus clause-level years, strength, conditionality, waivers, and alternatives.
- T3: reviewed semantic technology groups and transition from frozen candidate arms.
- T4: references the accepted existing coverage/timing table; no 204.8-million-row computation or historical-text claim is rerun.
- T5: software-versus-GenAI experience combinations and entry/current-duty co-occurrence under coarse common support.
- T6: defined-value, unknown-bound, conditionality, and support sensitivities.

All comparisons describe wording in the delivered current text. They do not identify historical change, technology effects, employer adoption, full-corpus prevalence, human-gold accuracy, or semantic correctness of unreviewed advertisements.

## Q2 execution clarification (root decision13)

The second core comparison directly reports strict current-duty wording among explicitly entrant-positive advertisements. It includes all semantic technology categories in the primary eligible-frame description; clean software/GenAI groups are supplementary strata. Unknown entrant membership is excluded and its weighted mass reported, while bounds address unknown duty values among the explicitly positive entrant domain only. A difference between technology groups in unconditional duty rates does not answer this question and is supplementary. Actual within-major rows are emitted for common-support majors. Clause summaries aggregate meaningful alternative relations and branch-conditioned status, never arbitrary within-record group/branch identifiers. Design intervals condition on the reported groups and support cells; they do not incorporate model error or uncertainty from selecting support cells.

## Q2 wording scope (root decision14, before final estimates)

The frozen no-experience inventory can contain a waiver of a particular domain or experience type. Consequently the broad no-experience-or-graduate indicator must not be called proven zero-total-experience eligibility. It measures text co-occurrence. The separate explicit-new-graduate-only conditional-duty table uses the existing graduate field without rereading, new classification or changing the sample; it is the narrower wording interpretation. Requirements elsewhere in the ad can still conflict, so neither wording measure establishes actual hiring eligibility or entry-level headcount. The original broad and unconditional outputs remain available.
