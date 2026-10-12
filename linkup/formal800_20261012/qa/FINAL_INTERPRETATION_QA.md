# Formal800 final interpretation QA

Date: 2026-10-12  
Status: pre-results interpretation review; aggregate-output acceptance remains pending.

This note is limited to the two frozen comparison families. It does not reopen the sample, rubric, labels, estimators, or execution path. The presently reported audit accounting is 719 primary reviewed contexts and 153 independently reviewed audit contexts. Of the audited contexts, 144 have at least one governed-signature difference and 9 have complete signature agreement. Root will read the fixed 40-context packet (36 disagreements and 4 agreements). Reported disagreement signatures include experience outcomes in 56 contexts, experience clauses in 110, technology roles in 88, responsibility outcomes in 46, and entry outcomes in 6; these categories overlap and must not be summed as contexts.

## Required interpretation boundaries

1. **Audit discordance is not an accuracy estimate.** The 144/153 result is exact disagreement on a broad composite signature, not 144 proven primary errors. The audit reviewer is independent but is not a gold standard, complete-signature agreement is stricter than agreement on any one estimand, and the four agreement cases in root review are checks rather than a basis for estimating accuracy. Do not report an accuracy, error rate, validation rate, kappa, sensitivity, or specificity from these counts. Call them audit disagreements or signature discordance.

2. **The final reviewed data have three materially different provenance states.** Root-adjudicated audit contexts receive complete replacements; unadjudicated audited disagreements have only the conflicting governed fields masked to unknown; unaudited contexts retain the primary review. Audited agreements also retain the primary review. The final release must state this mixture explicitly. It must not describe every retained non-unknown field as independently confirmed, and it must not imply that field masking was applied to comparable latent disagreements among unaudited contexts.

3. **Unknownness is informative by construction.** In audited contexts, observed disagreements create unknown fields; in unaudited contexts, the same possible errors are unobserved and therefore remain coded. Consequently, defined-value rates condition on a selected known-value domain. Their worst-case bounds cover recorded field-level unknowns only. They do not cover undetected primary-review error, disagreement that could have been found under audit, or uncertainty in unaudited records. Differences in defined coverage between groups or outcomes must be shown next to headline rates and discussed before interpreting a rate difference.

4. **Technology disagreement can change comparison membership.** An unadjudicated technology disagreement sets the inventory to unknown, which places the context in `uncertain_technology` and excludes it from the clean GenAI-versus-traditional-software comparison. Outcome unknown bounds within the retained semantic groups do not bound this exposure/group-membership exclusion. The final comparison therefore needs the weighted and unweighted uncertain-technology coverage, plus a clear statement that group misclassification and excluded uncertain membership are outside the bounds and confidence intervals. This concern is especially material given technology-role disagreement in 88 audited contexts.

5. **Context audit counts and advertisement estimands must remain distinct.** The 719 and 153 figures are unique-context counts. Sampling probabilities, weights, support, rates, and uncertainty are advertisement-level, and one reviewed context may map to several sampled advertisements. Do not call 153 the number or percentage of audited ads unless the ad-level public accounting independently shows it. The final audit accounting should identify, in both ad counts and weight mass where available, unaudited primary, audited agreement, root-adjudicated, and audited-unadjudicated/masked records.

6. **Root adjudication is deliberately nonrandom.** The 36 disagreement cases were prioritized by technology, entry, duty, then other differences. Root overturn patterns or agreement with either reviewer cannot be generalized to all disagreements, all audited contexts, or unaudited contexts. The four selected agreements do not repair that selection. Root adjudication can resolve the named cases; it cannot establish global semantic accuracy.

## Comparison-specific acceptance checks

### Comparison 1: experience wording in the two reviewed technology groups

- Describe the result as a design-weighted comparison of wording in delivered current advertisements in the post-exclusion eligible fixed10k frame.
- Pair each defined-value group rate and difference with each group's defined coverage and worst-case field-unknown bounds from the rate/bounds output. The difference confidence interval alone is insufficient because it conditions on potentially different known-value domains in the two groups.
- Do not describe `not_mentioned` as proof that an employer requires no experience or that the concept is absent in reality. A positive means the specified wording was identified; an unknown is not a zero.
- Keep clause summaries at clause level. Years, strength, conditionality, waivers, and alternative branches do not define a unique job-level minimum and must not be averaged into one.
- Treat `genai_use_with_or_without_software` as the frozen combination of exclusive GenAI use and GenAI/traditional-software overlap. Do not relabel it as exclusive GenAI use. Predictive AI, AI development/implementation, background-only, other, and uncertain categories are outside this two-group contrast.

### Comparison 2: strict current-duty wording among entrant-positive advertisements

