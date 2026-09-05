# Referee Report

**Manuscript:** *Constructed Exposure Measures and Statement-Specific Robustness: Evidence from Early-Career Employment*
**Materials reviewed:** September 2026 manuscript and online appendix.
**Recommendation:** **Reject in its present form at a top general-interest economics journal.**

*This report evaluates the arguments, specifications, and reported results in the supplied documents; it is not an independent replication of the computations.*

## Confidential assessment for the editor

This paper addresses an important question: how much of an empirical conclusion about occupational AI exposure comes from the construction of the exposure variable rather than from the underlying labor-market evidence? Its strongest feature is the effort to connect measurement decisions to distinct empirical objects—sample coverage, tail membership, conditional regression variation, and occupational mobility classifications. The manuscript also deserves credit for reporting unsuccessful diagnostics and distinguishing descriptive employment associations from causal AI effects.

My concern is not simply that the paper lacks causal identification. A measurement paper need not identify a causal effect to make an important contribution. Rather, the current manuscript does not yet sufficiently distinguish **measurement uncertainty, changes in the economic construct, changes in the estimand, and sampling uncertainty**. Several headline conclusions also rely too heavily on differences in statistical significance rather than evidence that the underlying estimates differ.

The result is a substantial and useful empirical audit, but not yet a sufficiently general methodological contribution or a sufficiently decisive substantive finding for a top general-interest journal. I would not recommend an incremental revise-and-resubmit consisting of additional robustness checks. A successful redevelopment would require a clearer organizing framework, sharper comparative inference, and a more convincing account of what researchers learn from this exercise that extends beyond this particular implementation.

## Report to the author

### Summary and overall assessment

The paper holds a CPS employment-stock design broadly fixed while varying occupational exposure constructions. The principal specification compares changes after January 2023 in the employment stocks of workers aged 22–25 relative to those aged 26–65, across occupation-level exposure quintiles, conditional on Webb software exposure. The primary beta Q5–Q1 coefficient is −0.1311, corresponding to a −12.28 percent change in the relative employment-stock ratio—not an employment-probability effect or a count of displaced jobs.  

The manuscript develops three related findings. First, taxonomy and support decisions materially affect which occupations enter the analysis. Second, employment estimates depend on the exposure construct, comparison group, and representation. Third, exposure measures can disagree about the direction of particular occupational moves despite producing similar aggregate shares of upward mobility. The appendix provides extensive supporting exercises on calendar corrections, influence, comparison technologies, age groups, longitudinal flows, and inference.

There is much to appreciate. The paper correctly recognizes that the six initial measures are dependent implementations from two families rather than six independent validations. It also acknowledges the exact relationship among the task-family primitives, uses paired inference for several comparisons, distinguishes employment stocks from flows, and does not conceal the failed predeclared simultaneous-band criterion. These are substantive strengths.   

Nevertheless, the paper needs a clearer distinction between what it **demonstrates**, what it **suggests**, and what remains **statistically unresolved**.

## Major comments

### 1. The contribution needs a framework that separates changes in measurement from changes in the question

The central proposition—that robustness is specific to an economic statement—is sensible. But several exercises currently grouped under that proposition concern fundamentally different operations.

Repairing an incompatible occupation-code merge corrects an implementation error. Replacing a task-based LLM score with a broad capability-gap measure changes the technology construct. Replacing Q5–Q1 with Q5–Q2 changes the comparison of interest. Switching from a continuous regressor to quintiles changes the statistical representation. Transforming the F/G coefficients back into family coefficients changes coordinates without changing the fitted model.

These are not interchangeable forms of robustness. Indeed, the paper already recognizes many of these distinctions locally, but they do not yet organize the contribution.

I would restructure the paper around an explicit mapping from the underlying data and construction decisions to a well-defined population statistic. Each exercise should identify whether it changes the construct, target population, comparison, estimator, or merely the parameterization. This would let the reader distinguish a finding that is unstable under alternative measurements of the *same* object from findings that differ because they answer different questions.

