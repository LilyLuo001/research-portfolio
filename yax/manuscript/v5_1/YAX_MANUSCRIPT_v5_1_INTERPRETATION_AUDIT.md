# What Is AI Exposure? Measurement Architecture and Statement-Specific Robustness in Early-Career Employment

Lily Luo  
September 2026

## Abstract

Occupational AI-exposure indices are often used as if they measure one treatment. They do not: prominent indices begin from different technologies, occupational primitives, label sources, aggregation rules, and taxonomies. I hold a nationally representative CPS employment-stock design fixed while varying six defensible exposure architectures and auditing the occupations that supply their variation. The architectures differ sharply in observable content, effective support, and rankings. Nevertheless, all six produce negative point estimates for a post-January-2023 high-versus-low early-career employment-stock contrast on literal common support; the confirmatory primary estimate is -0.131 log points (95% wild-score interval [-0.217, -0.045]). This aggregate directional robustness does not make the measures interchangeable. Among realized occupational switches, 53.3% receive opposite directional labels from at least two architectures, pairwise chance-adjusted agreement ranges from 0.125 to 0.932, and the stronger claim of unusual excess disagreement disappears after conditioning on broad occupational assortativity. A transparent family-balanced consensus component also preserves a negative stock association. Exact reparameterization of a single predeclared exploratory joint model places the negative conditional association on the Eloundou-family centroid rather than the AIOE-family centroid, but treatment-only leave-one-measure diagnostics show that this family-disagreement coordinate partly reflects alpha's distinctive position. Alternative constructions can therefore support the same aggregate employment tail contrast without supporting the same occupational ranking or interpretation. Robustness is statement-specific.

## 1. Introduction

“AI exposure” enters many empirical studies as an occupation-level regressor. The workflow appears straightforward: select an index, merge it to workers or firms through their occupations, interact it with time, and study an outcome. The apparent simplicity hides a prior empirical choice. An exposure index is not observed AI use. It is a constructed treatment produced by decisions about what counts as AI, which occupational descriptions matter, who or what supplies labels, how labels are aggregated, which taxonomy receives the score, and how unmapped occupations are handled.

Those decisions are economically meaningful. Felten, Raj, and Seamans (2018, 2021) map progress in ten AI applications to occupational abilities and combine those links with O\*NET ability requirements. Eloundou et al. (2024) instead ask whether an LLM, alone or with complementary software, can halve the time needed to complete occupational tasks. An ability-based index of broad AI applicability and a task-based index of current LLM capability may be correlated without measuring the same object. Within each family, alternative aggregation and scope choices further change rankings.

This paper asks what survives those choices. It traces six exposure architectures through construction, occupational harmonization, support, a fixed early-career employment-stock design, and realized occupational movements. The organizing question is not which index is “correct.” It is: **which economic statements remain stable when a defensible alternative architecture changes the constructed treatment?**

This is more than an elaborate robustness appendix for three reasons. First, changing exposure architecture changes the empirical treatment before an outcome model is estimated. The paper therefore studies treatment definition, not a menu of controls around a fixed treatment. Second, the audit follows architecture into the occupations that supply residual variation and estimator information. Nominal coverage and raw correlation cannot reveal whether a coefficient rests on a broad labor-market comparison or a small set of unusual occupations. Third, the exercise separates economic statements that consume different representations of exposure. A high-versus-low employment-stock contrast uses architecture-specific quintiles; a claim about occupational mobility uses the sign of destination-minus-origin score changes. Robustness of one does not logically validate the other.

The application is the recent deterioration of employment among workers aged 22–25 in AI-exposed occupations. Brynjolfsson, Chandar, and Chen (2026) document a related pattern in ADP payroll records and show that it has widened through June 2026. Their outcome-rich administrative data are well suited to firm and hiring margins. The CPS analysis here is not offered as a superior substitute. Better outcome data do not resolve treatment-definition uncertainty: if researchers classify the same occupations through different architectures, the treatment changes before payroll precision or administrative sample size becomes relevant. The two approaches are complementary.

Three findings organize the paper. First, architecture divergence is empirically large. The three AIOE variants and the beta–broad Eloundou pair are highly correlated, but the employment-weighted Pearson correlation between direct-ability AIOE and Eloundou alpha is only 0.276; their weighted rank correlation is 0.258. Cross-family Q5 overlap is correspondingly limited. Across 30 exposure-by-computerization constructions, effective continuous residual support ranges from 11.9 to 84.5 occupations. Occupational harmonization matters mainly by changing which occupations enter the estimand: a naive exact-code AIOE merge covers only 3.33% of computer and mathematical employment, while the repaired mapping covers 97.7%.