- The headline is the all-technology-groups estimate among advertisements with explicit entrant wording. Clean GenAI and traditional-software rows are supplementary strata; an unconditional technology-group difference is not the primary Q2 answer.
- State the conditioning denominator every time: duty wording among ads coded positive on the named entry definition. Unknown entry membership is excluded and its weighted mass must accompany the result.
- Duty bounds vary unknown duty values only within the observed entrant-positive domain. They do not bound the effect of unknown entrant membership, technology uncertainty, or unaudited semantic error.
- The broad `including_conditional` measure combines explicit no-experience wording and explicit new-graduate eligibility and may include a waiver of only one experience type. It is a wording co-occurrence measure, not proof of zero total experience, actual eligibility, hiring, or entry-level headcount. Present `unconditional_only` and `explicit_new_graduate_only` as labeled sensitivities, not interchangeable definitions.
- A strict duty positive requires advertised-worker subject plus current-duty relation. Capability, prior experience, client requirements, team duties, and other relations do not satisfy it. A strict zero is available only after a full review with a defined responsibility outcome.

## Support, uncertainty, and presentation

- The common-support rule is an unweighted minimum of five sampled ads in each main semantic group within an occupation major. It is an admission rule, not evidence of adequate precision, overlap quality, balanced design-weight mass, or reliable subgroup inference. Always show the actual sampled counts and design intervals; retain `NA` intervals where design variance is unidentified.
- Common-support pooled results are restricted descriptions. Without a verified eligible-frame occupation composition file, the two groups may have different observed occupation mixes and the pooled contrast is not composition-standardized. Prefer the within-major rows for claims about like occupation majors and label the pooled result accordingly.
- Confidence intervals quantify third-stage stratified sampling uncertainty conditional on the coded semantic groups, known-value domains, and selected support cells. They exclude semantic/model error, audit disagreement, root-selection uncertainty, and support-cell selection uncertainty.
- Use modest numerical precision: counts as integers, weighted rates/coverage/bounds as percentages with no more precision than the design uncertainty supports, and differences in percentage points with their intervals. Avoid ranking small differences whose intervals or unknown bounds make the ordering unstable.
- No result supports historical change, causal technology effects, employer adoption, human-gold accuracy, full-corpus prevalence, fine-occupation/title/firm claims, or claims about actual worker experience and duties. The target remains delivered-text wording in the eligible post-exclusion finite frame.

## Aggregate-output acceptance gate

Before public release, verify from the actual public aggregate files and receipt that:

- the analysis receipt binds the final validated reviews and the passing root overlay receipt, reports 800 sampled ads, uses only `w3 = 1/pi3`, and repeats the unknown/CI claim boundaries;
- public audit accounting uses unique-context counts for reviewer comparison and ad-level counts for the estimand, without conflating the two;
- Comparison 1 exposes both groups' sampled counts, defined denominators, defined coverage, unknown bounds, and design intervals, and the surrounding text discloses uncertain-technology exclusion;
- Comparison 2 exposes sampled and weighted entrant-positive denominators, unknown entrant-membership mass, duty-unknown counts, conditional duty bounds, and all three entry definitions;
- every occupation-major result satisfies the frozen five-per-group support rule, unsupported cells are absent from supported claims, and pooled common-support wording states whether composition standardization was unavailable;
- `NA` intervals, empty denominators, and unknowns remain visible rather than being rendered as zeros or omitted; and
- figures and prose use the same denominator, scope, technology grouping, and entry definition as their source rows, with no implied semantic-accuracy claim.

Acceptance of the final presentation is deferred until the public aggregate paths are available for this bounded check.

## Actual corrected-final acceptance — job 46394029

Status: **pass with the interpretation limits above**. This acceptance covers the corrected final aggregates and figures downloaded to `formal800_20261012/results`; the separately scheduled primary-baseline comparison remains pending.

- Every published CSV SHA-256 matches `ANALYSIS_RECEIPT.json`. The analyzer code hash also matches the reviewed local code. The figure receipt binds both comparison tables and the bounds table, and its four figure hashes are present.
- The receipt records 9,282 eligible-frame ads, 800 sampled ads, 719 validated contexts, 160 audited ads, 153 audited contexts, and 40 embedded root resolutions with a passing overlay receipt. The six T1 stratum rows conserve 800 sampled ads and 9,282 eligible ads. Main weights are exclusively `1/pi3`: candidate strata are censuses with weight 1; no-hit weights are approximately 11.812, 12.547, and 13.230.
- Reviewed technology counts are 71 GenAI-use ads (14 GenAI-only plus 57 GenAI/software overlap), 271 traditional-software-use/no-AI ads, and 222 uncertain-technology ads. The latter are excluded from Q1, and that membership exclusion remains outside the outcome-unknown bounds and confidence intervals.
- Four occupation majors meet the frozen five-per-group rule: 11, 13, 15, and 17. Their main-group sample counts are respectively 20/73, 12/30, 18/133, and 7/11 for GenAI/software. The common-support pooled result is not composition-standardized.

For Q1, the all-reviewed design-weighted GenAI-minus-software differences are 9.4 percentage points for general work experience (95% design CI -1.9 to 20.8), 6.8 for occupation/task experience (-0.1 to 13.8), 14.9 for industry/domain experience (3.1 to 26.8), and 26.1 for tool-specific experience (16.3 to 35.9). The four-major common-support differences are 15.6 (2.3 to 28.9), 5.4 (-2.5 to 13.4), 10.9 (-2.3 to 24.2), and 22.9 (12.1 to 33.7) percentage points, respectively. Thus tool-specific wording is the clearest result across both scopes; industry and general-work comparisons are scope-sensitive, and occupation/task intervals include or nearly include zero.

