# Revision V3: evidence-gated execution prompt

## Mission and completion rule

You are the empirical execution agent and manuscript editor for Lily Luo's paper currently titled **“AI Exposure or Occupational Composition? Young-Worker Employment Comparisons in the CPS.”** Revise the analysis, manuscript, appendix, responses, and deliverable replication package. This is an execution assignment, not a request for another proposal or a more reassuring narrative.

**Your objective is a smaller set of coherent, interpretable, correctly estimated results—not a larger inventory of robustness checks, a predetermined AI conclusion, or a guarantee of journal acceptance.** The strongest candidate contribution is the limited direct within-family support behind a nominally broad national exposure comparison. Test and explain that proposition; do not assume it is sufficiently novel or that it survives every valid comparison.

**Every request must receive an evidence-backed disposition. An acknowledgement, caveat, script, failed attempt, cached number, or proposed future analysis is not the same as a completed and validated analysis.** Do not silently omit anything. Equally, do not fabricate results or apply an invalid method merely to fill a completion box.

Treat this file and `requirements_seed.json` as complementary. The seed is a minimum tracking list, not permission to ignore a request in the sources. Expand compound requests into child rows as necessary. Preserve every existing requirement ID. The supplied delivery validator checks coverage and artifact integrity; it does not establish econometric correctness.

A final delivery must distinguish:

1. **All requests accounted for:** each has a response and an explicit status.
2. **Core analyses verified:** the foundational and scientific blocking tasks actually pass their acceptance checks.
3. **All requested empirical work executed:** no requested empirical task remains merely proposed, blocked, or deferred.
4. **Submission ready:** author disclosures, editable sources, figures, independent review, and delivery checks are also resolved.

These statements are not interchangeable. Report whichever are true. If work remains blocked, deliver the useful partial work with a precise resume plan, but do not call the revision complete or submission ready.

---

## 1. Inputs, source identities, and decision authority

Read these sources in full before changing scientific claims:

- **A:** latest referee recommending major revision, sections 3.1–3.11 and minor comments 1–10.
- **B:** latest referee recommending rejection at a leading general-interest journal, major comments 1–6 and specific presentation/reproducibility comments.
- **C:** the assistant's preceding audit of the updated draft, summarized in `ASSISTANT_AUDIT_AND_FAILURE_MODES.md`; use the original conversation text when available.
- **P0:** the previous execution prompt, `inputs/previous_execution_prompt.md`. Its uncompleted requirements remain active unless explicitly adjudicated here or retired with a reason and approval.
- The current manuscript and current appendix, and the earlier versions needed to identify regressions and historical results.

In the original conversation, the paths were:

| Input | Original path |
|---|---|
| Current main manuscript | `/mnt/data/a14b1433-ce78-4ea8-8eab-9163e8b1704f.pdf` |
| Current appendix | `/mnt/data/a4827da8-79e7-4839-8f31-4540dc7e5cee.pdf` |
| New report A | `/mnt/data/Pasted markdown(20260906-023153).md` |
| New report B | `/mnt/data/Pasted markdown (2)(5).md` |
| Previous execution prompt | `/mnt/data/revision_prompt/execution_agent_revision_prompt.md` |
| Earlier uploaded referee | `/mnt/data/Pasted markdown(20260905-111135).md` |
| Earlier main manuscript | `/mnt/data/0a7067ca-ce30-46f3-a669-ba1a0ec2ff32.pdf` |
| Earlier appendix | `/mnt/data/5a436977-088b-47b0-a07d-6ee63d45892b.pdf` |

The accompanying package contains copies under descriptive names in `inputs/`. Confirm titles, page counts, hashes, and versions; do not infer file identity from upload order. The current PDFs have 21 and 29 physical pages, respectively. Printed page numbers differ from physical positions in the main manuscript.

Locate the actual editable source, code repository, authorized microdata, DDI/codebooks, exposure inputs, crosswalks, derived artifacts, logs, and any existing response matrix. Their existence is not established by a pathname printed in the appendix. Never infer account permissions, redistribute licensed data, expose identifiers, send messages to authors, or incur paid-service costs without authorization.

Maintain `source_inventory.json` with `found`, `absent`, `inaccessible`, and `unverified` as distinct states. Verify current external data availability from official sources. Do not substitute general knowledge for the attached reports; label external verification and your own methodological adjudication separately.

**Decision authority:** econometric and data validity take precedence over literal implementation of a referee's proposed recipe. A referee request may be fulfilled by a defensible alternative, a verified correction of its premise, or a documented impossibility, but only with the original request, reasoning, evidence, and implication recorded. Do not silently reinterpret a hard request as optional.

---

## 2. Why the previous revision was incomplete: investigate, do not invent motives

The preceding PDFs establish an observable pattern, not the previous agent's internal reasoning. Investigate code and receipts before attributing an actual cause. Distinguish `observed_failure`, `hypothesized_cause`, and `verified_cause` in a short retrospective.

The known failure modes to prevent are:

**Topic coverage substituted for question resolution.** The draft says the static and dynamic parameters differ, but does not reconcile their numerical relationship. It reports an adverse simulation without establishing how the preferred procedures perform. A paragraph about a problem does not answer that problem.

**Local modules used incompatible definitions.** The focused characteristic exercise rebuilds exposure groups on 408 occupations, while the expanded module holds primary-universe groups fixed. The household exercise switches from family-by-month to family-by-post. These changes are disclosed, but disclosure does not make them fulfill a same-target request.

**A failed estimator became a stopping rule.** Nonconvergence is preserved, but the coding-stable post-2020 model is still missing. Changing a solver for the same objective is not necessarily changing the estimator. Diagnose separation, rank, conditioning, and implementation before declaring infeasibility.

**Available extract fields were mistaken for available data.** The earnings analysis ends when `EARNWEEK` ends, despite the documented replacement/comparable variable `EARNWEEK2`. Search official definitions and availability before declaring a data limit.

**Historical artifacts survived upstream corrections.** The appendix still relies on some historical-contract mapping, service, and influence results. A corrected baseline does not update downstream modules automatically.

**An asserted replication system substituted for a delivered one.** The PDFs describe ledgers, manifests, and commands, but the review package did not include the corresponding executable evidence. A cached-exhibit build cannot certify a fresh microdata estimation run.

