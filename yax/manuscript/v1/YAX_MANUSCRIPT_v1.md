# Measuring “AI Exposure”: Construct Divergence, Identifying Support, and Early-Career Employment

Lily Luo
First full manuscript draft — August 2026

## Abstract

The empirical AI-and-labor literature increasingly treats occupational “AI exposure” as a common treatment, although prominent indices begin from different technologies, label different occupational primitives, and use different aggregation rules. This paper traces those choices from native score construction through occupational mapping, effective identifying support, and downstream labor-market inference. Six AI-exposure measures are harmonized to a common occupational framework and evaluated against eight transparent occupational characteristics. The measures differ sharply in occupational content and in the comparisons that identify an exposure coefficient: across 30 frozen AI-by-computerization architectures, the effective number of identifying occupations ranges from 11.9 to 84.5, and the top five occupations account for 15.0% to 46.6% of residual variation. <!-- prov:A01 --> Yet a common nationally representative CPS design yields a strikingly stable sign. Across 12 pre-specified Eloundou alpha/beta models, the post-January-2023 top-versus-bottom exposure-quintile estimate ranges from -0.097 to -0.208 log points, and every wild-bootstrap confidence interval excludes zero. <!-- prov:A02 --> The primary estimate is -0.131 (95% CI [-0.217, -0.045]; p = .003), or about a 12.3% relative decline in the young-worker employment stock. <!-- prov:A03 --> A direct paired beta-minus-alpha comparison is -0.032 (95% CI [-0.102, 0.038]); the design detects no difference but cannot establish economic equivalence. <!-- prov:A04 --> Occupational harmonization matters mainly by changing which occupations enter the estimand, while the magnitude also varies materially with the definition of pre-existing computerization. The results support measurement discipline rather than a broad causal claim: exposure architectures and identifying occupations diverge, while the negative young-relative employment-stock gradient is robust in sign.

## 1. Introduction

The empirical AI-and-labor literature increasingly speaks of occupational “AI exposure” as though it were a common treatment. Researchers merge an exposure score onto occupations, interact it with time, and interpret the resulting coefficient as evidence about the labor-market consequences of artificial intelligence. That workflow is now routine. The object entering the regression is not.

Prominent measures are built from different economic primitives. The Felten-Raj-Seamans family begins with applications of artificial intelligence, asks how those applications relate to occupational abilities, and aggregates through O\*NET ability requirements (Felten, Raj, and Seamans 2018, 2021). The Eloundou-Manning-Mishkin-Rock family begins with large-language-model capabilities, asks whether an LLM—alone or with complementary software—could reduce the time required for occupational tasks, and aggregates task judgments to occupations (Eloundou et al. 2024). Newer families use observed platform activity, retrieval evidence, reinforcement-learning feasibility, startup targeting, or updated capability taxonomies. The resulting indices may be correlated, but correlation does not make their construction choices economically interchangeable.

This paper asks what survives once the full measurement chain is made explicit. The organizing sequence is:

> **measurement architecture → identifying variation → harmonization and support → downstream labor inference.**

The empirical laboratory is the recent debate over early-career employment in occupations more exposed to generative AI. This setting is useful because the outcome is substantively important, recent administrative-data work reports sizable declines for workers aged 22–25 in highly exposed occupations, and public-data analyses have reached less uniform conclusions. The paper does not treat that debate as a blank slate. It instead holds one public outcome, one estimator, one timing rule, and one inferential procedure fixed while changing the construction of the exposure variable and the pre-existing computerization margin against which it is evaluated.

Four findings emerge.

First, the exposure measures do not behave like mechanically interchangeable proxies. Across six measures and eight occupational characteristics, the three AIOE variants load strongly on cognitive content, education, wages, teleworkability, and computer use. Eloundou alpha—the share of tasks directly accelerated by an LLM—has much weaker relationships with most of those characteristics, while beta and the broad E1+E2 measure occupy intermediate positions. In a joint audit using all eight characteristics, the explanatory R-squared ranges from 0.368 for alpha to 0.971 for one AIOE variant. These patterns do not prove that no latent AI-exposure factor exists. They show that the convenient classical-error representation, in which every index is merely a noisy version of the same transparent treatment, should not be assumed.

Second, nominal occupational coverage substantially overstates effective identifying support. Across all 30 pre-specified AI-measure-by-computerization-control pairs, the effective number of occupations ranges from 11.9 to 84.5, and the five largest contributors account for 15.0% to 46.6% of residual variation. <!-- prov:I01 --> Conditional on Webb software-patent exposure, Eloundou alpha is identified by only 17.4 effective occupations, with 41.6% of residual variation carried by the top five; beta has 53.3 effective occupations and a 22.2% top-five share. <!-- prov:I02 --> The leading occupations also change: software developers and clerical occupations dominate alpha in that architecture, whereas beta draws more broadly on construction laborers, maids, bookkeeping clerks, and freight laborers. An “AI-exposure effect” is therefore partly a statement about which occupational comparisons remain after the researcher defines both AI exposure and prior computerization.

