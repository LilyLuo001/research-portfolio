Give the execution agent the prompt below together with the manuscript, appendix, both referee reports, and access to the replication repository and authorized data.

[Download the complete execution prompt](sandbox:/mnt/data/revision_prompt/execution_agent_revision_prompt.md)

---

# Execution prompt: substantive revision of the AI-exposure/CPS manuscript

## 1. Role, objective, and inputs

Act as the empirical research execution agent and substantive manuscript editor for Lily Luo’s paper, **“AI Exposure or Occupational Composition? Constructed Measures and Early-Career Employment.”** Execute a revision of the analysis, draft, appendix, and replication package. Do not return only recommendations, an outline, or a response letter describing work that has not been done.

Use both referee reports. **R1** means the earlier report in this conversation, beginning with the recommendation to reject at a top general-interest economics journal. **R2** means the subsequently uploaded referee report, with numbered sections 3.1–3.9, 4.1–4.9, and 5.1–5.11. Read both in full and create a comment-by-comment response matrix. Treat this prompt as an integrated execution specification, not as permission to ignore qualifications in the reports.

Available source files in this conversation are:

* Main manuscript: `/mnt/data/0a7067ca-ce30-46f3-a669-ba1a0ec2ff32.pdf`.
* Online appendix: `/mnt/data/5a436977-088b-47b0-a07d-6ee63d45892b.pdf`.
* R2: `/mnt/data/Pasted markdown(20260905-111135).md`.
* R1: the earlier referee report in the conversation; preserve its text with the revision inputs when available.

These paths identify files in the present conversation; locate the supplied equivalents in another execution environment. Locate the editable manuscript, bibliography, analysis repository, source exposure files, crosswalks, and authorized CPS microdata. These are not established as available merely because the PDFs mention repository paths. Never invent a repository, accessible dataset, executed result, or permission. Inspect filenames and first pages rather than relying on attachment order.

**Scientific objective:** establish what the public-CPS comparison measures, which occupational comparisons and characteristics support it, and how much uncertainty remains. Do not set out to prove either that AI caused the employment pattern or that computerization, pandemic recovery, or occupational composition explains it away. A credible descriptive contribution is an acceptable endpoint.

A provisional organizing question is: **What do occupational AI-exposure comparisons reveal about young-worker employment once overlapping occupational characteristics, limited within-family comparisons, and uncertainty are made explicit?** Finalize the title and central claim only after the revised results are available.

## 2. Rules for adjudicating the reports

Preserve the author’s distinctions between exposure and adoption, stocks and flows, age and experience, nondetection and equivalence, valid alternatives and implementation errors, and different conditional estimands. Resolve requests through evidence and valid methods, not mechanical compliance with every suggested procedure.

Several statements in the reports require explicit methodological adjudication:

**Paired comparisons:** a confidence interval for the conditioned coefficient containing the baseline point estimate does not establish that the coefficient movement is indistinguishable from zero. Use the joint covariance and the paired-difference interval. Conversely, a significant paired movement does not make the residual coefficient precise or identify a causal decomposition.

**Minimum detectable effects:** report the paired and conditional MDEs requested by R2. However, an observed movement below an 80-percent-power MDE can still be statistically significant. An MDE is not a threshold below which an observed result must be called statistically unresolved. Explain this courteously in the response letter rather than reproducing that interpretation from R2. 

**Survey uncertainty:** investigate whether and how cell sampling affects inference. Do not assume that sampling variability is entirely absent from an empirical cluster sandwich simply because a design-based variance was not computed. Equally, do not represent occupation clustering as complete CPS survey-design inference. Do not add variance estimates that may count the same variation twice.

**Permutation and bootstrap suggestions:** within-SOC2 permutation requires an exchangeability argument for inferential use. Different multiplier weights do not automatically fix few-cluster problems. Twelve-month CPS links do not automatically double usable information. Validate these suggestions rather than stating their benefits as facts.