**The previous prompt was broad and insufficiently testable.** It bundled many tasks, allowed feasibility exceptions without minimum evidence standards, and did not require enough cross-module integration checks. This is a weakness of the assignment design as well as a possible execution weakness. Fix it with staged dependencies and acceptance tests, not with repeated declarations that you have been careful.

Investigate whether context loss, module ownership, stale caches, wrong defaults, compute limits, missing data, or incomplete validation contributed. Do not report a particular explanation as fact without logs or code evidence.

---

## 3. Gate 0: demonstrate understanding before editing results

Create `UNDERSTANDING_CONTRACT.md` before running new substantive specifications. Write brief answers, equations, and planned evidence—not hidden chain-of-thought. Explain:

1. What the grouped-binomial criterion is estimated on, and why its coefficient parameterizes a log ratio of conditional mean stocks rather than an observed log ratio or individual employment probability.
2. What is learned from family-by-month conditioning and what remains observationally ambiguous between family-level AI effects and unrelated family developments.
3. Why losing residual exposure information does not mechanically force a coefficient toward zero.
4. How the national conditional Q5–Q1 contrast uses intermediate quintiles and common-coefficient restrictions when most families lack both tails.
5. Why the current static pair (approximately −0.1321, −0.0217) and dynamic post-functional pair (approximately −0.1199, −0.2074) require a numerical reconciliation, not simply different names.
6. Why changing an omitted period does not change an equivalent joint equality test, and why a post average relative to two unusual reference months can differ from a post-minus-pre average.
7. Why separate age-specific regressions generally do not add exactly to the nonlinear headline coefficient; in particular, a single-age model cannot identify occupation exposure × post while also retaining unrestricted occupation × month effects.
8. Why one-sided zero likelihood contributions can be valid even when some saturated fixed effects have no finite optimum.
9. Why a simulation's zero structural AI effect need not imply that every fitted conditional or misspecified projection target, or their difference, equals zero.
10. Why household sampling, occupation shocks, broad-family shocks, generated treatments, and mapping uncertainty are different targets, and why their variances cannot simply be added.
11. Why collinearity inflates uncertainty but does not alone explain a particular signed coefficient movement; why a linear omitted-variable sensitivity formula cannot be applied to pseudo-R² without derivation.
12. Why nonenrollment and link restrictions can introduce selection; why the enrollment universe matters for the older comparator.
13. Why larger ACS samples may improve sampling precision without changing the exposure-support graph, and why observed adoption does not automatically supply exogenous variation.
14. What concrete artifacts and tests will distinguish completion from an unexecuted script, a failed attempt, a scoped exception, and a cached rebuild.

Resolve these questions against the sources. A separate checker should review this contract when one is actually available. A second pass by the same agent must be called self-review, not independent verification. Do not outsource scientific judgment to the delivery validator.

---

## 4. Work management: atomic requests, immutable specifications, and proof of completion

### 4.1 The requirement ledger

Copy the seed to `requirements_status.json`. For every request, retain its source locator, actual requested operation, scientific question, priority, dependencies, acceptance checks, and final manuscript/response location. Add child rows whenever a source asks for several deliverables. Duplicate requests may share an analysis but must retain their separate source mappings.

Use these statuses accurately:

- `NOT_STARTED`
- `SPECIFIED`
- `IMPLEMENTED_UNRUN`
- `RUN_UNVALIDATED`
- `VERIFIED`
- `PREMISE_CORRECTED`
- `BLOCKED_INPUT`
- `BLOCKED_COMPUTE`
- `INAPPLICABLE_PROPOSED`
- `INAPPLICABLE_APPROVED`
- `DEFERRED_PROPOSED`
- `DEFERRED_APPROVED`

A `VERIFIED` empirical row needs a specification, executable code, successful run receipt, numerical output, substantive validation, and manuscript/response integration. One file may support several rows, but each linkage must be explicit. A drafted limitation is not that evidence.

A blocked row needs the exact missing input/resource, official availability search, attempted retrieval or run, error/log, alternative considered, consequences for claims, and next resumable step. Lack of a variable in the current extract is not proof that the survey lacks it. “Too expensive,” “not identified,” or “nonconvergent” without this evidence is insufficient.

For a proposed nonimplementation, state why a valid alternative would not answer the question, not merely why the original recipe is inconvenient. Core blockers cannot be self-waived into a declaration of full completion. An approved scope change is a documented decision, not an empirical result.

### 4.2 The canonical specification contract

Pass a serialized, immutable specification to every module. It must identify:

- source/data vintages and hashes; microdata eligibility and relevant variable universes;
- occupation taxonomy, family assignment, crosswalk version, and allocation rule;
- outcome units, cell construction, age groups, calendar and missing/transition handling;
- canonical occupation universe, analysis subset, and subgroup eligibility;
- exposure version, raw scale, construction weights and age universe, training dates, cutoffs, tie rule, fixed membership vector, and Webb normalization;
- objective, nuisance column space, identifying normalizations, separation treatment, and solver;
- target contrast, temporal weights, source of uncertainty, resampling unit, multiplier matrix, and conditioning on generated objects;
- dependencies, exact command, code/environment hash, and output locations.

Every result receives a `spec_id` and `result_id` based on these contents. An endpoint, age range, objective, grouping, or nuisance change produces a new ID. A module must fail if it receives incompatible objects. No local routine may silently recompute quintiles or normalization.

For primary conditioning and endpoint comparisons, **keep canonical preperiod labels and scales fixed**. Recomputed groups are separately named treatment-construction sensitivities. “Same support” is not sufficient if labels, means, scales, age universe, or the weighting window differ.

A genuine upstream correction invalidates all dependent results, figures, numeric prose, covariance matrices, and response claims. Implement dependency-aware caching. Never patch an estimate into an unrelated old result record.

### 4.3 Sequencing and resource discipline

Execute in this order:

**Gate 1:** inventory, canonical reconstruction, numerical existence/convergence, and exact-target integrity.

**Gate 2:** support, accounting decompositions, unified conditioning, and static/dynamic reconciliation.

**Gate 3:** calibrated inference and sensitivity analysis on those resolved targets.

**Gate 4:** cohort/enrollment, flows, coding-stable/mapping checks, and the public-data benchmark; external extensions after their feasibility/design gate.

