# What Is AI Exposure? Measurement Architecture, Identifying Variation, and Early-Career Employment

Lily Luo
Fourth manuscript draft — August 2026

## Abstract

Occupational “AI exposure” is not a common empirical object: prominent indices begin from different technologies, occupational primitives, labels, and aggregation rules. I trace those choices through occupational mapping, support, and labor-market inference. Six measures differ sharply in observable occupational content. Continuous residual-treatment support ranges from 11.9 to 84.5 effective occupations, while a supplementary decomposition shows that information support for the categorical headline estimator is a distinct object. <!-- prov:A01 --> Harmonization matters mainly through which occupations enter the estimand. In nationally representative CPS data, all pre-specified and literal-common-support exposure architectures produce negative Q5-versus-Q1 young-relative employment-stock coefficients. The primary estimate implies that the young employment stock evolved 12.3% less favorably relative to the older-worker stock in the highest-exposure quintile than in the lowest. <!-- prov:A02 --> The sign is robust, but point estimates are not invariant, especially to the definition of prior computerization. These observational stock gradients do not establish a causal AI effect and cannot distinguish occupational entry, employment exit, or switching.

## 1. Introduction

The empirical AI-and-labor literature increasingly speaks of occupational “AI exposure” as though it were a common treatment. Researchers merge an exposure score onto occupations, interact it with time, and interpret the resulting coefficient as evidence about artificial intelligence and work. That workflow is now routine. The object entering the regression is not.

Prominent indices begin from different economic primitives. The Felten-Raj-Seamans family starts with applications of artificial intelligence, relates them to occupational abilities, and aggregates through O\*NET ability requirements (Felten, Raj, and Seamans 2018, 2021). The Eloundou-Manning-Mishkin-Rock family starts with large-language-model capabilities, asks whether an LLM—alone or with complementary software—could reduce the time required for occupational tasks, and aggregates task judgments to occupations (Eloundou et al. 2024). The resulting variables may be correlated, but correlation does not make their technologies, occupational content, or identifying comparisons interchangeable.

This paper asks three linked questions:

> **What is the empirical X? What occupational variation identifies X? Which labor-market conclusions survive different definitions of X?**

The empirical laboratory is the recent debate over early-career employment in occupations more exposed to generative AI. Administrative-data work reports sizable young-relative stock changes for workers aged 22–25 in highly exposed occupations, while public-data evidence has been less uniform. I hold the CPS outcome, age comparison, timing, estimator, and inference framework fixed, then vary the architecture of the AI treatment and of the pre-existing technology margin against which it is evaluated. The original six-measure comparison used each measure's native strict support; a supplementary literal-intersection comparison fixes the same 444 occupations across all six measures. The outcome is an occupation-by-age employment stock. It cannot distinguish reduced occupational entry, employment exit, or occupational switching, and the design does not identify an individual unemployment effect.

The paper makes three contributions.

**First, it shows that widely used measures constitute different empirical X's.** Across six AI-exposure measures and eight transparent occupational characteristics, the three AIOE variants load strongly on cognitive content, education, wages, teleworkability, and computer use. Eloundou alpha—the share of tasks directly accelerated by an LLM—has much weaker relationships with most of those characteristics, while beta and the broad E1+E2 measure occupy intermediate positions. The original joint fit is partly mechanical because AIOE and four correlates draw on the same O\*NET information system. A supplementary split therefore separates those variables from RTI, wages, teleworkability, and STEM share. On this less construction-linked set, the AIOE variants still have R-squared values of 0.64–0.67, compared with 0.27 for alpha, 0.43 for beta, and 0.48 for the broad Eloundou score. <!-- prov:V3-I01 --> The attenuation matters, but the cross-family difference in observable occupational content remains. These patterns do not prove that no common latent AI factor exists. They show why the classical representation

\[
X_m=X^*+\epsilon_m
\]

should not be assumed without evidence: different measures can encode distinct technologies, occupational primitives, and implementation assumptions rather than classical noise around one transparent treatment.

**Second, it distinguishes two support questions that earlier drafts conflated.** Nominal coverage says how many occupations enter a regression; it does not say where treatment variation or estimator information lies. The pre-outcome Test B diagnostic studies continuous exposure residualized on continuous computerization. Across 30 architectures, effective residual-treatment support ranges from 11.9 to 84.5 occupations and the five largest contributors account for 15.0% to 46.6% of residual variation. <!-- prov:I02 --> This is an architecture-level diagnostic, not the finite-sample influence or exact information support of the nonlinear headline estimator.

A supplementary outcome-dependent decomposition bridges that gap. It absorbs the Q5–Q1 PPML design under fitted information weights, partials the Q5 column against the other slope columns, and decomposes conditional information by occupation. For the four Rule-A alpha/beta-by-Webb/O\*NET architectures, continuous and headline occupation-share ranks correlate about 0.71–0.74, but their concentration and leading occupations can differ sharply. Under Webb, alpha has 17.4 effective occupations in residual-treatment support and 56.1 in headline conditional-information support; only one of the top five occupations overlaps. <!-- prov:V3-I02 --> The central applied question therefore has two parts:

> **Which occupations carry residual treatment variation in the measurement architecture, and which occupations supply conditional information for the estimator actually reported?**

Occupational mapping and common support belong to the same problem. In a four-step AIOE decomposition, correcting exposure values on unchanged support barely changes the coefficient, from -0.01885 to -0.01920. Re-admitting occupations changes it to -0.03156; excluding computer and mathematical occupations leaves -0.02940. <!-- prov:I04 --> The main consequence of harmonization operates through who enters the estimand, not through large score revisions among occupations already matched.

**Third, it establishes sign robustness without magnitude or causal invariance.** Across 12 alpha/beta headline models, the era-average January-2023-to-July-2026 Q5–Q1 estimates range from -0.0971 to -0.2085 log points—Q5-versus-Q1 young-relative employment-stock contrasts of -9.3% to -18.8% after the transformation \(100(e^\beta-1)\)—and every one-step wild-score confidence interval excludes zero. <!-- prov:I05 --> The primary beta-by-Webb strict-support estimate is -0.1311 (cluster-robust SE 0.0444; one-step wild-score 95% CI [-0.2170, -0.0451]; p = .003). It implies that the young employment stock evolved 12.3% less favorably relative to the older-worker stock in Q5 than in Q1. <!-- prov:I06 --> A supplementary literal-intersection comparison holds 444 occupations fixed across all six measures. All six point estimates remain negative, although one interval narrowly includes zero. <!-- prov:V4-I01 --> Each measure defines its own employment-weighted quintiles, so exposure values, rankings, and high-exposure membership still vary.

