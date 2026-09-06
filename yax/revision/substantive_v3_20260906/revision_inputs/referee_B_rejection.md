# Referee Report

**Manuscript:** “AI Exposure or Occupational Composition? Young-Worker Employment Comparisons in the CPS”
**Recommendation:** Reject in its present form at a leading general-interest journal.

*This report is based on the submitted manuscript and online appendix. I have not independently re-estimated the models or inspected the replication code.*

## Summary and overall assessment

The paper examines which occupational comparisons underlie the negative association between generative-AI exposure and employment among young workers in the Current Population Survey. The principal specification compares employment stocks for ages 22–25 with those for ages 26–65, contrasting the highest and lowest exposure quintiles. The reported coefficient is −0.1321. Allowing broad occupation families to have separate young-relative monthly paths changes the coefficient to −0.0217; the paired movement is 0.1104, with a confidence interval excluding zero. The paper interprets these results as evidence about the occupational comparisons supporting the association, rather than as a causal decomposition.

There is much to appreciate. The manuscript distinguishes employment stocks from employment probabilities and employer hiring, preserves one-sided zero cells, reconstructs exposure groups using preperiod employment, and recognizes that changing occupational support changes the population being studied. It also correctly uses paired inference for coefficient movements rather than comparing significance levels across specifications. These are substantive strengths, not merely presentational improvements.

My principal reservation is that the paper has not yet converted this careful empirical audit into a sufficiently sharp contribution. The strongest result is sensitivity to broad-family conditioning, but the economic interpretation of that sensitivity remains unsettled. The direct within-family comparison has little support; the static and dynamic results summarize different objects with substantially different numerical implications; and the inference exercises do not yet establish the reliability of the procedures on which the strongest claims depend.

**The problem is not simply the absence of a causal estimate.** A consequential descriptive finding or a generalizable demonstration of an identification problem could justify publication. Here, however, the paper needs a clearer account of what its collection of conditional estimates establishes beyond the proposition that occupational exposure is correlated with occupational structure.

I would not recommend an ordinary revise-and-resubmit centered on adding further robustness checks. The more promising revision would substantially narrow the argument, establish a common target across the central comparisons, and make the support and inferential limitations part of the principal result.

## Major comments

### 1. The contribution needs a sharper benchmark and a more precise claim

The manuscript acknowledges that the motivating study already reports public CPS and ACS evidence. It also explains that its CPS analysis cannot reproduce the proprietary employer panel, firm controls, or worker–firm flows. These qualifications are appropriate, but they leave the incremental contribution insufficiently defined. What precisely is learned here that was not already apparent from the existing public-data comparison?

The paper should identify a specific public-data benchmark and distinguish departures in sample, outcome, exposure grouping, estimator, and conditioning structure. The payroll bridge is useful, but it is explicitly an approximation, and the paired attenuation in that closer grouping does not exclude zero. The evidentiary strength of the headline Q5–Q1 comparison therefore should not automatically be transferred to the bridge.

Likewise, the calendar and crosswalk audits are valuable, but correcting problems encountered in this project is not the same contribution as demonstrating that an influential published finding depends on those problems. The appendix appropriately declines to attribute its literal vintage-merge error to another paper without implementation evidence. That distinction should govern how much weight the introduction places on the reconstruction work as a contribution to the literature.

The most promising contribution, in my view, is more specific: **national occupational AI-exposure comparisons may contain much less direct within-family information than their apparent occupational coverage suggests.** This is potentially important and generalizable. The paper could make it compelling by showing how the relevant support restrictions and coefficient-homogeneity assumptions determine the comparison.

By contrast, the title’s “AI exposure or occupational composition” formulation suggests a distinction the design cannot adjudicate. If AI-related employment changes operate mainly at the broad-family level, family-by-month effects could absorb them. If unrelated family-level developments drive the association, those same effects could absorb those developments. The manuscript recognizes this observational ambiguity, but the framing should consistently reflect it.

### 2. Coefficient attenuation is not yet a decomposition of occupational composition

The distinction between a changed conditional coefficient and a composition explanation is central. The paper expressly states that the ratio of the coefficient movement to the baseline estimate is not a causal “share explained.” That is correct. My concern is that the repeated conclusion that the pattern rests principally on broad occupational structure can still be read as a stronger decomposition claim than the analysis establishes.