**Economic mechanisms:** correlations with computer use and the lambda pattern motivate diagnostics, not proof of a computer-intensity mechanism. “Direct” versus “software-complement” task exposure does not, by itself, establish which capabilities were deployed during the sample. Broad-family controls can remove AI-related as well as non-AI-related variation.

**External facts:** treat the reports’ claims about other papers, macroeconomic events, software, survey revisions, and data availability as verification tasks. Distinguish their assertions from verified findings. Do not silently convert a referee’s conjecture into the revised paper’s evidence.

Do not select specifications, endpoints, standard errors, controls, or sensitivity parameters to obtain a preferred significance result. Record the revision analysis plan before running new analyses, but do not call it an ex ante preregistration or imply it reverses earlier outcome-informed selection.

## 3. Execution order and evidence management

Start with an inventory and a baseline-reproduction audit. Preserve original files and create a separate revision branch or working directory. Create a specification registry and a results ledger before editing numerical claims.

Prioritize work in this order:

1. **Foundational correctness:** reproduce the existing baseline; repair and document the full pipeline; audit support, scales, calendars, and inference code.
2. **Core substantive revision:** within-family support and economic content; occupational-characteristic conditioning; sampling/dependence analysis; corrected dynamics and trend sensitivity.
3. **Targeted supporting analyses:** BCC comparability, flows, education and industry comparisons, lambda diagnostics, and feasible mapping/coding sensitivities.
4. **Writing and packaging:** rewrite around the validated evidence, shorten the paper, regenerate exhibits, and produce the response documents and reproducible build.

Independent modules may run in parallel after they share an audited specification contract. No module may silently redefine exposure groups, calendar, support, scaling, or weights.

For every analysis, record its hypothesis or descriptive question, estimand, sample, grouping rule, covariates, inference target, implementation status, and output location. Use statuses such as **completed**, **implemented but not executed**, **blocked by missing input**, and **not pursued with methodological justification**.

Missing inputs must not halt all feasible work. Write runnable code and a precise access/variable request for blocked analyses, continue supported edits, and disclose the limitation. Never insert hypothetical results into the manuscript. If only PDFs are available, distinguish reconstructed editable source from original source, and distinguish a provisional editorial revision from an empirically re-estimated revision.

## 4. Rebuild an auditable corrected baseline

**Addresses R1 §§6–7 and additional comments; R2 §§3.8, 4.5–4.6, 4.9, and numerical/documentation comments.**

Reproduce the reported corrected baseline and its declared inferential procedure as a historical checkpoint, not a numerical target that future corrected estimates must match. The submitted manuscript reports approximately −0.1346 with SE 0.0450 and interval [−0.2223, −0.0468]. Investigate discrepancies instead of adjusting code to hit these numbers. 

Distinguish three constructions: the original calendar, corrected outcomes with the historical treatment definition held fixed, and a fully rebuilt corrected pipeline. For the last, recompute every affected preperiod object: employment weights, availability/support rules, normalization, cutoffs, ties, memberships, and subsequent diagnostics. Document whether restoring the five March Basic Monthly samples changes those objects. Keep the historical treatment definition as a comparison, not an unexplained hybrid primary specification.

Audit observed versus expected months, the exclusion of December 2022 from the static model, its separate treatment in dynamic specifications, and the October 2025 gap. Do not interpolate a nonexistent survey month. Reconcile raw records, unique persons or households where measurable, route-expanded rows, fractional counts, fitted cells, and occupation counts. Define fractional unweighted record counts precisely rather than calling them respondents without qualification. Verify that CPS final weights enter the cell stocks once, not twice. Retain valid one-sided zero cells; do not promote a sample selected on minimum realized young-cell counts to the baseline. Check the treatment of cells with both stocks zero.

Verify crosswalk classification systems as well as vintages, split-route probability sums, conservation of weighted stock, code uniqueness, and the construction of broad SOC families. Produce explicit membership and exclusion-reason files for the nonnested occupation universes promised in the manuscript. Recompute support counts after rebuilding rather than hard-coding the submitted counts.