Third, occupational harmonization changes the estimand mainly through sample composition. In a four-step AIOE decomposition, repairing exposure values on unchanged support barely changes the coefficient, from -0.01885 to -0.01920. Expanding support changes it to -0.03156; excluding computer and mathematical occupations leaves -0.02940. <!-- prov:I03 --> Thus the important margin is not a large revision of values among occupations already matched. It is the re-admission of occupations previously outside the estimation sample, and the result is not driven solely by restoring software-intensive jobs.

Fourth, the downstream sign is more stable than the measurement architecture. Across the 12 frozen alpha/beta headline models, top-versus-bottom exposure-quintile coefficients range from -0.0971 to -0.2085 log points—roughly -9.3% to -18.8%—and all 12 wild-bootstrap confidence intervals exclude zero. <!-- prov:I04 --> The primary beta-by-Webb strict-support estimate is -0.1311 (95% CI [-0.2170, -0.0451]; p = .003), approximately a 12.3% relative decline in the young-worker employment stock in the most versus least exposed quintiles after January 2023. <!-- prov:I05 --> This outcome is an occupation-by-age-group employment stock. It is not an individual unemployment probability and can move through entry, exit, or occupational switching.

Sign robustness is not magnitude equivalence. The direct paired beta-minus-alpha estimate is -0.0324 with a paired standard error of 0.0370 and a 95% interval of [-0.1023, 0.0376] (p = .403). <!-- prov:I06 --> Common bootstrap draws preserve the covariance between coefficients. The frozen design therefore does not detect a beta-alpha difference; because the interval contains economically meaningful differences, it also does not establish equivalence. The ex-ante paired design had 80% power to detect a difference of about 3.27 percentage points, but the realized interval is wider than that design-stage diagnostic implied. <!-- prov:I07 -->

This evidence contributes to a fast-moving measurement literature. Yin, Vu, and Persico (2026) show that occupational LLM-exposure scores can be unstable across annotating models even when the rubric is held fixed. Yin and Ogut (2026) show that platform selection alters observed-use exposure and downstream estimates. Rai (2026), Frank et al. (2025), the Economic Innovation Group (Eckhardt and Goldschlag 2025), the Budget Lab (2026a, 2026b), Pulito et al. (2026), and Brynjolfsson, Chandar, and Chen (2026) each compare important aspects of exposure construction or downstream relationships. This paper does not claim to be the first comparison of AI-exposure measures, the first occupational crosswalk, or the first public-data study of young workers. Its narrower contribution is to join cross-family construction, construct diagnostics, occupational influence, mapping and common support, and paired same-design inference in one frozen empirical chain.

The paper proceeds as follows. Section 2 describes the measurement architectures and adjacent literature. Section 3 presents the CPS data and occupational harmonization. Section 4 defines the employment-stock estimand. Sections 5 and 6 examine construct content and identifying support. Section 7 holds the outcome and design fixed while varying exposure. Section 8 studies computerization and remotability. Section 9 presents dynamics and falsification. Sections 10–12 discuss implications, limitations, and conclusions.

## 2. What Is Occupational AI Exposure?

### 2.1 Measurement architecture

An occupational exposure score compresses a long sequence of choices into one variable. At minimum, the researcher chooses a technology or capability definition, an occupational primitive, a source of labels, an aggregation rule, an occupational taxonomy, a crosswalk, a support rule, and a regression scale. Figure 1 separates native construction from empirical harmonization.

![Figure 1. Measurement genealogy](figures/figure1_measurement_genealogy.png)

**Figure 1. Measurement genealogy.** Native technology and labeling choices are followed by occupation aggregation, taxonomy mapping, common-support decisions, and construction of the regression treatment. The figure is a presentation of the frozen measurement documentation and introduces no empirical result.

Table 1 summarizes the measures used in the confirmatory analysis. The AIOE family maps ten AI applications to 52 occupational abilities using crowd judgments and then combines ability exposure with occupation-specific O\*NET requirements (Felten, Raj, and Seamans 2018, 2021). The three YAX variants retain the same conceptual family but vary aggregation: an administrative equal-weight construction, a direct ability construction, and a source-employment-weighted construction.

The Eloundou family instead labels occupational tasks according to whether an LLM can reduce task-completion time by at least half while maintaining quality (Eloundou et al. 2024). Alpha counts E1 tasks, for which an LLM alone can achieve the threshold. Beta adds half weight to E2 tasks, for which the threshold becomes feasible with complementary software. The broad E1+E2 score is called zeta in the published paper; the repository preserves the source data's `gamma` field name but labels the object “broad” in the manuscript.

The difference is economic, not merely computational. An ability-based score may emphasize broad cognitive requirements relevant to many AI applications. A task-based LLM score may emphasize current technical feasibility. Adding E2 embeds a view about complementary software and organizational implementation. None is automatically the “correct” treatment for every question.

See [Table 1](tables/table1_anatomy_of_ai_exposure_measures.md).

### 2.2 Related measurement literature

