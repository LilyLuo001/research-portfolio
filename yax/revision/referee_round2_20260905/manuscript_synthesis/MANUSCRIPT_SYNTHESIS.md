# Evidence-led manuscript synthesis

Status: editorial synthesis for referee round 2. This note introduces no new
outcome result and does not edit `paper/main` or `paper/appendix`. All new
round-2 outcome analyses cited below are post-outcome exploratory and must be
labeled as such.

## Editorial decision

Recenter the paper on one substantive question:

> Where does the negative young-relative employment association attributed to
> occupational AI exposure actually come from in the public CPS design?

The answer supported by the completed evidence is narrower and more useful
than either current framing.

- The repaired-calendar Eloundou-beta Q5--Q1 association is negative and
  sizeable: -0.1346 log points, with a 95% interval of [-0.2223, -0.0468].
- After absorbing broad-occupation-family differential evolution, the
  coefficient is -0.0315 with a 95% interval of [-0.1676, 0.1046]. The
  absolute point estimate attenuates by 76.6%; the paired coefficient change
  is +0.1031, with a 95% interval of [0.0035, 0.2026]. A fully flexible
  SOC2-by-month specification gives nearly the same result.
- This is evidence that the baseline point estimate is largely organized by
  comparisons across broad occupational groups. It is not a causal
  decomposition: the SOC2 controls change the conditioning estimand, leave
  only narrow within-family support, and reduce conditional target
  information to about 30% of baseline.
- Clean occupation-side exclusions do not support the stronger story that a
  food-service recovery mechanism explains the result. Excluding Q1 food
  occupations attenuates the frozen coefficient by 8.8%, while broader
  in-person-service exclusions make it slightly more negative.
- The architecture exercise shows different empirical treatments much more
  clearly than it shows different employment coefficients. The reported point
  estimates are negative across all eight examined architectures, and every Q5--Q1 paired
  beta-versus-alternative interval includes zero. The appropriate result is
  limited precision, not architecture invariance and not established
  architecture heterogeneity.
- Implementing the public BCC top-two-versus-bottom-three grouping in the
  frozen CPS design yields a negative coefficient of -0.0728, with a 95%
  interval of [-0.1240, -0.0216]. This bridges to the motivating empirical
  claim while preserving the crucial differences in data, outcome, and
  estimand.

The revised paper should therefore be a **composition-centered measurement
paper**. Its substantive center is the location of the descriptive CPS
association; its methodological contribution is a disciplined framework for
distinguishing implementation repair, measurement change, construct change,
support change, estimand change, representation change, and pure
reparameterization. Do not center the paper on a generic slogan that
"measurement is a choice," on a claimed food-service mechanism, or on the
claim that exposure architectures have been shown to yield different economic
conclusions.

## 1. Proposed title and abstract

### Preferred title

**The Anatomy of an Occupational AI-Exposure Association: Measurement,
Precision, and Broad-Occupation Comparisons**

Shorter alternative: **The Anatomy of an Occupational AI-Exposure
Association**

### Proposed abstract

Occupation-level AI exposure is a constructed treatment: abilities, tasks,
patents, or capability assessments are mapped to occupations and transformed
into an empirical comparison. I study how those operations shape a widely
discussed young-worker employment pattern in the Current Population Survey.
The estimand is the post-January-2023 change in the log young-to-older
employment-stock ratio, ages 22--25 relative to ages 26--65, for high- versus
low-exposure occupations; it is not an employment-probability or causal
effect. On the corrected calendar, the Eloundou-beta Q5--Q1 coefficient is
-0.1346 (95% interval [-0.2223, -0.0468]). In post-outcome diagnostics,
absorbing major-occupation-group-specific post changes produces a narrower
within-group estimand of -0.0315 [-0.1676, 0.1046], a 76.6% attenuation in the
absolute point estimate. Only four of 22 major groups contain both Q1 and Q5.
A separate post-outcome bridge applies the public top-two-versus-bottom-three
grouping used by Brynjolfsson, Chandar, and Chen and yields -0.0728 [-0.1240,
-0.0216] in the frozen CPS design, but does not reproduce their private payroll
or hiring analysis. Across eight
examined exposure implementations, the reported point estimates are all
negative, yet every Q5--Q1 paired beta-versus-alternative interval includes
zero; paired 80% minimum detectable effects range from 0.061 to 0.169 log
points. The six initially selected scores are also highly dependent: two
components explain 96.11% of their weighted variance. Clean service-occupation
exclusions do not support a food-service mechanism. The evidence locates most
of the baseline point-estimate magnitude in comparisons across broad
occupational groups and shows why this design cannot identify AI displacement
or rank most exposure architectures.