This robustness has limits. The beta point estimate moves from -0.1001 to -0.2085 as the definition of pre-existing computerization changes. <!-- prov:I07 --> The paired beta-minus-alpha difference between architecture-specific Q5–Q1 coefficients is -0.0324 log points (95% CI [-0.1023, 0.0376]; p = .403). <!-- prov:I08 --> The design does not detect a difference between those empirical objects, but the interval is too wide to establish either magnitude divergence or economic equivalence. The ex-ante paired design had 80% power to detect a difference of about 0.0327 log points. Measurement disagreement therefore need not imply sign fragility, yet a stable sign does not make magnitude or causal interpretation invariant.

The contribution is relevant beyond AI. Applied economics routinely constructs treatments from automation exposure, trade exposure, routine-task content, climate risk, technology indices, and policy-intensity scores. Different constructions of a nominally similar treatment may change not only correlation or coverage, but residual treatment support, estimator information, and the substantive parameter. This paper provides one transparent case in which that full chain can be observed.

The paper proceeds as follows. Section 2 presents measurement architecture and the three nearest literatures. Section 3 describes CPS employment stocks and occupational harmonization. Section 4 separates the continuous-score and headline-quintile estimands and defines the inference algorithm. Sections 5 and 6 study observable occupational content, residual-treatment support, and headline information support. Section 7 asks what survives measurement divergence. Sections 8 and 9 examine comparison technologies, remotability, dynamics, and falsification. Sections 10–12 discuss implications, limitations, and conclusions.

## 2. What Is Occupational AI Exposure?

### 2.1 Measurement architecture

An occupational exposure score compresses a long sequence of choices into one variable. At minimum, the researcher chooses a technology or capability definition, an occupational primitive, a source of labels, an aggregation rule, an occupational taxonomy, a crosswalk, a support rule, and a regression scale. Figure 1 separates native construction from empirical harmonization.

![Figure 1. Measurement genealogy](figures/figure1_measurement_genealogy.png)

**Figure 1. Measurement genealogy — confirmatory design documentation.** Native technology and labeling choices are followed by occupation aggregation, taxonomy mapping, common-support decisions, and construction of the regression treatment. The figure summarizes material held fixed before outcome access and introduces no outcome result.

Table 1 summarizes the measures used in the confirmatory analysis. The AIOE family maps ten AI applications to 52 occupational abilities using crowd judgments and then combines ability exposure with occupation-specific O\*NET requirements (Felten, Raj, and Seamans 2018, 2021). The three AIOE variants retain the same conceptual family but vary aggregation: an administrative equal-weight construction, a direct ability construction, and a source-employment-weighted construction.

The Eloundou family instead labels occupational tasks according to whether an LLM can reduce task-completion time by at least half while maintaining quality (Eloundou et al. 2024). Alpha counts E1 tasks, for which an LLM alone can achieve the threshold. Beta adds half weight to E2 tasks, for which the threshold becomes feasible with complementary software. The broad E1+E2 score is called zeta in the published paper and is labelled “broad” here.

The difference is economic, not merely computational. An ability-based score may emphasize broad cognitive requirements relevant to many AI applications. A task-based LLM score may emphasize current technical feasibility. Adding E2 embeds a view about complementary software and organizational implementation. None is automatically the “correct” treatment for every question.

Table 1 reports the six construction architectures and their native taxonomies.

### 2.2 Three nearest literatures

**Measurement instability.** Yin, Vu, and Persico (2026) hold a task rubric fixed and vary the frontier LLM supplying annotations; exposure scores and downstream coefficients change materially. Yin and Ogut (2026) hold an observed-use design fixed but vary platform-user inputs, showing how platform selection affects measured exposure and employment estimates. Those papers isolate instability within an annotator or input family. I study a complementary margin: cross-family architecture, from abilities versus tasks through taxonomy and support, and then into the occupations that supply identifying variation in a common labor design.

**Construct and comparative-exposure research.** Rai (2026) shows that AIOE and Eloundou scores load on cognitive occupational content, while Webb behaves differently. Frank et al. (2025) compare several scores as predictors of pre-ChatGPT unemployment risk. Eckhardt and Goldschlag (2025) use five measures for CPS unemployment, labor-force exit, and switching, with public code that makes mapping alternatives visible. The Budget Lab (2026a, 2026b) harmonizes seven metrics and applies them to public labor outcomes. Pulito et al. (2026), the closest same-outcome/same-specification predecessor, estimate firm AI adoption with five standardized exposure indices. These studies establish that score comparison, harmonization, and coefficient movement are not new in isolation. The incremental step here is to connect construction and construct content to effective support, mapping-induced estimand composition, and direct same-design inference.

**Early-career labor-market evidence.** Brynjolfsson, Chandar, and Chen (2026) document a deterioration in employment stocks for workers aged 22–25 in highly exposed occupations using ADP administrative data; their August revision includes multiple exposure measures, improved mapping, remote-work controls, and CPS/ACS benchmarks. Emanuel, Harrington, and Pallais (2026) show in the CPS that post-pandemic labor-market deterioration for young college graduates is concentrated in remotable occupations and remains after an AI-exposure control. EIG and other public-data work examine related unemployment, exit, and switching outcomes. This paper does not claim to discover the young-worker pattern. It asks which parts of that conclusion remain stable when exposure architectures are made commensurable inside one nationally representative employment-stock design.

The paper is not the first comparison of exposure scores or occupational mappings. Its contribution is to connect **what X is, where continuous treatment variation lies, where the reported estimator obtains information, and what conclusion survives alternative definitions of X**. Newer capability, retrieval, reinforcement-learning, and market-targeted measures make that sequence increasingly relevant, but an inventory of those indices is not needed for the main argument.

## 3. Data and Occupational Harmonization

### 3.1 CPS employment stocks

The labor-market analysis uses monthly IPUMS Current Population Survey microdata from January 2017 through July 2026. The wide extract contains 9,262,480 person records. Employed respondents are aggregated with CPS weights into occupation-by-age-group-by-month employment stocks. The young group is ages 22–25; the comparison group pools ages 26–65. The resulting unit is a cell, not a person.