At least three different objects need to be distinguished: changes in the distribution of employment across families; changes in young-to-older employment ratios within families; and changes in a fitted exposure coefficient when family-specific paths are admitted. The present headline exercise primarily concerns the third object.

For example, an aggregate stock ratio for exposure group `q` can be written as

```math
R_{qt} = \frac{\sum_g N^{y}_{gqt}}{\sum_g N^{o}_{gqt}} = \sum_g s^{o}_{gqt}R_{gqt},
```

where `s^{o}_{gqt}` is family `g`’s share of older employment in that exposure group and `R_{gqt}` is its young-to-older ratio, wherever the component ratio is defined. This identity suggests a transparent descriptive decomposition separating changing family weights from changing within-family ratios. Such an exercise would not identify an AI effect, and it would not equal the regression-coefficient decomposition. Its virtue would be to make “composition” an explicit economic object rather than a label attached to attenuation.

The paper also needs a more unified comparison of family conditioning and computer-use conditioning. The main text emphasizes that family paths attenuate the coefficient while computer use makes it more negative. Yet Appendix Table 9 reports a coefficient of approximately −0.124 for the parsimonious characteristic block including SOC2 interactions on the 341-occupation support. This is not a contradiction: the sample and conditioning structure differ. It does mean, however, that near-zero residual coefficients are not a general summary of the conditioned specifications.

A particularly informative replacement for part of the current specification inventory would be a matched-support comparison of the baseline, computer-use conditioning, family-month conditioning, and their combination. It should retain the same exposure assignments and use paired inference throughout. This would clarify whether the two central results reflect distinct dimensions of the occupational comparison or interact materially with one another.

I am not asking the author to call any residual coefficient “AI.” I am asking for a clearer description of why these particular coefficient movements constitute the paper’s principal economic finding.

### 3. The limited overlap is a central result, not a secondary qualification

The support analysis is among the paper’s strongest elements. Only four broad families contain occupations in both exposure tails. Restricting attention to those directly supported tails leaves 29 occupations and 5.03 percent of preperiod employment. Moreover, the direct-tail comparison has an information-based effective occupation count of 6.2, with the five largest contributions accounting for 77.8 percent of information. These statistics materially change how the family-conditioned coefficient should be understood.

Outside the directly overlapping families, the common Q5–Q1 coefficient is assembled through intermediate exposure groups and common-coefficient restrictions. It is therefore not an employment-weighted average of independently observed within-family Q5–Q1 comparisons. The manuscript says this, but the economic interpretation deserves considerably more prominence.

I would place the family-by-quintile support matrix in the main paper and explain the connections that identify the common coefficient. A compact support diagram would help readers see which families provide direct comparisons and which provide only intermediate links. The information shares are also revealing: the computer-and-mathematical family supplies only 0.28 percent of the conditioned Q5 target’s reported information. This matters when interpreting the result as evidence relevant to employment changes in occupations commonly associated with the motivating question.

The existing deletion exercises address concentration and sensitivity to particular families. They do not resolve the separate issue of common-coefficient restrictions across families with different exposure support. The paper should show which supported pairwise contrasts can be estimated without imposing the full common quintile profile, while recognizing that those estimates may be imprecise.

There is also a useful, relatively contained extension already suggested by the appendix. Table 19 reports a broader, 490-occupation beta-valid sample that does not require Webb availability. Does the poor direct overlap remain essentially unchanged on that support? This would clarify whether the support problem is intrinsic to the exposure comparison or partly induced by requiring an auxiliary control.

The appropriate conclusion may be that the CPS cannot deliver a precise national within-family tail comparison without substantial restrictions. That would be an informative finding. It is stronger and clearer than presenting a near-zero coefficient first and treating the weakness of its direct support as an ensuing caveat.

### 4. The static and dynamic findings need to be reconciled substantively

The static result moves from −0.132 to approximately −0.022 after family-month conditioning. The calendar-weighted postperiod event-study functional instead moves from approximately −0.120 to −0.207. The manuscript correctly explains that the dynamic functional is not the nonlinear static coefficient. Nevertheless, the difference is too consequential to leave at that statement.