### Abstract discipline

- Use "workers ages 22--25" or "young workers," not "labor-market entrants"
  or unqualified "early-career workers."
- Use "log young-to-older employment-stock ratio" at first mention. The
  equivalent conditional-logit interpretation is the log odds that an employed
  person in the two-age-group sample is 22--25 rather than 26--65.
- State that the SOC2 exercises and BCC bridge are post-outcome exploratory.
- Do not use "explains 76.6%." Use "attenuates the absolute point estimate by
  76.6%."
- Do not say that external architectures "change the conclusion." Their point
  estimates are smaller, but the Q5--Q1 paired differences are unresolved.

## 2. Exact revised contribution and non-claims

### Contribution 1: a framework that distinguishes operations

The methodological contribution is an operational map from construct to
reported coefficient:

\[
C \rightarrow M \rightarrow H \rightarrow (\Omega,w) \rightarrow R
\rightarrow (Q,P) \rightarrow B.
\]

Here, the layers are the technology construct, measurement rule, taxonomy
harmonization, support and weights, representation, economic comparison and
target population, and reporting coordinates. An exercise can change more
than one layer, but each direct change and its induced consequences must be
named.

The paper contributes three exact results that discipline the application:

1. A positive affine transformation preserves ranks and tie-preserving
   weighted bins on fixed support and weights.
2. For the task-family score `D + lambda S`, occupational ranks and categorical
   assignments are piecewise constant between pairwise score crossings. A
   categorical coefficient can change only when a relevant assignment changes;
   it need not move monotonically with `lambda`.
3. A full-rank coordinate change preserves the fitted model. The F/G-to-A/E
   rotation is therefore an exact reparameterization, not new empirical
   corroboration.

This framework turns the application into more than a specification curve. It
states which empirical object changes and which conclusions are invariant to a
given operation.

### Contribution 2: the association is mainly an across-broad-group result

The corrected-calendar baseline is -0.1346. Adding SOC2-by-post controls yields
-0.0315; absorbing SOC2-specific young-relative monthly paths yields -0.0317.
The corresponding paired changes from baseline are +0.1031 [0.0035, 0.2026]
and +0.1028 [0.0035, 0.2021]. These specifications use less residual
information and a different estimand, but they directly establish that the
large baseline point estimate is not present in the residual within-SOC2
comparison.

The support result is part of this contribution, not a footnote: all 22 major
groups contain at least two quintiles, but only four contain both Q1 and Q5.
The conditional coefficient is therefore connected mainly through
intermediate quintiles rather than repeated direct Q5--Q1 comparisons within
broad families. Conditional target information falls from 26.44 million to
7.95 million under SOC2-by-post controls.

### Contribution 3: precision-aware architecture comparison

The paper separates three claims that the current text sometimes blends:

1. **Point-estimate sign:** the reported coefficients are negative across all
   eight examined architectures.
2. **A joint sign statement:** the original six are dependent implementations
   from two families, and the predeclared simultaneous one-sided band failed.
3. **Differences between architectures:** every Q5--Q1 paired
   beta-versus-alternative interval includes zero; the design does not detect
   these differences and also does not establish equivalence.

The primary normal-theory MDE80 is 0.1244 log points. Paired MDE80 values range
from 0.0609 to 0.1689. Two weighted principal components explain 96.11% of the
six original scores on the exact 444-occupation support. Together, these facts
replace "six measures confirm the result" and "outside architectures overturn
it" with a more accurate conclusion: the treatments differ, but this CPS
design is unable to resolve most corresponding coefficient differences.

### Contribution 4: a direct but bounded bridge to BCC

The public component that can be transported is the BCC Eloundou-beta,
employment-weighted top-two-versus-bottom-three grouping rule. In the frozen
YAX CPS design it yields -0.0728 [-0.1240, -0.0216] with Webb conditioning and
-0.0729 [-0.1236, -0.0221] without it. From November 2022 to June 2026, young
CPS employment stock rises 5.78% in the bottom-three group and falls 5.03% in
the top-two group; older stock grows about 0.6% in both. These are descriptive
CPS aggregates.

This bridge makes the application relevant to a specific public claim without
pretending to reproduce proprietary ADP outcomes, firms, hiring and separation
margins, job-title mapping, or controls. The BCC grouping also demonstrates
that architecture distinguishability is contrast-specific: on the literal
426-occupation support, beta differs detectably from OECD under this grouping
(-0.0733 [-0.1390, -0.0076]) but not from the other six alternatives. Under
the Q5--Q1 contrast, every paired architecture interval includes zero.