Second, the aggregate stock direction is comparatively robust. Across 12 prespecified alpha/beta specifications, Q5-versus-Q1 estimates range from -0.097 to -0.209 log points. The primary beta-by-Webb coefficient is -0.131, implying that the young-to-older employment-stock ratio evolved 12.3% less favorably in Q5 than Q1 after January 2023. On the same 444 occupations, all six architecture-specific point estimates are negative. One common-support interval includes zero, and the fixed simultaneous procedure does not establish that all six coefficients are negative at familywise 95% confidence. The result is directional robustness of a tail contrast, not a common causal parameter.

Third, marginal rankings are much less interchangeable. On six-way support, 53.28% of realized occupational switches receive at least one positive and one negative directional label. Pairwise Cohen κ ranges from 0.125 to 0.932. Pair-specific support changes agreement by at most 1.95 percentage points, so the pattern is not created by the literal intersection alone. At the same time, a hard rematching benchmark that preserves broad origin-destination assortativity raises expected conflict from 45.27% to 52.32%, leaving a realized excess of only 0.96 percentage points. The evidence supports frequent classification disagreement, but not a meaningful claim that actual worker pairings are unusually conflict-heavy.

A final, tightly predeclared exploratory model places two continuous summaries in the stock equation together. The family-balanced consensus component has a negative coefficient, -0.0404, while the AIOE-versus-Eloundou family-disagreement component has a positive coefficient, 0.0309; both fixed wild-score intervals exclude zero. Correcting for their different standardization scales algebraically implies +0.0249 per weighted SD of the AIOE centroid and -0.0615 per weighted SD of the Eloundou centroid. The negative conditional association therefore loads on the Eloundou coordinate in this frozen construction. Yet removing alpha changes G materially, so this remains bounded exploratory evidence rather than a general ranking of families. The disagreement component is not every architecture-specific difference, and neither coefficient identifies a causal AI effect.

The rest of the paper develops the relevant literatures, defines the architectures and harmonization, states the exact stock estimator, audits support, reports employment and reallocation results, and draws implications for research using constructed treatments.

## 2. Related literature

### 2.1 AI exposure and labor-market measurement

The first literature constructs occupational exposure to new technologies. Felten, Raj, and Seamans (2018, 2021) link AI applications to abilities; Webb (2020) maps patent text for software, robots, and AI to occupational tasks; and Eloundou et al. (2024) assess LLM task acceleration with and without complementary software. Newer measures emphasize observed use, frontier capabilities, market investment, or multidimensional capability gaps (OECD 2026; Merola et al. 2026). These measures are useful precisely because direct adoption data are sparse, but exposure remains technological susceptibility rather than an employment forecast.

Recent work makes measurement instability an empirical subject. Yin, Vu, and Persico (2026) hold an LLM task rubric fixed and change the annotating model, producing large score and coefficient variation. Yin and Ogut (2026) study how platform-user selection changes observed-use exposure. Rai (2026), Frank et al. (2025), Eckhardt and Goldschlag (2025), the Budget Lab (2026a, 2026b), and Pulito et al. (2026) compare indices, mappings, or downstream relationships. The closest studies establish that score comparison itself is not new. This paper contributes the linked chain from construction and taxonomy through residual support, estimator information, common-support inference, and statement-specific downstream conclusions.

Actual-adoption and outcome-rich studies answer a different question. Hampole et al. (2025) link task exposure and firm adoption to labor demand; Humlum and Vestergaard (2026) combine adoption surveys with Danish administrative records and find task reorganization alongside precise near-term earnings and hours nulls; Brynjolfsson, Chandar, and Chen (2026) use high-frequency ADP payroll data to study young-worker employment and hiring. Bick, Blandin, and Deming (2025) measure adoption in a nationally representative survey, while Bick et al. (2026) link reported use to detailed occupations and tasks and show that exposure explains only part of adoption. These studies improve observation of use and outcomes. YAX isolates a prior source of uncertainty that remains when outcomes improve: the architecture used to translate occupations into treatment.

### 2.2 Computerization, tasks, and competing shocks

The distinction between AI and prior computerization draws on a long task-based literature. Autor, Levy, and Murnane (2003) emphasize routine-task substitution; Autor and Dorn (2013) connect computerization to occupational polarization; Acemoglu and Restrepo (2019) distinguish displacement from reinstatement through new tasks. Webb (2020) explicitly separates software, robot, and AI patent exposure. These are not interchangeable “computerization controls.” In the present data, replacing Webb with O\*NET computer use, routine-task intensity, or Frey–Osborne automation susceptibility changes which occupational comparison remains and more than doubles the range of beta point estimates.

Remote work is another competing interpretation. Emanuel, Harrington, and Pallais (2026) show that proximity affects feedback and skill development and document worse post-pandemic outcomes for young college graduates in remotable occupations. Their individual unemployment estimand differs from the occupation-stock contrast here. Dingel–Neiman remotability therefore enters as a serious robustness margin, not as proof that remote work has been removed.

