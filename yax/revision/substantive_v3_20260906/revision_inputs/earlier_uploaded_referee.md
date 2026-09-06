# Referee Report

**Manuscript:** "AI Exposure or Occupational Composition? Constructed Measures and Early-Career Employment"
**Author:** Lily Luo (single-authored; affiliation pending)
**Materials reviewed:** Working paper (24 pp.) and Online Appendix (29 pp.), September 2026 versions

**Recommendation:** Reject in present form, with encouragement to resubmit a substantially restructured manuscript. I would be willing to review a revision.

---

## 1. Summary of the paper

The paper aggregates public IPUMS Basic Monthly CPS microdata (January 2017–July 2026) into occupation × age-group × month employment stocks, defines ages 22–25 as "young" and 26–65 as the comparison group, and estimates a conditional-Poisson (grouped-binomial) model of the change in the young-to-older employment-stock ratio after January 2023 across employment-weighted quintiles of Eloundou et al.'s GPT-4 "beta" exposure score.

Three results are offered. First, the Q5–Q1 contrast is −0.1346 log points (canonical 95% interval [−0.2223, −0.0468]), but falls to −0.0315 once two-digit occupation-family × young × post terms are added, with the paired movement of +0.1031 marginally detected (p = .042). Second, the design is imprecise: the realized occupation-clustered SE of 0.0444 implies MDE80 ≈ 0.124, roughly the size of the headline coefficient, and all seven paired beta-minus-alternative architecture differences include zero. Third, a public implementation of the Brynjolfsson–Chandar–Chen top-two-versus-bottom-three grouping yields −0.0728 in CPS. A supporting measurement contribution documents that a literal SOC-2010 exact-code merge covers 3.33% of computer-and-mathematical employment against 97.7% under a versioned crosswalk, and that the six exposure "measures" are two families with 96.11% of variance in two principal components.

## 2. Overall assessment

Let me start with what is unusually good here, because it is genuinely unusual.

The manuscript is one of the most epistemically disciplined empirical papers I have refereed. The author consistently distinguishes "the design does not detect a difference" from "the constructs are equivalent," reports minimum detectable effects alongside point estimates, refuses to treat a confidence interval containing zero as evidence of invariance, retires her own prior claims (the intersection–union sign calculation, the F/G "consensus/disagreement" decomposition) when they do not survive scrutiny, and documents failed diagnostics rather than suppressing them. The reconciliation of occupation universes (Table 2) and the taxonomy-repair sequence in §3.3 and §6.3 are careful work that most authors would not have done and almost none would have reported. The replication infrastructure is exemplary.

My problem is not with the care. It is that the paper's central claim outruns what the design delivers, and that the identification problem the paper is closest to solving is not the one it actually addresses.

The abstract concludes that "the CPS association is principally a broad-occupation comparison, not an identified effect of detailed AI susceptibility." That conclusion rests on a single marginal test (p = .042), conducted post-outcome, among several dozen reported diagnostics, in a design whose own stated resolution limit is approximately the size of the object being tested. Meanwhile, the more fundamental confound — that the Eloundou beta score is close to a measure of computer intensity, and that 2023–2026 was a period of well-documented white-collar hiring contraction and in-person-services expansion for reasons unrelated to generative AI — is present throughout the paper's own appendix tables but is never confronted as an identification problem in its own right.

A paper that argued the second point head-on, with the same inferential discipline, would be a considerably stronger paper. Right now the SOC2 exercise is a coarse and underpowered proxy for that argument, and the manuscript treats it as the headline.

Below I separate major concerns (which I think must be addressed before the paper is publishable in a general-interest journal) from moderate and minor points.

---

## 3. Major comments

### 3.1 The headline claim is not established at conventional precision

The conditional estimate after SOC2 × young × post is −0.0315 with SE 0.0706 and interval [−0.1676, 0.1046]. That interval contains the baseline point estimate of −0.1346. The data are therefore consistent with *no attenuation at all* as well as with complete attenuation. The paired-difference test (+0.1031, [0.0035, 0.2026], p = .042) is what carries the abstract's conclusion, and it barely clears the conventional threshold.

Three things follow that the paper should address directly:

1. **Report the paired MDE80 for the conditioning comparison.** The manuscript computes paired MDEs for every architecture comparison in Table 4 (ranging 0.0609–0.1689) and uses them to argue those comparisons are unresolved. It does not compute the analogous quantity for the SOC2 comparison, which is the paper's most important paired test. With paired SE 0.0511, MDE80 ≈ 0.143. The observed movement of 0.103 is *below* the design's own stated detection threshold. By the paper's own standard — applied consistently — this comparison is also in the "does not resolve" category. The asymmetry is difficult to defend.
2. **Account for selection.** The paper is admirably explicit that the SOC2 exercise is "post-outcome exploratory." But a p = .042 selected from a large menu of exploratory diagnostics should not then be promoted to the abstract as the paper's decisive finding. Either pre-commit to it (which is no longer possible) or downgrade the claim.
3. **Reframe the conclusion.** I think the defensible statement is: *the CPS design cannot separate a detailed within-family AI gradient from broad occupational composition, because only four of 22 families span both tails and conditioning discards 70% of target information.* That is a real and useful finding about the limits of public data. It is not the same as "the association is principally a broad-occupation comparison," which asserts a decomposition the paper elsewhere correctly disclaims (§5.1, "should not be described as the causal contribution of broad composition"). The abstract and conclusion are currently in tension with §5.1.

### 3.2 The paper does not confront the computer-intensity confound

This is my most substantive concern, and I think it should reorganize the paper.

Appendix Table 2 reports employment-weighted correlations of the beta score with occupational characteristics: **+0.797 with computer use, −0.758 with manual, +0.589 with remotability, +0.478 with wage, +0.425 with education.** The AIOE measures are even more extreme (+0.849 with computer, −0.936 with manual). The Q5–Q1 contrast is therefore close to a contrast between desk-based, credentialed, remote-capable occupations and manual, in-person, lower-wage occupations.

The post-January-2023 window contains several large shocks that load on exactly that margin and have nothing to do with generative AI:

- the 2022–23 technology-sector correction and subsequent white-collar hiring freeze;
- the fastest tightening cycle in four decades, which disproportionately hit interest-rate-sensitive, high-wage professional employment;
- the return-to-office reversal, which is nearly collinear with remotability (ρ = 0.589 with beta);
- continued post-pandemic normalization in leisure, hospitality, and personal services, which are concentrated in Q1;
- shifts in immigrant labor supply, which are concentrated in the same low-exposure occupations.

The paper's only conditioning technology is Webb's software-exposure measure, which the appendix reports correlates 0.7021 with Webb AI. A single control that is itself 70% correlated with an AI construct cannot separate these channels.

The food-service exclusions in §5.3 are a useful start but do not do the job, for two reasons. First, they operate on the extensive margin (drop occupations) rather than conditioning on the underlying characteristic, so they cannot address the gradient within retained occupations. Second, and more importantly, the relevant COVID-recovery variation is *dynamic*: occupations differ in how far below trend they were in 2021–22 and therefore in how much mechanical catch-up growth they display in 2023–26. Dropping SOC35 does not control for that; it removes five or ten occupations from a design in which the top five carry a quarter of the information.

**What I would want to see.** Re-run the main specification with a set of pre-determined occupational characteristics each interacted with young × post: O\*NET computer use, remotability, mean log wage, education requirement, routine-task intensity, and — critically — the occupation's own 2020–2022 employment shortfall relative to its 2017–19 trend. Report the sequence exactly as §6.3 reports the taxonomy layers, with paired differences and paired MDEs. If the beta coefficient survives conditioning on remotability and COVID shortfall, that is a much stronger paper than the one currently written. If it does not, that is a much cleaner negative result than the SOC2 exercise supplies, and it does not depend on a 4-of-22 support problem.

A related and cheap check: report the beta Q5–Q1 coefficient conditioning on industry × young × post. The tech-sector correction is an industry shock; occupations and industries cross-classify, so this is identifiable in CPS in a way the SOC2 exercise is not.

### 3.3 Inference conditions on the CPS cells and the cells are extremely sparse

Appendix Table 9 reports that young cells have a median of **2** respondent equivalents, that 26.32% are zero, and that 69.93% are below five. The inference procedure (§4.2) explicitly "conditions on the observed CPS-weighted cells" and does not propagate the complex-survey design.

With a median cell count of two, the sampling variance of the cell stock is not a second-order concern. It is plausibly the dominant source of variance in the outcome, and it is entirely outside the reported standard errors. I take the unexplained 3.65× gap between the planning SE (0.0122) and the realized SE (0.0444) as circumstantial evidence for exactly this: the planning simulation held the cells fixed and resampled residuals, and the sharp global-sign sensitivity in Appendix K (which also holds cells fixed) closes none of the gap. The author correctly says the sensitivity "rules out this global-sign implementation" without identifying the source. Cell sampling error is the obvious candidate and has not been tested.