### Contribution 5: transparent data and inference diagnostics

- The known March-sample error is an implementation failure, not an economic
  robustness alternative. The repaired 113-month calendar is the substantive
  baseline; the frozen 108-month estimate remains a chronology benchmark.
- The AIOE taxonomy repair changes the fixed-support continuous coefficient
  only from -0.01885 to -0.01920, while expansion from 410 to 495 occupations
  changes it to -0.03156. The principal effect is occupation re-admission.
- Monthly sparsity is substantial, but quarterly aggregation reproduces the
  monthly coefficient to within 0.00004 log points. A 12-month time-HAC score
  sensitivity raises the SE from 0.0444 to 0.0491 without moving the point
  estimate.
- The balanced 2017--2019 pseudo-break estimates center near zero and none is
  as negative as -0.1311. Their plus-one tail of 0.0769 is an attainable floor
  from 12 dependent breaks, not a conventional p-value.
- Available population-control diagnostics do not show a discrete negative
  January 2025 official-weight break, but a literal no-revision age-by-
  occupation counterfactual is unavailable.

### Non-claims that must appear explicitly

The revised paper does **not** claim any of the following:

1. **A causal AI effect, displacement effect, or adoption effect.** Exposure is
   potential susceptibility; occupation-level adoption is unobserved, and
   January 2023 is not an instrument.
2. **A causal decomposition into broad occupation, food service, reopening,
   immigration, minimum wages, remote work, or any other mechanism.** SOC2
   conditioning changes the estimand; exclusion and influence diagnostics are
   outcome-informed sensitivities.
3. **That 76.6% of the effect is "explained" by broad occupations.** That
   number is attenuation of one coefficient after changing its conditioning
   set.
4. **That detailed AI exposure has no within-family association.** The
   conditional estimates are near zero but imprecise; intervals permit
   meaningful effects in either direction.
5. **That architectures are equivalent, invariant, or statistically
   different under Q5--Q1.** Every paired interval includes zero and several
   MDEs exceed the observed difference.
6. **That Webb or OECD invalidates task-based exposure.** They measure different
   constructs; OECD in particular is a reversed, broad capability-to-demand
   gap rather than a contemporary LLM-task measure.
7. **A monotone dose response.** The order-restricted test neither rejects nor
   establishes monotonicity (`p = 0.3933`); failure to reject a common Q2--Q5
   coefficient (`p = 0.1185`) is not evidence of equality.
8. **A food-service recovery mechanism.** The clean Q1-food exclusion
   attenuates by only 8.8%, and broader service exclusions do not attenuate.
9. **A complete survey-design confidence interval or construction-uncertainty
   interval.** Reported inference conditions on the constructed scores,
   mapping, support, and realized aggregate CPS cells.
10. **A literal counterfactual without the January 2025 population-control
    revision.** The required subgroup counterfactual weights are not
    published.
11. **A replication of the BCC labor-market result.** Only its public exposure
    and grouping rule are implemented in a different CPS estimand.
12. **A global census of published AI-exposure measures.** The census is
    repository-bounded: six core implementations, two externally admitted
    implementations, one scope failure, and several pending or locally
    unverified candidates.
13. **That the stable-tail result rescues a general AI interpretation.** Its
    -0.2120 coefficient applies to only 64 occupations and 9.74% of common-
    support employment; effective information is 15.0 and the top five
    occupations carry 46.7%.

## 3. Section-by-section rewrite blueprint

### Section 1. Introduction

Open with the empirical puzzle, not the generic fact that indices are
constructed. A suitable first sentence is:

> A negative employment gradient by occupational AI exposure has become an
> important descriptive fact in the policy debate, but the coefficient does
> not reveal which occupational comparisons generate it.

Then do five things in sequence:

1. Define the CPS estimand in plain language and distinguish it from jobs,
   employment probabilities, hiring, and causal displacement.
2. Report the repaired-calendar baseline and the SOC2-conditioned result in
   the first page.
3. State that clean service exclusions do not establish a food-service
   explanation.
4. Introduce the precision result: all architecture point estimates are
   negative, but most direct differences are unresolved.
5. State three contributions: the construct-to-statistic taxonomy and exact
   invariance results; the empirical location of the CPS association; and the
   direct, bounded BCC grouping bridge.

End the introduction with the non-claims. Delete the ten-journal search
paragraph, the phrase "robustness belongs to a statement" as the thesis, and
revision-history language such as "referee-requested," "R1-style," or
"R2-style."

### Section 2. From construct to statistic