### 2.3 Generated covariates, constructed indices, and uncertainty

AI-generated labels belong to a broader measured-covariate problem. Classical errors-in-variables intuition is incomplete when errors are systematic, architecture-dependent, rank-changing, and correlated with occupational content. Multiple-proxy methods can identify latent variables only under additional measurement and exclusion assumptions (Hu and Schennach 2008); the six indices here do not automatically satisfy them. Battaglia et al. (2025), Ludwig, Mullainathan, and Rambachan (2026), Christensen and Hansen (2026), and Duan and Pelger (2026) show that AI/ML-generated covariates can invalidate ordinary plug-in inference and that correction generally requires validation structure. YAX does not estimate label error against validated true exposure and therefore does not claim their correction. It instead makes architecture observable, holds outcomes and estimators fixed, and reports where conclusions change.

Composite-index research provides a second analogy. Weighting, normalization, scope, and missing-component rules can change ranks and group assignment even when aggregate correlations remain high (Decancq and Lugo 2013). Here those choices are not treated as an ordinary specification curve: each architecture defines a distinct treatment with its own substantive primitive. The controlled comparisons are used to bound statements, not to select the most favorable coefficient.

### 2.4 Occupational mobility and simultaneous inference

Measured occupational mobility is sensitive to coding error and dependent interviewing. Mellow and Sider (1983) document response error in CPS labor-market variables, while Kambourov and Manovskii (2008) show how occupation coding can distort measured mobility. Modern linked-survey practice therefore uses exact adjacent-month links, rotation structure, and persistence checks. The CPS instrument imports prior-month industry and occupation information in eligible continuing interviews, improving consistency without eliminating misclassification (U.S. Census Bureau 2006, 2025). The analysis follows that structure and reports both immediate and persistent switches.

Finally, the paper distinguishes repeated marginal significance from a joint statement. The common-multiplier procedures preserve cross-architecture covariance and use max-statistic simultaneous inference in the spirit of Romano and Wolf (2005). The purpose is not a generic multiple-testing correction; it is to test the exact compound claim that every architecture-specific coefficient is negative.

## 3. Exposure architectures and harmonization

### 3.1 Architecture matrix

Table 1 summarizes the six treatments. The three AIOE variants share an application-to-ability primitive but differ in how source scores are carried to the target occupation: equal administrative aggregation, direct reconstruction from target O\*NET abilities, or May 2018 OEWS source-employment weighting. The three Eloundou variants share GPT-4 task labels but change capability scope: alpha includes direct LLM acceleration, beta adds half weight to software-complemented tasks, and broad includes all E1 and E2 tasks.

| Measure | Primitive | Aggregation distinction | Native taxonomy | Final representation |
|---|---|---|---|---|
| AIOE administrative | Ten AI applications × 52 abilities | Equal mean across source occupations | SOC 2010 | Census-2018 score; weighted quintiles/continuous z-score |
| AIOE ability | Same | Direct target-ability reconstruction | O\*NET ability system | Same |
| AIOE source-weighted | Same | May-2018 OEWS source weights | SOC 2010 | Same |
| Eloundou alpha | Direct LLM task acceleration | E1 share | O\*NET-SOC 2019 | Same |
| Eloundou beta | LLM plus limited software complementarity | E1 + 0.5E2 | O\*NET-SOC 2019 | Same |
| Eloundou broad | LLM plus software | E1 + E2 | O\*NET-SOC 2019 | Same |

The complete architecture matrix records label sources, bridges, and support rules. The primary support rule is strict no-renormalization: every mapped source component must have a finite score. A partially scored occupation is excluded rather than reconstructed by rescaling its observed components.

### 3.2 Occupational harmonization

Raw CPS occupation codes use Census 2010 in 2017–2019 and Census 2018 thereafter. Pre-2020 records are route-expanded using official Census total conversion rates; later records match directly. SOC-based measures are collapsed at six digits and then carried through official SOC-to-Census bridges using documented source- or target-vintage weights.

This is substantively important. An exact SOC-code merge between AIOE and the post-2018 outcome taxonomy covers 3.33% of computer and mathematical employment because older software-developer codes were split or renumbered. The repaired mapping covers 97.7%. In a four-row decomposition, changing score values while holding original support fixed moves the continuous coefficient from -0.01885 to -0.01920. Expanding support moves it to -0.03156; removing computer and mathematical occupations from the expanded support gives -0.02940. The main mapping consequence is who enters the estimand, not a large score revision for already matched occupations.

Literal common support fixes 444 occupations across all six measures and represents 83.14% of model-period employment. It does not fix ranks or quintile membership. That distinction permits a direct same-sample comparison without pretending that Q5 denotes the same occupations under every architecture.

### 3.3 Consensus and between-family components