**What I would want to see.** At minimum, a two-stage variance that adds within-cell sampling variance to the current model-based component. Better: a household-level (or rotation-group-level) bootstrap of the underlying microdata that rebuilds the cells in each replicate, which is feasible since the author is working from IPUMS microdata rather than published aggregates. If the resulting intervals are materially wider, that changes the paper's conclusions — probably in the direction of strengthening the "public CPS cannot resolve this" message, which is fine.

A second inference concern: the effective number of information-bearing clusters is 43.3, not 468 (Appendix C), with a top-five information share of 24.6%. Rademacher wild-score bootstraps are known to under-cover with few effective clusters and asymmetric influence. Please report at least one alternative — Webb six-point weights, a CR3/jackknife variance, or randomization inference over quintile assignment within SOC2 families — and show the canonical interval is not an artifact of the multiplier choice.

### 3.4 Parallel trends is not tested with adequate power, and Rambachan–Roth is cited but not implemented

The event study reports a preperiod max statistic of 1.502 with common-multiplier p = .929 (Appendix F.1). But Figure 3 shows pointwise pre-period intervals of roughly ±0.2, and the design's MDE is 0.124. A pre-trend of the same magnitude as the estimated post effect would not be detected. The paper says the test "does not establish parallel trends," which is correct, but a reader will take p = .929 as reassurance it does not warrant.

Rambachan and Roth (2023) is cited in §2.3 and then never used. This is the single highest-value addition available to the author at low cost. Report the breakdown value: how large a violation of parallel trends (in relative-magnitude or smoothness terms) would be needed to overturn the −0.1346 estimate, and separately the −0.0315 conditional estimate? Given the confounds in §3.2 above, I expect the breakdown value to be small, and that would be an honest and informative headline number.

The balanced pseudo-break exercise (Appendix D.5) is a weaker substitute: 12 overlapping dates in a 36-month window with a 1/13 empirical tail floor, restricted to a period that contains no comparable macro shock. It shows the estimator does not mechanically produce −0.13, which is worth knowing, but it cannot speak to differential trends in 2020–2022.

### 3.5 The bridge to Brynjolfsson–Chandar–Chen is not informative in its current form

Section 6.2 implements BCC's public top-two-versus-bottom-three grouping in the CPS model and obtains −0.0728, "roughly half the corrected Q5–Q1 log-point magnitude." The paper is careful that this is not a replication. But it is not clear what the reader is supposed to learn.

BCC's outcome is firm-level headcount from ADP payroll records, with firm-time controls, and their emphasis is that the effect operates through *hiring*. This paper's outcome is a CPS-weighted employment *stock* ratio. Stocks are the integral of flows: if entry-margin hiring falls in exposed occupations, the stock response is attenuated and lagged relative to the hiring response, by a factor determined by turnover rates in the affected age group. A smaller CPS stock coefficient is therefore entirely consistent with BCC's finding and cannot be read as evidence for or against it.

**Suggestion.** Make the comparison quantitative. Given CPS-measurable separation and accession rates for 22–25 year olds by exposure quintile, what stock response over 2023m1–2026m7 does BCC's reported hiring decline imply? If the implied stock response is, say, −0.05 to −0.09, then −0.0728 is a successful out-of-sample check rather than a discrepancy, and the paper's framing changes materially. If the implied response is −0.25, that is a real tension worth reporting. As written, the reader gets two numbers of different units side by side.

Relatedly: does BCC condition on broad occupation or on firm effects that absorb occupational composition? If they do, then the SOC2 result in this paper does not have the implication for their design that §1 and §8 seem to suggest.

### 3.6 The flow evidence belongs in the main text

Appendix G reports employment exit of +0.1195 (SE 0.0944), occupational outflow of +0.0107, and entry destination of −0.0888 (SE 0.0976), all with intervals containing zero.

These are the results that speak to mechanism, which is the question the reader most wants answered, and the entry-destination and exit signs are directionally consistent with an entry-margin story. The paper buries them on the grounds that "their intervals are wide." But every estimate in this paper has wide intervals, and the author has built an entire apparatus (paired MDEs, explicit non-equivalence language) precisely for reporting imprecise results honestly. Apply it here and move the table to the main text.

The precision may also be improvable. Exact adjacent-month CPSIDV links discard a great deal of usable variation; consider 12-month-apart (MIS 1→5, 2→6, etc.) links, which double the linkable sample and are standard in the CPS flows literature, and consider quarterly pooling as is already done for the stock model.