Replace the current literature-led architecture section with the seven-layer
pipeline. Give the seven operation types in a compact table and present the
three invariance propositions in short form; move proofs to the appendix.

Follow with a bounded architecture census and construct matrix. Distinguish:

- the three AIOE implementations as same-construct measurement changes;
- `D`, `D + S/2`, and `D + S` as changes in task-family technology scope using
  two primitives;
- Webb AI patent--task overlap and the OECD capability gap as different
  constructs;
- Frey--Osborne and computerization measures as controls or comparators, not AI
  architectures; and
- pending candidates from failed candidates. "Not yet instantiated" is not a
  failed admission test.

Report that two components explain 96.11% of the six original scores. Treat
the distinct-quintile-cut condition as representation feasibility, not
construct validity. Position the paper against measurement and sensitivity
work by what its framework adds, not by a scoped journal count.

### Section 3. CPS outcome, corrected data, and inferential target

Make the repaired 113-month calendar the substantive data baseline. Preserve
the frozen 108-month estimate in a labeled chronology row rather than silently
replacing it. Explain the March basic-sample repair and the genuinely absent
October 2025 survey month in one paragraph.

Define the estimand as a conditional log-odds/relative-stock-ratio coefficient.
State the age groups, exposure grouping, omitted transition month, Webb
conditioning, support, and fixed effects together. Explain boundary cells:
the grouped-binomial objective admits cells with one zero age stock and omits
only cells with zero total stock.

State the inferential target and source of randomness explicitly. The
occupation-cluster wild-score interval permits arbitrary serial dependence
within occupation, conditional on scores, mapping, support, and aggregate CPS
cells. The time-HAC calculation adds a model-based sensitivity to
cross-occupation monthly score covariance. Neither procedure reproduces the
full CPS survey design or includes label-generation and taxonomy-allocation
uncertainty.

Put the primary MDE80 next to the primary interval. Define respondent-
equivalent cells operationally as separately routed unweighted respondent
counts; they are not the result of dividing every weighted cell by a common
constant.

### Section 4. Reconstructing the public association

Begin with the BCC grouping rather than with six architectures. State exactly
what is reproduced: Eloundou beta, employment-weighted quintiles, and top two
versus bottom three. Report -0.0728 [-0.1240, -0.0216] on the frozen calendar,
the near-identical no-Webb result, and the November 2022--June 2026 descriptive
stock changes. Place a data/estimand bridge beside the result: CPS versus ADP,
employment stock versus firm employment and hiring, occupational mapping,
controls, and public versus proprietary inputs.

Then present the sharper YAX Q5--Q1 corrected-calendar estimate of -0.1346 as a
diagnostic contrast, not as a competing estimate of the same BCC parameter.
Plot young-to-older ratios rather than six dense level series. If levels are
retained, put them in the appendix.

### Section 5. Where the Q5--Q1 association is located

This is the paper's empirical center.

1. Lead with the corrected baseline, SOC2-by-post, and SOC2-by-month models.
   Show coefficient, interval, paired change, target information, effective
   occupation count, and within-SOC2 tail support in one display.
2. Explain that both SOC2 specifications produce the same near-zero point
   estimate, while the residual comparison is imprecise and information-poor.
3. Replace "reference dependence" with "alternative exposure-group
   comparisons." Report the full quintile profile, the Q2--Q5 equality test,
   and the unresolved monotonicity test.
4. Report the stable-tail result as a deliberately narrow population result,
   with its 9.74% employment share and concentrated information.
5. Report joint influence diagnostics. Top-five deletion attenuates to
   -0.1011, but top-10 and top-20 deletion make the estimate more negative;
   symmetric trimming and Huber down-weighting remain near baseline. This
   establishes consequential, offsetting influence rather than a fragile
   handful-of-cases story.
6. End with the clean food and in-person-service exclusions. State plainly
   that they do not support the proposed food-service mechanism and therefore
   cannot sustain it as the manuscript's center of gravity.

The old within-SOC2 permutation belongs after the regression result as a
secondary diagnostic. Do not describe its mean as "five-sixths of the effect"
or as a decomposition.

### Section 6. What the data can distinguish across architectures

Organize the section around paired coefficient differences, not individual
significance. Show native estimates for descriptive coverage, then matched-
support beta-minus-alternative differences, intervals, and MDE80 values.

The first paragraph should state that the reported point estimates are
negative across all eight architectures. The second should state that external point estimates are smaller
but that every Q5--Q1 paired interval includes zero. The third should explain
that the BCC grouping detects beta versus OECD on its own 426-occupation common
support, demonstrating that comparative resolution depends on the economic
contrast.