**Gate 5:** rewrite, responses, full delivery, clean build, and independent or explicitly labeled self-review.

Independent branches can run in parallel after their prerequisites pass. Save a compact `STATE.md` after each stage and before handoff: authoritative IDs, completed/blocked rows, commands, scientific decisions, and next tasks. A resumed agent must reload this state and the ledger rather than reconstructing conventions from memory.

A run failure blocks dependent analyses but should not stop unrelated feasible work. Do not let a solver installation consume the entire project while the core model remains unaudited. Profile a pilot, estimate resource needs, use restartable checkpoints, and disclose hard budget limits. Never omit failed simulation or bootstrap replicates without accounting for them.

---

## 5. Referee adjudications that must govern the revision

### A's valuable requests are not all established facts

**The row-count allegation appears to be a PDF-extraction error.** In the supplied appendix, printed page 3 ends with the sentence leading into the count and a footer “3”; printed page 4 begins “6,188,956.” The rendered count is 6,188,956, consistent with main Table 1. Do not manufacture a correction to 36,188,956. Verify the raw count anyway, record the rendered-page evidence, and explain the apparent concatenation politely in A's response.

**Attenuation is not mathematically implied by information loss.** Controls remove variation and can reduce precision; the signed point-estimate movement depends on the outcomes and model. Distinguish this from the valid support critique.

**Pandemic-driven rejection is a hypothesis.** Run A's requested block tests, but do not state that the pandemic must drive rejection. A nonrejection after excluding pandemic quarters neither proves parallel evolution nor establishes that the CPS cannot evaluate any trend restriction. The earlier conditioned figure also makes the reference period worth investigating.

**Variance inflation is not a signed mechanism.** Report the computer coefficient, covariance, and collinearity. Do not assert that variance inflation alone produces a move from −0.107 to −0.212. Also distinguish nonlinear conditioning effects from a linear omitted-variable interpretation.

**Do not choose December 2024 because the estimate remains significant or “costs little.”** Present the through-2024 window as a prominent pre-2025-production-break benchmark and the full window as the later extension, on the same canonical treatment. State any change in primary emphasis as an outcome-informed revision motivated by data comparability. Both must remain visible; neither is a causally clean sample.

**Separate stock regressions are not automatically an exact decomposition of the headline.** Supply exact accounting identities and explicitly different companion models instead of forcing their coefficients to sum to −0.132.

**Formal confounder sensitivity requires a valid estimand and assumptions.** Do not insert grouped-binomial pseudo-R² into Oster's formula or claim that citing Diegert–Masten–Poirier implements their analysis. A family-common young-relative confound already in the span of family-by-month effects is absorbed there; sensitivity for the residual target must describe a genuinely unabsorbed dimension.

**BTOS is a Census Bureau survey, not a BLS survey.** Its AI questions changed in November 2025. Published adoption variation is not necessarily occupation-specific, time-comparable, or exogenous. Treat these as design checks.

**Unlinked outcomes have no known bias direction without assumptions.** Do not automatically call selective linkage attenuation toward zero. Evaluate plausible signs and supported bounds.

**ACS does not fill missing occupation-by-exposure combinations by increasing sample size alone.** It can improve estimation and may admit additional occupations. Distinguish changed taxonomy/support from increased sampling information.

### Preserve valid safeguards from P0

Use paired covariance; do not infer differences from significance stars. An observed movement below an 80%-power MDE may still be statistically significant. Nondetection is not equivalence. Broader cluster definitions and alternative multipliers do not automatically validate inference. Do not add overlapping variances. No within-family permutation is a randomization test absent justified exchangeability. No exposure index becomes observed adoption by relabeling it. No retrospective plan becomes preregistration.

---

## 6. Foundational reconstruction and numerical existence

### 6.1 Reproduce and audit the current canonical analysis

First reproduce the submitted checkpoints: pooled approximately −0.132109, family-month approximately −0.0217, 468 primary occupations, canonical preperiod January 2017–November 2022, and the documented 113 static months. These are diagnostic checkpoints, not outcomes to target by changing code.

Verify all upstream objects, including the age universe used to weight exposure construction; it need not be identical to the regression age universe, but must be stated and constant across primary modules. Reconcile source rows, eligible records, expanded rows, fractional contributions, unique sampled units where available, and fitted cells. A physical row count is an integer even when the row's stock contribution is fractional.

Check replacement of March 2017–2021 files before filtering/routing; the October 2025 gap; December 2022 transition handling; 2025 and 2026 population-control/file/identifier revisions; exact extract receipts; and weight application once. Do not invent a counterfactual vintage of subgroup weights. Retain genuine one-sided zero cells; zero-total cells have no likelihood contribution. Never select the primary sample on a minimum realized young count.

### 6.2 Distinguish valid cell contributions from finite model estimates

For pooled, family-post, family-month, dynamics, post-2020, and seasonal models, audit rank, normalization, connectedness, complete/quasi-separation, and boundary nuisance parameters. Tabulate family-month groups with positive total but zero young or zero older stock. Establish whether boundary nuisance values leave target coefficients estimable.

Use a mathematically valid treatment: profiling boundary nuisance components, detecting separated observations/groups, or an equivalent supported likelihood implementation. Explain any implied removal of noninformative contributions. Do not add arbitrary pseudocounts, clip fitted probabilities to disguise an infinite estimate, drop all sparse cells, or silently introduce penalization.

For failures, examine parameter/gradient trajectories, scaled score residuals, Hessian conditioning/rank, likelihood progression, and the target profile. Try better scaling, analytic profiling, warm starts, or a second trusted solver **for the same objective and column space**. Record precision tolerances and compare fitted means and target coefficients, not just an optimizer's success flag.

Reattempt the post-2020 coding-stable and lower-dimensional seasonal models after this diagnosis. If the exact model is not estimable, demonstrate why and declare any alternative aggregation, penalty, support, or target separately. “The first algorithm did not converge” is not a completed numerical audit.

**Acceptance:** a convergence/existence report for every core specification; boundary/separation counts; a second implementation or carefully designed numerical benchmark; unit tests with one-sided zeros and separated nuisance groups; no concealed estimator substitution.

---

## 7. Make support and economic comparisons the central evidence