While in CPS, I would also want to see the corroborating margins that are free in these data and currently absent: hours, weekly earnings, unemployment incidence and duration, and labor force participation for the same occupation-age-month cells. A displacement story predicts a coherent pattern across these; a composition story does not necessarily.

### 3.7 The λ pattern deserves engagement, not just a disclaimer

Appendix I reports Q5–Q1 estimates along D + λS: **−0.1013 at λ = 0, −0.1256 at 0.25, −0.1297 at 0.5, −0.1432 at 0.75, −0.1482 at 1.**

The λ = 0 measure (alpha) is direct LLM task acceleration — the construct closest to what could plausibly have bitten in 2023–2026. λ = 1 adds tasks that require complementary software that may not yet exist. The association gets monotonically *stronger* as the measure moves away from currently realizable capability and toward the speculative complement. Appendix Table 2 explains why: alpha correlates 0.304 with computer use, while broad correlates 0.833.

The manuscript notes in §2.1 that categorical coefficients need not be monotone in λ, which is true but is a disclaimer rather than an argument. This pattern is a substantive piece of evidence, and it points the same direction as §3.2: the coefficient grows with the measure's loading on generic computer-intensity, not with its loading on realizable AI capability. I would put this in the main text as a first-order diagnostic rather than in Appendix I.

### 3.8 The measurement contribution needs attribution and scaling

The crosswalk finding — 3.33% versus 97.7% coverage of computer-and-mathematical employment — is the most portable result in the paper and the one most likely to be cited. But two things are unclear:

- **Whose implementation is being corrected?** If published work merges SOC-2010 AIOE codes into post-2018 Census occupation codes without a versioned route, say so explicitly, cite it, and quantify what it implies for the published estimates. That would be a real service. If instead this is a repair of the author's own earlier draft, it should be presented as implementation guidance, not as a finding about the literature. As written, §3.3 and §6.3 read ambiguously, and the ambiguity works in the paper's favor in a way that should be resolved.
- **What is the scale of the continuous coefficients?** The sequence −0.01885 → −0.01920 → −0.03156 → −0.02940 is central to the argument that "most movement comes from changing who enters, not correcting scores." But these are continuous-exposure coefficients whose units are never stated (per standard deviation? per unit of the raw share?), and they are never related to the quintile estimates that carry the rest of the paper. A reader cannot tell whether the 0.012 movement is large or trivial.

Separately: Table 1 is a useful checklist, and I would keep it. But the two "invariance results" in §2.1 — that positive affine transformations preserve ranks and fixed-weight quantile membership, and that nonsingular reparameterizations preserve fitted values — are textbook facts. Presenting them as results that "discipline the exercise" invites the reaction that the methodological contribution is thinner than advertised. State them in a footnote and let the taxonomy stand on its practical usefulness.

### 3.9 Scope: the paper is doing too much and reads as a revision log

At 24 + 29 pages with roughly 25 tables and figures, the manuscript attempts a labor result, a methods taxonomy, a measurement audit, a precision audit, a mobility analysis, and a reproducibility protocol. The result is that no single contribution is developed to the standard a general-interest journal requires.

I would cut, without loss:

- **Appendix H (mobility disagreement and the rematching benchmark)** entirely. Nearly two pages of machinery — Hamilton allocation, sealed no-self permutation, 399 exponential multipliers, omitted-support bounds — yields a 0.96 percentage-point gap between realized and benchmark disagreement rates with no stated implication for any coefficient in the paper. The author's own conclusion is that "the defensible comparison is therefore 'relative to the specified broad-assortative no-self benchmark,'" which is a statement about the benchmark, not about AI or employment.
- **Appendix I (F/G rotation)** entirely. The paper states repeatedly and correctly that this is an identity supplying no evidence. Keeping it as "a complete record" is what a replication package is for. Retain only the D and S primitive model, which is interpretable, and the λ series, which should move to the main text per §3.7.
- **Appendix K's failed diagnostics** and **Appendix L's commit hashes, repository paths, and design chronology.** These belong in the replication README. Table 24 in particular (a manifest of CSV file paths) has no place in a journal article.
- **The dual frozen/corrected reporting throughout.** The two calendars differ by 0.0035 log points. Report the corrected calendar and note the frozen one once.

The abstract currently contains roughly a dozen numerical quantities. Three is the right number.