A useful methodological contribution could then consist of precise invariance and sensitivity results. For example, positive affine transformations preserve rankings and weighted-quintile membership on fixed support, whereas changing \(D+\lambda S\) can alter rankings and therefore treatment assignments. With a fixed outcome model, categorical estimates remain unchanged between values of \(\lambda\) at which relevant assignments change. These implications would give the empirical audit a stronger analytical foundation.

The literature positioning also needs revision. The manuscript emphasizes that a scoped search did not find a paper combining this exact CPS design with the same sequence of audits. That is not, by itself, a persuasive novelty criterion.  The relevant comparison is with what existing measurement and sensitivity research enables researchers to learn. Andrews, Gentzkow, and Shapiro provide a formal relationship between estimates and identifying moments; Loughran and McDonald’s work on financial-disclosure readability illustrates a measurement contribution that diagnoses why a widely used construction is poorly suited to its application. These are useful benchmarks for sharpening the present paper’s contribution, not merely additional citations to insert. ([OUP Academic][1])

**Required improvement:** State a small number of general propositions or operational diagnostics, then show how the application establishes their empirical importance.

### 2. The principal architecture comparison does not establish the degree of heterogeneity suggested by the framing

The manuscript needs to distinguish three statements:

**Point-estimate agreement:** Do the estimates have the same sign?

**Evidence for uniformly negative coefficients:** Can a joint sign claim be supported over a specified architecture set?

**Evidence of differences across architectures:** Are paired coefficient differences distinguishable from zero?

The reported results do not give the same answer to these questions. All six initial common-support estimates are negative. The two external estimates are also negative: −0.0649 for Webb AI and −0.0110 for the OECD measure. Thus, the reported point-estimate sign pattern does extend to the external measures, although those estimates are not all reported on the same support. What weakens is the evidence for a uniformly negative association and the similarity of the estimated magnitudes. 

Moreover, the paired external-minus-beta intervals include zero: [−0.0411, 0.1704] for Webb AI and [−0.0015, 0.2244] for the OECD measure. The beta-minus-alpha contrast is likewise imprecise, with an interval of [−0.1023, 0.0376]. These intervals permit economically important differences, but they do not establish them.  

The manuscript acknowledges these facts, but phrases such as the broader architecture audit “changes the conclusion” can still invite a stronger interpretation than the evidence supports.

I would summarize the finding as follows:

> The reported coefficients are negative across all eight examined architectures, but statistical support for uniformly negative associations weakens when the architecture set expands. The external point estimates are smaller, while paired comparisons remain too imprecise to establish or exclude substantial architecture differences.

This is neither an equivalence conclusion nor a finding of invariance.

The main paper needs a consolidated table containing native-support estimates, matched-support estimates, paired differences, and their intervals. A joint test of equality over a clearly defined common-support set would also be informative. Where a full intersection would sacrifice too much coverage, report that limitation rather than treating separately matched comparisons as one common-sample experiment.

**Required improvement:** Organize the central empirical claims around direct comparisons, not whether individual intervals cross zero.

### 3. The external architectures require a stronger construct-validity argument

The admission rule requires documented constructs, public sources, non-title mapping, available components, distinct quintile cuts, and employment coverage above 80 percent. These are useful operational criteria. They do not establish that every admitted measure should capture the same economically relevant exposure for the post-2023 employment comparison. 

This matters particularly for the OECD measure. Its source describes a forward-looking framework covering nine cognitive, social, and physical domains, including exposure associated with robotics and embodied AI, and motivates applications over the next five to ten years. That differs substantively from measuring tasks accelerated by contemporary LLMs. ([OECD][2])

Consequently, a near-zero OECD coefficient might reflect a different technology boundary or horizon rather than poor reliability in measuring a common underlying object. The manuscript need not resolve which architecture is “true,” but it should explain what disagreement between these constructs teaches us.

I would add a compact architecture matrix specifying technology scope, primitive, label-generation method, source vintage, intended horizon, mapping route, and the substantive employment hypothesis associated with each measure. Publication dates and the dates of the underlying occupational information should be distinguished. Later-vintage measures are not automatically invalid for retrospective description, but they require a different interpretation from genuinely preperiod exposure measures.