Audit the January 2025 population-control issue and verify the additional January/February 2026 control and January-file-revision issues raised by R1 using official BLS, Census, and IPUMS documentation. Establish exactly which extract and weight vintage the analysis uses. Verify the late-2025 collection, response, and weighting issues before characterizing them.

Provide targeted endpoint/weight diagnostics, including a pre-2025 endpoint, a suitable pre-2026 endpoint, the full window, and exclusion of September and November 2025 around the missing month. Separate the 2023–24 and later associations with paired uncertainty. Do not create subgroup counterfactual weights by mechanically applying aggregate population adjustments. Unweighted fractional counts are a different outcome, not a recovered counterfactual weight vintage.

Create one machine-readable numerical source of truth. Repeated occurrences of an identical estimate must use identical definitions and the declared canonical inference output; explicitly label genuinely different draw sets or procedures.

## 5. Make the broad-family finding economically interpretable

**Addresses R1 §§1–2; R2 §§3.1 and 4.1.**

Replace the implicit “AI versus composition” dichotomy with a comparison-based interpretation. Changes after SOC2 conditioning identify sensitivity to a conditioning restriction; they do not allocate a causal share to non-AI composition.

Build a family-by-quintile support exhibit containing occupation counts, preperiod employment shares, exposure ranges, direct Q1/Q5 overlap, and identifying information. Name the families that span both tails. Explain how the other families connect the conditional Q5–Q1 contrast through intermediate quintiles and what common-coefficient restrictions are needed for those indirect comparisons.

Estimate and report:

* The full Q2–Q5 coefficient profile before and after family conditioning, with a joint test of all four conditional exposure coefficients equaling zero and appropriately simultaneous uncertainty.
* A direct-tail benchmark limited to families containing both tails, with explicit within-family comparisons and transparent aggregation. Label its changed population.
* A continuous within-family exposure companion specification, with its scale and common-slope restriction stated.
* Leave-one-family-out results and the identity and employment trajectories of the occupations/families contributing most to the headline. Retain selected leave-one-occupation-out diagnostics without treating outcome-selected deletions as preferred estimates.

Show young and older employment paths separately for the important families and both tails. Explain whether attenuation comes from a few economically recognizable comparisons or a dispersed pattern. Any proposed narrative about technology-sector contraction, reopening, immigration, or graduate labor supply must remain a hypothesis unless separately supported.

Define the information statistics. For a scalar target, verify whether the implemented quantity is the nuisance-adjusted information

$$
I=\sum_{o,t}h_{ot}r_{ot}^{2},\qquad
s_o=\frac{\sum_t h_{ot}r_{ot}^{2}}{I},\qquad
G_{\mathrm{eff}}=\frac{1}{\sum_o s_o^2},
$$

where \(h_{ot}=T_{ot}p_{ot}(1-p_{ot})\) and \(r_{ot}\) residualizes the target against all nuisance regressors in the fitted information metric. Confirm the implementation rather than assuming this is what the existing tables compute. Distinguish fitted information from pre-outcome residual-exposure support, sampling precision, and the nominal number of independent clusters.

Report absolute and relative information, paired uncertainty for coefficient changes, conditional MDEs, and paired MDEs. Using the submitted SEs gives approximate normal-theory checkpoints of 0.198 for the conditional coefficient and 0.143 for the paired movement; recalculate after the audit. Use

$$
MDE_{80}\approx(z_{0.975}+z_{0.80})SE
$$

only as a labeled two-sided, five-percent normal-theory approximation; distinguish it from power under the actual few-cluster procedure. These are precision descriptions, not extra rejection rules. 

Consider an equal-occupation-weighted companion only after defining its objective and changed estimand. Do not obtain it by casually deleting survey weights from the original objective.

## 6. Confront occupational-characteristic overlap directly

**Addresses R2 §3.2 and §4.2; complements R1 §§1–2.**