I also recommend dropping the pre-registration vocabulary — "frozen," "confirmatory," "design-freeze tag," "post-outcome exploratory" repeated on nearly every table. The author concedes in Appendix L that the commit hashes "are not represented as an externally registered pre-analysis plan." Without a registry, the vocabulary conveys a warrant the design does not have, and its repetition makes the paper hard to read. State the chronology once in a data section and use ordinary language thereafter.

---

## 4. Moderate comments

**4.1 Influence and effective support.** Effective information is 43.3 occupations with a top-five share of 24.6%; deleting one occupation (fast food and counter workers) moves the headline by 15.7% of its magnitude; deleting five moves it to −0.1011 while deleting ten moves it to −0.1522. The author reports all of this, which is to her credit. But the main text should say plainly which handful of occupations drives the result and show the reader their employment paths. Consider reporting an equal-occupation-weighted companion estimator so readers can see how much the result depends on the information weighting.

**4.2 The age comparison and cohort composition.** The composition of 22–25 year-olds differs sharply across exposure quintiles by education, and the 2020–2023 period saw large disruptions to college enrollment, completion timing, and entry into the labor market. A differential change in the *supply* of young college graduates would move the Q5 young/older ratio without any AI channel. Please report education-stratified estimates (BA+ versus non-BA within each quintile) or, at minimum, control for occupation-specific young-share trends interacted with post. The 22–25 versus 26–35 comparison (−0.1307) is helpful but does not address this.

**4.3 The older denominator.** With the comparison group spanning ages 26–65, movements in the ratio can originate on either side, and Figure 3 shows both matter. If AI exposure affects older workers at all — in either direction — the estimand is a difference of two treated groups, not a treatment-control contrast. Please state what is being assumed about the 26–65 group and show the young and older paths for Q5 and Q1 separately in the main text rather than in a six-panel figure.

**4.4 Break date.** ChatGPT was released in November 2022, GPT-4 in March 2023, and meaningful enterprise deployment mostly later. January 2023 is defensible but not obvious. Please show sensitivity to break dates across 2022m11–2023m6, and state whether the choice was made before the outcome was examined.

**4.5 Endpoint sensitivity.** Appendix Table 16 shows the coefficient is −0.1135 through December 2024 and −0.1346 through July 2026, with 2025–26 at −0.1664 and 2023–24 at −0.1108. A material share of the association is generated in 2025–26. Given that this is precisely the period of the January 2025 population-control revision, the discussion in §7.2 should be foregrounded rather than presented as a robustness note. The author's argument that the revision does not "mechanically account for the full postperiod pattern" is reasonable; the point is that a reader should be told up front where in time the result lives.

**4.6 Split-route age allocation.** Applying official conversion proportions equally to young and older source records mechanically preserves the source age ratio, which is the assumption the exercise most needs to relax. The predeclared tilt covers only 6.88% of early stock. Consider estimating age-specific route shares from the 2019–2020 CPS overlap or from ACS, which codes both vintages in overlapping years. This would convert an acknowledged unknown into a measured one.

**4.7 Occupational coding error.** CPS occupation is self-reported and independently recoded, with an immediate-reversal rate of roughly 10% among observable switches (Appendix G, H.3). The author declines to construct an attenuation curve because differential error could attenuate, amplify, or reassign. That is correct in general, but a bound under a simple symmetric-misclassification assumption would tell the reader whether classical attenuation alone could plausibly account for a coefficient of this size, and it costs little.

**4.8 The stable-tails estimate.** The −0.2120 result rests on 64 occupations with effective information of 15.0 and a top-five share of 46.7%. This is too thin to appear in a main-text table (Table 3) alongside the baseline, even with a caveat. Either drop it or present it as a figure annotation.

**4.9 "Respondent equivalents."** After fractional route expansion, these are not respondents. The term appears throughout, including in a main-text table row, and is defined only glancingly in §7.2. Define it precisely at first use and consider renaming.

---

## 5. Minor points, internal inconsistencies, and specifics