For descriptive organization, each of the six measures is standardized using frozen pre-period employment weights. Let `A` be the equal-weight centroid of the three AIOE scores and `E` the equal-weight centroid of the three Eloundou scores. Define

\[
F_o=(A_o+E_o)/2,\qquad G_o=(A_o-E_o)/2.
\]

`F` is the family-balanced consensus component. It gives each family equal total weight and is not an inferred underlying truth. `G` is the between-family disagreement component; it captures the AIOE-versus-Eloundou centroid dimension only.

## 4. CPS data and exact empirical design

### 4.1 Employment stocks and sample calendar

The analysis uses 9,262,480 IPUMS CPS records and aggregates employed respondents aged 22–65 with `WTFINL` into occupation-by-age-group-by-month stocks. Young workers are ages 22–25; the comparison group is ages 26–65. The extract contains 109 observed months from January 2017 through July 2026; March is absent in 2017–2021 and October 2025 is absent. December 2022 is a transition month excluded from static models. January 2023 through July 2026 contains 43 calendar months, but the absent October 2025 observation leaves 42 observed post months.

The unit is a stock cell, not a person-month employment probability. The outcome can move through entry, employment exit, occupational switching, or changes in the older comparison stock.

### 4.2 Headline PPML specification

Let `N_oat` be the CPS-weighted employment stock for occupation `o`, age group `a`, and observed calendar month `t`. `Young_a` equals one for ages 22–25, `Post_t` equals one from January 2023 forward, and `Q_oq` indicates architecture-specific employment-weighted exposure quintile `q`. Q1 is omitted. With standardized Webb software-patent exposure `W_o`, the implemented conditional-mean model is

\[
E[N_{oat}\mid X]=\exp\left[
\gamma_{oa}+\delta_{ot}+\lambda_{at}
+\sum_{q=2}^{5}\beta_q Q_{oq}Young_aPost_t
+\theta W_o Young_aPost_t
\right].
\]

The fixed effects are occupation×age group, occupation×month, and age group×month. CPS person weights construct `N_oat`; the cell likelihood receives no additional survey weight. The code estimates the algebraically equivalent grouped-binomial conditional likelihood for the young share within occupation-month. Inference clusters by occupation and uses 999 one-step Rademacher wild-score draws.

The headline `beta_5` is the post-period change in the young-to-older employment-stock ratio for Q5 relative to Q1, conditional on Q2–Q4, the fixed effects, and Webb's young-by-post slope. It is an era-average observational tail contrast.

### 4.3 Design sequence

The primary beta/alpha models, support rules, comparison technologies, post period, and paired-difference interpretation were fixed before protected outcomes were opened and are preserved by the `v1.1-design-freeze` tag. Common-support, estimator-information, mobility, consensus, and F+G analyses were specified in versioned plans after outcome access and are labeled exploratory in tables and appendices. The final F+G plan was committed at `6fed6f5` before the one authorized joint model ran. This sequence is a credibility record, not a source of causal identification.

## 5. Architecture content and support

### 5.1 Correlation and observable content

The full Pearson and weighted rank matrices make the architecture structure visible. AIOE variants correlate 0.981–0.996 in levels and 0.982–0.993 in ranks. Beta is highly correlated with AIOE (0.821–0.833) and broad Eloundou exposure (0.941), whereas alpha correlates only 0.276–0.295 with AIOE and 0.346 with broad. Rank results are similar. High correlation within some pairs coexists with large divergence elsewhere.

Observable-content projections tell the same story. AIOE is strongly associated with cognitive content, education, wages, teleworkability, and computer use. Alpha is much less associated with most of those attributes; beta and broad lie between. Because AIOE and several validators share O\*NET inputs, same-source fit is partly mechanical. On the four less construction-linked correlates—routine-task intensity, wages, teleworkability, and STEM share—AIOE R-squared remains 0.64–0.67, compared with 0.27 for alpha, 0.43 for beta, and 0.48 for broad.

### 5.2 Residual and estimator-information support

Nominal occupation count is not effective support. After a standardized exposure is residualized on one computerization measure, the employment-weighted residual-variance shares imply effective counts from 11.9 to 84.5 occupations across 30 architectures. Alpha conditional on Webb is particularly concentrated: 17.4 effective occupations, with the top five carrying 41.6% of residual variation.

The headline estimator consumes a different object. Absorbing the exact Q5–Q1 PPML design under fitted information weights yields 42.9–71.1 effective occupations across the 12 headline models. Continuous residual-support and headline information-share ranks correlate roughly 0.71–0.74 in the four central comparisons, but concentration and leading occupations differ. Under Webb, alpha moves from 17.4 effective occupations in the continuous diagnostic to 56.1 in headline information support, with only one top-five occupation shared. Neither statistic is a finite-sample causal influence measure.

## 6. Employment-stock results