Bring the exposure–characteristic correlations into the substantive analysis. Verify the existing computer-use, remotability, wage, education, routine-task, and manual-task inputs, including their vintages, scales, support, and provenance. Use measurements available before the designated post period wherever possible. Do not assume an occupation’s observed average educational attainment is the same as an externally measured education requirement. The existing appendix’s correlation table is the starting point, not validation of any characteristic as the true confound. 

Run a deliberately limited set of one-at-a-time and cumulative conditioning blocks, each interacted with young × post: computer use; remotability; preperiod wage, education, and routine-task characteristics; a defensible pandemic-shortfall measure; and broad-family conditioning. Include a parsimonious combined model when residual variation and rank support it. Explain the ordering economically rather than selecting the sequence that maximizes attenuation.

For each addition, report the baseline and augmented coefficients on identical support, their paired difference and interval, paired MDE, sample coverage, residual exposure variation, and information. Show sample loss separately from the effect of adding a control. Report collinearity and leverage diagnostics and do not interpret a noisy coefficient after removing almost all variation as proof of no AI relationship.

**Pandemic shortfall requires special care.** Construct and document a measure of 2020–2022 employment shortfall relative to a trend estimated from 2017–2019, with transition-month handling consistent with the design. Explain whether it measures total employment or young-relative employment. Avoid arbitrary log pseudocounts for sparse cells; use an estimable aggregation or model and report its limitations.

Because this regressor is estimated from related employment outcomes, investigate shared sampling error and regression-to-the-mean effects. Where feasible, use an independent source or a household/sample-split construction that respects repeat observations. Re-estimate generated quantities within resampling when the declared inference requires it. Do not label the shortfall exogenous simply because it precedes January 2023.

**Industry comparison:** assess whether sufficiently informative occupation × industry × age × month cells can support a broad-industry × young × post analysis. Retain necessary lower-order effects and document any changed sample, objective, or dependence assumptions. Adding the dominant industry of an occupation is not equivalent to conditioning on industry in the underlying microdata. A fixed preperiod industry-share proxy is a separate ecological specification and must be labeled as such.

**Education/cohort composition:** provide a feasible BA+/non-BA comparison or related education-composition analysis, with explicit risk sets and support. Separate changes in young labor supply from differences in occupational task requirements. Treat extrapolated occupation-specific trends as strong restrictions, not an automatic substitute for this analysis.

Neither coefficient survival nor attenuation establishes a causal mechanism. Explain that these occupational characteristics may also describe channels along which AI effects operate.

## 7. Reassess sampling, dependence, and finite-sample inference

**Addresses R1 §3; R2 §3.3. This is core work, not an optional robustness footnote.**

State the stochastic target for each interval: economic-shock uncertainty, repeated CPS sampling conditional on a population, or a justified combination. Describe which dependencies each procedure captures and which it omits.

**Audit existing inference.** Verify nuisance residualization, score construction, Hessian/bread, finite-cluster factors, studentization, paired covariance, null centering, and simulation seeds. More multiplier draws reduce simulation error but do not validate an approximation. Do not clip inadmissible pseudo-outcomes.

**Cross-occupation dependence.** Evaluate broad-family dependence for the baseline, conditional coefficient, and paired movement using an appropriate few-cluster method. Report sensitivity rather than asserting that clustering at SOC2 is uniquely correct. Examine dependence induced by split source occupations and repeated/moving CPS households. Do not substitute the effective-information count mechanically for the cluster count in a reference distribution.

**Rebuild cells under microdata resampling.** Implement an appropriately justified household/sample-unit resampling or multiplier procedure using verified longitudinal identifiers and available survey-design information. Preserve all relevant observations of the same sampled unit across months and preserve each source record’s fractional crosswalk descendants under the same resampling weight. Reconstruct cells and refit the estimator in every replicate. Do not treat the eight month-in-sample categories as eight independent primary sampling units.

Report the resulting sampling-oriented uncertainty separately unless a valid integrated variance construction is derived. Establish whether actual design variables or suitable replicate weights are available for these Basic Monthly data; do not borrow ASEC procedures without justification. Identify any approximation from unavailable public design information. Explain whether support and labels are held fixed or reconstructed, and why; changing this choice changes the uncertainty target.