The conditioning variable creates another comparability issue. Webb software exposure has a reported correlation of 0.7021 with Webb AI. Holding this control fixed across regressions does not ensure that the same economic component is removed from each AI measure.  The paper should systematically show, on matched support, the progression from unconditioned exposure comparisons to Webb-conditioned comparisons and then to the principal alternative conditioning sets.

Finally, requiring distinct quintile cuts makes architecture admission depend partly on the chosen representation. The manuscript permits natural categories for telework and STEM when quintiles collapse, but excludes candidate AI architectures that fail a distinct-cut requirement. This asymmetry needs justification.  

**Required improvement:** Separate disagreement about the technology being measured from disagreement among implementations of a common construct.

### 4. The employment evidence needs a sharper interpretation of the reference group and broad occupational variation

Figure 3 is one of the most useful pieces of evidence in the paper. By displaying young stocks, older stocks, and their ratios separately for Q1 and Q5, it makes clear why the fitted contrast should not be described simply as a collapse in high-exposure young employment. The low-exposure trajectory and the older-worker denominator both matter.  

However, “reference dependence” needs more precise terminology. Re-expressing the same fitted model with a different omitted category does not change the Q5–Q1 contrast. Comparing Q5–Q1 with Q5–Q2 changes the estimand. The interesting economic question is therefore not whether the coefficient is sensitive to relabeling, but whether the pattern is predominantly an unusually favorable Q1 trajectory, a broadly graded exposure relationship, or a disadvantage concentrated in the upper tail.

The reported profile—0, −0.0855, −0.0478, −0.0970, and −0.1311 from Q1 through Q5—motivates that question but does not settle it.  I would request a joint test that Q2–Q5 share a common post coefficient, together with an appropriately formulated assessment of monotone ordering. Failure to detect Q5–Q2 and Q5–Q4 differences is not evidence that those groups are economically equivalent.

The within-SOC2 permutation is also more consequential than its current placement suggests. The observed coefficient is −0.1311, while the permutation distribution is centered at −0.1097. This motivates asking directly how much identifying variation comes from differences across broad occupational families rather than detailed occupations within them. It does not provide a formal decomposition, and the author appropriately disclaims exchangeability. 

A transparent next exercise would add broad-occupation-family-specific young-relative monthly effects. This would change the conditioning estimand and potentially remove substantial exposure variation, so it should be accompanied by support and information diagnostics. Nevertheless, it addresses the relevant question more directly than an assumption-dependent permutation probability.

The event study should also report the magnitude of differential trends that the design can meaningfully exclude, rather than emphasizing the pretrend \(p\)-value of .929.  A trend-sensitivity analysis could quantify how conclusions change under specified departures from parallel trends; it would not establish AI specificity. Rambachan and Roth provide the relevant conceptual framework. ([The Review of Economic Studies][3])

**Required improvement:** Identify which occupational comparisons generate the descriptive association before giving it an AI-related interpretation.

### 5. The data corrections are valuable, but implementation errors should not be treated as economically defensible alternatives

The taxonomy example is striking: computer-and-mathematical employment coverage rises from 3.33 to 97.7 percent. But the manuscript also correctly describes exact-code matching across incompatible vintages as a failure mode rather than a defensible preferred specification. 

That distinction should carry through the contribution. Showing that an incorrect merge changes results is useful quality-control evidence. It is not equivalent to showing that reasonable alternative constructions produce materially different economic conclusions. The broader importance would be clearer if the paper demonstrated how this failure arises in commonly used workflows, or supplied a general diagnostic that reliably detects it.

The more substantive issue is the corrected bridge. Applying common conversion proportions to young and older workers mechanically preserves the source occupation’s age ratio across its target components. The manuscript reports that one-to-many sources account for 20.03 percent of early-period weighted employment. 

The stable-taxonomy and post-2020 checks are valuable, but I would also request results for one-to-one mappings, comparisons between split and nonsplit sources, and a statement of how age-specific allocation uncertainty could affect the estimates. This is an especially relevant measurement uncertainty because the outcome itself is an age comparison. It cannot be resolved by documenting the crosswalk alone.

