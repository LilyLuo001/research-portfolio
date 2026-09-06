# Referee Report

**Manuscript:** "Constructed Exposure Measures and Statement-Specific Robustness: Evidence from Early-Career Employment"

**Author:** Lily Luo (anonymized version reviewed together with the Online Appendix)

**Recommendation:** Reject and resubmit (major restructuring required). The underlying work is unusually careful and the data infrastructure is real, but the paper as written does not yet make a contribution that clears the bar at a general-interest journal. The path to publication runs through re-centering the paper on the results it actually establishes, and through fixing an inference problem that currently undercuts most of its comparative claims.

---

## 1. Summary of the paper

The paper fixes a CPS employment-stock design — a grouped-binomial (conditional Poisson) model of the young (22–25) to older (26–65) employment ratio within occupation-month cells, with a post-January-2023 interaction by exposure quintile — and then varies the *construction* of the occupational AI exposure treatment. Six implementations are drawn from two families (three AIOE variants; three Eloundou et al. task shares indexed by the complementarity weight λ), and two outside architectures (Webb AI patent–task overlap; a reversed OECD capability gap) are admitted under an ex-ante rule.

The headline object is a Q5–Q1 coefficient of −0.1311 log points. The paper's claims are that (i) taxonomy repair changes which occupations are in the sample far more than it changes scores on fixed support (coverage 3.33% → 97.7% for computer/math); (ii) all six selected implementations give negative tail estimates but the two external architectures do not; (iii) the headline is reference-dependent (Q5 differs from Q1 and Q3, not from Q2 or Q4); (iv) a within-SOC2 permutation does not establish AI specificity; and (v) ranking disagreement across architectures is common at a zero threshold but falls sharply once movements must be economically material.

## 2. Assessment of the contribution

I want to be direct about where I think the paper stands.

The execution is meticulous — the sample-flow reconciliation (Appendix Table 3), the hash-and-tag chronology (Appendix L), the honest reporting of the failed simultaneous-band criterion, the failed 5,148-parameter seasonality model, and the residual-wild refit that produced zero admissible draws are all more than one normally sees. I do not doubt the arithmetic.

The problem is the framing. As written, the paper's thesis is that "robustness belongs to a specified architecture, support, reference group, and economic statement, not to the label 'AI exposure' in general." Stated at that level of generality, this is a proposition most readers already accept, and it has a large prior literature the paper does not engage (Leamer 1983; Athey and Imbens 2015 on specification robustness; Young and Holsteen 2017; Simonsohn, Simmons, and Nelson 2020 on specification curves). A referee report that only said "we knew treatments are constructed" would be unfair, but the manuscript needs to say what is *specifically* learned here that a multiverse analysis of any constructed regressor would not have told us.

There is a much stronger paper inside this one, and the author has already produced its two central results without foregrounding them:

- **The within-SOC2 permutation.** Reassigning beta scores across detailed occupations *within* two-digit families produces a mean coefficient of −0.1097 against an observed −0.1311, with the observed value at the 22nd percentile of the permutation distribution. Read plainly, roughly five-sixths of the headline magnitude is reproduced by any within-family shuffle. That is not a caveat about specificity. It is a finding: the early-career pattern in CPS is largely a broad-occupation-composition pattern, and the detailed AI score adds little on top of it.
- **The influence concentration.** Deleting a single Q1 occupation — fast food and counter workers — moves the estimate from −0.1311 to −0.1106. Deleting customer service representatives moves it to −0.1131. The low-exposure reference group is anchored by occupations whose 2023–2026 evolution has obvious non-AI drivers (reopening dynamics, immigration-driven labor supply, minimum wage changes, return-to-office).

Put those two together with the reference-dependence result and the paper has a substantive, policy-relevant negative finding about a widely cited empirical pattern. That is publishable at a general-interest journal. "Measurement is a choice" is not. I would encourage the author to make this the paper.

## 3. Major comments

### M1. The inference is too weak to support the paper's comparative language, and this should be stated as a result rather than a limitation

This is my most serious concern.