Keep one short task-family primitive subsection. Lead with `D` and `S`, and,
if retained, the transparent AIOE-plus-beta horse race. Move the F/G rotation,
leave-one-measure F/G table, and exact A/E transformation to the appendix. Do
not call `F` and `G` independent economic channels.

### Section 7. Diagnostics, scope, and implications

Collect only diagnostics that bear directly on the revised core:

- quarterly aggregation and cell sparsity;
- time-HAC sensitivity and balanced pseudo-break distribution;
- January 2025 population-control checks;
- corrected taxonomy/support decomposition; and
- the unobserved validation object needed for generated-covariate corrections.

The event study must state its exact omitted reference and transition month.
Do not lead with the pretrend `p = 0.929`; emphasize the range of trends the
design can or cannot exclude. The historical covariance simulation rejects
only the tested global-sign mechanism as an explanation for the precision
gap; it does not diagnose the full gap.

Default treatment of mobility: remove the standalone mobility section from the
main paper and retain one paragraph explaining that ranks and thresholded
movements are a different representation and estimand. Put the detailed
switch, rematching, and flow results in the appendix unless the separate
round-2 mobility work produces an identical-support benchmark and sampling
uncertainty adequate for a compact main-text proposition. In no case should
employed-to-employed switches be used to make a hiring claim.

### Section 8. Conclusion

Use three short paragraphs:

1. The corrected CPS design contains a negative high-versus-low young-relative
   association and reproduces a negative coefficient under the public BCC
   grouping.
2. The large Q5--Q1 point estimate is largely absent after broad-family
   differential evolution is absorbed, while clean service exclusions do not
   isolate a food mechanism and comparative architecture evidence is
   underpowered.
3. The general lesson is the seven-layer reporting protocol: state which
   construct, population, representation, comparison, and uncertainty a
   robustness claim covers.

Do not end with "robustness is statement-specific" alone. End with the
substantive result and the reporting rule it motivates.

### Online appendix reorganization

1. Formal proofs and full bounded architecture census.
2. Source lineage, mapping, corrected calendar, and bridge-allocation limits.
3. Estimator, wild-score algorithm, finite-bootstrap reconciliation, and
   inferential target.
4. Expanded composition, support, quintile-shape, stable-tail, and influence
   results.
5. Rotation/time-HAC, pseudo-break, cell-boundary, and population-control
   diagnostics.
6. Task primitives and the supplementary F/G coordinate rotation.
7. Mobility, rematching, and longitudinal flows, with entry limits explicit.
8. Validation-sample agenda and reproducibility/design chronology.

## 4. Main-table and figure ordering

Use four main tables and four main figures. This is enough to make the paper
self-contained without recreating the appendix.

### Figure 1. From construct to reported coefficient

Redesign the current genealogy around the seven-layer pipeline. Tag each
empirical exercise by the layer it changes and mark the three exact invariance
results. The visual should distinguish error correction from defensible
alternatives.

### Table 1. Architecture census and construct matrix

One row per implemented score. Columns: family; technology boundary;
primitive/label source; publication and occupational-information vintage;
mapping route; support; role/status; and operation relative to beta. Put the
96.11% two-component result in the table note. List pending candidates in the
appendix, not as failures.

### Table 2. Core CPS association and its identifying comparisons

Panel A, chronology and frequency:

- corrected 113-month baseline: -0.1346 [-0.2223, -0.0468];
- frozen 108-month benchmark: -0.1311 [-0.2171, -0.0451];
- corrected quarterly: -0.1345 [-0.2222, -0.0468]; and
- corrected respondent-equivalent: -0.1348 (analysis-specific interval
  [-0.2216, -0.0481]).

Panel B, broad-family conditioning:

- SOC2-by-post: -0.0315 [-0.1676, 0.1046], paired change +0.1031 [0.0035,
  0.2026];
- SOC2-by-month: -0.0317 [-0.1674, 0.1040], paired change +0.1028 [0.0035,
  0.2021]; and
- columns for target information, effective occupation count, and top-five
  information share.

Panel C, BCC public grouping on the frozen calendar:

- with Webb: -0.0728 [-0.1240, -0.0216]; and
- without Webb: -0.0729 [-0.1236, -0.0221].

Do not juxtapose the frozen BCC coefficient with the repaired Q5--Q1
coefficient as if calendar and contrast were both common. If the BCC grouping
is not rerun on the repaired calendar, label its 108-month calendar in the row.

### Figure 2. Descriptive relative-stock paths