Do not mechanically add this variance to the occupation-cluster variance. If combining them, derive the decomposition, address overlapping variation, and validate it. Wider intervals are possible, not a predetermined result.

**Time-HAC audit.** Resolve R1’s concern about double-counting lagged within-occupation covariance. Using nuisance-adjusted score contributions \(\psi_{ot}\), investigate the schematic inclusion–exclusion construction

$$
\widehat B=
\widehat B_{\mathrm{occupation}}
+\widehat{\mathrm{HAC}}_L
\left(\left\{\sum_o\psi_{ot}\right\}_t\right)
-\sum_o\widehat{\mathrm{HAC}}_L
\left(\{\psi_{ot}\}_t\right),
$$

with consistent score-sum units, kernels, normalizations, and finite-sample conventions. At positive lags the overlap is not generally just the contemporaneous occupation-month intersection. Determine what the code actually does before diagnosing an error. Use elapsed calendar lags, not adjacency of observed rows across missing months. Document covariance definiteness and any remedy rather than silently repairing a matrix. The submitted appendix’s description is the implementation claim to audit. 

**Finite-sample validation.** Provide at least one valid full-refit benchmark or a coverage simulation targeted to sparse cells, concentrated influence, broad-family shocks, and the actual design. A positive-weight likelihood/microdata reweighting procedure may be appropriate for its stated target; establish that appropriateness. Consider alternative multipliers or jackknife corrections as sensitivity tools, not guaranteed cures. Within-family randomization remains descriptive absent justified exchangeability.

Summarize inference for the same core estimates in one comparison table. Explain any change in the scientific conclusion. Address the planning-versus-realized SE gap without claiming to identify its cause from that gap alone.

## 8. Replace the restricted dynamic diagnostic and implement trend sensitivity

**Addresses R1 §4; R2 §3.4 and §§4.4–4.5.**

Re-estimate dynamics on the corrected pipeline. The submitted event-time model allows Q5 monthly effects but restricts Q2–Q4 to post indicators. Do not use that specification alone to reassure readers about unrestricted tail pretrends. 

Implement either a fully interacted quintile-by-time model or a Q1/Q5-only dynamic comparison, preferably with quarterly or otherwise justified temporal aggregation when needed for precision and covariance rank. Provide the baseline and an informative family-conditioned counterpart. State reference periods, transition exclusions, sample support, and the meaning of every dynamic coefficient. Report joint preperiod uncertainty and explain what economically meaningful drift the design can fail to detect.

Implement a **Rambachan–Roth-style sensitivity analysis** only after verifying its applicability to the estimated parameter. Use the joint event-time coefficient vector and full covariance matrix. Define the postperiod linear functional and its weights. Do not feed a single nonlinear static coefficient and SE into a procedure requiring an event-study vector; do not assume the static grouped-binomial coefficient equals a simple average of dynamic coefficients.

Use a suitable asymptotic approximation or a clearly labeled companion estimand, documenting its relationship to the headline. Verify covariance rank and software requirements. Consider relative-magnitude and smoothness restrictions, report a transparent parameter grid and sensitivity intervals, and explain their economic meaning in the chosen time units. Report zero-exclusion breakdown values for both the baseline and conditional comparison where well-defined. If the relevant no-deviation benchmark already includes zero, report that there is no positive zero-exclusion robustness to lose rather than inventing an “overturning” threshold.

Keep historical pseudo-breaks as descriptive context, not a substitute for this analysis or an exchangeability-based test. Distinguish the absence of detectable pretrends from evidence validating parallel trends.

Add lower-dimensional seasonality controls, such as exposure-group-specific young-relative month-of-year effects, and/or matched-calendar-month windows. Failure of the highly saturated occupation-season model is not a reason to omit simpler seasonal diagnostics. Examine a limited set of economically motivated windows, including a post-2020 coding-stable window where feasible.