Recent work makes the instability of exposure measurement itself an empirical object. Yin, Vu, and Persico (2026) hold a task rubric fixed and vary the frontier LLM that supplies annotations, finding substantial score and downstream-coefficient instability. Yin and Ogut (2026) hold an observed-use design fixed but vary platform-user inputs, showing that selection into platforms affects exposure and employment estimates. Rai (2026) evaluates whether several prominent indices load on cognitive occupational content. Frank et al. (2025) compare multiple scores as predictors of pre-ChatGPT unemployment risk and show that an ensemble can outperform individual measures.

Institutional and applied studies extend the comparison. Eckhardt and Goldschlag (2025) use five measures for CPS unemployment, labor-force exit, and occupational switching and make alternative mappings visible in public code. The Budget Lab (2026a) harmonizes seven metrics to a common taxonomy and later uses the harmonized measures and principal components in public labor-market outcomes (Budget Lab 2026b). Pulito et al. (2026), the closest same-outcome/same-specification predecessor, put five standardized indices into the same Danish firm-adoption design. Brynjolfsson, Chandar, and Chen (2026) use multiple exposure measures, improved occupational mapping, remote-work controls, and public-data benchmarks in the exact early-career-employment debate studied here.

These papers close several broad novelty claims. Comparing multiple scores is not new. Harmonizing taxonomies is not new. Finding that coefficients move across scores is not new. YAX instead links the native construction of each score to observable occupational content, asks which occupations identify it conditional on alternative computerization definitions, separates value correction from sample re-admission, and carries the measures into a common national outcome design with direct paired inference.

Other emerging measures underscore why this chain will remain useful. The OECD (2026) maps capability domains to occupational requirements. Mouchel, Bouquet, and Sheffi (2026) use retrieval evidence rather than model priors. Tomei and Klein Teeselink (2026) use reinforcement-learning feasibility. Fenoaltea et al. (2026) use startup-backed applications to capture market targeting. Lund et al. (2026), Merola et al. (2026), and del Rio-Chanona et al. (2025) emphasize that technical exposure is neither realized adoption nor net labor-market impact. As the set of indices expands, the need to audit the entire measurement-to-inference pipeline grows rather than recedes.

## 3. Data and Occupational Harmonization

### 3.1 CPS employment stocks

The labor-market analysis uses monthly IPUMS Current Population Survey microdata from January 2017 through July 2026. The wide extract contains 9,262,480 person records. Employed respondents are aggregated with CPS weights into occupation-by-age-group-by-month employment stocks. The young group is ages 22–25; the comparison group pools ages 26–65. The resulting unit is a cell, not a person.

This choice avoids assigning an occupation to someone who is not employed. It also defines the interpretation sharply. A decline in the young employment stock of an occupation can reflect fewer entrants, exits from employment, or movement to another occupation while remaining employed. The design cannot separate these channels and does not estimate an individual probability of unemployment.

The static post period begins in January 2023 and ends in July 2026. December 2022 is retained as a transition month in the event study but excluded from the static post coefficient because ChatGPT was released on November 30, after the November CPS reference week. October 2025 is absent from the source series and is excluded.

### 3.2 Occupational taxonomies

The CPS occupation system changes during the sample. Raw 2017–2019 codes use the Census 2010 occupation taxonomy, while 2020 onward uses Census 2018. The harmonization maps pre-2020 occupations to Census 2018 using the Census Bureau's official total conversion rates. Post-2020 codes are matched directly. Native SOC-based exposure measures are first collapsed within six-digit SOC codes and then mapped to Census occupations using official crosswalks and available employment weights. Missing components are never silently renormalized under the primary rule.

The strict primary coverage rule retains an occupation only when every mapped component has an exposure score. It covers 88.70% of eligible employment. Two pre-specified sensitivities report sibling imputation and scored-component renormalization when at least 95% of component mass is observed. These rules are not interchangeable: they define different populations and therefore different estimands.

The analysis distinguishes nominal code coverage from employment coverage and both from effective identifying support. A dataset can contain hundreds of occupations while a regression coefficient is effectively driven by a few dozen. Section 6 makes that distinction operational.

### 3.3 Mapping decomposition

The four-step decomposition in Table 4 asks whether harmonization matters by changing exposure values among already matched occupations or by changing which occupations enter the analysis. It begins with the original AIOE values on original support, replaces values while holding support fixed, expands support using the repaired mapping, and finally excludes computer and mathematical occupations from the expanded sample. Because the coefficient is reported per fixed SD of AIOE and always conditions on Webb exposure, the sequence isolates measurement correction from composition as transparently as the available mapping permits.

## 4. Empirical Framework

The primary model is a saturated Poisson pseudo-maximum-likelihood difference-in-difference-in-differences specification on employment-stock cells:

\[
E[N_{oat}] = \exp\left[\gamma_{oa}+\delta_{ot}+\lambda_{at}
+\beta_{AI}(AI_o\times Young_a\times Post_t)
+\beta_C(Comp_o\times Young_a\times Post_t)\right].
\]

Here, \(N_{oat}\) is the weighted employment stock in occupation \(o\), age group \(a\), and month \(t\). Occupation-by-age-group fixed effects absorb each occupation's persistent young-versus-older gap. Occupation-by-month fixed effects absorb shocks to an occupation that affect both age groups. Age-group-by-month fixed effects absorb the national young-versus-older path. The remaining coefficient compares changes in the within-occupation young-versus-older gap across occupations with different pre-defined AI exposure, conditional on the corresponding interaction for pre-existing computerization.