Use two readable panels: Q1 versus Q5 young-to-older ratios, and BCC bottom
three versus top two. Plot raw monthly series plus a modest smoothing line;
show the January 2023 marker, omitted December 2022, and absent October 2025.
Move separate young and older level panels to the appendix. The caption must
say that neither panel decomposes the fitted nonlinear coefficient.

### Figure 3. Baseline versus broad-family-conditioned estimates

Plot the corrected baseline, SOC2-by-post, and SOC2-by-month coefficients with
95% intervals. Add a small second axis or aligned annotation showing that
conditional target information falls from 26.44 million to 7.95/7.93 million.
State that the models change the conditioning estimand.

### Table 3. Shape, stable tails, and occupation influence

Panel A: Q1--Q5 profile and selected alternative contrasts, followed by the
Q2--Q5 equality test (`p = 0.1185`) and monotonicity verdict (`p = 0.3933`,
unresolved).

Panel B: always-Q5 versus always-Q1 (-0.2120 [-0.4131, -0.0109]), including 64
occupations, 9.74% employment, effective information 15.0, and top-five share
46.7%.

Panel C: top-5, top-10, top-20, symmetric trim, and Huber influence results,
with deleted employment shares and an "outcome-adaptive" flag.

Panel D: all-food, Q1-food, all SOC35/37/39, and Q1 SOC35/37/39 exclusions.

### Figure 4. Pre-AI pseudo-break distribution

Show all 34 feasible 2017--2019 estimates faintly, emphasize the 12 balanced
breaks, and draw the frozen -0.1311 coefficient as an external reference line.
The caption must state that breaks overlap, the exercise is post-outcome, and
0.0769 is the plus-one resolution floor rather than a randomization p-value.

### Table 4. Architecture estimates, paired differences, and detectable scale

Panel A: Q5--Q1. Columns: architecture; operation type; native support and
estimate; paired support; beta-minus-alternative difference; 95% paired
interval; MDE80. Every row should use the 9,999-draw round-2 results.

Panel B: BCC top-two versus bottom-three on literal 426-occupation support.
Use the same columns and visually isolate the beta-minus-OECD result, the only
paired difference detected under that grouping. State that it is a different
contrast, not a contradiction of Panel A.

### Move out of the main display sequence

- Full sample flow, correlation matrices, scree details, interval
  reconciliation, boundary selections, all age comparisons, all conditioning
  technologies, and complete LOCO rankings go to the appendix.
- F/G tables and coordinate algebra go to the appendix; retain `D,S` primitives
  briefly in main text.
- Mobility and flow displays remain appendix material under the default rule
  above.
- Drop the current figure that mixes identical-support benchmark rows with
  native-support external rows.

## 5. Paste-ready exact language

### A. Precision and inference

> The sole interval attached to the frozen primary estimate uses 9,999 common
> occupation-level wild-score draws. The Q5--Q1 coefficient is -0.1311 log
> points (occupation-clustered SE 0.0444; 95% interval [-0.2171, -0.0451]). Its
> normal-theory 80% minimum detectable effect is 0.1244 log points, roughly the
> magnitude of the coefficient itself. This MDE is a precision diagnostic, not
> a smallest effect of substantive interest or an equivalence margin. Paired
> MDEs for beta versus the seven alternative implementations range from 0.0609
> to 0.1689 log points, and every corresponding Q5--Q1 paired interval includes
> zero. The design therefore does not detect those coefficient differences; it
> also does not establish that the coefficients are equal or economically
> equivalent.

> Occupation clustering permits arbitrary serial dependence within an
> occupation. A model-based sensitivity that adds contemporaneous and lagged
> covariance of aggregate monthly scores raises the SE from 0.0444 to 0.0491 at
> a 12-month lag and leaves the normal interval below zero. This calculation is
> not a replicate-weight or full CPS survey-design variance estimator, and none
> of the reported intervals incorporates exposure-label or taxonomy-allocation
> uncertainty.

Table-note version:

> MDE80 values are normal-theory minimum detectable magnitudes at 5% two-sided
> size and 80% power. They are not equivalence bounds. Paired intervals use
> common occupation multipliers. Failure to detect a difference does not imply
> equality.

### B. SOC2 conditioning and broad occupational composition

> On the repaired 113-month calendar, the baseline Q5--Q1 coefficient is
> -0.1346. Adding major-occupation-group-by-post interactions changes the
> coefficient to -0.0315 (95% interval [-0.1676, 0.1046]); the paired change is
> +0.1031 [0.0035, 0.2026]. Absorbing a separate major-group-specific
> young-relative effect in every month yields -0.0317 [-0.1674, 0.1040]. Thus
> the absolute point estimate attenuates by about 77% when broad-group
> differential evolution is absorbed. These specifications change the
> conditioning estimand and are not a causal decomposition. Conditional target
> information falls to about 30% of baseline, and only four of 22 major groups
> contain both Q1 and Q5. The evidence therefore shows that the large baseline
> point estimate is organized mainly by comparisons across broad occupational
> groups; it does not show that the remaining within-group association is zero
> or that broad occupation causes the pattern.