Q1 defined coverage is high but not complete. Across all reviewed occupations, GenAI/software coverage is 98.4%/94.4% for general work, 92.1%/94.8% for occupation/task, 98.4%/96.1% for industry/domain, and 95.3%/98.4% for tool-specific experience. Each defined rate lies inside its published recorded-unknown bounds. These bounds do not address the 222 uncertain-technology ads, unaudited semantic error, or model error.

For Q2, the broad conditional-or-unconditional waiver/graduate definition contains 54 sampled wording-positive ads with weighted mass 254.3; unresolved entry membership has additional weighted mass 11.8. Any strict advertised-worker current duty is estimated at 50.3% among defined duty labels (95% design CI 30.0% to 70.6%), with five sampled duty-unknown ads and a recorded-unknown bound of 47.0% to 53.6%. Independent judgment is 40.2% (20.9% to 59.5%; bound 39.9% to 40.7%), client ownership 6.8% (0% to 16.3%; bound 6.5% to 11.4%), people supervision 4.9% (0% to 14.0%), and training/mentoring 13.3% (0% to 26.8%; bound 12.5% to 18.6%).

The narrower explicit-new-graduate definition contains 33 sampled positive ads with weighted mass 103.6 and the same separately reported 11.8 weighted unknown-membership mass. Any strict current duty is 42.6% among defined labels (95% design CI 12.3% to 72.9%), with five duty-unknown ads and a 35.8% to 51.7% recorded-unknown bound. These are conditional wording estimates, not rates of actual eligibility, hiring, or entry-level employment.

The figures are legible and use the intended rows. Figure 1 states that uncertain technology and unknown outcomes are excluded and points readers to T6 bounds; Figure 2 uses all technology groups and distinguishes the broad wording definition from explicit-new-graduate wording. All intervals describe sampling uncertainty only. No accuracy, causal, historical-change, employer-adoption, or full-corpus claim is supported.

## Same-sample primary-baseline comparison acceptance — job 46394098

Status: **pass**. No material artifact or interpretation error was found. Every primary-baseline CSV matches its analysis receipt, every baseline-versus-final CSV matches the summary receipt, and the summary script hash matches the reviewed source. The baseline and final receipts bind the same analyzer version and code hash, frozen sample-map hash, 9,282-ad frame, 800 sampled ads, 719 contexts, `1/pi3` weighting, and estimand. The comparison is therefore same-sample and same-estimator.

The four common-support majors remain 11, 13, 15, and 17. No Q1, Q2, or support row is lost or newly created. Technology membership nevertheless changes materially: the GenAI-use group falls from 84 to 71 sampled ads, the traditional-software group from 286 to 271, and uncertain technology rises from 136 to 222. One old-arm/semantic-group transition cell is baseline-only. Baseline-versus-final deltas therefore combine root adjudication, field-level conflict masking, and consequent comparison-membership changes; they are not paired corrections of a fixed set of observations.

Within the four common-support majors, the GenAI-minus-software experience gaps change as follows:

- general work: 11.60 to 15.58 percentage points;
- occupation/task: 5.95 to 5.44 percentage points;
- industry/domain: 2.80 to 10.95 percentage points; and
- tool-specific: 24.44 to 22.94 percentage points.

The tool-specific contrast is comparatively stable and remains the strongest descriptive result. The industry/domain contrast is highly sensitive to adjudication, masking, and membership changes. General-work and occupation/task changes are smaller, but neither sign preservation nor interval movement establishes semantic correctness. These are descriptive procedure-induced changes, not causal robustness checks, error-correction estimates, or accuracy measures.

The Q2 headline rate increases do not reflect additional positive ads or additional positive weighted mass. For explicit-new-graduate wording, the sampled positive count stays 33, weighted entry-positive mass stays 103.5969, and the positive numerator stays 37.0425. Five duty labels become unknown, reducing the defined denominator from 103.5969 to 87.0499; the defined-value rate therefore rises from 35.76% to 42.55%. Its worst-case lower bound remains 35.76%, while the upper bound expands to 51.73%.

The same mechanism applies to the broad waiver-or-graduate definition: the sampled positive count remains 54, weighted entry-positive mass remains 254.2952, and the positive numerator remains 119.6394. Five duty labels become unknown, reducing the defined denominator to 237.7482; the defined-value rate rises from 47.05% to 50.32%. Its lower bound remains 47.05%, while the upper bound expands to 53.55%. Unknown entry-membership mass remains separately reported at 11.8123 in both versions.

Accordingly, the final Q2 rates must not be described as more entrant-positive ads having duties. They are rates among the smaller final defined-duty denominator. Neither the baseline comparison nor the corrected final supports causal, full-corpus, human-gold-accuracy, sensitivity, or specificity claims.