Report the complete proposed onset-date sensitivity from November 2022 through June 2023 without choosing the best date. Explain the original January 2023 choice and its chronology. Align partial-year endpoints and foreground where in calendar time the association emerges. Simultaneous or family-wise summaries should be used for coherent collections of comparisons; acknowledge that they do not erase earlier exploratory selection.

## 9. Make the BCC comparison genuinely comparable

**Addresses R1 §5; R2 §3.5 and version comments.**

Verify the exact Brynjolfsson–Chandar–Chen version, classification, weighting base, exposure cutoffs, sample, endpoints, outcome definitions, and controls. Check the CPS/ACS comparisons identified in R1 before claiming novelty for producing a public-CPS exercise.

Distinguish reproducing a public grouping rule from reproducing identical occupation assignments. Provide membership concordance or explain why exact concordance cannot be verified. Align endpoints and the CPS employment population as closely as feasible with the relevant payroll concept; state what remains unmatched.

Report the BCC-style top-two-versus-bottom-three comparison under the baseline, SOC2-by-post, and SOC2-by-month specifications, with common support and paired uncertainty. Do not assume the Q5–Q1 conditioning result carries over to another contrast. Clarify the manuscript’s ambiguous “unconditioned result” wording.

Compare employment stocks with employment stocks first. Verify the motivating study’s hiring and separation analyses rather than describing its entire contribution as a hiring-rate estimate. Do not compare numbers with different age groups, denominators, grouping rules, time horizons, or units as though they were competing estimates.

Attempt the suggested stock-flow calibration only if compatible flow quantities can be measured. Write a stock-accounting model including nonemployment entry/exit, relevant occupation switching, and aging into/out of the 22–25 group; address the older denominator and residual population/sample-composition changes. State how employer hires relate to CPS transitions, including job-to-job moves the latter may not capture. Show uncertainty and assumptions rather than an unsupported single implied stock response. If not identified or comparable, explain the precise gap and narrow the bridge rather than manufacture a calibration.

Verify whether firm-time controls in the motivating design absorb the relevant comparisons; do not equate them automatically with SOC2-by-age-by-time controls.

## 10. Promote useful mechanisms without inventing unavailable outcomes

**Addresses R2 §3.6, §§4.2–4.3, and R1’s stock/flow and denominator cautions.**

Bring a compact, valid flow table into the main text, with enough explanation to make its imprecision informative. Rebuild it using the corrected data and clearly defined longitudinal samples. Report effect units, risk sets, uncertainty, and feasible MDE summaries. Maintain the distinction between employment exit, occupation switching, and allocation across destinations conditional on entry.

The existing entry-destination estimate is not an employment-finding probability or an employer hiring rate. Do not describe signs consistent with one story as identification of that story. 

Evaluate adjacent-month and twelve-month links using official linking definitions and appropriate weights. Document eligibility, attrition, aging, occupation-code transitions, and the different time horizons. Longer-horizon endpoint transitions are not interchangeable with monthly flows and may miss intervening changes. Quarterly pooling does not create independent observations; preserve person/household dependence.

Prepare a feasibility assessment for hours, weekly earnings, unemployment incidence and duration, and labor-force participation. Execute the most informative valid specifications without turning the paper into an indiscriminate outcome search. Respect earnings-sample restrictions and weights. Nonemployed people do not generally have a comparable current occupation: use a defensible prior-occupation/longitudinal risk set where available, or explicitly define a different population-level estimand. Never assign an occupation to never-employed or out-of-labor-force respondents merely to complete cells.

Show young and older stock paths separately in uncluttered exhibits and explain that the older group need not be untreated by AI. Retain the near-age comparison as a descriptive sensitivity, not a cure for education/cohort composition.

## 11. Retain the informative exposure diagnostics and narrow the measurement claim

**Addresses R1 §5 and additional scale comments; R2 §§3.7–3.9 and §§4.6–4.8.**

Move a concise lambda diagnostic into the substantive discussion. On common support and the same corrected model, evaluate \(D+\lambda S\) over the proposed grid. Show exposure correlations with occupational characteristics, changes in tail membership, and paired uncertainty in the coefficient path. Examine whether the pattern persists after the focused computer-use/remotability conditioning.