Short abstract version:

> Absorbing broad-occupation-group differential evolution changes the
> Q5--Q1 coefficient from -0.1346 to -0.0315, a 76.6% attenuation in the
> absolute point estimate, but also produces a narrower and substantially less
> precise within-group estimand.

Forbidden substitutions:

- Do not write "broad occupational composition explains 76.6% of the effect."
- Do not write "the AI effect disappears with SOC2 controls."
- Do not write "the permutation shows that five-sixths is composition."

### C. Architecture comparisons

> The reported point estimates are negative across all eight examined
> architectures. The Webb AI
> and reversed OECD coefficients are smaller (-0.0649 and -0.0110), and their
> marginal intervals include zero. The direct Q5--Q1 comparisons are also
> imprecise: beta minus Webb AI is -0.0646 [-0.1682, 0.0389], with MDE80
> 0.1499, and beta minus OECD is -0.1115 [-0.2257, 0.0027], with MDE80
> 0.1689. Every beta-versus-alternative paired interval includes zero. The
> expanded architecture set therefore weakens evidence for a uniformly
> negative association and contains smaller external point estimates, but the
> data do not establish or exclude economically important architecture
> differences.

> These comparisons do not all vary measurement of one latent object. The
> three AIOE scores are dependent implementations of one ability-based
> construct; the task scores vary the weight on software-complemented tasks;
> Webb uses patent--task overlap; and OECD uses a reversed nine-domain
> capability-to-demand gap. On the exact six-score support, two weighted
> principal components explain 96.11% of variance. The original six should
> therefore be described as six implementations from two tightly related
> families, not six independent validations.

BCC contrast addendum:

> Comparative resolution itself depends on the economic contrast. Under the
> public BCC top-two-versus-bottom-three grouping on literal 426-occupation
> support, beta differs detectably from OECD (-0.0733 [-0.1390, -0.0076]) but
> not from the other six alternatives. Under Q5--Q1, every paired interval
> includes zero. The grouping-specific OECD result is not a universal ranking
> of architectures.

Replace these current formulations:

- Replace "the broader architecture audit changes the conclusion" with "the
  external point estimates are smaller, while paired differences remain too
  imprecise to establish or exclude substantial architecture differences."
- Replace "the sign statement does not extend" with "all point estimates are
  negative, but statistical support for uniform negativity weakens when the
  architecture set expands."
- Replace "robust across architectures" with the exact architecture set,
  support, contrast, and type of inference.

### D. Food-service and influence finding

> Fast food and counter workers are the most influential single occupation in
> the frozen leave-one-out audit: deleting that occupation changes the
> coefficient from -0.1311 to -0.1106. That outcome-informed deletion does not
> identify a food-service mechanism. Under a clean Census-2018 occupation
> definition, excluding all food-preparation and serving occupations yields
> -0.1201 [-0.1993, -0.0409], and excluding only Q1 food occupations yields
> -0.1196 [-0.1988, -0.0404], an 8.8% attenuation in absolute magnitude.
> Broader SOC35/37/39 in-person-service exclusions yield -0.1370 and -0.1387,
> slightly more negative than baseline. These checks show that particular
> service occupations are influential, with offsetting signed contributions;
> they do not support the claim that food-service recovery, reopening,
> immigration, or minimum-wage changes explain the association.

Joint-influence addendum:

> Joint deletion confirms concentration without a monotone fragility story.
> Deleting the five most influential occupations attenuates the coefficient to
> -0.1011, whereas deleting the top 10 or 20 yields -0.1522 and -0.1555.
> Symmetric trimming (-0.1281) and Huber down-weighting (-0.1314) remain close
> to baseline. All of these diagnostics are outcome-adaptive and are not
> preferred estimators.

### E. January 2025 population controls

> The January 2025 CPS controls use Vintage 2024 population estimates and
> create a documented discontinuity in official levels. A literal
> age-by-occupation counterfactual without that revision is unavailable. On
> the repaired calendar, the official-weight and respondent-equivalent
> coefficients are -0.1346 and -0.1348. Ending in December 2024 yields -0.1135
> and -0.1056, respectively. In the official-weight joint model, the 2025--26
> minus 2023--24 change is -0.0556 [-0.1228, 0.0116], and the raw
> December-to-January official-weight contrast moves +0.0139 rather than
> discretely downward. These diagnostics do not indicate that revised weights
> mechanically generate the negative association, but they cannot reproduce
> the unavailable no-revision subgroup counterfactual.