### 6.1 Confirmatory tail contrasts

Across 12 prespecified alpha/beta headline models, Q5-versus-Q1 estimates range from -0.0971 to -0.2085 log points. The primary strict-support beta-by-Webb estimate is -0.1311 (occupation-cluster SE 0.0444; wild-score 95% CI [-0.2170, -0.0451]; `p=.003`) across 468 occupations. The transformation `100(exp(beta)-1)` is -12.3%.

The full quintile profile does not justify a monotonicity claim: relative to Q1, the primary Q2–Q5 coefficients are -0.0855, -0.0478, -0.0970, and -0.1311. The paper therefore reports a tail contrast rather than an exposure dose-response.

On literal common support, the three AIOE coefficients are -0.0739, -0.1029, and -0.1021; alpha, beta, and broad are -0.1013, -0.1290, and -0.1465. All point estimates are negative, but the administrative-AIOE interval includes zero. Under common-multiplier simultaneous inference, its one-sided upper bound is also positive; the compound all-six-negative statement is not established.

The paired beta-minus-alpha contrast is -0.0324 log points (paired SE 0.0370; 95% CI [-0.1023, 0.0376]; `p=.403`). The design does not detect a difference and does not establish equivalence. An outcome-blind donor simulation had implied an MDE of 0.0327 log points, but the realized SE is 3.17 times the synthetic SE. The appendix classifies this as MDE-R2 and treats it as design-history provenance rather than a headline precision claim.

The same calibration problem affects the primary design history. Its outcome-blind beta×Webb simulation recorded a null mean cluster SE of 0.01217, whereas the realized primary SE is 0.04441, a ratio of 3.65. Both prospective simulations are reproducible but materially optimistic and remain design-history provenance, not substantive evidence about realized power. The available records do not isolate a unique cause for either gap.

### 6.2 Consensus and between-family evidence

An exploratory F-quintile model on the same 444 occupations produces -0.1285 log points (95% wild-score CI [-0.2185, -0.0386]). This shows that a transparent equal-family-weight summary can reproduce the negative aggregate tail direction; it does not establish a uniquely correct exposure variable.

The one authorized joint continuous model goes further by including standardized `F`, standardized `G`, and Webb together. The consensus coefficient is -0.04036 per SD (occupation-cluster SE 0.01407; wild-score CI [-0.06925, -0.01147]; `p=.007`). Conditional on `F` and Webb, the between-family coefficient is +0.03089 (SE 0.01486; CI [0.00180, 0.05999]; `p=.040`). The centered wild-score covariance is -0.00009825 (correlation -0.464), and the max-|t| joint test of both coefficients equal to zero gives `p=.008`.

Because `F` and `G` were standardized separately, their coefficients cannot be converted to AIOE and Eloundou coefficients by simply adding and subtracting them. On the frozen model support, the weighted SDs are `s_A=0.99865`, `s_E=0.86665`, `s_F=0.87774`, and `s_G=0.32214`. Exact algebra gives an implied AIOE-centroid coefficient of +0.02496 per original centroid unit (+0.02493 per weighted SD; covariance-transformed normal 95% interval [-0.01492, 0.06477]) and an Eloundou-centroid coefficient of -0.07094 per original unit (-0.06148 per weighted SD; interval [-0.10836, -0.01460]). The original-unit A-minus-E contrast is +0.09590 (normal interval [0.00645, 0.18535]); because that contrast is exactly `b_G/s_G`, its transformed existing-G wild-score interval is [0.00559, 0.18621]. This transformation reproduces the fitted F/G contribution to machine precision; it is not a new regression.

This is AE-R1 scaling evidence: in the exploratory joint specification, the negative conditional stock association loads more heavily on the Eloundou-family centroid than on the AIOE-family centroid. The treatment-only stability audit is only G-PARTIAL, however. Removing beta or broad leaves G highly similar, but removing alpha lowers the weighted level/rank correlations to 0.865/0.855, retains 72.5% of frozen-Q1 and 69.5% of frozen-Q5 weight, and changes zero-direction for 17.9% of employment. The result therefore partly reflects alpha's distinctive position and is not elevated into a general family-level story. It does not reveal which family is correct; it does not imply that AIOE has no effect; and `G` is not all architecture-specific disagreement. The serialized result did not retain draw-level shifts or the analytic covariance off-diagonal, so the algebraic audit reports transformed common-draw covariance intervals rather than fabricating exact transformed wild-score intervals.

### 6.3 Dependence sensitivity and dynamics

Two-way occupation×calendar-month clustering is reported as a model-based sensitivity. It changes the primary SE from 0.04441 to 0.04493 and gives a normal interval [-0.21914, -0.04300]. The common-support intervals retain the same five-versus-one pattern. This is not a reconstruction of CPS design-based variance.