Figure 2 is particularly informative. In its lower panel, much of the conditioned preperiod path is already below the omitted reference period, as is much of the postperiod path. The omitted reference is 2022Q4, represented by only October and November. The postperiod average relative to those two months can therefore be substantially negative even when the average pre-to-post change is small. This visual feature is consistent with a normalization and weighting explanation for part of the discrepancy, but the paper needs to quantify the relationship rather than leave readers to reconstruct it.

I would report a common descriptive functional of the dynamic coefficients, such as

```math
\tau^{D} = \sum_{t\in\mathrm{post}}w_t b_t - \sum_{t\in\mathrm{pre}}v_t b_t, \qquad \sum_t w_t=\sum_t v_t=1,
```

using fixed, explicitly stated weights in both the pooled and conditioned models. This contrast is invariant to the choice of omitted reference period. It will not automatically equal the static nonlinear coefficient, but it would establish how much of the discrepancy reflects the baseline period and how much reflects weighting or functional-form restrictions.

The preperiod tests also need a more diagnostic interpretation. The reported joint tests reject equality of all preperiod coefficients to the reference value in both specifications. That is evidence against the particular flat-preperiod restriction. The next question is whether rejection is associated with persistent drift, recurrent seasonal variation, older-period differences, or a relatively unusual reference period.

Changing the reference period alone cannot eliminate rejection of an equivalent joint equality test. Nor should the sample window be selected to obtain a favorable pretest. The purpose of the additional analysis would be to explain the rejection and assess its relevance to the substantive timing argument.

Finally, the HonestDiD conclusions concern the event-study functional supplied to that procedure, whose conventional interval already contains zero. They do not, without an explicit connection between targets, establish the robustness or lack of robustness of the static −0.132 coefficient. The manuscript acknowledges the distinction, but the resulting limitation should be integrated into the central interpretation.

### 5. The inference and numerical audits require a more decisive resolution

The paper is unusually transparent about uncertainty. However, transparency about an unresolved inferential problem is not the same as demonstrating that the preferred inference is reliable.

The adverse simulation reports rejection rates of 26.7 percent for the pooled model and 11.3 percent for the family-conditioned model under a zero target when using nominal occupation-cluster normal intervals. The appendix appropriately emphasizes that these are not estimates of actual CPS coverage. Nonetheless, this is a substantial warning sign.

The most useful next step is not another alternative interval. It is a focused assessment of the procedures actually supporting the paper’s headline statements. The simulation should report coverage or rejection behavior for the occupation wild-score procedure, the broad-family procedure, and, especially, the paired coefficient movement. Its calibration should distinguish empirically motivated features from deliberately adverse assumptions. A simulation demonstrating that an alternative dependence structure can produce overrejection does not establish that the reported intervals are wrong; it does create a burden to explain why the preferred procedure is informative in this application.

The household-resampling exercise should also be interpreted narrowly. Main Table 4 correctly identifies it as a family-by-post companion rather than inference for the family-by-calendar-month parameter. It therefore cannot independently validate the precise conditioned target featured in the abstract. Appendix E.3 should make this distinction equally explicit when describing its “family-conditioned” interval.

I also have a numerical-estimation concern. Retaining one-sided zero occupation–month cells is appropriate, but it does not by itself establish existence of finite fixed-effect estimates in the saturated model. For example, if a family–month contains older employment but no young employment, its young-relative intercept can approach minus infinity in the grouped-binomial objective. This need not invalidate the exposure coefficient, but it requires explicit treatment of boundary or separated groups. The appendix describes convergence and score checks, yet the report should state whether such groups occur and how they are handled.

This is especially important because the shortened post-2020 specification and more saturated seasonality specifications did not converge under the declared algorithm. Preserving the failed attempts is good practice. It does not settle whether failure reflects separation, identification, conditioning of the numerical problem, or the particular implementation.

The post-2020 exercise has substantive value because the earlier observations require occupational routing across coding systems. The appendix reports that split sources account for 14.93 percent of young and 17.75 percent of older early employment, while age-specific routing is unvalidated. A successful current-vintage or stable-taxonomy benchmark would therefore address a central measurement assumption, not merely add another robustness row.