1. **Conflicting intervals for the same estimate.** Appendix Table 16 reports the corrected baseline interval as [−0.2226, −0.0465]. Main-text Table 3, Appendix Table 5, and Appendix Table 8 all report [−0.2223, −0.0468]. The paper explicitly claims in §4.2 and Appendix D.2 to have resolved the earlier problem of multiple intervals attached to one coefficient by declaring a canonical interval. This one needs fixing, and it is the kind of discrepancy that undermines the credibility the rest of the reporting protocol is designed to build.
2. **Unsourced range in the abstract.** The abstract states that reapplying the BCC grouping produces coefficients "between approximately −0.088 and −0.008 on common support." Section 6.2 reports a *native-support* range of −0.0817 (Eloundou broad) to −0.0096 (OECD), and gives common-support values only for beta (−0.0810) and OECD (−0.0076). The figure −0.088 appears nowhere in either document. Please reconcile, and state whether the range is native or common support.
3. **Calendar mixing in the abstract.** The abstract quotes SE 0.0444 and MDE80 0.1244, which are frozen-calendar (108-month) values, while identifying −0.1346 (corrected, 113-month) as the baseline. The corrected values are 0.0450 and 0.1260. Use one calendar consistently.
4. **§6.2, "The unconditioned result is −0.0728 as well."** Unconditioned on what — the Webb software interaction, the intermediate quintile terms, or something else? As written this sentence is uninterpretable.
5. **"Info. share" (Table 3) and "effective information count" (Appendix C, Table 11) are load-bearing but never defined.** Give the formulas in the main text. I infer the latter is an inverse-Herfindahl of information weights, but the reader should not have to infer.
6. **Revision-history language persists.** §3.2 refers to "two counts that appeared to be a five-occupation discrepancy"; §4.2 refers to "previously displayed variants"; §6.4 and §1 refer to "the prior draft" and "the earlier manuscript." Appendix L states the policy of removing referee-round framing, but the main text has not fully complied. A reader who has not seen the previous version cannot parse these.
7. **Record count.** 9,843,021 records over 114 months implies roughly 86,000 records per month. Please clarify whether this is pre- or post-route-expansion, and whether route expansion generates fractional records that are being counted as rows.
8. **October 2025.** The shutdown gap is handled honestly. Please add a check that dropping September and November 2025 as well does not move the post-2024 estimates, since the gap sits in the period doing the most work.
9. **BCC version.** The reference lists a 2026 revision of a 2025 original. Please state which version's classification and results are being compared throughout, since the exposure grouping may differ across versions.
10. **Figures.** Figure 3 has six panels; the ratio panels carry the message and the rest crowd them. Consider two panels plus an appendix figure. In Figure 4 the legend overlaps the OECD row. Figure 2 is visually a robustness ladder even though the note correctly says the rows do not estimate a common parameter; consider separating the conditioning rows from the support rows into distinct panels.
11. **Front matter.** Affiliation, email, and acknowledgments remain to be completed. The JEL codes (J23, J24, O33, C81) are appropriate.

---

## 6. What would change my assessment

I want to be constructive about the path forward, because I think there is a publishable paper here and possibly two.

The single most valuable additions, in order:

1. **A Rambachan–Roth breakdown analysis** on the primary estimate. This is cited already and is the natural formalization of what the paper is trying to say about the fragility of the association.
2. **A variance estimator that includes CPS cell sampling error**, given median young-cell counts of two. This may widen the intervals substantially; if so, that is the paper's real finding.
3. **The extended conditioning set of §3.2** — remotability, computer use, wage, education, and pre-period COVID shortfall, each × young × post — reported as a layered sequence with paired differences and paired MDEs in exactly the format of Table 4. This directly addresses the confound the paper's own correlation table exposes, and it does not suffer the 4-of-22 support collapse that cripples the SOC2 exercise.
4. **The flow margins and corroborating outcomes** (hours, earnings, unemployment, LFP) promoted from appendix to main text.
5. **A manuscript roughly 40% shorter** with one clear claim, the mobility and rotation material removed, and a three-number abstract.

If the author would rather split the project, the measurement paper — versioned crosswalks, the 3.33%-versus-97.7% coverage failure, the two-families-not-six-measures result, and the Table 1 taxonomy — is close to self-contained and would make a strong short piece in a methods or applied-econometrics outlet, particularly if the coverage failure can be documented in published work with quantified consequences.

## 7. Recommendation

I cannot recommend publication in present form. The paper's central conclusion depends on a marginal, post-outcome test in a design whose stated resolution limit exceeds the movement being tested, and the identification problem that most threatens the finding — that the exposure measure is largely a computer-intensity index over a period of unusual white-collar cyclicality — is documented in the appendix but never addressed.

At the same time, this is careful, honest work by an author who is clearly willing to retire her own claims when the evidence does not support them, which is rarer than it should be. I would review a revision that reorganizes around the confound in §3.2, fixes the inference in §3.3, implements the sensitivity analysis in §3.4, and cuts roughly half the current material. Should the editor conclude that the resulting paper is better suited to a strong field outlet than to this journal, I would not disagree, but I would not want the project abandoned.