Promote a compact **22-family × five-quintile matrix** to the main text. Each cell must show occupation counts and preperiod employment shares, with clear denominators. Include total family coverage, Q1/Q5 overlap, exposure range, and named occupations supplying direct tails.

Provide a support graph or equivalently readable table identifying direct edges and intermediate connections. Explain the common-coefficient/homogeneity assumptions that connect Q1 to Q5 across families. Do not call the national conditional coefficient an average of directly observed within-family tail effects.

Reestimate the direct-tail comparison, continuous within-family companion, full Q2–Q5 profile, joint null, simultaneous intervals, and family/occupation influence under the canonical contract. Name the four spanning families and the occupations that dominate the direct comparison. Show supported pairwise within-family contrasts without imposing the entire common quintile profile; use transparent aggregation only where actual overlap supports it. Imprecision is an acceptable finding; manufacturing unsupported family tails is not.

Repeat the overlap diagnostic on the broader beta-valid support without requiring Webb. First extend fixed raw primary cutoffs to newly eligible occupations to isolate support expansion; then show reclassification as a separate construction sensitivity. Check rather than assume that the support deficit is intrinsic rather than induced by the auxiliary-control requirement.

Audit information calculations:

\[
I=\sum_{ot}h_{ot}r_{ot}^2,\qquad
s_o=\frac{\sum_t h_{ot}r_{ot}^2}{I},\qquad
G_{\mathrm{eff}}=1/\sum_o s_o^2.
\]

Identify every nuisance projection and denominator. Distinguish information under each model's own fitted curvature from a fixed-reference-curvature comparison of nuisance spaces. Across models, both curvature and residualization may change; do not describe every change in fitted information as purely outcome-independent geometry. Separate pre-outcome support, fitted information, sampling precision, and nominal clustering units. Absolute information is not comparable across differently scaled targets.

Show the economic paths for influential between-family comparisons, not only the four sparse direct-tail families. Use readable quarterly/annual aggregation or carefully labeled smoothing; do not interpolate the missing survey month, conceal raw volatility, or create false precision. Keep the full unsmoothed series in the archive.

Resolve the inherited equal-occupation-weighted companion request as well: define the alternative objective and its economic weighting explicitly before estimating it, or document why it adds no relevant comparison. Removing CPS final weights is not automatically an equal-occupation version of the same model.

**Acceptance:** actual matrix, membership files, graph/connection explanation, supported heterogeneous contrasts, broader-support comparison, formula reconciliation, full joint-test statistics, and updated interpretable employment paths. A list of quintiles merely present in each family is not the full matrix.

---

## 8. Quantify numerator, denominator, family composition, and cohort effects

### 8.1 Exact stock accounting first

With a common calendar, fixed exposure labels, and explicitly normalized temporal weights, define period-average stocks \(N^a_{qP}\) for age group \(a\), exposure group \(q\), and period \(P\). Report

\[
D_a=\log(N^a_{5,post}/N^a_{5,pre})
 -\log(N^a_{1,post}/N^a_{1,pre}),\qquad D_R=D_y-D_o.
\]

This is an exact aggregate log-ratio identity where the aggregates are positive. It is **not automatically the grouped-binomial regression coefficient**. Show both age components, all four underlying stock series, paired uncertainty where justified, and the difference between this accounting target and the headline regression target. Do not silently exchange average logs for logs of average stocks.

A separate pair of young/older stock regressions can be useful, but state the nuisance terms and common normalization. Prove any claimed coefficient identity. Unrestricted occupation×month effects absorb exposure×post in a single-age sample, so a usable companion must change the nuisance structure or target explicitly. Conditioning on observed total stock also does not identify an independently observed total-employment response.

### 8.2 Give “composition” an explicit accounting meaning

For valid positive-denominator family cells,

\[
R_{qP}=\sum_g s^o_{gqP}R_{gqP}.
\]

Use an exact symmetric two-period decomposition separating changes in older-employment family weights from changes in within-family young/older ratios. For level ratios, the midpoint decomposition

\[
\Delta R_q=\sum_g\bar s^o_{gq}\Delta R_{gq}
 +\sum_g\bar R_{gq}\Delta s^o_{gq}
\]

is one acceptable choice. If reporting contributions on the log-change scale, derive an exact transformation or a declared Shapley decomposition; do not relabel level-ratio contributions as log points. Report closure residuals at numerical tolerance and make the temporal aggregation explicit.

Check zero older denominators before applying the identity. A cell with zero older and positive young stock cannot simply be assigned ratio zero. Aggregate to a justified period/support or account explicitly for the undefined-denominator component. Do not drop problematic families to make the decomposition look clean.

This accounting exercise remains distinct from the change in a conditional regression coefficient and from causal attribution.

### 8.3 Older age profiles and enrollment

Reestimate the core contrast against a limited, specified set of narrower older bands and, if supported, a fixed-age-composition denominator. Define the standardization formula, reference age weights, population denominators, and handling of sparse cells. Do not call any older band untreated. Update—not merely cite—the older-band results inherited from the earlier draft.

Verify school-enrollment variables in the actual monthly files. Official `SCHLCOLL` documentation lists a 16–54 universe from 2013 onward, and the checked December 2019 and August 2025 Basic CPS dictionaries also specify ages 16–54 for the underlying enrollment item. Some summary prose is ASEC-specific, so confirm the sample-specific dictionary and observed codes rather than relying on a search snippet. A 55–65 not-in-universe code is not evidence of nonenrollment. At minimum, show the contrast for non-enrolled young workers against a clearly specified older comparator; separately use non-enrolled older workers only on a common observable universe, with a same-age-universe unrestricted baseline.

Report education/enrollment profiles by exposure quintile **among employed young workers**, and separately national young-population/cohort profiles where the full CPS universe permits. Do not assign occupational exposure to never-employed or other nonemployed people to manufacture a population denominator. Restrictions on contemporaneous enrollment may be selective or affected by labor-market conditions; they clarify composition rather than identify a causal correction.

**Acceptance:** exact identities pass, component levels and changes are visible, companion-regression differences are explicit, older composition and enrollment comparisons use valid universes, and neither descriptive decomposition is called an AI share.

---

## 9. Reconcile static and dynamic models before interpreting trend sensitivity

### 9.1 A common descriptive functional

Use the same canonical exposure assignments, support, core calendar, and appropriate nuisance structures. Report for pooled and family-month models:

- the static coefficient;
- the published post average relative to 2022Q4;
- a reference-invariant dynamic contrast

\[
\tau^D=\sum_{t\in post}w_tb_t-\sum_{t\in pre}v_tb_t,
\qquad \sum w_t=\sum v_t=1;
\]

- their differences and the paired conditioning movement for each object.

Fix and publish \(w_t\) and \(v_t\) before inspecting revised results. Weight observed calendar months correctly within partial quarters, including the two-month reference quarter, the missing October 2025, and the one-month 2026Q3 endpoint. Label alternative temporal weights separately.

Transform the **full covariance and common-draw vector** with every rebasing or aggregation. Numerically verify reference invariance of \(\tau^D\) and of equivalent joint preperiod-equality tests.

A particularly valuable nested-model check is available. If the static design is in the dynamic design's column space, \(X_s=X_dA\), the dynamic score equations imply

\[
X_s'(y-T\hat p_d)=0.
\]

Then refitting the static criterion to pseudo-stocks \(T\hat p_d\) and \(T(1-\hat p_d)\), with the same totals and regressors, should reproduce the static target within numerical tolerance under the applicable finite/boundary conditions. Establish the nesting and existence assumptions first. This is a check of moment preservation and nonlinear projection, not a new causal estimator. If nesting fails, identify precisely which nuisance term, sample, or restriction differs.

Use this reconciliation to explain the role of the unusual reference period, temporal weighting, and nonlinear restrictions. “The estimands differ” is not sufficient acceptance evidence.

### 9.2 Diagnose—not select away—preperiod rejection

Report A's requested collections: 2017Q1–2019Q4; 2021Q1–2022Q3; and the original preperiod excluding 2020Q2–2020Q4. Also retain the full-preperiod test. For each, distinguish equality to the original reference from equality within the selected block. These are different nulls. State restrictions, rank, degrees of freedom, and inferential procedure.

Identify influential quarters using simultaneous intervals and clearly defined leave-block-out or restriction diagnostics. A correlated Wald statistic has no unique additive “quarter contribution”; do not invent one. Inspect seasonal structure and persistent level/drift differences as well as pandemic quarters. Do not attribute rejection to COVID solely because the dates include it.

A prewindow chosen after viewing p-values is not a repaired design. State the scientific reason for every window, retain the full grid, and discuss power. With few family clusters, respect covariance rank; use feasible lower-dimensional contrasts or a justified maximum-statistic method rather than inverting a singular matrix.

### 9.3 HonestDiD and actual calendar restrictions

Verify the official paper and package definitions and version. Explain the estimand, bias process, no-anticipation restrictions where invoked, and why an approximate Gaussian event-vector analysis is justified for this nonlinear estimator.

Define smoothness as the bound on changes in the differential-trend slope across equal-spaced periods, not merely a bound on the trend level. Define the chosen relative-magnitude restriction on the appropriate consecutive-period changes in the counterfactual differential trend; do not simply substitute the largest plotted coefficient or a referee's description.

Do not pass the static coefficient and its SE to an event-vector procedure. Likewise, a post-minus-pre descriptive contrast is not automatically accommodated by a package argument that weights only post-treatment effects. Derive and validate the mapping or clearly retain separate targets. Rebase the bias restrictions consistently; a display normalization is not a new identifying assumption.

Report the full-window sensitivity and a substantively motivated contiguous non-pandemic prewindow where supported. Do not delete internal pandemic quarters and renumber the remaining observations as adjacent quarters. A gapped calibration requires restrictions that preserve elapsed time or an explicitly valid alternative. Do not selectively discard the largest preperiod deviations to generate a preferred robustness value.

Publish the exact coefficient ordering, covariance, weight vector, restriction matrices/parameters, solver output, and sensitivity grid. Report conventional intervals and what a zero-exclusion breakdown of zero means for **that target only**. If inference is not validated in Section 10, HonestDiD cannot cure the input covariance problem.

**Acceptance:** numerical reconciliation table; nesting/normalization tests; diagnostic block tests; clearly interpreted, reproducible sensitivity analysis; no claim that the current dynamic interval formally overturns the static headline absent a valid connection.

---

## 10. Validate the inference actually supporting the claims

### 10.1 Define truth before measuring size

For each simulation DGP, define the population/pseudo-true targets of the pooled model, family-month model, and their paired difference. Compute or otherwise establish those truths independently of a single noisy simulation sample.

A structural AI parameter set to zero is not enough. If correlated family shocks or model misspecification make a pooled projection coefficient nonzero, rejection of zero need not be a size failure for that projection target. Distinguish finite-sample inference failure, estimator bias, estimand mismatch, and confounding. This check is mandatory before interpreting the existing 26.7% and 11.3% figures.

### 10.2 Compare procedures within the same designs

Create a small, declared simulation design table containing:

- an empirically calibrated design, with clearly documented moments and uncertainty about their estimation;
- the previous adverse design, exactly reproduced where possible;
- a limited factor-ablation sequence varying cell sparsity/weight heterogeneity, family dependence, serial correlation, and influence concentration separately.

Compare the procedures actually used in the article: occupation wild-score, broad-family wild-score with the stated multipliers, and a defensible full-refit or finite-sample benchmark. Evaluate the pooled target, the **same family-month target**, and the paired movement. A normal-interval simulation does not validate the wild-score interval by implication.

Report bias relative to each defined target, empirical SD, mean reported SE, coverage or rejection rates, interval lengths, failure/separation rates, and Monte Carlo uncertainty. Predeclare computational accuracy targets, pilot sizes, and expansion rules. Increase outer replications and/or inner bootstrap draws until the claimed comparison is numerically resolved, or state it remains unresolved. More inner draws alone do not repair poor finite-sample coverage.

Do not estimate a universal correction by multiplying actual SEs by an arbitrary factor derived from one adverse design. If a size-calibrated/test-inverted interval is justified, derive and validate it. Select a primary procedure by design validity and performance—not by whether it preserves a significant headline. If no procedure is adequately validated, demote sharp rejection language and make the uncertainty limitation explicit.

### 10.3 Microdata refits and dependence