The categorical monthly event study detects no differential pretrend under the fixed max-statistic procedure: the maximum absolute pre-event t-statistic is 1.502 and the wild-score `p` is .929. Forty of 42 observed post coefficients are negative, but the path is neither immediate nor monotone. The static coefficient is an era average. Interest rates, technology-sector adjustment, remote-work changes, post-pandemic normalization, and occupation-by-age shocks remain plausible concurrent forces.

## 7. Realized occupational reallocation

### 7.1 Adjacent-month construction

The longitudinal sample uses exact adjacent-month `CPSIDV` links from MISH 1, 2, 3, 5, 6, or 7 to the next interview and assigns the official origin `LNKFW1MWT`. The eight-month MISH 4→5 gap is excluded. December 2019→January 2020 is excluded whenever destination occupation matters because the taxonomy changes. The adjacent-month design benefits from CPS dependent interviewing and excludes the eight-month rotation gap, but occupational coding error remains possible; persistence-based results provide a sensitivity check rather than a correction for all misclassification. The immediate A→B→A reversal rate is 9.865%.

### 7.2 Directional non-interchangeability

Among 108,500 switches with finite scores under all six architectures, 53.28% receive at least one positive and one negative label; 45.56% receive the same nonzero direction. Any sign reversal counts, regardless of the movement's magnitude. The statistic therefore describes classification non-interchangeability, not economically large displacement.

Pairwise support retains 59.54%–90.80% of weighted switches and changes agreement by at most 1.95 percentage points relative to the six-way intersection. Weighted raw exact agreement ranges from 55.37% to 96.58%; Cohen κ ranges from 0.125 to 0.932. The standard six-rater Fleiss κ is 0.501, with a descriptive official-weight analogue of 0.502. Kappa addresses base rates; it does not turn constructed indices into random raters or encode movement size.

The young-by-post conflict comparison is essentially zero: its 95% interval is [-2.67, 2.66] percentage points. Measurement disagreement is a general feature of the rankings, not one detected specifically among young post-2022 movers.

### 7.3 Consensus distance and hard benchmark

Conflict falls from 94.59% in the smallest absolute-`F` movement bin to 19.06% in the largest. This is an organizing decomposition, not an independent economic finding. Some concentration is mechanically expected because `F` averages the same families whose signs define conflict. The useful interpretation is limited: architectures disagree most often when consensus movement is small relative to architecture-specific movement.

The hard benchmark defines broad families using the first two digits of the Census-2018-linked SOC major group. It yields 23 numeric broad families on employed switch support. Rematching is conducted within age group, calendar month, origin broad family, and destination broad family; it preserves weighted detailed origin and destination marginals and destroys only detailed origin-destination pairing. The primary implementation spans 30,170 nonempty strata and 84,192 detailed joint cells and represents 98.31% of official switch weight.

This is stronger than independent age-by-month marginal rematching because it preserves broad assortativity in both directions. Conditioning on that structure raises expected conflict from 45.27% to 52.32%, compared with 53.28% realized. The remaining 0.96-point gap is below the predeclared one-point meaningful-gap threshold. The `.001` upper-tail area comes from a 200,000-pseudo-unit, 999-draw computational reference distribution; it is not a conventional sampling p-value or evidence of economic importance.

## 8. Computerization, remotability, and mechanism boundary

“AI net of computerization” is not defined until the comparison technology is named. Under strict support, beta's tail coefficient is -0.1311 with Webb, -0.2085 with O\*NET computer-use importance, -0.1512 with O\*NET level, -0.1277 with routine-task intensity, and -0.1001 with Frey–Osborne automation susceptibility. The sign is stable while magnitude varies by more than a factor of two. Webb is primary because its software-specific comparison was fixed before outcomes, not because it generates a preferred estimate.

Adding occupation-level Dingel–Neiman remotability barely changes the continuous beta coefficient, and the beta×remotability interaction interval includes zero. This means remotability does not mechanically absorb beta in this specification. It does not adjudicate realized remote work or contradict the individual-level proximity evidence.

A separately predeclared longitudinal CPS exercise using validated adjacent-month links and official `LNKFW1MWT` did not precisely distinguish employment exit, occupational outflow, or entry-destination changes as the source of the stock contrast. The appendix defines each risk set, assignment rule, likelihood, and estimand. The three coefficients are not an accounting decomposition and do not sum to the stock result.

## 9. Implications

The main implication is practical: exposure should be reported as an architecture, not merely a variable name. Technology scope, occupational primitive, labels, aggregation, taxonomy, crosswalk, support, normalization, and treatment representation jointly define the empirical object.

Second, common support solves only composition. It prevents a comparison from being driven mechanically by different missing occupations, but it does not hold scores, ranks, quintiles, or residual variation fixed. Reporting continuous correlations, rank correlations, effective support, and estimator information alongside coefficients makes that distinction visible.