This choice avoids assigning an occupation to someone who is not employed. It also defines the interpretation sharply. A decline in the young employment stock of an occupation can reflect fewer entrants, exits from employment, or movement to another occupation while remaining employed. The design cannot separate these channels and does not estimate an individual probability of unemployment.

The CPS stocks are survey-weighted estimates. Occupation-cluster inference captures serial dependence across months within occupation and estimation uncertainty conditional on the realized cell outcomes. It does not separately propagate first-stage CPS sampling variance, calibration-weight uncertainty, or the full covariance induced by the survey design. The extract contains household, person-panel, and rotation identifiers but lacks the public strata, PSU, and replicate-weight information required to reconstruct a defensible design-based variance procedure. A feasibility audit therefore rejects an ad hoc microdata bootstrap. <!-- prov:V3-D01 -->

The static post period begins in January 2023 and ends in July 2026. December 2022 is retained as a transition month in the event study but excluded from the static post coefficient because ChatGPT was released on November 30, after the November CPS reference week. October 2025 is absent from the source series and is excluded.

### 3.2 Occupational taxonomies

The CPS occupation system changes during the sample. Raw 2017–2019 codes use the Census 2010 occupation taxonomy, while 2020 onward uses Census 2018. The harmonization maps pre-2020 occupations to Census 2018 using the Census Bureau's official total conversion rates. Post-2020 codes are matched directly. Native SOC-based exposure measures are first collapsed within six-digit SOC codes and then mapped to Census occupations using official crosswalks and available employment weights. Missing components are never silently renormalized under the primary rule.

The strict primary coverage rule retains an occupation only when every mapped component has an exposure score. It covers 88.70% of eligible employment. Two pre-specified sensitivities report sibling imputation and scored-component renormalization when at least 95% of component mass is observed. These rules are not interchangeable: they define different populations and therefore different estimands.

The analysis distinguishes nominal code coverage from employment coverage and both from effective support. A dataset can contain hundreds of occupations while residual treatment variation or fitted estimator information is concentrated in a much smaller set. Section 6 makes that distinction operational.

### 3.3 Mapping decomposition

The four-step decomposition in Table 4 asks whether harmonization matters by changing exposure values among already matched occupations or by changing which occupations enter the analysis. It begins with the original AIOE values on original support, replaces values while holding support fixed, expands support using the repaired mapping, and finally excludes computer and mathematical occupations from the expanded sample. Because the coefficient is reported per fixed SD of AIOE and always conditions on Webb exposure, the sequence isolates measurement correction from composition as transparently as the available mapping permits.

## 4. Empirical Framework

The analysis uses two related but distinct saturated Poisson pseudo-maximum-likelihood specifications. Separating them matters because the headline Q5–Q1 coefficient is not the continuous-score coefficient reported in the mapping and remote-work exercises.

### 4.1 Continuous-score specification

For per-standard-deviation analyses, the model is

\[
E[N_{oat}] = \exp\left[\gamma_{oa}+\delta_{ot}+\lambda_{at}
+\beta_X(X^z_o\times Young_a\times Post_t)
+\beta_C(C^z_o\times Young_a\times Post_t)
+\beta_R(R^z_o\times Young_a\times Post_t)\right],
\]

where \(X^z_o\) is the employment-weighted standardized AI-exposure score, \(C^z_o\) is standardized computerization, and \(R^z_o\) is standardized occupation-level remotability when that control is included. Terms not used in a particular pre-specified model are omitted. \(\beta_X\) is the post-period change in the young-relative employment-stock gradient per one weighted standard deviation of exposure. The four-row mapping decomposition fixes the AIOE standardization reference so that coefficient movement does not mechanically reflect a changing SD. The remote-work models also use the continuous scale.

### 4.2 Headline quintile specification

The main literature-comparable estimates replace the continuous AI interaction with four exposure-quintile indicators:

\[
E[N_{oat}] = \exp\left[\gamma_{oa}+\delta_{ot}+\lambda_{at}
+\sum_{q=2}^{5}\beta_q\left(\mathbf{1}\{Q_o=q\}\times Young_a\times Post_t\right)
+\beta_C(C^z_o\times Young_a\times Post_t)\right].
\]

Quintiles are formed from the native AI-exposure score using young-plus-older employment-stock weights over the 108 static estimation months, excluding the December 2022 transition month, on each model's estimation support. This describes the implemented estimator exactly; the weights are not pre-period-only. Q1 is omitted. Q2, Q3, and Q4 enter separately rather than being pooled. The headline parameter is therefore \(\beta_5\): the post-period change in the young-to-older employment-stock relationship for Q5 compared with Q1, conditional on the standardized computerization interaction and the fixed effects. The primary estimate \(-0.131\) is \(\hat\beta_5\); it is not the continuous-score coefficient \(-0.038\) reported in the remotability analysis.

The design freeze specified employment-weighted quintiles but did not state which calendar months must supply those weights. The historical implementation therefore resolves an underspecified construction choice; it is not an explicitly frozen full-period rule. A post-outcome sensitivity constructs only the AI-exposure quintiles with January 2017–November 2022 employment while holding the support, model cells, Webb scaling, estimator, and inference fixed. <!-- prov:V41-W01 -->

Each exposure measure defines its own quintiles. Q5 under AIOE is therefore not necessarily the same occupation set as Q5 under alpha or beta. This is intentional: the cross-measure exercise asks what conclusion follows when each architecture defines which occupations are highly and weakly exposed. Fixed occupational support does not imply fixed treatment-group membership. On pairwise common support, Q5 Jaccard overlap is 0.216–0.237 between AIOE and alpha, 0.414–0.465 between AIOE and beta, and 0.539 between alpha and beta. <!-- prov:V3-E01 -->

### 4.3 Fixed effects, inference, and interpretation

In both equations, \(N_{oat}\) is the weighted employment stock in occupation \(o\), age group \(a\), and month \(t\). Occupation-by-age-group fixed effects absorb each occupation's persistent young-versus-older gap. Occupation-by-month fixed effects absorb shocks to an occupation that affect both age groups. Age-group-by-month fixed effects absorb the national young-versus-older path. Every lower-order interaction is absorbed by one of those fixed-effect families. What remains is a change in the within-occupation young-versus-older gap across occupations with different pre-defined exposure, conditional on the same age-relative post interaction for the comparison technology.