Extend household/sample-unit positive-weight full refits to the central family-month comparison where estimable. Preserve each sampled unit's months, co-resident records, and fractional crosswalk descendants under the same resampling weight. Verify longitudinal identifier corrections and treatment of missing identifiers. Eight month-in-sample categories are not eight independent survey PSUs.

Report which design variables and replicate weights are actually available. Do not borrow ASEC weights for Basic Monthly CPS. Separate released-weight repeated-sample sensitivity from occupation-shock inference; do not double-count by adding variances without a derived decomposition.

Assess Monte Carlo stability of the household interval; 199 draws is a pilot, not a demonstrated precision standard. Increase draws or report endpoint simulation uncertainty. Keep a family-post companion if informative, but never pass it off as validation of family-month inference.

Provide a distinct full-pipeline resampling sensitivity that regenerates preperiod construction and other generated inputs where feasible, with the changed uncertainty target explicit. If computationally blocked, retain that blocker rather than implying that fixed-label intervals include label/shortfall uncertainty.

### 10.4 Preserve and verify the HAC repair

Audit occupation covariance plus aggregate elapsed-time HAC minus within-occupation elapsed-time HAC in consistent score units. Include positive-lag overlaps, correct calendar gaps, bandwidth/kernel choices, finite-sample factors, and cross-model blocks needed for paired contrasts. Validate symmetry, rank, and definiteness; do not silently clip eigenvalues. Keep historical incompatible matrices in the implementation archive, not as interchangeable inference for the current target.

**Acceptance:** the actual preferred methods and the paired target are evaluated against declared truths; same-target full-refit evidence or an explicit remaining blocker; coverage and computation uncertainty are visible; inferential claims change when the evidence warrants it.

---

## 11. Consolidate conditioning into a matched-support design

Replace the fragmented main horse races with a **2×2 comparison** on one fixed common support and the same canonical assignments:

| Model | Computer use | SOC2 × young × calendar month |
|---|---|---|
| Baseline | No | No |
| Computer only | Yes | No |
| Family only | No | Yes |
| Combined | Yes | Yes |

Retain Webb consistently or explicitly run a separately labeled without-Webb collection. Use a computer-available support for this primary comparison; do not unnecessarily require every other characteristic. Separately show the smaller common support needed for the parsimonious characteristic block. For every comparison, display both estimates, paired movements with covariance, information loss, and support-only changes.

Report the computer-use coefficient itself in stated raw and standardized units, its SE/interval, and covariance with the exposure target. Explain the residualized comparison and collinearity using consistent information denominators, a condition diagnostic, and overlap plots or summaries. Reconcile the 408-, 455-, and 341-occupation figures, correlations, construction windows, and fixed versus recomputed labels. Retire unnecessary duplicate conventions from the main narrative.

Perform an explicit applicability assessment for a formal omitted-confounder sensitivity analysis. Either implement a method valid for the declared target, derive a justified extension, or use a transparently different linear companion with its own estimand and assumptions. Do not apply linear R² formulas to the nonlinear likelihood by analogy. State whether the confounder is family-common or within-family, whether included controls may be endogenous, and what strength restrictions mean. Cite the correct versions of Oster and Diegert–Masten–Poirier and relevant developments. Report sign sensitivity and magnitude sensitivity as different questions where appropriate.

Finish the pandemic-shortfall analysis honestly. Define both the total-stock and young-relative measures, their scales, trends, windows, and zero handling. Re-estimate generated quantities in the appropriate resampling exercise and/or implement an independent-source or household-split diagnostic. Preserve repeated households when splitting. If these designs are infeasible, label the current fixed-generated-regressor row as a limited diagnostic rather than a completed confounder investigation.

Retain the industry-cell analysis with its own baseline and changed objective explicitly labeled, and show a concise common-support comparison for education, wages, remotability, and routine/manual tasks. Do not respond to a failed “computerization explains away the effect” prediction by claiming the remaining coefficient is AI.

**Acceptance:** the four-model table resolves the current interaction between family and computer conditioning; labels are identical within the collection; computer coefficients and covariance are visible; formal sensitivity is implemented validly or explicitly adjudicated; generated shortfall uncertainty is not hidden.

---

## 12. Carry mapping sensitivity through the current coefficient

Re-run mapping, unsplit-support, stable-taxonomy, service-exclusion, and influence exercises that still use historical treatment definitions. Every current empirical claim must be supported by the current construction or explicitly confined to historical implementation documentation.

For age-specific routing, define the joint feasible allocation set over source occupation, age group, and time. Preserve source-age-month stock, structural route zeros, and any additional all-age route-total constraints actually imposed. Official conversion shares are not automatically known age-specific probabilities or exact realized margins; state what is assumed fixed.

Implement at least an odds-tilt sensitivity on the rebuilt coefficient with an explicit parameter grid and coverage of eligible split stock. At the no-tilt value, reproduce the canonical cells and coefficient. Show both fixed-label measurement sensitivity and, separately, a full-preperiod-rebuild sensitivity where routes change construction weights/cutoffs. Report which quantities change in each.

Investigate more adverse joint allocations or coefficient bounds where computationally justified. Marginal Q1/Q5 stock-ratio ranges do not directly provide simultaneous bounds on the coefficient; optimizing numerator, denominator, and each tail separately can violate joint feasibility. A local nonlinear search is not a certified global bound, and a sensitivity grid is not a sharp identified set. Report optimization tolerances, starts, constraints, and the difference between explored envelopes and guaranteed bounds.

Do not infer dual-coded validation data from adjacent occupation vintages or from a larger ACS sample. If genuine validation data are unavailable, state that exact limitation and complete the feasible sensitivities instead.

Explicitly close the inherited optional symmetric occupation-coding-error simulation request: run an assumption-labeled sensitivity if scientifically useful, or record a reasoned feasibility/scope disposition. An observed occupation reversal rate is not a validated error matrix.

State the units of the continuous AIOE audit—holding a scale fixed is not specifying that scale. Show a common illustrative increment. Attribute the invalid literal merge to this project unless another implementation has actually been inspected. Preserve D/S units, paired architecture comparisons, and the exact lambda=0.5 identity. Reconcile the inherited non-lambda alternatives (the AIOE constructions, Webb AI, and OECD comparison) individually: the lambda grid alone does not satisfy those original requests. Re-run retained scientific comparisons on the current contract or explicitly archive/retire them with a recorded scope disposition; move redundant architectural material to the archive when it does not answer the central question.