Third, robustness belongs to a statement. The negative aggregate tail direction survives large architecture changes. Magnitudes and computerization-conditioned comparisons move. Marginal occupational directions disagree frequently. Broad assortativity explains nearly all excess conflict over simple rematching. The scaled joint F+G result places the negative conditional association on the Eloundou-family coordinate, while the treatment-only leave-one-out audit shows that this coordinate partly reflects alpha. None of these facts cancels the others because they concern different treatment representations and estimands.

The evidence has a compact boundary. It is observational, exposure is not adoption, CPS stock cells do not identify individual displacement, and full survey-design variance is unavailable. These limits constrain causal interpretation without erasing the measurement result: treatment-definition uncertainty remains consequential even when an aggregate direction is stable.

## 10. Conclusion

Six defensible AI-exposure architectures construct different empirical treatments. They differ in occupational content, taxonomy, effective support, and rankings. Yet they all produce a negative high-versus-low early-career employment-stock point estimate on literal common support. A family-balanced consensus construction carries the same aggregate direction.

That convergence has sharp limits. One architecture's common-support interval includes zero, the compound all-six-negative statement is not supported by the fixed simultaneous rule, and the exploratory joint model implies a stronger negative conditional association along the Eloundou-family coordinate. Because the treatment-only G construction changes materially when alpha is removed, that reparameterized result remains bounded evidence about the frozen construction rather than a general family ranking. More than half of realized occupational switches receive conflicting signs, although broad occupational assortativity removes the claim of meaningful excess conflict.

The durable conclusion is therefore neither that AI has caused early-career displacement nor that exposure choice is irrelevant. It is that alternative constructions can support the same aggregate tail contrast without being interchangeable for the rankings and interpretations researchers attach to it. Robustness is statement-specific.

## References

Acemoglu, Daron, and Pascual Restrepo. 2019. “Automation and New Tasks: How Technology Displaces and Reinstates Labor.” *Journal of Economic Perspectives* 33(2): 3–30.

Autor, David H., and David Dorn. 2013. “The Growth of Low-Skill Service Jobs and the Polarization of the US Labor Market.” *American Economic Review* 103(5): 1553–1597.

Autor, David H., Frank Levy, and Richard J. Murnane. 2003. “The Skill Content of Recent Technological Change: An Empirical Exploration.” *Quarterly Journal of Economics* 118(4): 1279–1333.

Battaglia, Laura, Timothy Christensen, Stephen Hansen, and Szymon Sacher. 2025. “Inference for Regression with Variables Generated by AI or Machine Learning.” CEPR Discussion Paper 19115, revised May.

Bick, Alexander, Adam Blandin, and David J. Deming. 2025. “The Rapid Adoption of Generative AI.” NBER Working Paper 32966, revised February.

Bick, Alexander, Adam Blandin, David J. Deming, and Tyler R. Schumacher. 2026. “What Work Does Generative AI Do?” NBER Working Paper 35677.

Brynjolfsson, Erik, Bharat Chandar, and Ruyu Chen. 2026. “Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of Artificial Intelligence.” Stanford Digital Economy Lab Working Paper, revised August 12.

Budget Lab at Yale. 2026a. “Labor Market AI Exposure: What Do We Know?” February 19.

Budget Lab at Yale. 2026b. “What We Do and Don’t Know About How AI Is Affecting the Labor Market.” May 7.

Cameron, A. Colin, Jonah B. Gelbach, and Douglas L. Miller. 2011. “Robust Inference with Multiway Clustering.” *Journal of Business & Economic Statistics* 29(2): 238–249.

Cohen, Jacob. 1960. “A Coefficient of Agreement for Nominal Scales.” *Educational and Psychological Measurement* 20(1): 37–46.

Christensen, Timothy, and Stephen Hansen. 2026. “Performing Valid Inference with AI/ML-Generated Covariates: A Guide for Empirical Practice.” *AEA Papers and Proceedings* 116: 92–97.

Decancq, Koen, and María Ana Lugo. 2013. “Weights in Multidimensional Indices of Wellbeing: An Overview.” *Econometric Reviews* 32(1): 7–34.

del Rio-Chanona, R. Maria, Ekkehard Ernst, Rossana Merola, Daniel Samaan, and Ole Teutloff. 2025. “AI and Jobs: A Review of Theory, Estimates, and Evidence.” arXiv:2509.15265.

Dingel, Jonathan I., and Brent Neiman. 2020. “How Many Jobs Can Be Done at Home?” *Journal of Public Economics* 189: 104235.

Duan, Junting, and Markus Pelger. 2026. “Inference with AI-Generated Covariates.” NBER Working Paper 35481.

Eckhardt, Sarah, and Nathan Goldschlag. 2025. *AI and Jobs: The Final Word (Until the Next One).* Economic Innovation Group.