The primary exposure is Eloundou beta. Alpha is the frozen contrast. Webb software-patent exposure is the primary computerization control; O\*NET computer-use importance, O\*NET computer-use level, Autor-Dorn routine-task intensity, and Frey-Osborne automation probability are pre-specified alternatives. Standardized-score models support the remote-work and mapping exercises. The headline literature-comparable contrast places each exposure on employment-weighted quintiles and reports Q5 relative to Q1, with Q2–Q4 absorbed separately.

Inference clusters by occupation. The primary confidence intervals and p-values use at least 999 occupation-cluster Rademacher wild-bootstrap draws. The paired beta-alpha comparison applies the same draw to both estimators and constructs the difference within draw, preserving covariance. The design and interpretation rules were frozen before protected post-period outcomes were opened; the repository tag is a git-verifiable design freeze, not an external preregistration.

Three families of tests organize the evidence. Test A asks whether exposure measures encode different occupational content. Test B asks which residual occupational comparisons identify each score conditional on a chosen computerization margin. Test C holds outcome, support, estimator, and inference fixed and asks whether alternative exposure definitions yield distinguishable downstream coefficients.

## 5. Do AI-Exposure Measures Capture the Same Occupational Construct?

Table 2 reports all 48 pre-specified employment-weighted correlations: six AI-exposure measures by eight occupational characteristics. The characteristics are cognitive ability importance, manual and physical ability importance, Autor-Dorn routine-task intensity, required education, log mean annual wage, Dingel-Neiman teleworkability, STEM employment share, and O\*NET computer-use importance.

The AIOE variants form a recognizable cluster. Their correlations with cognitive content range from 0.653 to 0.689; with education, 0.688 to 0.708; with log wages, 0.611 to 0.640; with teleworkability, 0.741 to 0.754; and with computer use, 0.847 to 0.854. Their correlations with manual and physical content are between -0.913 and -0.939. This is coherent with an ability-based measure that emphasizes cognitively intensive work, but it also means AIOE is empirically close to familiar dimensions of skilled, computer-mediated work.

Eloundou alpha behaves differently. Its correlations are -0.032 with cognitive content, -0.034 with education, 0.011 with wages, 0.200 with teleworkability, 0.436 with STEM share, and 0.304 with computer use. Beta becomes more similar to the AIOE pattern once software-complemented tasks enter: 0.478 with cognitive content, 0.425 with education, 0.478 with wages, 0.589 with teleworkability, and 0.797 with computer use. The broad E1+E2 measure moves further in that direction. These differences are consistent with the economics of the scoring rules: E2 introduces tasks whose acceleration depends on complementary software, which overlaps naturally with the digital organization of work.

Routine-task intensity is not the axis on which the measures diverge most. Correlations with RTI are positive but modest, from 0.108 to 0.217. Nor do the results imply that AIOE is merely teleworkability or computer use. The point is that the measures weight those dimensions differently and therefore encode different occupational content.

The joint residual audit sharpens the comparison. On common support of 348 occupations, the eight characteristics explain 95%–97% of the three AIOE variants, 74% of beta, 81% of the broad Eloundou measure, and only 37% of alpha. Alpha's residual is not diffuse: 31.5 effective occupations remain, and the top five account for 33.7% of residual variance. The corresponding effective counts are 35.5–44.2 for AIOE and 36.9 for beta. A score can therefore be distinct from observable characteristics and still rely on a concentrated residual.

See [Table 2A](tables/table2a_construct_diagnostics.md) and [Table 2B](tables/table2b_joint_construct_residual_audit.md).

The evidence supports “construct divergence” in a disciplined sense. It does not establish six unrelated treatments, and it does not recover a uniquely correct latent index. It establishes that construction architecture has observable empirical content and that researchers should not invoke a common latent treatment without showing what is shared and what is measure-specific.

## 6. Where Does the Identifying Variation Come From?

Test B residualizes each AI-exposure measure on each of five computerization controls using frozen pre-period employment weights. For each of the 30 combinations, it reports the residual variance, the inverse-Herfindahl effective number of identifying occupations, the share carried by the five largest contributors, the dominant occupational family, and the names of the leading occupations.

![Figure 2. Identifying support](figures/figure2_identifying_variation.png)

**Figure 2. Identifying support across all 30 frozen architectures.** The left panel reports the effective number of identifying occupations; the right panel reports the residual-variance share carried by the five largest occupations. Values are presentation-only reproductions of `TEST_B_IDENTIFYING_VARIATION_FULL.csv`; no outcome is used. Across cells, effective occupations range from 11.9 to 84.5 and top-five shares from 15.0% to 46.6%. <!-- prov:F02 -->

The key distinction is between nominal support and effective support. Eloundou alpha and beta both have 468 occupations when conditioned on Webb. Yet alpha has only 17.4 effective occupations and a 41.6% top-five share, while beta has 53.3 effective occupations and a 22.2% top-five share. Software developers alone carry 19.6% of alpha's residual variance in that architecture. The remaining leading contributors are computer programmers, bookkeeping clerks, billing clerks, and administrative assistants. Beta's top contributors are software developers, construction laborers, maids, bookkeeping clerks, and hand freight laborers.