**Acceptance:** current-contract mapping results, no-tilt identity, joint feasibility and mass-conservation tests, honest scope of bounds, and no historical numerical result masquerading as a new robustness check.

---

## 13. Repair flow selection and outcome coverage, then keep only useful mechanisms

Report weighted baseline transition probabilities, risk counts, and link rates by age, exposure group, and period, not just six regression coefficients. Compare linked and eligible unlinked origins on observable characteristics using the eligible-origin population and clearly stated weights. Distinguish ineligible rotation positions from eligible-but-unlinked observations.

Address selection rather than only clustering. Evaluate an observable-selection reweighting sensitivity with its assumptions and positivity/weight diagnostics, and/or transparent missing-outcome bounds. For a binary margin with link share \(\ell\) and linked probability \(p_L\), a basic accounting range is \([\ell p_L,\ell p_L+1-\ell]\) under the specified population/weight interpretation. Carry justified comparisons through jointly feasible bounds; log contrasts may be unbounded when a probability endpoint is zero. Do not clip them to fabricate finite precision. Do not apply Lee-style trimming as if occupational exposure were randomized or monotone selection were established.

Discuss whether movers plausibly have different outcomes, but do not assert the sign of bias from the young/older link-rate difference alone.

For entry, estimate destination-specific probabilities from the **same nonemployment risk set**, including remaining nonemployed and entering outside the retained exposure support. No origin occupation is needed to define an event of entering destination q. The probabilities across all destinations must reconcile with total observed employment entry. Keep the conditional allocation contrast as a different object, not a hiring rate. Do not assign a destination occupation to a failed/nonexistent entry or define a nonemployed person's cluster by an unobserved destination.

State annual-link timing rules: origin and destination ages, links crossing January 2023, the December 2022 transition, occupation-code changes, population/file revisions, and missing survey months. Links straddling the onset cannot silently be treated as wholly preperiod because their origins precede it. Compare a justified exclusion or exposure-duration convention; annual endpoint changes are not sums of monthly transitions.

Fix the earnings source limitation. Investigate `EARNWEEK2`, its monthly availability, outgoing-rotation eligibility and weights, rounding, allocation, and changing topcodes. Build a consistent series as far as authorized data permit. Do not splice old and new fields without a documented compatibility rule. If a new extract is needed, request the exact variables and months and mark the extended analysis blocked; do not claim the survey has no later earnings data. Retain hours and other valid ancillary margins with units and conditioning clear; no occupation assignment to never-employed or out-of-labor-force respondents.

If these margins remain unable to discriminate mechanisms, shorten their scientific presentation. Retain important selection limitations and actual results, not an extensive section whose sole message is that every CI contains zero. Preserve the justified decision not to manufacture a complete CPS-to-employer stock–flow calibration.

**Acceptance:** link selection is measured, missingness implications are addressed, entry denominators reconcile, annual rules are explicit, and the earnings limitation is resolved or precisely blocked rather than accepted as a natural data boundary.

---

## 14. Establish the public-data benchmark and evaluate extensions deliberately

### 14.1 BCC's own public evidence is the benchmark

Read the specific August 2026 BCC version, especially the public CPS/ACS analyses, rather than relying only on the dashboard grouping description. Identify the exact public result being compared: plotted stock series, aggregate growth contrast, or regression coefficient. Record sample, ages, employment population, taxonomy, exposure assignment, weights, endpoint, normalization, estimator, and inferential method.

Reproduce the public-data benchmark before adding family controls. If the benchmark is an aggregate graph rather than the present regression, first reproduce the graph/aggregate contrast and then introduce a **separately defined conditional extension**. Do not call the paper's own Q5–Q1 model a direct replication merely because it uses CPS.

Acquire available public code/memberships through authorized means. If code is available only on request, record that limitation and seek user authorization before contacting anyone. Do not assume absent dashboard memberships make every public-data comparison infeasible. Conversely, do not claim exact concordance without them.

Report a differences table between BCC's public target and this paper's canonical target. Align the June-2026 endpoint and feasible full-time civilian wage-and-salary population where appropriate; these are different from inaccessible employer identifiers. Compare family-post and family-month conditioning on the same target and labels. Preserve the paired uncertainty of the top-two/bottom-three comparison; do not transfer the stronger Q5–Q1 paired result to it.

### 14.2 ACS extension: a focused design, not an automatic precision cure

Complete a mandatory feasibility/design assessment. Prefer a compact annual ACS comparison through the latest verified available one-year PUMS, aligned with annual CPS and BCC's public benchmark. Check current release availability rather than assuming 2025 ACS microdata exist. As of this prompt's source check, the 2025 ACS release was not established as available; verify anew when executing.

Use one-year files, not overlapping five-year products as independent annual observations. Official guidance says the 2020 one-year experimental estimates should not be compared with ordinary years; do not splice them into a standard time series. State how annual 2022 handles the late-2022 transition and how this differs from the monthly design. Check ACS occupation and population-control changes, geography/group-quarters/worker coverage, and weight definitions. ACS is not a production-break-free replacement by default.

If valid inputs are available, execute a limited extension: benchmark reproduction, aligned annual CPS, pooled and family-year conditioned contrasts, direct-tail support/information, and uncertainty using the appropriate official ACS replicate-weight procedure where applicable. Verify replicate factors, year independence/dependence assumptions, and fixed versus regenerated exposure definitions. Do not substitute survey variance for occupation-shock inference without explaining the target.

Let the outcome change the paper. If ACS supplies precise within-family evidence, narrow the claimed limit to CPS or to the relevant unsupported comparison. If the structural overlap remains poor, quantify that distinction. If the extension is blocked, provide exact evidence and a runnable design; do not silently omit A's suggestion.

### 14.3 Adoption extension: mandatory assessment, conditional execution

Verify public Census BTOS and Bick–Blandin–Deming/RPS products, their granularity, sampling uncertainty, time span, use definitions, and public availability. Distinguish worker generative-AI use from firm use of broader AI. BTOS question wording changed in November 2025; do not treat a resulting jump as deployment growth without a compatible bridge.

Determine whether adoption varies below a nuisance level already absorbed by family×month or industry×time controls. A family-time adoption main effect can be collinear with those controls; an exposure×adoption interaction may remain estimable but asks a different question and may rely on the same thin within-family exposure variation. Derive the residual variation and lower-order terms before fitting it.