The realized primary SE is 0.0444 against a prospective 0.01217 — a ratio of 3.649 (Appendix K). The ex-ante design was powered for differences around 3.27 percentage points; at the realized SE, the minimum detectable effect at conventional power is roughly 0.124 log points, i.e. approximately the size of the headline estimate itself. Every "the stronger claim does not survive" statement in the paper is therefore ambiguous between two very different readings:

1. Architecture choice changes the economic conclusion.
2. Architecture choice moves point estimates by amounts this design cannot resolve either way.

The paper's own numbers favor (2). The paired beta-minus-Webb-AI difference is 0.0646 with interval [−0.0411, 0.1704]; beta-minus-OECD is 0.1115 with [−0.0015, 0.2244]; beta-minus-alpha is −0.0324 with [−0.1023, 0.0376] and *p* = .403. The Q5–Q2 and Q5–Q4 contrasts have intervals half as wide as the contrasts they are being compared against. Section 5.1's sentence, "the six-measure sign statement therefore does not generalize to every admissible exposure concept," is doing work the intervals do not license — it is equally consistent with Webb AI and beta measuring the same thing badly.

**Requests.** (a) Report a minimum detectable effect for the primary design and for each paired architecture contrast, and use it to discipline the language throughout Sections 5, 6 and 8. (b) Where a contrast is imprecise, say so in those terms rather than in terms of what "does not extend." (c) Attempt a diagnosis of the 3.6× precision gap. The paper lists six candidate omissions from the planning simulation but does not try to separate them. At minimum, re-run the historical simulation adding contemporaneous cross-occupation covariance (the omission most likely to dominate) and report how much of the gap that alone closes. Leaving the gap unexplained is a substantial and — since the author flags it prominently — self-inflicted problem.

### M2. Effective clustering and the CPS rotation structure

Nominal clusters are 468, but fitted conditional information has effective count 43.3 with a top-five share of 24.6% (Section 4.2). Wild-score bootstrap with roughly 43 effective clusters and that much concentration has known coverage problems, and the paper's own two-way sensitivity (0.0444 → 0.0449) is uninformative here because the age-by-month fixed effects absorb the common time component that two-way clustering is designed to catch.

Separately, and I think more importantly: the CPS rotation design induces 75% sample overlap between adjacent months and 50% overlap at twelve-month lags. Monthly occupation-by-age stocks built from these samples are strongly serially dependent for purely mechanical reasons, and the paper's inference does not account for it anywhere. With 108 monthly cells per occupation and 42 post coefficients, this is not second-order.

**Requests.** (a) Report the distribution of respondent counts per occupation-month-age cell (median, 10th, 90th percentiles), and re-estimate on quarterly cells to check that monthly sparsity is not driving either the point estimate or the SE. (b) Add inference that is robust to the rotation-induced serial correlation — occupation-level block bootstrap over time, or clustering on occupation with a time-series-robust score. (c) Add a placebo-in-time distribution: re-estimate the identical design with pseudo-break dates in each month of 2015–2019 and report where −0.1311 sits in that empirical null. Given M1 and the concentration of information, this is the single most informative inference exercise available, and it does not require any assumption about score exchangeability (unlike the within-SOC2 permutation, whose limitations the author correctly concedes).

### M3. The permutation result implies a regression that is not run

The natural regression analogue of the within-SOC2 permutation is to include **two-digit-SOC × age-group × post** interactions in the primary model and report what happens to the Q5–Q1 coefficient. If the permutation mean is −0.1097, I expect the coefficient to fall substantially — perhaps to something indistinguishable from zero — once broad-family differential evolution is absorbed.

This must be in the paper. It is the direct test of whether the detailed exposure score carries information beyond occupational composition, it is cheap, and its answer determines how the paper should be framed. If the coefficient survives, the AI-specificity discussion becomes much stronger than the permutation alone can make it. If it does not, the author has the substantive result I described in Section 2 above.

Please also report: (i) a formal test of monotonicity across the quintile profile (−0.0855, −0.0478, −0.0970, −0.1311), since the profile is visibly non-monotone and the paper asserts rather than tests this; and (ii) the contrast estimated only on the 46 always-Q1 and 18 always-Q5 occupations. The paper notes these represent just 7.34% and 2.41% of employment while 271 reclassified occupations carry 82.30% of mean fitted influence — which means "common support" is doing much less work than the phrase suggests, and readers will want to see the stable-classification estimate even if it is noisy.