Changing the computerization control changes the comparison. Conditional on O\*NET computer-use importance, alpha has 31.1 effective occupations; its leading contributors remain concentrated in programming and clerical work. Beta has 63.2 effective occupations and is led by retail supervisors, automotive technicians, bookkeeping clerks, wholesale sales representatives, and truck drivers. Conditional on Autor-Dorn RTI, alpha falls to 11.9 effective occupations and a 46.6% top-five share. The broad Eloundou score, by contrast, reaches 84.5 effective occupations under Webb and 77.5 under RTI.

The three AIOE variants are generally more diffuse than alpha across computerization controls, with effective counts mostly between 59 and 82. They are not identical. The ability-direct variant under O\*NET level reaches 82.2 effective occupations, while the OEWS-weighted variant under RTI has 62.1. The identities of the top occupations also rotate across architectures.

See [Table 3](tables/table3_identifying_variation_all_30_architectures.md).

These are not leverage diagnostics in the conventional regression sense. They describe the pre-outcome residual variation available to identify the AI coefficient after conditioning on another occupational technology measure. They reveal what comparison the design is asking the outcome data to price. Two models can use almost the same number of occupation codes yet estimate substantively different weighted contrasts.

This result also changes how collinearity should be discussed. A high raw correlation does not automatically make a coefficient unidentified; it raises variance and changes the residual comparison. Conversely, low raw correlation does not guarantee broad support. Alpha conditional on Webb has low correlation but highly concentrated residual variance. Effective identifying support is therefore a more informative complement to the usual variance-inflation factor.

## 7. Same Outcome, Same Design, Different AI Exposure

### 7.1 Headline estimates

Table 5A reports all 12 frozen headline models: alpha and beta, two computerization controls, and three support rules. There is no outcome-based selection. Every Q5–Q1 coefficient is negative and every wild-bootstrap 95% confidence interval excludes zero. The estimates range from -0.0971 to -0.2085 log points, equivalent to approximately -9.3% to -18.8% in relative magnitude.

The primary strict-support beta-by-Webb estimate is -0.1311 (bootstrap SE 0.0444, 95% CI [-0.2170, -0.0451], p = .003) across 468 occupations. It means that, after the frozen January-2023 start, the young-versus-older employment stock evolved about 12.3% less favorably in the most exposed quintile than in the least exposed quintile, conditional on Webb software-patent exposure and the saturated fixed effects. It does not mean that a young individual became 12.3% more likely to be unemployed.

Support rules matter less than computerization definitions in these headline models. Under Webb, beta estimates are -0.1311, -0.1186, and -0.1186 across Rules A, B, and C. Under O\*NET computer-use importance they are -0.2085, -0.1744, and -0.1746. Alpha estimates cluster between -0.0971 and -0.1087 across all six support-control combinations. Sign robustness is therefore unusually strong relative to the heterogeneity documented in Sections 5 and 6.

See [Table 5A](tables/table5a_frozen_headline_models.md).

### 7.2 All six exposure constructions

Table 5B places all six exposure constructions into the same strict-support/Webb design. The three AIOE Q5–Q1 coefficients are -0.1032, -0.1176, and -0.0977. Alpha is -0.0987, beta is -0.1311, and the broad Eloundou score is -0.1570. Every interval excludes zero. The pattern is not monotonic across all construction families, but within the Eloundou family a broader definition produces a more negative point estimate.

This is evidence of downstream sign robustness, not proof that exposure measurement is irrelevant. First, the point estimates differ by economically meaningful amounts. Second, Sections 5 and 6 show that the measures have different occupational content and identifying support. Third, the inferential question is the coefficient difference, not whether one coefficient is significant and another is not.

### 7.3 Paired beta-alpha inference

The direct paired comparison uses common Rule-A/Webb support and common wild-bootstrap draws. Beta is -0.13107, alpha is -0.09868, and beta minus alpha is -0.03240. The paired standard error is 0.03697; the 95% percentile-t interval is [-0.10235, 0.03755], with p = .403. The interval includes zero. The binding interpretation is therefore that the design does not detect a difference.

That sentence cannot be inverted into equivalence. The original plan required an economically meaningful equivalence bound derived from a literature-comparable benchmark. The benchmark audit found no published estimate matching the YAX age groups, employment-stock outcome, Q5–Q1 contrast, young-relative-to-pooled-older estimand, and scale. Rather than invent a threshold, the design retired equivalence inference. The ex-ante paired precision diagnostic—80% power to detect about 3.27 percentage points—remains useful, but the realized confidence interval still contains large positive and negative differences.

See [Table 5B](tables/table5b_same_design_different_x.md).

### 7.4 Relation to recent administrative-data estimates