A national time series interacted with exposure is not an independent identification strategy beyond exposure-by-time dynamics. Occupation-industry mapping must use declared preperiod shares or actual appropriate cells, with ecological aggregation and generated-input uncertainty explicit. Do not backfill pre-adoption values as zeros merely because the survey began later, or use future adoption without labeling the resulting descriptive classification.

Execute one focused association only if it contributes a clearly defined, supported comparison after core work is verified. Otherwise present a specific scientific or access-based disposition and obtain approval for deferral. Do not turn the revision into an unplanned second paper or conclude that measured adoption solves causality.

### 14.4 Focused literature check

Search and document a ten-journal economics/finance scope: AER, QJE, JPE, Econometrica, REStud, REStat, JEEA, Journal of Finance, Journal of Financial Economics, and Review of Financial Studies. This is a declared search scope, not a universal journal ranking. Include relevant primary work outside it and official statistical documentation.

Engage the actual contributions and versions of Bick–Blandin–Deming, Hampole–Papanikolaou–Schmidt–Seegmiller, Deming–Noray, and Autor–Thompson, plus the necessary inference and sensitivity work. Do not invent a title, publication status, DOI, or result from an author list. Distinguish evidence that a concurrent event occurred from evidence it explains this paper's coefficient.

**Acceptance:** a reproducible public-data benchmark or a precisely verified comparability gap; explicit ACS and adoption dispositions; no generic “future research” paragraph in lieu of checking feasible data.

---

## 15. Rewrite around the resolved evidence and deliver the actual project

### 15.1 Article architecture

After the core gates—not before—rewrite the title, abstract, introduction, and conclusion. A suitable provisional title is **“Occupational AI Exposure and Young-Worker Employment: Support and Comparisons in the CPS.”** Finalize it from the evidence.

Lead with the empirical target and the positive descriptive result about comparisons, not a near-zero residual coefficient or a marginal significance claim. Explain early that broad-family AI effects and unrelated family effects remain observationally ambiguous. Descriptive support/composition analyses can be useful even when parallel trends is not credible; state what they establish without presenting them as causal decompositions.

A focused organization is: empirical target and public benchmark; data/support; stock and composition accounting; unified conditioning and dynamic reconciliation; validated uncertainty; short corroborating evidence; conclusion. Aim for a small number of main exhibits, with the support matrix, exact accounting, matched conditioning, and reconciliation doing the work. Additional analyses belong in the appendix or archive according to scientific relevance, not just whether a referee requested them.

Consolidate definitions of nondetection, MDEs, conditional targets, and causal limitations in one short subsection. Remove repetitive caveats without deleting the substantive limitations. Put most MDEs in one diagnostics table. Describe the exploratory chronology once; no renewed preregistration vocabulary or repetition of “post-outcome” in every sentence.

Keep the mobility-rematching benchmark, F/G rotations, installation failures, old coefficient discrepancies, and operational hashes out of the scientific exposition. Archive them. Do not revive superseded tables simply because they are easy to regenerate. Do not shorten the main paper by expanding an unfocused appendix indefinitely.

### 15.2 Numerical and visual checks

Generate quantitative prose and tables from the canonical result ledger wherever possible. Check every reported number, interval, scale, sample count, percentage denominator, and cross-reference. Reconcile the AIOE units; service SOC33 versus SOC35/37/39 labels; historical attenuation percentages; Webb scales and CI rounding; industry-cell baseline labels; exact-age and subgroup universes; and current versus historical data products. Correct “chapter” and inaccurate dependent-variable notes.

Inspect rendered PDF pages, especially disputed counts crossing page breaks, every table and figure, legends, axes, typography, float placement, and bibliography. Main Table 2 must describe the weighted-stock estimating criterion and log conditional-mean-ratio parameter, not claim an observed log-dependent variable in cells containing zeros. Avoid unreadably compressed wide tables and near-empty float pages; figures must not interrupt the conclusion.

The alleged 36-million count must be answered with the actual render and raw audit, not altered to satisfy a mistaken extraction. If the same statistical target has a different interval solely because another module used a different finite draw set, use the canonical output consistently or explain the genuinely different procedure.

### 15.3 Deliverables

Deliver editable main and appendix sources, compiled PDFs, source diff/change-marked version, editor letter, responses to A and B, and a closure report for C/P0. Map every response to the analysis/result ID and revised location. Do not write “we have done” for implemented-but-unrun code.

Deliver the actual sanitized code/result package: dependency environment, input manifest, canonical contracts, requirement ledger, numerical results, covariance/influence objects needed for verification, support/membership files, run receipts, scientific validation reports, test reports, commands, and README. Include the protected-data access instructions without raw CPS data, direct link identifiers, credentials, licensed raw inputs, or private absolute paths.

Provide separate commands for (a) re-estimation from authorized microdata and (b) rebuilding exhibits from aggregate results. Run a clean re-estimation when inputs/resources permit. If only the aggregate build was executed, report precisely that. A package manifest without the files is not delivery.

Resolve author affiliation, contact, funding, acknowledgments, conflicts, and journal disclosures with the author; never invent them. Pending fields prevent a claim of submission readiness, not necessarily completion of valid empirical work.

### 15.4 Final independent challenge and stop conditions

Have a separate reviewer, when genuinely available, try to falsify the completion claims: inspect code rather than just reading responses; choose several results from the paper and trace them backward; choose several requirements from A/B/P0 and trace them forward; rerun at least one core model and one changed-target comparison; verify both numerical and semantic consistency. If only self-review is possible, label it and leave independent verification pending.

Run the supplied delivery validator against the final ledger and files. Its success establishes structural coverage/integrity only. Scientific acceptance additionally requires the tests in this prompt.

Your final message must state the four completion flags from the start of this prompt; counts by status; unresolved blocking IDs; exactly which commands were actually run; which claims changed and why; and links to the delivered files. Do not promise background work. Do not hide unfinished tasks behind a polished manuscript.

**Final instruction:** execute in dependency order, investigate every omission, and let inconvenient results alter the paper. No silent skipping; no invalid recipe to satisfy a referee; no invented completion; no declaration of full success until the evidence supports it.