### M4. Influence concentration needs to be a headline, not a sensitivity

Section 5.2 and Appendix J report leave-one-out movements up to 0.02052, with fast food and counter workers alone accounting for a 16% attenuation. The paper's framing ("no sign reversal") is the least informative summary available.

**Requests.** (a) Report leave-*k*-out estimates for *k* = 5, 10, 20 most influential occupations deleted jointly, not one at a time. Sequential deletion is not additive but the joint number is what a skeptical reader wants. (b) Report a trimmed estimate that down-weights the tails of the influence distribution. (c) Discuss directly whether the Q1 reference is contaminated by post-pandemic food-service and in-person-services recovery. The IND1990 leisure/hospitality exclusion (−0.1325 / −0.1388) is not a clean test because, as the author notes, code 800 bundles theaters and motion pictures; a cleaner construction is needed.

### M5. CPS weighting discontinuities over the post period

The 2025–26 era estimate (−0.1629) is the most negative in the paper, and the paper's post window spans a period of unusually large revisions to CPS population controls and a continued decline in response rates. Annual January population-control adjustments create level shifts in weighted stocks that are concentrated in young and immigrant-heavy occupations — precisely the cells this design compares.

The unweighted respondent-equivalent specification (−0.1308) is reassuring and should be promoted from Appendix Table 4 into the main text as a first-order robustness check rather than a footnote. In addition, please state explicitly which vintage of population controls each monthly extract carries, and show the primary series with and without the January 2025 control revision.

### M6. The architecture space is itself a selected object, and the selection is under-documented

The paper is candid that six implementations from two families are not six independent measurements — the employment-weighted correlations of 0.981–0.996 within AIOE and the exact identity Xβ = (Xα + Xγ)/2 make that unavoidable. But the paper then reports an intersection–union *p*-value of .045 across the six, which is close to meaningless under that dependence and is in any case pinned by administrative AIOE alone.

More substantively: the admission rule for outside architectures (documented construct, public and hashed source, non-title mapping, full components, distinct cuts, >80% preperiod coverage) is presented as ex-ante and therefore neutral, but the rule's *content* is a researcher choice. Readers will want to know how many published occupation-level AI exposure measures exist, how many pass, and which fail on which criterion.

**Requests.** (a) A census table of candidate architectures with explicit pass/fail and reason. (b) Report the eigenvalue spectrum of the six standardized scores on common support; I expect two components to exceed 95% of variance, and stating that number is more honest than "six implementations." (c) Either drop the IUT or reframe it explicitly as a statement about a dependent set. (d) Add at least one measure from the AI-and-labor-demand literature that uses a different primitive — Acemoglu, Autor, Hazell and Restrepo (2022) construct occupation-level AI exposure from several of these sources and compare them directly; Babina, Fedyk, He and Hodson (2024) and Hampole, Papanikolaou, Schmidt and Seegmiller offer firm- and demand-side alternatives. Their absence is conspicuous.

### M7. Reported intervals for the same coefficient are inconsistent across the paper

The headline −0.1311 appears with at least four different 95% intervals:

| Location | Interval | Reported SE |
|---|---|---|
| Section 5.1 | [−0.2170, −0.0451] | 0.0444 |
| Appendix Table 4 | [−0.2166, −0.0455] | — |
| Appendix Table 8 | [−0.2179, −0.0443] | 0.0442 |
| Appendix Table 9 | [−0.2190, −0.0431] | 0.0443 |
| Appendix Table 10 (min 100) | [−0.2198, −0.0423] | — |

I assume these reflect different common-draw sets constructed for different paired comparisons, which is defensible — but nowhere is it explained, and in a paper whose entire argument is about the reproducibility of constructed quantities, this will read to many readers as an error. Please either report one canonical interval throughout with the paired variants clearly labeled as such, or add a short note stating the convention and why draw sets differ.