Verify that \(\lambda=0.5\) reproduces raw beta and, under identical mapping, weights, support, cutoffs, and specification, reproduces the beta contrast. The submitted appendix’s lambda=0.5 coefficient differs from the headline; reconcile this rather than copying both values into the revision. 

Retain an interpretable D/S primitive model with raw units, standardized units where useful, covariance, and a common illustrative change. Do not claim that monotonic coefficients reveal which technology actually existed or was adopted. Distinguish changing ranks/bins from continuous-scale changes.

For architecture comparisons, show both component estimates and their paired difference on each common support. Identify whether scales and memberships are fixed or recomputed. Separate sample changes from score changes. Preserve the nondetection-versus-equivalence distinction and do not treat the selected scores’ principal components as validated latent AI factors.

For the crosswalk audit, determine whose implementation is being corrected. Cite and demonstrate effects on published work only if directly verified. Otherwise present the exercise as a documented implementation failure encountered in this project and a portable compatibility check. State continuous-coefficient units and show a comparable illustrative scale. Do not label the invalid merge an equally legitimate alternative specification.

Evaluate age-specific route shares only after checking whether genuine dual-coded or otherwise suitable validation data exist. Adjacent coding vintages do not by themselves supply a same-person bridge. Without suitable data, retain clearly bounded allocation sensitivities and do not advertise estimated age-specific route probabilities.

An optional coding-error simulation must state its hypothetical misclassification matrix, persistence, and age/time assumptions. Immediate reversals do not identify a coding-error rate. Do not turn a symmetric-error exercise into a data-identified correction or a simple universal attenuation factor for the nonlinear quintile estimator. Prioritize this below the core analyses.

Remove the stable-tails result from the main comparison table; retain it, if useful, as a narrowly scoped appendix support diagnostic.

## 12. Rewrite, shorten, and repair all reporting inconsistencies

**Addresses both reports’ framing and presentation recommendations.**

Write the revised paper around one empirical question rather than a sequence of referee rounds. A suitable structure is: introduction; data and exposure construction; estimand and inference; occupational comparisons and characteristic conditioning; dynamics and sensitivity; a short mechanisms/BCC section; conclusion. Retain only the measurement material needed for the substantive argument and a concise practical taxonomy.

Aim for roughly a one-third to 40-percent reduction in redundant exposition, while preserving necessary definitions and uncertainty. Do not replace deleted pages with an even larger menu of loosely motivated tests. Keep only a small number of main exhibits; move technical derivations and secondary analyses to a focused appendix and implementation history to the replication documentation.

Remove the mobility-rematching benchmark and F/G rotation machinery from the scientific article and appendix unless a new, specific relevance is demonstrated. Preserve historical code/results in the replication archive. Move failed-diagnostic logs, commit hashes, CSV path manifests, and design chronology to the README/technical audit. State ordinary affine/basis invariances briefly rather than presenting them as methodological results.

Use one corrected substantive baseline throughout. Describe the earlier chronology once. Remove repeated “frozen,” “confirmatory,” “design-freeze,” “prior draft,” and referee-round framing, while retaining a clear, honest statement that key analyses are exploratory. Historical transparency must remain in the response letter and archive.

Keep the abstract to one question, the main result, the uncertainty, and the implication, with approximately three substantive numerical quantities. Do not headline a marginal p-value, say that controls identify a non-AI counterfactual, or conclude that AI has no employment effect.

Explicitly audit and repair the following:

* Calendar-mixed SE/MDE reporting and conflicting intervals for the same estimate.
* The food-service attenuation percentage and its denominator; verify the exclusions’ calendar rather than only changing the percentage.
* Service-group names versus SOC codes, particularly the mention of protective services alongside SOC35/37/39.
* The unexplained approximately −0.088 architecture-range endpoint and common-versus-native support labels; verify its actual location rather than repeating the report’s location claim.
* The meaning of “unconditioned” in the BCC paragraph.
* Continuous-coefficient units, information-share formulas, record counts, and fractional-count terminology.
* The effect of Webb availability on sample support: estimate with/without Webb on identical support and, separately, without Webb on broader beta coverage.
* Original versus corrected quintile profiles, age comparisons, influence analyses, flow estimates, and lambda results still embedded in prose or tables.
* Missing occupation membership lists and stale cross-references.
* Figure 3’s crowded alternative normalizations; retain clear young, older, and ratio exhibits without repeating two full sets in the main text. Separate conditioning changes from support/contrast changes in the comparison figure. Fix the architecture-figure legend overlap.
* Author affiliation, email, acknowledgments, funding, conflicts, and required disclosures: obtain or flag missing information, never invent it.

Verify every quantitative sentence against generated results. A reported coefficient is a log relative-stock contrast, not automatically a percentage change in an individual employment probability. Use \(\exp(\beta)-1\) when a ratio-percent interpretation is appropriate, with the denominator and comparison stated.

## 13. Literature and factual verification

Keep verification focused on the contribution and methods rather than adding a literature-review project. Use primary research, official data documentation, and official software documentation. Verify current sources and versions rather than relying on either referee report as a bibliographic authority.

For journal literature, search a stated ten-journal scope spanning economics and finance: *American Economic Review, Quarterly Journal of Economics, Journal of Political Economy, Econometrica, Review of Economic Studies, Review of Economics and Statistics, Journal of the European Economic Association, Journal of Finance, Journal of Financial Economics,* and *Review of Financial Studies*. This is a declared search scope, not a claim of a uniquely agreed ranking. Include directly relevant work outside that scope and official CPS/IPUMS/BLS/Census documentation.

Prioritize the motivating paper’s actual contribution and versions; inference under clustering and few clusters; sensitivity to nonparallel trends; constructed-regressor uncertainty where applicable; task/computerization controls; and CPS stock/flow comparability. Cite claims about concurrent macroeconomic shocks only after verification, and distinguish the occurrence of an event from evidence that it explains this paper’s coefficient.

## 14. Required deliverables and completion tests

Deliver the revised main manuscript and focused appendix in editable source and compiled PDF, with a change-marked version or source diff. When empirical work is blocked, label the draft’s status explicitly and keep unexecuted results out of it.

Also deliver:

1. **A concise editor response and separate point-by-point responses to R1 and R2**, identifying the actual change, result, location, and limitation for each comment. Explain justified nonimplementation respectfully; do not promise work as though completed.
2. **A machine-readable comment-response matrix** covering every major, moderate, and minor point, linked to analysis status, code, results, and revised locations.
3. **A reproducible analysis package** with a master command, dependency/environment record, source manifest, specification registry, seeds, tests, machine-readable estimates and covariance matrices, and generated tables/figures. Do not redistribute restricted microdata, identifiers, credentials, or inaccessible private paths.
4. **An inference/implementation audit** covering cell reconstruction, crosswalk conservation, paired covariance, HAC overlap, fixed versus regenerated treatments, and the distinction between sampling and shock uncertainty.
5. **A numerical-consistency audit and a short unresolved-items memo** stating precisely which inputs or assumptions prevent stronger conclusions.

The revision passes only when the main claim matches the validated evidence; every displayed result is traceable; paired comparisons use the correct covariance and support; MDEs are interpreted correctly; subgroup and flow estimands are explicit; and statistical nondetection is not presented as equivalence or causal explanation.

Compile and visually inspect every revised figure/table and representative PDF pages. Check clipping, legends, type size, notes, cross-references, and bibliography. Run a clean build where data access permits; distinguish a build from cached outputs from a full microdata rerun.

**Final instruction:** execute this revision in priority order. Let the results determine whether the paper’s contribution is a substantive occupational comparison, a limitation of inferential resolution, a measurement audit, or a combination that remains sufficiently focused. Do not force a rejection of AI, a defense of the original headline, or a claim that revision guarantees top-journal publication.