The calendar correction should become the default descriptive estimate in the revised exposition. Preserving the original frozen estimate is important for the design record, but retaining a known incomplete calendar as the primary empirical benchmark creates unnecessary friction. The repaired estimate, −0.1346, is close to the frozen −0.1311, so this change would not alter the broad result. 

Finally, the separate continuous exercise expands to 495 occupations, while the main sample accounting starts from 490 candidate occupations. These may be different legitimate universes, but their relationship should be explicitly reconciled.  

**Required improvement:** Make the corrected data pipeline the substantive baseline and separate coding failures from uncertainty among defensible harmonizations.

### 6. Inference requires an explicit account of the source of randomness

The grouped-binomial objective is explained carefully. In particular, the manuscript correctly treats CPS-weighted stocks as estimating-equation inputs rather than literal independent binomial trials. My concern is not the use of fractional weighted totals; it is the inferential model attached to those totals. 

What is random for the paper’s principal confidence interval? Possible answers include household sampling, repeated observations of respondents, occupation-level economic shocks, exposure-label generation, and taxonomy allocation. The reported occupation-cluster procedure addresses a particular model of uncertainty conditional on the selected labels and mappings. It does not automatically cover the other sources.

This requires more than noting that the estimator has 468 clusters. Because the analysis includes most candidate occupations, the author should clarify whether the target is a finite-population descriptive contrast estimated from a household survey or a parameter under a stochastic model of occupational shocks. Either can be meaningful, but they imply different justifications for uncertainty. The broader distinction between sampling and design components is central to the clustering literature. ([OUP Academic][4])

The two-way occupation/month comparison is useful but not dispositive. It need not accommodate persistent shocks shared by multiple occupations in the same broad family, or dependence introduced when source observations contribute to several target occupations. The paper reports very similar one- and two-way standard errors, but that similarity should not be interpreted as validating all relevant dependence assumptions. 

I would request a self-contained description of the wild-score procedure: the nuisance-adjusted score, Hessian or information matrix, null imposition, studentization, finite-sample corrections, and construction of paired and simultaneous statistics. The effective information count of 43.30 and top-five information share of 24.57 percent make finite-sample calibration particularly relevant. They do not, by themselves, establish that the reported procedure is unreliable. 

The failed residual-wild refit should also be interpreted differently. Reporting that all pseudo-outcomes violated binomial bounds is transparent. But failure of that particular pseudo-outcome construction is not a reason to leave the one-step approximation unvalidated. A score bootstrap need not generate admissible pseudo-outcomes to be valid; conversely, its validity is not established because an inappropriate full-refit construction fails. A feasible full-refit scheme under a stated sampling model, or a targeted simulation calibration, would be more informative.

Finally, the paper should preserve the distinction between the intersection–union test and the predeclared simultaneous-band criterion. The maximum marginal one-sided \(p\)-value of .045 is not mathematically inconsistent with failure of the simultaneous band. It should not, however, substitute retrospectively for a different predeclared success criterion. More bootstrap draws would also improve numerical stability for borderline results. 

**Required improvement:** State the maintained inferential model and validate the procedure for that model, without implying that clustering absorbs construction uncertainty.

### 7. The F/G analysis should be simplified and expressed in primitive economic units

The exact F/G-to-family transformation is handled appropriately, and the acknowledgment that these coordinates are not orthogonal is important.  Nevertheless, the labels “consensus” and “disagreement” risk giving the coordinates more independent economic content than their construction warrants.

The task-family centroid averages three separately standardized variables:

$$
D,\qquad D+\tfrac12S,\qquad D+S.
$$

It therefore remains a linear combination of only two primitives. If their standard deviations are \(\sigma_\alpha,\sigma_\beta,\sigma_\gamma\), then, up to a constant,

$$
E=
\frac13\left(
\frac1{\sigma_\alpha}+\frac1{\sigma_\beta}+\frac1{\sigma_\gamma}
\right)D+
\frac13\left(
\frac{1/2}{\sigma_\beta}+\frac1{\sigma_\gamma}
\right)S.
$$