### M8. The relationship to Brynjolfsson, Chandar, and Chen is asserted rather than tested

The paper leans on BCC for motivation, then correctly disclaims any ability to speak to their results (different data, margin, crosswalk, estimand). The result is that the comparison generates expectations the paper then refuses to meet.

There is a concrete way to fix this: **implement BCC's own exposure classification inside the CPS design**, report what the CPS says under their measure choice, and then show how that estimate moves across the architecture space. This converts an abstract audit into a direct statement about a specific, widely cited finding — which is what will make an editor and a general readership care. Absent that, I would cut the BCC and Humlum–Vestergaard discussion to a single short paragraph, since the paper's honest position is that it cannot adjudicate between them.

### M9. The January 2023 break is arbitrary given the paper's own event study

ChatGPT was released November 30, 2022; the paper omits December 2022 as a transition month and treats January 2023 onward as post. But adoption diffused over years, and the paper's own event study reports a path that is "neither immediate nor monotone," with a non-monotone era profile (−0.1356, −0.0783, −0.1629). A sharp binary break is a poor match to that.

**Request.** Replace or supplement the binary post indicator with exposure interacted with a time-varying adoption or capability index — the Real-Time Population Survey / Bick–Blandin–Deming generative AI adoption series, or Census BTOS firm AI use by industry, are both public and cover the relevant window. This would also give the paper its cleanest response to the exposure-versus-adoption objection it raises repeatedly but never acts on.

### M10. The F/G reparameterization should be cut or heavily demoted

Section 6 is the weakest part of the manuscript. G = (A − E)/2 is a difference of two constructed indices whose economic interpretation is opaque; its coefficient is positive, and the paper then shows it becomes imprecise when either beta or broad is removed (Appendix Table 15). The exact basis-change result (equation 4, γA = +0.0248, γE = −0.0707) is, as the author says, "an exact change of basis of the same fitted predictor" — i.e. mechanically true and not evidence of anything.

The transparent version of this exercise is already in the paper: enter administrative AIOE and beta jointly, giving +0.0449 and −0.0788. That is interpretable and it makes the point. I would keep the two-score horse race and the D + λS grid, move F/G to the appendix as a completeness exercise, and reclaim the space for M3 and M4.

### M11. The mobility section omits the margin that matters

The switch-only frame contains 108,500 employed-to-employed transitions and explicitly "does not contain entrants from nonemployment." But the mechanism emphasized in the literature the paper is engaging is *hiring* — entry. The mobility results therefore cannot bear on the question a reader most wants answered, and the paper says so only in passing.

Two further points. First, the hard-rematching benchmark comparison is framed against a Monte Carlo SE of 0.0017pp, which makes a 0.96pp gap look enormous, but the relevant uncertainty is sampling uncertainty in the realized 53.28% — please report a cluster-bootstrap SE on the realized conflict share so the comparison is apples-to-apples. Second, the 9.865% immediate-reversal rate implies substantial occupation coding error, which affects the *employment* results too (misclassification into quintiles attenuates the tail contrast) and is currently only discussed in the mobility context. A simulation that imposes misclassification at the observed rate and reports the implied attenuation of the Q5–Q1 coefficient would be valuable and is well within reach.

### M12. The generated-covariate literature is cited but never used

Battaglia et al. (2024), Christensen and Hansen (2026), Duan and Pelger (2026), and Ludwig, Mullainathan and Rambachan (2026) appear in the related-work section, and the paper's justification for not applying them is that no validated true exposure is observed. That is true but incomplete. Please add a short subsection specifying what a validation sample for occupational AI exposure would have to look like — what the labels would be, who would produce them, what sample size the corrections require — so the reader leaves with a concrete research agenda rather than a dead end. This is a natural place for the paper to deliver something forward-looking.

## 4. Secondary comments

1. **Delete the ten-journal search paragraph** (Section 2.3, "A targeted search of the AER, QJE, ..."). Priority claims framed as literature searches read poorly and invite exactly the rebuttal the author anticipates in the following sentence.