Brynjolfsson, Chandar, and Chen (2026) report early-career employment declines of a similar order in ADP administrative data. The comparison is informative but not an exact replication. Their prominent 19% statistic compares the two most exposed quintiles with the bottom three for workers aged 22–25; their -0.179 Q5 coefficient is a within-young occupation-level long difference. YAX compares Q5 with Q1 in a saturated monthly cell-stock model and identifies the post change relative to pooled ages 26–65. The data source, mapping, exposure contrast, age comparison, and estimator all differ. The defensible claim is independent nationally representative evidence of a similar-order early-career employment pattern under a different outcome construction and design.

## 8. Computerization and Remote Work

### 8.1 Computerization is also a measurement choice

The question “AI rather than computerization?” cannot be answered by adding an unexamined generic control. Webb software-patent exposure, O\*NET computer use, Autor-Dorn routine intensity, and Frey-Osborne automation probability are different constructs. Their occupational rankings differ, and the same beta score leaves different residual comparisons against each.

Panel A of Table 6 reports the downstream consequence. Under strict support, the beta Q5–Q1 estimate is -0.1311 with Webb, -0.2085 with O\*NET computer-use importance, -0.1512 with O\*NET level, -0.1277 with RTI, and -0.1001 with Frey-Osborne. All remain negative and their intervals exclude zero, but the magnitude varies by more than a factor of two.

This does not identify a causal effect of computerization. It shows that an AI-exposure coefficient is jointly defined by the treatment and the prior-technology margin partialled out of it. A reader asking whether an estimate is “really computerization” should therefore ask which computerization construct is intended, what occupational comparison remains, and whether the identifying support matches the mechanism.

### 8.2 Occupation-level remotability

Remote work is a core competing interpretation because Emanuel, Harrington, and Pallais (2026) document a national CPS deterioration for young college graduates concentrated in remotable occupations and robust to a generative-AI exposure control. Their outcome, sample, and period differ from YAX, but their evidence rules out treating remotability as a cosmetic robustness row.

The frozen per-SD beta coefficient is -0.03814 in an AI-only model and -0.03795 after adding occupation-level remotability. In the full AI-plus-Webb-plus-remotability model it is -0.03718. The remote coefficient is 0.00469 in the joint AI-remote model and 0.00606 in the full model; both intervals include zero. Alpha moves from -0.02795 to -0.02376 after adding remotability and to -0.02410 in the full model, with wider intervals that include zero. The remote-only estimate is -0.01884 (95% CI [-0.04508, 0.00739], p = .154).

The appropriate conclusion is narrow: occupation-level remotability does not mechanically absorb the beta exposure gradient in the frozen design. The exercise neither shows that “AI beats remote work” nor that remote work has no effect. Dingel-Neiman remotability is occupational feasibility, not realized individual telework, and the remote coefficient changes sign across alpha and beta architectures.

See [Table 6](tables/table6_computerization_and_remotability.md).

## 9. Dynamics and Falsification

Figure 3 reports the frozen monthly event study for the primary beta/Webb strict-support architecture. October 2022 is the reference month, December 2022 is the transition month, and the static post period begins in January 2023.

![Figure 3. Frozen event study](figures/figure3_frozen_event_study.png)

**Figure 3. Young-relative employment gradient by Eloundou beta exposure.** Points are monthly exposure-by-young interactions per weighted SD, relative to October 2022; shading is the frozen 95% confidence interval. None of 65 non-reference pre-event intervals excludes zero. Six of 43 event/post intervals exclude zero: November–December 2023 and April–July 2026. <!-- prov:F03 --> Source: canonical frozen `figure1_event_study.png`, copied byte-for-byte into the manuscript package.

The frozen 2017–2019 placebo is 0.00142 (95% CI [-0.02040, 0.02324], p = .894). None of 65 non-reference pre-event monthly intervals excludes zero. The correct description is “no evidence of differential pre-trends under the frozen specification,” not “pre-trends are zero.”

The post path is neither an immediate step nor a smooth monotone decline. Six of 43 event/reference-era coefficients exclude zero, concentrated in November–December 2023 and April–July 2026. The later-window beta coefficient is more negative than the 2023–2024 coefficient: -0.04755 versus -0.03032 per SD. The frozen joint difference is -0.01722 with p = .127, so the analysis does not detect a statistically distinguishable post-2025 acceleration.

These timing checks strengthen the descriptive design but do not establish a causal AI shock. A post-2022 break can coexist with technology-sector adjustment, interest-rate changes, return-to-office mandates, post-pandemic normalization, or evolving CPS composition. The saturated fixed effects and age-relative comparison absorb broad versions of those shocks, not every occupation-by-age-specific alternative.

## 10. Implications for the AI-Labor Literature

The first implication is that an exposure coefficient should be reported as an architecture, not merely a variable name. At minimum, researchers should identify the native construct, annotator or evidence source, aggregation rule, taxonomy mapping, support restriction, comparison technology, and regression scale. A statement such as “we control for AI exposure” hides too many consequential choices.

Second, common support is necessary but not sufficient. A fixed sample prevents coefficient differences from being driven mechanically by different missing-data patterns. It does not ensure that the same occupations identify each coefficient. Effective-occupation counts, residual concentration, and named contributors should accompany cross-measure comparisons, particularly when the mechanism invokes a specific occupational family.