### 6. The age comparison and flow results need a tighter connection to the stock finding

The paper correctly states that the outcome is a relative employment-stock comparison, not a young worker’s employment probability. Figure 1 further shows why this distinction matters: the numerator and denominator both move, and the low-exposure reference trajectory contributes to the result.

The broad older denominator deserves more attention. Age-by-month effects absorb changes common to the two age groups, but they do not absorb differential age composition across occupations within ages 26–65. The reported exact-age exercises for ages 22–25 do not address that issue.

A limited comparison using narrower older age bands, or a fixed-age-composition standardization of the older denominator, would help establish whether the headline pattern is primarily about early-career employment or about changing occupational age profiles more generally. This should be framed as clarification of the descriptive target, not as finding an “untreated” older group.

The linked-flow analysis is careful about risk sets but currently adds relatively little discrimination among mechanisms. All six primary intervals include zero, and the annual linking rate is substantially lower for young than older workers—50.98 percent versus 70.55 percent.

For these results to remain a substantial part of the paper, readers need weighted baseline transition rates, linking rates by age, exposure group, and period, and a comparison of observable composition between linked and eligible unlinked records. Clustering addresses dependence; it does not itself address selective linkage.

For entry, destination-specific probabilities from a common nonemployment risk set would help readers distinguish overall entry levels from allocation across destinations. This would not require assigning an occupation to a nonemployed origin, nor would it create an employer-hiring measure. The existing conditional allocation contrast can remain, but its connection to the stock question would become clearer.

I agree with the decision not to manufacture a complete stock–flow calibration from incompatible risk sets and missing components. The alternative, however, may be to shorten this section rather than retain an extensive mechanism discussion whose principal conclusion is insufficient resolution.

The earnings result should also be clearly ancillary: its sample ends in March 2023 and contains only three postperiod months, making it poorly aligned with the main employment analysis through July 2026.

## Specific presentation and reproducibility comments

**Clarify the model’s dependent variable.** The note to main Table 2 calls the dependent variable the log young-to-older stock ratio. Given the retained zero cells, this is not literally the observed dependent variable. The model is estimated on weighted stocks and parameterizes a log ratio of conditional means. The distinction should be maintained in table notes as well as the methods section.

**Make exposure-group reconstruction explicit in the main characteristic table.** The appendix explains that the focused 408-occupation exercise rebuilds groups on that support, whereas the expanded module retains the primary-universe assignments on its characteristic-specific subsets. This explains otherwise confusing differences in baseline coefficients. The distinction should appear directly in the relevant main-table notes, and fixed-assignment comparisons should be the default when the purpose is to isolate conditioning.

**Reduce repeated qualifications and implementation history.** The distinctions between nondetection and equivalence, between MDEs and rejection thresholds, and between conditional associations and causal effects are important. Once established clearly, they need not be repeated after nearly every estimate. Similarly, installation failures, historical numerical discrepancies, and execution receipts belong primarily in replication documentation. The main paper should devote that space to the economic target and the evidence supporting it.

**Separate reproducibility claims from verified replication.** The described manifests, ledgers, and execution checks are promising, but the submitted PDFs do not permit an independent assessment of those claims. An editorial replication package should make it straightforward to trace each central exhibit to the same treatment definition, sample, estimator, and inference procedure. The incomplete author and disclosure fields also need resolution before submission.

## Concluding assessment

The manuscript’s strongest potential contribution is to show how little direct within-family information may support an apparently broad national exposure comparison. Its most important empirical observation is that the headline coefficient changes substantially when broad-family age paths are allowed. Neither observation establishes that occupational composition, rather than AI, caused the employment pattern—and the author appropriately recognizes that limitation.

What remains missing is a sufficiently unified account of the descriptive target: how the static and dynamic results relate, what the indirect within-family comparisons identify, and how reliably their uncertainty is measured. Resolving those issues would be more valuable than expanding the existing specification inventory.

**I therefore recommend rejection in the present form.** A substantially refocused paper could make a useful contribution by centering the support problem, presenting a transparent fixed-target decomposition, and establishing the inferential reliability of a smaller set of economically interpretable results.