### F. BCC bridge

> I implement the public component of the Brynjolfsson--Chandar--Chen design:
> the Eloundou GPT-4 beta score, employment-weighted quintiles, and a top-two-
> versus-bottom-three comparison. In the frozen CPS employment-stock model,
> the coefficient is -0.0728 [-0.1240, -0.0216]. This is a negative
> young-relative CPS association under their grouping rule. It is not a
> replication of the proprietary ADP firm panel, job-title mapping, or hiring
> and separation margins, and it cannot adjudicate those mechanisms.

### G. Quintile shape and stable tails

> The frozen coefficients relative to Q1 are -0.0855, -0.0478, -0.0970, and
> -0.1311 for Q2 through Q5. A joint test does not reject a common Q2--Q5 post
> coefficient (`p = 0.1185`), but this is not evidence that the groups are
> equal. An order-restricted test neither rejects nor establishes monotone
> decline (`p = 0.3933`). The appropriate conclusion is that the dose-response
> shape is unresolved.

> Restricting the sample to the 46 occupations always assigned to Q1 and the 18
> always assigned to Q5 gives -0.2120 [-0.4131, -0.0109]. The estimate applies
> only to 9.74% of common-support employment and is based on effective
> information of about 15 occupations, with 46.7% carried by the top five. It
> is evidence for a negative association in this small stable-tail population,
> not a general robustness result.

## 6. Consistency and claim-control rules

1. Attach only [-0.2171, -0.0451] to the frozen -0.1311 primary estimate.
   Earlier 999-draw intervals reflect finite-bootstrap variation; the
   minimum-100 row changes sample and is not primary.
2. For the repaired -0.1346 standalone baseline, use the precision audit's
   [-0.2223, -0.0468] interval throughout. If a paired-analysis table displays
   another common-draw interval, label it explicitly as analysis-specific and
   do not repeat it in prose.
3. Keep calendars visible. The current BCC grouping result uses the frozen
   108-month calendar; the substantive Q5--Q1 baseline uses the repaired
   113-month calendar.
4. Round coefficients and intervals to four decimal places in tables and
   three significant figures in prose. Round percentages to one or two decimal
   places. Do not report benchmark or bootstrap quantities to five digits.
5. Use "alternative comparison" for Q5--Q2 or Q5--Q4. Re-labeling an omitted
   category is a coordinate change; changing the requested contrast changes
   the estimand.
6. Label every round-2 outcome exercise post-outcome exploratory. Preserve the
   frozen confirmatory result as chronology, not as the substantive corrected-
   data baseline.
7. Keep point-estimate agreement, a joint sign statement, and paired
   coefficient differences in separate sentences and table columns.
8. Never interpret an interval crossing zero as evidence that two
   specifications differ. Report the paired difference.
9. Never interpret failure to reject as equivalence, equality, absence, or
   robustness.
10. Never use the SOC2 attenuation, occupation deletions, population-control
    checks, or raw paths as causal components of the coefficient.

## Evidence ledger

| Manuscript object | Authoritative completed source |
|---|---|
| Canonical interval, MDEs, architecture precision, cells, quarterly, time-HAC, pseudo-breaks, covariance simulation | `yax/revision/referee_round2_20260905/precision_rotation/RESULTS_MEMO.md` and its `results/` files |
| SOC2 conditioning, paired attenuation, shape tests, stable tails, joint influence, service exclusions | `yax/revision/referee_round2_20260905/composition_influence/RESULTS_MEMO.md` and its `results/` files |
| January 2025 controls and admissible counterfactual language | `yax/revision/referee_round2_20260905/population_controls/POPULATION_CONTROL_FINDINGS.md` |
| Six-score dependence and eigenvalue spectrum | `yax/revision/referee_round2_20260905/architecture/ARCHITECTURE_STRUCTURE_FINDINGS.md` |
| Operation taxonomy, propositions, and bounded candidate ledger | `yax/revision/referee_round2_20260905/framework_census/ANALYTICAL_TAXONOMY_AND_PROPOSITIONS.md` and `CANDIDATE_ARCHITECTURE_CENSUS.md` |
| BCC public grouping bridge and grouping-specific architecture comparisons | `yax/revision/referee_round2_20260905/bcc_bridge/BCC_GROUPING_FINDINGS.md` and its `results/` files |