Third, harmonization can change the target population even when it barely changes scores among matched occupations. The AIOE decomposition shows that the largest consequence arises from re-admitting occupations. This finding cautions against describing a crosswalk as a neutral clerical step. It also cautions against accusing prior work of a naive exact-code merge without auditing what that work actually did. The latest BCC revision, EIG code, and Budget Lab harmonization all use explicit repairs; YAX studies alternative defensible mappings rather than attributing a known error to those papers.

Fourth, downstream robustness can coexist with measurement divergence. That combination is the empirical surprise of this paper. Six measures correlate differently with occupational characteristics and draw on different identifying occupations, yet every frozen same-design Q5–Q1 estimate is negative. This is stronger than a result from one favored index and weaker than proof of a common structural treatment effect. It suggests that the negative early-career stock pattern is not an artifact of one exposure architecture, while leaving its exact magnitude and causal mechanism unsettled.

Finally, comparison technologies deserve the same discipline as treatments. “Computerization” may refer to software-patent task overlap, computer-use intensity, routine-task content, or broad automation susceptibility. The more than twofold range in beta point estimates across those controls is not a reason to choose the estimate one prefers. It is evidence that the conditioning margin is part of the empirical object.

## 11. Limitations

The study has six central limitations.

First, the outcome is an occupational employment stock. It is not an individual employment probability. Reduced entry, exit from employment, and occupational switching can all generate the same cell-stock decline. Without separate flow outcomes, the paper cannot label the result layoffs or displacement.

Second, occupational exposure is not realized individual adoption. The scores describe potential exposure or capability-task alignment. They do not observe whether a worker, firm, or occupation uses AI, how intensively it is used, or whether it complements or substitutes for labor.

Third, the DDD is observational. The event study shows no detected differential pre-trends, and the saturated fixed effects absorb rich lower-order shocks. They do not rule out an unobserved occupation-by-age shock correlated with exposure after 2022. Remote-work and computerization exercises constrain simple alternatives but do not establish causal attribution.

Fourth, construct diagnostics depend on the transparent characteristics selected. The eight-characteristic matrix is broad and frozen, but it is not an exhaustive ontology of work. A high joint R-squared does not make a score invalid; a low one does not make a score uniquely AI-specific.

Fifth, the paired consequence comparison is imprecise. The beta-alpha interval includes zero and economically large differences. The design detects no difference but offers no formal economic-equivalence conclusion. Only one direct paired contrast was frozen.

Sixth, exposure and computerization measures inherit their own taxonomy, vintage, and labeling errors. The harmonization is explicit and reproducible, but it cannot recover information absent from the source measures. Effective-support diagnostics describe where the available variation lies; they cannot create missing independent variation.

These limitations define the contribution. The paper is not a definitive causal estimate of generative AI's employment effect. It is an audit of how exposure measurement becomes identifying variation and how much of one salient labor-market conclusion survives that architecture.

## 12. Conclusion

Occupational “AI exposure” is not one self-defining treatment. Widely used indices begin from different technologies and occupational primitives, load differently on familiar characteristics, and leave different occupations to identify a coefficient once pre-existing computerization is conditioned out. Across the frozen 30-cell identifying-variation audit, effective support ranges from 11.9 to 84.5 occupations, and the top five contributors carry 15.0% to 46.6% of residual variation. <!-- prov:C01 --> Mapping choices matter principally by changing who enters the estimand rather than by substantially revising exposure values on fixed support. <!-- prov:C02 -->

At the same time, the downstream sign is remarkably robust. All 12 frozen alpha/beta headline estimates are negative, ranging from -0.097 to -0.208 log points, and every wild-bootstrap confidence interval excludes zero. <!-- prov:C03 --> The primary estimate is -0.131 (95% CI [-0.217, -0.045]; p = .003), about a 12.3% relative decline in the young-worker employment stock in the most versus least exposed occupational quintiles. <!-- prov:C04 --> A paired beta-alpha comparison does not detect a difference, but its interval is too wide to establish economic equivalence. <!-- prov:C05 --> The size of the beta estimate also depends materially on whether prior computerization is represented by software-patent exposure, computer use, routine-task intensity, or automation probability. <!-- prov:C06 -->

The practical lesson is measurement discipline. Researchers should show how an exposure score is built, which occupations identify it, how taxonomy and support define the sample, and whether a conclusion survives alternative defensible architectures. In this empirical laboratory, the negative young-relative employment-stock gradient survives. Its magnitude, mechanism, and causal interpretation do not become invariant merely because its sign does.

## References

Brynjolfsson, Erik, Bharat Chandar, and Ruyu Chen. 2026. “Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of Artificial Intelligence.” Stanford Digital Economy Lab Working Paper, revised August 12.

Budget Lab at Yale. 2026a. “Labor Market AI Exposure: What Do We Know?” February 19.

Budget Lab at Yale. 2026b. “What We Do and Don’t Know About How AI Is Affecting the Labor Market.” May 7.

del Rio-Chanona, R. Maria, Ekkehard Ernst, Rossana Merola, Daniel Samaan, and Ole Teutloff. 2025. “AI and Jobs: A Review of Theory, Estimates, and Evidence.” arXiv:2509.15265.