This follows directly from the paper’s construction. Equal weighting of standardized implementations therefore embeds a particular, scale-dependent weighting of direct exposure and complementary-software exposure.  

The paper should report those effective weights and explain why they are economically meaningful. Deleting a measure changes those weights; it is not simply withdrawing an independent piece of information.

The leave-one-measure interpretation also needs restraint. Removing beta changes \(b_G\) from .0309 to .0287, while its interval begins to include zero. This is a modest point-estimate change, not demonstrated instability merely because statistical significance changes. Removing broad produces a larger change to .0215, but that change also needs direct comparative inference. 

I would move the representative AIOE-plus-beta and direct \(D,S\) specifications ahead of F/G, report common-unit contrasts, and retain the rotation as a supplementary illustration. The primitive models are easier to interpret, although their conditional coefficients still should not be treated as causal technology channels. 

**Required improvement:** Make primitive constructions and effective weights primary; do not equate crossing a significance threshold with a significant change.

### 8. The mobility analysis needs an economically motivated scale and a more fully specified benchmark

The distinction between any directional conflict and substantial opposition is useful. The reported decline from 53.28 percent conflict at zero to 14.00 percent substantial opposition at 0.5 standard deviations shows that the headline depends heavily on what counts as a consequential disagreement. 

However, 0.5 standard deviations is a statistical scale, not automatically an economically meaningful threshold. The paper should connect thresholds to interpretable changes in task shares or to a concrete classification decision. Percentile-rank thresholds help assess scale sensitivity, but they do not by themselves establish economic materiality.

The task-family structure also yields a useful exact implication. For a switch,

$$
\Delta X(\lambda)=\Delta D+\lambda\Delta S.
$$

For \(\lambda\in[0,1]\), this lies between the two endpoint movements. Consequently, beta cannot create a new positive-versus-negative conflict when alpha and broad agree in sign. Separate positive standardizations preserve that sign result. Beta is therefore redundant for detecting zero-threshold directional conflict when both endpoints are already included, although it need not be redundant for separately standardized magnitude thresholds or movement-mass weighting. This is an analytical implication of the reported primitive identity, not an additional empirical result. 

This suggests reporting a family-balanced pairwise disagreement matrix alongside the six-way “any conflict” statistic. Movement-mass weighting also needs justification because summing movements across implementations makes the statistic depend on how many versions of each primitive have been included.

The rematching benchmark raises a separate concern. The main implementation represents 98.31 percent of switch weight and produces a realized-minus-benchmark gap of approximately 0.96 percentage points, close to a one-point threshold.  It is unclear whether the realized conflict rate is recalculated on exactly the represented support. That must be explicit. If the target remains all switches, the omitted 1.69 percent of weight is potentially consequential: absent restrictions, its contribution can generate a range of 1.69 percentage points in an overall conflict rate, larger than the reported excess.

In addition, preserving margins and eliminating self-transitions does not uniquely define a probability distribution over feasible rematchings. The no-self repair needs an algorithmic description and an explanation of the induced distribution. Different repair rules could preserve the same margins but yield different expected conflict.

Finally, the Monte Carlo standard error measures numerical uncertainty in estimating the benchmark expectation conditional on the observed data. It is not the sampling uncertainty of the realized-minus-benchmark gap. These should be reported separately. The conclusion that broad assortativity “explains” most excess conflict is also too strong without defining the comparison benchmark and what is meant by explanation. 

**Required improvement:** Specify the decision-relevant disagreement statistic, compare identical support, and separate benchmark simulation uncertainty from sampling uncertainty.

### 9. The design chronology should be verifiable, but should not organize the entire narrative

The appendix reports commit hashes and distinguishes frozen artifacts from exploratory revisions. That is good practice. However, hashes alone do not establish the timing or content of a design freeze for a reader who does not have the associated repository, protocol, and artifacts. 

The replication materials should include a dated protocol, a precise definition of protected outcomes, the information available when design choices were made, a mapping from prespecified hypotheses to reported tests, and a manifest connecting each headline result to its sample, script, and output.