The primary exposure is Eloundou beta. Alpha is the pre-specified contrast. Webb software-patent exposure is the primary computerization control; O\*NET computer-use importance, O\*NET computer-use level, Autor-Dorn routine-task intensity, and Frey-Osborne automation probability are pre-specified alternatives. Webb was fixed before outcome access because it provides a predetermined, software-specific patent-task comparison technology from a framework that separates software, robot, and AI exposure. It is not uniquely correct: O\*NET measures computer use, RTI measures routine-task composition, and Frey-Osborne measures broad automation susceptibility. Standardized-score models support the remote-work and mapping exercises.

Inference clusters by occupation. The implemented procedure is a one-step occupation-cluster Rademacher wild-score method, not a fully re-estimated wild bootstrap. The estimator uses a grouped-binomial quasi-likelihood representation of the PPML score after profiling the occupation-month effects; the noninteger survey-weighted stocks are not assumed to be literal binomial counts. The code absorbs the slope matrix against occupation and month effects under fitted information weights, forms occupation-cluster scores, and maps them through the inverse information matrix. Each of 999 draws multiplies the resulting occupation contributions by one Rademacher sign. It does not perturb pseudo-outcomes, impose a null-restricted fit, or re-estimate PPML and fixed effects in every draw. The analytic occupation-cluster standard error is the fixed studentizer. The two-sided p-value uses the finite-sample correction \((1+\#\{|t_b|\geq |t_{\mathrm{obs}}|\})/1000\); the interval uses the 95th higher empirical quantile of \(|t_b|\). Appendix D provides the full algorithm and the quasi-likelihood derivation.

The paired beta-alpha comparison uses the same occupation multiplier for both estimators, forms the coefficient difference within draw, and thereby preserves covariance. Its paired SE is the standard deviation of the centered shift distribution, which also serves as the fixed studentizer. The ex-ante \(MDE_{\Delta,80}=0.03272\) is on the Q5–Q1 log-coefficient-difference scale; \(100(e^{0.03272}-1)=3.326\%\) is an optional multiplicative translation, not an additive percentage-point estimand. The design and interpretation rules were time-stamped before post-period outcomes were opened.

Three families of tests organize the main evidence. Test A asks whether exposure measures encode different observable occupational content. Test B describes effective residual-treatment support in continuous exposure-by-computerization architectures. Test C compares architecture-specific Q5–Q1 coefficients while holding the outcome, pairwise sample, estimator, computerization control, and inference framework fixed. A separate outcome-dependent analysis studies conditional information support for the categorical headline estimator.

## 5. How Do AI-Exposure Measures Differ in Observable Occupational Content?

Table 2 reports all 48 pre-specified employment-weighted correlations: six AI-exposure measures by eight occupational characteristics. The characteristics are cognitive ability importance, manual and physical ability importance, Autor-Dorn routine-task intensity, required education, log mean annual wage, Dingel-Neiman teleworkability, STEM employment share, and O\*NET computer-use importance.

The AIOE variants form a recognizable cluster. Their correlations with cognitive content range from 0.653 to 0.689; with education, 0.688 to 0.708; with log wages, 0.611 to 0.640; with teleworkability, 0.741 to 0.754; and with computer use, 0.847 to 0.854. Their correlations with manual and physical content are between -0.913 and -0.939. This is coherent with an ability-based measure that emphasizes cognitively intensive work, but it also means AIOE is empirically close to familiar dimensions of skilled, computer-mediated work.

Eloundou alpha behaves differently. Its correlations are -0.032 with cognitive content, -0.034 with education, 0.011 with wages, 0.200 with teleworkability, 0.436 with STEM share, and 0.304 with computer use. Beta becomes more similar to the AIOE pattern once software-complemented tasks enter: 0.478 with cognitive content, 0.425 with education, 0.478 with wages, 0.589 with teleworkability, and 0.797 with computer use. The broad E1+E2 measure moves further in that direction. These differences are consistent with the economics of the scoring rules: E2 introduces tasks whose acceleration depends on complementary software, which overlaps naturally with the digital organization of work.

Routine-task intensity is not the axis on which the measures diverge most. Correlations with RTI are positive but modest, from 0.108 to 0.217. Nor do the results imply that AIOE is merely teleworkability or computer use. The point is that the measures weight those dimensions differently and therefore encode different occupational content.

The joint audit requires a source-overlap caveat. AIOE is constructed from O\*NET occupational abilities, while cognitive and manual/physical abilities, required education, and computer use are also O\*NET-derived. The eight-characteristic R-squared of 95%–97% for AIOE therefore combines substantive occupational alignment with mechanical same-source information. It is not validation against a true AI-exposure criterion.

A supplementary split, reported in Table 2C, holds the 348-occupation sample fixed and estimates separate projections on four construction-linked O\*NET variables and four less construction-linked occupational correlates: Autor-Dorn RTI, OEWS wages, Dingel-Neiman teleworkability, and OEWS-based STEM share. AIOE R-squared falls from 0.945–0.966 on the linked group to 0.637–0.671 on the less-linked group. The corresponding values are 0.272 for alpha, 0.428 for beta, and 0.479 for the broad Eloundou score. <!-- prov:V3-A01 --> Same-source overlap therefore explains an important part of AIOE's original joint fit, but not the full AIOE-versus-alpha contrast.

The defensible conclusion is divergence in observable occupational content and measurement architecture. The evidence does not establish six unrelated treatments, recover a uniquely correct latent index, or prove that no common latent AI factor exists. It does show that researchers should not assume classical measurement error around a common treatment without explaining what is shared and what is measure-specific.

## 6. Where Do Treatment Variation and Estimator Information Come From?

Test B residualizes each continuous AI-exposure measure on each of five continuous computerization controls using pre-period employment weights. For each of the 30 combinations, it reports residual variance, the inverse-Herfindahl effective residual-treatment support, the share carried by the five largest contributors, the dominant occupational family, and the names of the leading occupations. Section 6.3 then constructs a distinct information diagnostic for the exact categorical headline estimator.

### 6.1 Continuous residual-treatment support

Let \(X_o\) denote an AI-exposure score, \(C_o\) the relevant computerization measure, and \(w_o\) the occupation's total January 2017–November 2022 employment stock across the two age groups. The diagnostic first estimates the weighted projection

\[
X_o=a+bC_o+\widetilde X_o.
\]

Occupation \(o\)'s share of residual treatment variation is exactly

\[
s_o=\frac{w_o\widetilde X_o^2}{\sum_j w_j\widetilde X_j^2}.
\]

The effective occupation count is the inverse Herfindahl of these shares:

\[
N_{\mathrm{eff}}=\frac{1}{\sum_o s_o^2}.
\]

An effective count of 17 does not mean that only 17 occupations enter the regression. It means that the concentration of weighted residual treatment variation is equivalent to 17 equally contributing occupations under this diagnostic. \(N_{\mathrm{eff}}\) is not conventional regression leverage, an influence-function estimate of \(\hat\beta\), an exact information decomposition of the categorical PPML estimator, or an outcome-based diagnostic. It was computed before post-period outcomes were read and describes support in the continuous measurement architecture.

### 6.2 Results across 30 architectures

![Figure 2. Two support diagnostics](figures/figure2_support_bridge.png)

**Figure 2. Continuous residual-treatment support and headline information support.** Panel A reports the continuous residual-treatment diagnostic across all 30 architectures. Panel B reports the outcome-dependent conditional-information decomposition for the four Rule-A headline architectures. The two panels answer different questions and neither is a realized influence measure. <!-- prov:F02 -->

The key distinction is between nominal support and effective support. Eloundou alpha and beta both have 468 occupations when conditioned on Webb. Yet alpha has only 17.4 effective occupations and a 41.6% top-five share, while beta has 53.3 effective occupations and a 22.2% top-five share. Software developers alone carry 19.6% of alpha's residual variance in that architecture. The remaining leading contributors are computer programmers, bookkeeping clerks, billing clerks, and administrative assistants. Beta's top contributors are software developers, construction laborers, maids, bookkeeping clerks, and hand freight laborers.

Changing the computerization control changes the comparison. Conditional on O\*NET computer-use importance, alpha has 31.1 effective occupations; its leading contributors remain concentrated in programming and clerical work. Beta has 63.2 effective occupations and is led by retail supervisors, automotive technicians, bookkeeping clerks, wholesale sales representatives, and truck drivers. Conditional on Autor-Dorn RTI, alpha falls to 11.9 effective occupations and a 46.6% top-five share. The broad Eloundou score, by contrast, reaches 84.5 effective occupations under Webb and 77.5 under RTI.

The three AIOE variants are generally more diffuse than alpha across computerization controls, with effective counts mostly between 59 and 82. They are not identical. The ability-direct variant under O\*NET level reaches 82.2 effective occupations, while the OEWS-weighted variant under RTI has 62.1. The identities of the top occupations also rotate across architectures.

These diagnostics reveal what comparison the design is asking the outcome data to price. Two models can use almost the same number of occupation codes yet estimate substantively different weighted contrasts.

This result also changes how collinearity should be discussed. A high raw correlation does not automatically make a coefficient unidentified; it raises variance and changes the residual comparison. Conversely, low raw correlation does not guarantee broad support. Alpha conditional on Webb has low correlation but highly concentrated residual variance. Effective residual-treatment support is therefore a more informative complement to the usual variance-inflation factor.

### 6.3 Exact information support of the headline estimator

The headline estimator replaces the continuous treatment with measure-specific Q5 and Q1 indicators. Its conditional information support therefore cannot be inferred from the continuous residual-treatment diagnostic. In a supplementary outcome-dependent decomposition, let R denote the slope matrix after absorbing the fixed effects under fitted quasi-likelihood information weights W, and let R_t denote the headline Q5 column. Partialling that column against all remaining absorbed slopes gives

\[
z=R_t-R_{-t}(R_{-t}'WR_{-t})^{-1}R_{-t}'WR_t.
\]

Occupation \(o\)'s conditional information contribution is

\[
H_o=\sum_{i\in o}W_i z_i^2,
\qquad q_o=H_o/\sum_j H_j.
\]

The occupation shares sum to one, reproduce the relevant Schur complement to numerical precision, and yield an inverse-Herfindahl effective information count. This decomposes fitted conditional curvature for the reported coefficient. It does not show which occupation caused the coefficient to be negative, how much the coefficient would move if an occupation were removed, or realized influence on the estimator. The analysis was conducted after outcome access and is labelled supplementary in its table note.

Across all 12 headline models, effective information support ranges from 42.9 to 71.1 occupations and the top five occupations supply 15.8% to 24.9% of conditional information. For the four strict-support Rule-A architectures, continuous and headline occupation-share ranks correlate between 0.71 and 0.74, but concentration and leading occupations can differ sharply. Beta conditional on Webb has 53.3 effective occupations in continuous residual-treatment support and 43.3 in headline information support, with two of the top five occupations overlapping. Alpha conditional on Webb moves in the other direction, from 17.4 to 56.1 effective occupations, with only one top-five occupation overlapping. Under O*NET computer use, alpha moves from 31.1 to 71.1 and has no top-five overlap. <!-- prov:V3-S01 -->

The bridge therefore rejects both simple shortcuts. The continuous diagnostic remains useful for describing measurement architecture, but it is not a reliable numerical proxy for concentration in the categorical estimator. The headline information decomposition answers an estimator-specific question and, because it uses fitted outcome probabilities, is reported separately as supplementary. Table 3C reports both diagnostics side by side.

### 6.4 Why can construct divergence coexist with sign robustness?

The pre-outcome rank-overlap audit gives a mixed answer. Within the AIOE family, extreme rankings are highly similar: Q5 Jaccard overlap ranges from 0.793 to 0.886. <!-- prov:B01 --> Within the Eloundou family, beta and alpha share moderate Q5 overlap (0.539) and their weighted residuals correlate 0.716; beta and the broad score share 0.585 of Q5 and have residual correlation 0.880. <!-- prov:B02 --> Shared tails can therefore help explain directional stability within a construction family.

Cross-family overlap is much weaker. The Q5 overlap between the three AIOE variants and alpha is only 0.216–0.237; for AIOE and beta it is 0.414–0.465. <!-- prov:B03 --> The common negative sign is thus not merely the same set of occupations receiving different numerical labels. Some extreme occupations overlap, especially for beta, but cross-family constructs and residual comparisons remain distinct. Sign robustness is consequently more informative than a within-family robustness check, while still falling short of a common structural effect.

## 7. What Survives Measurement Divergence?

### 7.1 Headline estimates

Table 5A reports all 12 headline models: alpha and beta, two computerization controls, and three support rules. Every measure constructs its own employment-weighted exposure quintiles, so Q5 and Q1 membership can change with the measure. Every Q5–Q1 coefficient is negative and every one-step wild-score 95% confidence interval excludes zero. The estimates range from -0.0971 to -0.2085 log points, implying Q5-versus-Q1 young-relative employment-stock contrasts of -9.3% to -18.8% under \(100(e^\beta-1)\).

The primary strict-support beta-by-Webb estimate is -0.1311 (cluster-robust SE 0.0444; one-step wild-score 95% CI [-0.2170, -0.0451]; wild-score p = .003) across 468 occupations. It means that the young employment stock evolved 12.3% less favorably relative to the older-worker stock in Q5 than in Q1 over January 2023–July 2026, conditional on Webb software-patent exposure and the saturated fixed effects. Equivalently, it is a 12.3% relative decline in the young-to-older employment-stock ratio in Q5 relative to Q1. The estimate can reflect movement in the young stock, the older stock, or both; it does not mean that a young individual became 12.3% more likely to be unemployed.

The pre-period-weighted sensitivity leaves Q5 membership unchanged, has Q1 Jaccard overlap of 0.970, and moves 9 of 468 occupations across any quintile boundary. Its Q5–Q1 coefficient is -0.1285 (cluster-robust SE 0.0446; one-step wild-score 95% CI [-0.2160, -0.0410]; p = .003), only 0.0026 log points above the historical estimate. Thus post-period-inclusive classification weights do not materially drive the primary directional or magnitude conclusion in this application. The sensitivity does not retrospectively make either temporal weighting rule pre-specified. <!-- prov:V41-W02 -->

Support rules matter less than computerization definitions in these headline models. Under Webb, beta estimates are -0.1311, -0.1186, and -0.1186 across Rules A, B, and C. Under O\*NET computer-use importance they are -0.2085, -0.1744, and -0.1746. Alpha estimates cluster between -0.0971 and -0.1087 across all six support-control combinations. Sign robustness is therefore unusually strong relative to the heterogeneity documented in Sections 5 and 6.

### 7.2 All six exposure constructions

The original six-measure comparison did not use a literal common occupation set. Under each measure's native Rule-A/Webb support, occupation counts were 495, 484, 485, 468, 468, and 468. Those confirmatory estimates remain in the appendix because they answer how the result behaves under each measure's native strict-support architecture.

Main-text Table 5B instead reports a supplementary literal-intersection comparison. All six estimates use the identical 444 occupations, representing 83.14% of model-period employment. Only exposure values, rankings, and measure-specific quintile membership vary. The three AIOE Q5–Q1 coefficients are -0.0739, -0.1029, and -0.1021; alpha is -0.1013, beta is -0.1290, and broad Eloundou exposure is -0.1465. <!-- prov:V4-T5B --> All six point estimates remain negative. Five one-step wild-score intervals exclude zero; the AIOE administrative-equal interval narrowly includes zero (CI [-0.1491, 0.0014], p = .057). Literal common support therefore preserves point-estimate sign robustness but not uniform inferential rejection across all six constructions.

This is evidence of downstream sign robustness, not proof that exposure measurement is irrelevant. The point estimates differ by economically meaningful amounts, and Sections 5 and 6 show that the measures have different occupational content and support. Fixed occupational support isolates exposure construction from support composition, but it does not create a common treatment group: each architecture still determines which occupations enter Q5 and Q1.

### 7.3 Paired beta-alpha inference

The paired comparison holds the 468-occupation Rule-A/Webb sample, outcome, estimator, computerization control, and inference framework fixed. Alpha and beta nevertheless define different rankings and Q5/Q1 membership, so the comparison is between two architecture-specific empirical objects rather than two noisy scores applied to one treatment group. Beta is -0.13107, alpha is -0.09868, and the beta-specific coefficient minus the alpha-specific coefficient is -0.03240. The paired shift-distribution SE is 0.03697; the 95% studentized interval is [-0.10235, 0.03755], with p = .403. The design does not detect a difference between the alpha- and beta-specific Q5–Q1 coefficients.

That sentence cannot be inverted into equivalence. No published benchmark matches the paper's age groups, employment-stock outcome, Q5–Q1 contrast, young-relative-to-pooled-older estimand, and scale, so no arbitrary equivalence threshold is imposed. The ex-ante paired precision diagnostic was 0.0327 log points; as an optional multiplicative translation, \(100(e^{0.0327}-1)=3.33\%\). The realized confidence interval contains economically meaningful differences in either direction and provides no evidence that the architecture-specific estimands are economically equivalent.

### 7.4 Relation to recent administrative-data estimates

Brynjolfsson, Chandar, and Chen (2026) report early-career employment declines of a similar order in ADP administrative data. This paper is not an exact replication. Their prominent 19% statistic compares the two most exposed quintiles with the bottom three for workers aged 22–25; their -0.179 Q5 coefficient is a within-young occupation-level long difference. This paper uses CPS rather than ADP, Q5 versus Q1 rather than the headline top-two/bottom-three contrast, pooled ages 26–65 as the comparison group, a saturated monthly employment-stock estimator, and an independently harmonized occupational mapping. The defensible claim is **independent nationally representative evidence of a similar-order early-career employment pattern under a different outcome construction and empirical design**. The 19% statistic is neither an exact benchmark nor a calibration target.

## 8. Computerization and Remote Work

### 8.1 Defining AI exposure net of prior computerization

The empirical object “AI exposure net of prior computerization” is not defined until the comparison technology is itself defined. The question “AI rather than computerization?” therefore cannot be answered by adding an unexamined generic control. Webb software-patent exposure, O\*NET computer-use importance, O\*NET computer-use level, Autor-Dorn routine-task intensity, and Frey-Osborne automation probability are not interchangeable measures of one obvious conditioning variable. They represent patent-task overlap, the importance and level of computer interaction, routine-task composition, and broad automation susceptibility. Each leaves a different residual occupational comparison.

Panel A of Table 6 reports the downstream consequence. Under strict support, the beta Q5–Q1 estimate is -0.1311 with Webb, -0.2085 with O\*NET computer-use importance, -0.1512 with O\*NET level, -0.1277 with RTI, and -0.1001 with Frey-Osborne. All remain negative and their intervals exclude zero, but the magnitude varies by more than a factor of two.

Webb is primary because that choice was fixed before outcome access, not because its realized estimate was preferred. Its software-specific patent-to-task exposure predates ChatGPT and comes from a framework that separates software, robot, and AI technologies, making it a conceptually direct measure of prior software exposure. It is not uniquely correct. O\*NET computer use, RTI, and Frey-Osborne capture different technology margins, and the full set is reported precisely because the conditioning construct is contestable. <!-- prov:V3-W01 -->

This is not merely specification instability, and it does not select one estimate as the true AI effect. The estimand is jointly defined by the AI treatment and the prior-technology margin partialled out of it. The more-than-twofold point-estimate range is therefore a substantive limitation: a single causal-sounding AI coefficient is not invariant to the comparison technology. A reader asking whether an estimate is “really computerization” must ask which computerization construct is intended, what occupational comparison remains, and whether its effective residual-treatment support matches the proposed mechanism.

### 8.2 Occupation-level remotability

Remote work is a core competing interpretation because Emanuel, Harrington, and Pallais (2026) document a national CPS deterioration for young college graduates concentrated in remotable occupations and robust to a generative-AI exposure control. Their outcome, sample, and period differ from this paper, but their evidence rules out treating remotability as a cosmetic robustness row.

The pre-specified per-SD beta coefficient is -0.03814 in an AI-only model and -0.03795 after adding occupation-level remotability. In the full AI-plus-Webb-plus-remotability model it is -0.03718. The remote coefficient is 0.00469 in the joint AI-remote model and 0.00606 in the full model; both intervals include zero. Alpha moves from -0.02795 to -0.02376 after adding remotability and to -0.02410 in the full model, with wider intervals that include zero. The remote-only estimate is -0.01884 (95% CI [-0.04508, 0.00739], p = .154).

The appropriate conclusion is narrow: occupation-level remotability does not mechanically absorb the beta exposure gradient in this design. The exercise neither shows that “AI beats remote work” nor that remote work has no effect. Dingel-Neiman remotability is occupational feasibility, not realized individual telework, and the remote coefficient changes sign across alpha and beta architectures. Emanuel-Harrington-Pallais study individual unemployment among college graduates under different ages, timing, treatment, and comparison groups; their result and this paper's stock gradient are not competing estimates of the same parameter.

A supplementary interaction test, reported in Table 6B, asks whether the continuous beta gradient varies with occupation-level remotability, while retaining Webb exposure and the same saturated fixed effects. The coefficient on standardized beta exposure times standardized remotability times the young-post indicator is 0.0070 (cluster-robust SE 0.0162; one-step wild-score 95% CI [-0.0247, 0.0388]; p = .663). <!-- prov:V3-R01 --> The design does not detect remotability heterogeneity. The interval does not establish homogeneous effects, and the result does not show that remote work is irrelevant.

## 9. Dynamics and Falsification

Figure 3 reports the categorical monthly event study aligned with the primary beta/Webb strict-support headline estimator. October 2022 is the reference month, December 2022 is the transition month, and the static post period begins in January 2023.

![Figure 3. Categorical Q5-Q1 event study](figures/figure3_categorical_q5_q1_event_study.png)

**Figure 3. Categorical Q5–Q1 event study for the primary beta/Webb headline architecture.** Panel A plots the monthly Q5-versus-Q1 coefficient with pointwise one-step wild-score 95% intervals. Panel B plots the 65 pre-event coefficients with simultaneous 95% bands from a common-multiplier max-|t| procedure. Q2–Q4 event interactions and a standardized Webb-by-month interaction are included but not plotted. October 2022 is the reference month; December 2022 is the transition month. Conducted after outcome access and reported as supplementary. <!-- prov:V4-F03 -->

The categorical event study directly tests the headline treatment coding: Q1 is omitted, Q2–Q5 enter month by month, and the plotted coefficient is Q5 relative to Q1. A joint test of the 65 non-reference Q5 pre-event coefficients yields a maximum absolute t-statistic of 1.502 and a wild-score p-value of .929; none of the simultaneous 95% bands excludes zero. <!-- prov:V4-P01 --> The supplementary categorical event study provides no detected evidence of differential pretrends for the actual headline Q5–Q1 contrast. It does not prove parallel trends. The legacy continuous per-SD event study and its joint test remain in the appendix as a measurement-architecture diagnostic.

The categorical post path is negative in 40 of 42 observed post months but neither immediate nor monotone. Eight pointwise intervals exclude zero on the negative side: October–December 2023, December 2025, and April–July 2026; none excludes zero on the positive side. <!-- prov:V4-P02 --> The static coefficient should therefore be read as an era-average January 2023–July 2026 young-relative Q5–Q1 gradient, not evidence of a sharp January 2023 break. The pattern is compatible with delayed or intermittent adjustment, late-sample drift, gradual diffusion, and other occupation-by-age shocks. The existing post-2025 comparison does not detect a statistically distinguishable acceleration (p = .127); no additional timing window is searched.

These timing checks strengthen estimand alignment but do not establish a causal AI shock. A post-2022 gradient can coexist with technology-sector adjustment, interest-rate changes, return-to-office mandates, post-pandemic normalization, or evolving CPS composition. The saturated fixed effects and age-relative comparison absorb broad versions of those shocks, not every occupation-by-age-specific alternative.

## 10. Implications for the AI-Labor Literature

The first implication is that an exposure coefficient should be reported as an architecture, not merely a variable name. At minimum, researchers should identify the native construct, annotator or evidence source, aggregation rule, taxonomy mapping, support restriction, comparison technology, and regression scale. A statement such as “we control for AI exposure” hides too many consequential choices.

Second, common support is necessary but not sufficient. The literal 444-occupation comparison prevents six-measure coefficient differences from being driven mechanically by different missing-data patterns. It does not fix treatment-group membership or ensure that the same occupations carry residual-treatment variation or estimator information. Those are distinct diagnostics: the former describes the conditioned measurement architecture, while the latter decomposes fitted conditional curvature for the reported coefficient.

Third, harmonization can change the target population even when it barely changes scores among matched occupations. The AIOE decomposition shows that the largest consequence arises from re-admitting occupations. This finding cautions against describing a crosswalk as a neutral clerical step. It also cautions against accusing prior work of a naive exact-code merge without auditing what that work actually did. The latest BCC revision, EIG code, and Budget Lab harmonization all use explicit repairs; this paper studies alternative defensible mappings rather than attributing a known error to those papers.

Fourth, downstream sign robustness can coexist with measurement divergence. Six measures correlate differently with occupational characteristics and draw on different residual-treatment comparisons, yet every native-support and literal-common-support Q5–Q1 point estimate is negative. This is stronger than a result from one favored index and weaker than proof of a common structural treatment effect. One literal-intersection interval includes zero, and all estimates remain architecture-specific young-relative stock gradients rather than a common causal parameter.

The information-support decomposition should also be read narrowly. It shows where conditional curvature for the reported coefficient resides under the fitted model. It is not a leave-one-occupation-out influence measure and does not show which occupation caused the coefficient's sign.

Finally, comparison technologies deserve the same discipline as treatments. “Computerization” may refer to software-patent task overlap, computer-use intensity, routine-task content, or broad automation susceptibility. The more than twofold range in beta point estimates across those controls is not a reason to choose the estimate one prefers. It is evidence that the conditioning margin is part of the empirical object.

The logic extends beyond AI exposure. Automation, trade, routine-task, climate-risk, and policy-intensity measures are also constructed treatments. For any such index, apparently similar variables can imply different support, residual comparisons, and substantive parameters. The practical standard should therefore extend beyond reporting pairwise correlations: document the architecture, map it transparently, identify the observations supplying residual treatment variation, and test which conclusions survive defensible constructions. This paper establishes that workflow in one setting; it does not claim that the same degree of robustness will hold elsewhere.

## 11. Limitations

The study has seven central limitations.

First, the outcome is an occupational employment stock. It is not an individual employment probability. Reduced entry, exit from employment, and occupational switching can all generate the same cell-stock decline. Without separate flow outcomes, the paper cannot label the result layoffs or displacement.

Second, occupational exposure is not realized individual adoption. The scores describe potential exposure or capability-task alignment. They do not observe whether a worker, firm, or occupation uses AI, how intensively it is used, or whether it complements or substitutes for labor.

Third, the DDD is observational. The categorical event study shows no detected differential pretrends for the headline Q5–Q1 contrast, and the saturated fixed effects absorb rich lower-order shocks. They do not rule out an unobserved occupation-by-age shock correlated with exposure after 2022. Remote-work and computerization exercises constrain simple alternatives but do not establish causal attribution.

Fourth, occupational-content diagnostics depend on the transparent characteristics selected. The eight-characteristic matrix is broad but is not an exhaustive ontology of work. A high joint R-squared does not make a score valid or invalid; a low one does not make a score uniquely AI-specific.

Fifth, the paired consequence comparison is imprecise. The beta-alpha interval includes zero and economically large differences. The design detects no difference between the architecture-specific coefficients but offers no formal economic-equivalence conclusion. Only one direct paired contrast was specified before outcome access.

Sixth, exposure and computerization measures inherit their own taxonomy, vintage, and labeling errors. The harmonization is explicit and reproducible, but it cannot recover information absent from the source measures. Effective-support diagnostics describe where the available variation lies; they cannot create missing independent variation.

Seventh, the occupation-cluster intervals condition on the realized survey-weighted CPS cells. The public extract lacks the strata, primary sampling-unit, and replicate-weight information needed to propagate the full first-stage sampling and calibration-weight uncertainty. Household, person-panel, and rotation identifiers are available, but they are not a substitute for a defensible design-based variance procedure. No ad hoc microdata bootstrap is used.

Eighth, the design freeze specified employment-weighted exposure quintiles but left the temporal weighting window ambiguous. The executed headline classification uses post-period employment stocks and therefore depends partly on realized outcome-period composition, although the underlying exposure score remains predetermined. A supplementary pre-period-weighted construction produces nearly identical treatment membership and coefficient magnitude; this result limits the practical concern here but does not erase the design ambiguity. <!-- prov:V41-W03 -->

These limitations define the contribution. The paper is not a definitive causal estimate of generative AI's employment effect. It studies how exposure measurement becomes empirical variation and how much of one salient labor-market conclusion survives alternative architectures.

## 12. Conclusion

Constructed treatments should be evaluated not only for correlation and nominal coverage, but for their architecture, effective support, mapping, conditioning margins, and downstream robustness. Those steps answer different questions. Architecture determines what the index encodes. Residual-treatment support shows which variation remains after conditioning. Conditional information support describes fitted curvature for the reported estimator. Mapping determines who enters the estimand. Same-design inference reveals whether an economic conclusion depends on those choices.

In this setting, AI-exposure architectures differ substantially. Their occupational content diverges, their residual variation is supplied by different numbers and types of occupations, and harmonization matters chiefly through sample composition. <!-- prov:C01 --> Headline conditional-information support is also distinct from continuous residual-treatment support, so neither should be used as a shortcut for the other. <!-- prov:V3-C01 --> The definition of prior computerization more than doubles the range of beta point estimates. <!-- prov:C02 --> Yet every native-support and literal-common-support exposure architecture produces a negative Q5-versus-Q1 young-relative employment-stock coefficient, with the confirmatory headline contrasts spanning roughly 9%–19%. <!-- prov:C03 --> Measurement disagreement therefore need not imply sign fragility.

That robustness has a precise boundary. Point estimates are not invariant to the exposure and computerization definitions, and one literal-intersection interval includes zero. The paired beta-alpha comparison is too imprecise to establish economic equivalence; occupation-level exposure is not realized adoption; and an observational employment-stock gradient does not identify individual unemployment, displacement, or a unique AI mechanism. <!-- prov:C04 --> In this application, the sign survives. Its magnitude and causal interpretation do not become invariant simply because its sign does.

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

## Online Appendix

The online appendix documents exposure construction and lineage; occupational harmonization and coverage rules; complete occupational-content, rank-overlap, and residual-support diagnostics; all confirmatory outcome models; the one-step wild-score algorithm; the grouped-binomial quasi-likelihood representation; and complete monthly dynamics. It also reports analyses conducted after outcome access: the construction-link split, headline information support, literal six-way common support, categorical event study, remotability interaction, joint pretrend tests, survey-uncertainty feasibility assessment, paired-MDE scale clarification, and the pre-period quintile-weight sensitivity. Table and figure notes distinguish these analyses from the confirmatory evidence.