Eckhardt, Sarah, and Nathan Goldschlag. 2025. *AI and Jobs: The Final Word (Until the Next One).* Economic Innovation Group.

Eloundou, Tyna, Sam Manning, Pamela Mishkin, and Daniel Rock. 2024. “GPTs Are GPTs: Labor Market Impact Potential of LLMs.” *Science* 384(6702): 1306–1308. https://doi.org/10.1126/science.adj0998.

Emanuel, Natalia, Emma Harrington, and Amanda Pallais. 2026. “The Power of Proximity to Coworkers.” *Quarterly Journal of Economics* 141(3): 1825–1870. https://doi.org/10.1093/qje/qjag027.

Felten, Edward W., Manav Raj, and Robert Seamans. 2018. “A Method to Link Advances in Artificial Intelligence to Occupational Abilities.” *AEA Papers and Proceedings* 108: 54–57. https://doi.org/10.1257/pandp.20181021.

Felten, Edward, Manav Raj, and Robert Seamans. 2021. “Occupational, Industry, and Geographic Exposure to Artificial Intelligence: A Novel Dataset and Its Potential Uses.” *Strategic Management Journal* 42(12): 2195–2217. https://doi.org/10.1002/smj.3286.

Fenoaltea, Enrico Maria, et al. 2026. “Follow the Money: A Startup-Based Measure of AI Exposure Across Occupations, Industries, and Regions.” *PNAS Nexus* 5(6): pgag185. https://doi.org/10.1093/pnasnexus/pgag185.

Frank, Morgan R., et al. 2025. “AI Exposure Predicts Unemployment Risk: A New Approach to Technology-Driven Job Loss.” *PNAS Nexus* 4(4): pgaf107. https://doi.org/10.1093/pnasnexus/pgaf107.

Lund, Campbell, Thomas Euyang, Zanele Munyikwa, and Marzieh Fadaee. 2026. “AI Exposure Scores: What They Measure, What They Miss, and What Comes Next.” arXiv:2606.23633.

Merola, Rossana, Ekkehard Ernst, Daniel Samaan, R. Maria del Rio-Chanona, and Ole Teutloff. 2026. “Workers’ Exposure to AI: What Indicators Tell Us—and What They Don’t.” ILO Research Brief. https://doi.org/10.54394/00033279.

Mouchel, Luca, Pierre Bouquet, and Yossi Sheffi. 2026. “Jobs’ AI Exposure Should Be Measured from Evidence, Not Model Priors.” arXiv:2605.15474.

OECD. 2026. *The OECD AI Exposure Measure: Mapping the OECD AI Capability Indicators to Occupations.* OECD Artificial Intelligence Papers No. 59. https://doi.org/10.1787/f3da0f0a-en.

Pulito, Giuseppe, Mariola Pytlikova, Sarah Schroeder, and Magnus Lodefalk. 2026. “Who Adopts AI? Evidence on Firms, Technologies and Workers.” Örebro University School of Business Working Paper 3/2026.

Rai, Sudhanshu. 2026. “Do AI Occupational-Exposure Scores Measure AI? AIOE and Eloundou (2024) Largely Capture Cognitive Content; Webb (2020) Does Not.” MPRA Paper 129904.

Tomei, Philip Moreira, and Bouke Klein Teeselink. 2026. “What Jobs Can AI Learn? Measuring Exposure by Reinforcement Learning.” arXiv:2605.02598.

Yin, Michelle, and Burhan Ogut. 2026. “Who Uses AI? Platform Selection and the Measurement of Occupational AI Exposure.” arXiv:2605.21743.

Yin, Michelle, Hoa Vu, and Claudia Persico. 2026. “How (un)Stable Are LLM Occupational Exposure Scores? Evidence from Multi-Model Replication.” NBER Working Paper 35110. https://doi.org/10.3386/w35110.

## Appendix Roadmap

The submission appendix should be assembled from existing frozen artifacts only.

- **Appendix A: Exposure construction and lineage.** Native data sources, AIOE aggregation variants, Eloundou notation, and all source hashes.
- **Appendix B: Occupational harmonization.** Census 2010-to-2018 bridge, SOC-to-Census mapping, Rules A–C, excluded occupations, and employment coverage.
- **Appendix C: Complete Test A diagnostics.** Pearson and Spearman matrices, raw rankings, rank overlap, residual correlations, and named residual contributors.
- **Appendix D: Complete Test B diagnostics.** All 30 architectures, residual distributions, occupational-family shares, named contributors, and pairwise overlap in Q1/Q5 and residual rankings.
- **Appendix E: Frozen outcome tables.** All 12 headline models, all six alternative exposure constructions, all five computerization controls, the paired Test-C distribution and interval, and the full remote-work table.
- **Appendix F: Dynamics.** All 109 event-study months, the 2017–2019 placebo, the normalized reference month, and the post-2025 joint test.
- **Appendix G: Audit and reproducibility.** Design-freeze differences, first-outcome-access receipt, post-outcome implementation-change ledger, 195-row result ledger, artifact hashes, completion matrix, integrity checks, and clean-checkout reproduction.