The supplied PDFs are not enough to verify those claims, so I treat the chronology as reported rather than independently established.

At the same time, the manuscript reads in places like a response-to-referees document rather than a self-contained article. Phrases such as “referee-requested,” “R1-style,” “R2-style,” and repeated explanations that unfavorable results were not replaced belong primarily in the response letter or design appendix. The main article should explain why an exercise is scientifically informative, not who requested it.  

**Required improvement:** Make the record auditable while reorganizing the article around economic questions rather than revision history.

## Specific corrections and presentation issues

**Event-study specification.** Figure 5 identifies October 2022 as the omitted reference month, while its caption identifies December 2022 as the omitted transition month. These can be different legitimate roles, but they should be stated unambiguously. Supply the exact event-study equation, the treatment of Webb exposure over time, and whether the plotted model is frozen or exploratory. 

**Beta estimates across exercises.** The common-support table reports beta at −0.1290, while the \(D+\lambda S\) exercise reports −0.1297 at \(\lambda=.5\). Explain whether support, classification, weights, or another specification component differs. Under identical construction and estimation, these should coincide.  

**Respondent-equivalent outcomes.** Define this term operationally. Dividing all cell stocks by a single common constant multiplies the objective by that constant and cannot change its maximizer. The reported movement to −0.1308 therefore requires a different cell construction or noncommon rescaling; specify which.  

**Early-career terminology.** Ages 22–25 define an age group, not observed labor-market experience. The paper acknowledges this, but should consistently avoid implying that every included worker is a new entrant. Composition by education and enrollment would help interpret the comparison. 

**Main results table.** The core architecture coefficients, direct differences, and simultaneous inference should appear in one main-text table. Currently, the reader must assemble the central evidence from prose, figures, and appendix tables.

**Longitudinal evidence.** Retaining the imprecise flow estimates in the appendix is appropriate. Continue to describe entry destination as an allocation conditional on entering employment, not an employment-finding probability, and do not interpret the insignificant flow coefficients as evidence that those mechanisms are absent. 

## What would materially strengthen the paper

The highest-return revision is not another large collection of robustness checks. It is a reorganization around three deliverables.

First, establish a framework distinguishing alternative measurements of a common object from different constructs, populations, contrasts, and parameterizations.

Second, rebuild the employment section around a corrected-data baseline and direct, matched-support comparisons. Report what architecture differences the data can establish, what differences they cannot exclude, and where the identifying occupational variation lies.

Third, develop the measurement-specific content more deeply: taxonomy allocation uncertainty, analytical implications of the task-family primitives, family-balanced disagreement statistics, and a fully specified rematching benchmark.

A new adoption dataset or a causal research design is not a prerequisite for this measurement-centered route. But the paper must deliver something stronger than the general observation that different constructions can yield different answers.

## Concluding assessment

The manuscript contains a useful descriptive employment pattern and an unusually extensive record of measurement and implementation audits. Its strongest ingredients are the distinction between support and scores, the recognition that common support does not imply common treatment groups, and the demonstration that mobility disagreement depends on both construction and scale.

At present, however, the overarching interpretation runs ahead of the comparative evidence. **The paper documents substantial differences in empirical treatment construction more convincingly than it establishes statistically distinguishable differences in employment relationships.** It also combines genuine measurement sensitivity with changes in the economic question.

For a top general-interest journal, I would therefore recommend rejection in the current form. The promising route forward is a more sharply defined measurement contribution—with exact invariance results, interpretable comparisons, and credible uncertainty—not simply a longer robustness appendix.

[1]: https://academic.oup.com/qje/article-abstract/132/4/1553/3861634 "oup.silverchair-cdn.com"
[2]: https://www.oecd.org/en/publications/the-oecd-ai-exposure-measure_f3da0f0a-en.html "The OECD AI exposure measure | OECD"
[3]: https://www.restud.com/a-more-credible-approach-to-parallel-trends/ "A More Credible Approach to Parallel Trends - The Review of Economic Studies"
[4]: https://academic.oup.com/qje/article/138/1/1/6750017 "oup.silverchair-cdn.com"