Eloundou, Tyna, Sam Manning, Pamela Mishkin, and Daniel Rock. 2024. “GPTs Are GPTs: Labor Market Impact Potential of LLMs.” *Science* 384(6702): 1306–1308.

Emanuel, Natalia, Emma Harrington, and Amanda Pallais. 2026. “The Power of Proximity to Coworkers.” *Quarterly Journal of Economics* 141(3): 1825–1870.

Felten, Edward W., Manav Raj, and Robert Seamans. 2018. “A Method to Link Advances in Artificial Intelligence to Occupational Abilities.” *AEA Papers and Proceedings* 108: 54–57.

Felten, Edward, Manav Raj, and Robert Seamans. 2021. “Occupational, Industry, and Geographic Exposure to Artificial Intelligence: A Novel Dataset and Its Potential Uses.” *Strategic Management Journal* 42(12): 2195–2217.

Fleiss, Joseph L. 1971. “Measuring Nominal Scale Agreement among Many Raters.” *Psychological Bulletin* 76(5): 378–382.

Frank, Morgan R., et al. 2025. “AI Exposure Predicts Unemployment Risk: A New Approach to Technology-Driven Job Loss.” *PNAS Nexus* 4(4): pgaf107.

Hampole, Menaka, Dimitris Papanikolaou, Lawrence D. W. Schmidt, and Bryan Seegmiller. 2025. “Artificial Intelligence and the Labor Market.” NBER Working Paper 33509, revised September.

Humlum, Anders, and Emilie Vestergaard. 2026. “Still Waters, Rapid Currents: Early Labor Market Transformation under Generative AI.” NBER Working Paper 33777, revised March.

Hu, Yingyao, and Susanne M. Schennach. 2008. “Instrumental Variable Treatment of Nonclassical Measurement Error Models.” *Econometrica* 76(1): 195–216.

Kambourov, Gueorgui, and Iourii Manovskii. 2008. “Rising Occupational and Industry Mobility in the United States: 1968–97.” *International Economic Review* 49(1): 41–79.

Ludwig, Jens, Sendhil Mullainathan, and Ashesh Rambachan. 2026. “Large Language Models: An Applied Econometric Framework.” *Annual Review of Economics*.

Mellow, Wesley, and Hal Sider. 1983. “Accuracy of Response in Labor Market Surveys: Evidence and Implications.” *Journal of Labor Economics* 1(4): 331–344.

Merola, Rossana, Ekkehard Ernst, Daniel Samaan, R. Maria del Rio-Chanona, and Ole Teutloff. 2026. “Workers’ Exposure to AI: What Indicators Tell Us—and What They Don’t.” ILO Research Brief.

OECD. 2026. *The OECD AI Exposure Measure: Mapping the OECD AI Capability Indicators to Occupations.* OECD Artificial Intelligence Papers No. 59.

Pulito, Giuseppe, Mariola Pytlikova, Sarah Schroeder, and Magnus Lodefalk. 2026. “Who Adopts AI? Evidence on Firms, Technologies and Workers.” Örebro University School of Business Working Paper 3/2026.

Rai, Sudhanshu. 2026. “Do AI Occupational-Exposure Scores Measure AI? AIOE and Eloundou (2024) Largely Capture Cognitive Content; Webb (2020) Does Not.” MPRA Paper 129904.

Romano, Joseph P., and Michael Wolf. 2005. “Stepwise Multiple Testing as Formalized Data Snooping.” *Econometrica* 73(4): 1237–1282.

U.S. Census Bureau. 2006. *Current Population Survey Design and Methodology.* Technical Paper 66.

U.S. Census Bureau. 2025. *Basic Current Population Survey Interviewer’s Manual.*

Webb, Michael. 2020. “The Impact of Artificial Intelligence on the Labor Market.” Stanford University Working Paper.

Yin, Michelle, and Burhan Ogut. 2026. “Who Uses AI? Platform Selection and the Measurement of Occupational AI Exposure.” arXiv:2605.21743.

Yin, Michelle, Hoa Vu, and Claudia Persico. 2026. “How (un)Stable Are LLM Occupational Exposure Scores? Evidence from Multi-Model Replication.” NBER Working Paper 35110.

## Online appendix roadmap

The appendix contains the full architecture and correlation matrices; exposure lineage and occupational bridges; residual-treatment and conditional-information support; all native and common-support stock models; the Q2–Q5 profile; headline and paired power-calibration reconciliation; event-study coefficients; computerization and remotability results; two-way dependence sensitivity; adjacent-link construction; separate exit, outflow, and entry-destination estimands; all 15 κ results; hard-benchmark taxonomy and implementation; the partly mechanical consensus-distance organization; the one joint F+G plan and result; its exact A/E reparameterization and treatment-only G-stability audit; and complete reproducibility receipts.