2. **Clarify the estimand statement.** Equation (2) with occupation-by-month fixed effects and two age groups is a conditional logit on the young employment share. The paper describes β₅ as "the post-period change in the young-to-older employment-stock ratio" — accurate, but the log-odds-of-young-share formulation is more transparent and would help readers see immediately why occupation-month shocks cancel.

3. **Zero cells.** 13,305 of 50,544 cells have zero young stock (26%), and these are retained (only the 965 both-zero cells drop out). Please confirm the conditional likelihood handles the boundary correctly and report the estimate on the subsample of cells with, say, at least five young respondents, to show the result is not carried by boundary cells.

4. **The route-expansion bridge manufactures pre-period variation.** For the 20.03% of early weighted employment in one-to-many source codes, the young/older ratio is mechanically constant across target components before other sources arrive. This is a real limitation of the pre-period and hence of the event study. The Census-2018-only estimate (−0.1211, 77 months, 457 occupations) removes the bridge entirely and should be promoted into the main text as the paper's cleanest specification rather than presented as a harmonization bound.

5. **"Reversed OECD capability gap"** needs a paragraph on the sign convention. Reversing a capability *gap* is not obviously the same construct as an exposure level, and given that this measure produces the near-zero estimate carrying substantial argumentative weight in Section 5.1, the transformation deserves more than a phrase.

6. **Frey–Osborne** is announced as a retained automation-risk comparator (Section 2.2) but appears only as one column of Appendix Table 5. Either use it in the outcome models or drop the announcement.

7. **Figure 2** mixes rows on identical 363-occupation support with rows on native external support and warns the reader not to read it as a single panel. Split it into two panels; a figure that requires a note telling the reader not to compare its rows is not doing its job.

8. **Figure 3** is six panels of dense monthly series at small scale and is effectively unreadable. The ratio panels carry the message; consider dropping the level panels to the appendix and adding a smoothed series over the raw one.

9. **False precision.** Benchmark conflict at 52.3227%, a critical value of 2.26036, a permutation SD of 0.0268, coefficients to five decimals in Appendix J. Round to a number of digits the design can support — three significant figures nearly everywhere, and two for percentages.

10. **Define "respondent-equivalent" once, early, and prominently.** It appears in Table 1, Table 3, and the minimum-size sensitivities, and the caveat that these are not unique people is repeated but never fully explained in one place.

11. **Notation.** Equation (1) defines Xγ; the text and figures call the same object "broad." Pick one.

12. **Encoding errors.** The appendix contains mojibake where smart quotes should be — notes to Appendix Table 13 ("âĂĲAny conflictâĂİ") and to the paired-contrast paragraph in Appendix D.

13. **Author information.** Affiliation, email, acknowledgments, funding and disclosure remain marked for completion. The disclosure statement in particular will be required.

14. **Pre-registration.** The design-freeze and confirmatory-results commit tags are excellent practice, but economics readers will want to know whether the pre-analysis plan was registered anywhere external and when, and to see it as an appendix. Internal git tags establish ordering relative to the author's own repository, not relative to data access.

## 5. Note to the editor

I want to be clear that my recommendation is not a judgment on the quality of the work. The author has done more careful, more transparent, and more self-critical empirical work than most submissions I see, and the reporting of failed diagnostics is exemplary.

My concern is that the paper currently presents a set of null and near-null comparisons — across architectures, reference groups, and benchmarks — without acknowledging that the design lacks the precision to distinguish those alternatives from one another, and then draws methodological conclusions from that pattern. Comment M1 is the crux: once minimum detectable effects are on the table, most of Section 5's comparative claims will need softer language, and the paper will need a different center of gravity.

I think that center of gravity already exists in the manuscript. The permutation result and the influence concentration together suggest that the widely discussed early-career AI employment pattern, when reconstructed in public CPS data, is largely a broad-occupational-composition pattern anchored by a handful of low-exposure service occupations with well-known non-AI drivers. That is a substantive, timely, falsifiable claim about an active policy debate. If the author is willing to run the SOC2 × age × post specification (M3), the leave-*k*-out and placebo-in-time exercises (M2, M4), and the BCC-measure implementation (M8), and to rebuild the paper around what those show, I would be glad to look at a resubmission.