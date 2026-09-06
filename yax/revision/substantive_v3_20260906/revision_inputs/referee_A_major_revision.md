# Referee Report

**Manuscript:** "AI Exposure or Occupational Composition? Young-Worker Employment Comparisons in the CPS"

**Author:** Lily Luo (single-blind: author identified on title page)

**Recommendation:** Major revision

---

## 1. Summary of the paper

The paper reconstructs, in public IPUMS Basic Monthly CPS data for January 2017–July 2026, the young-worker employment pattern that Brynjolfsson, Chandar, and Chen (2026) document in ADP payroll records. It compares employment stocks for ages 22–25 against ages 26–65 within occupation, classifies occupations by the Eloundou et al. (2024) GPT-4 beta score, and asks which occupational contrasts generate the association.

The headline sequence is: a pooled highest-versus-lowest exposure-quintile coefficient of −0.132 log points; a fall to −0.022 once each SOC two-digit family receives its own young-relative monthly path, with a detected paired movement of 0.110; a direct within-family tail benchmark resting on 29 occupations and 5.03 percent of preperiod stock with an interval spanning [−0.169, 0.468]; a computer-use control that makes the coefficient more negative rather than attenuating it; rejection of joint preperiod equality in unrestricted quarterly dynamics; and a set of linked-CPS flow margins whose intervals all contain zero. The stated conclusion is that the public-CPS pattern is a descriptive comparison across broad occupational structure rather than an identified causal effect.

## 2. Overall assessment

The empirical craftsmanship here is well above the norm. The separation of construct, measurement, harmonization, support, representation, and estimand is genuinely useful discipline; the decision to hold support fixed while repairing scores, and then vary support separately (Appendix Table 4), is exactly right and is a mistake I see routinely in this literature. The information and concentration diagnostics in Appendix Table 6 are the most original material in the paper. The failure registry and the refusal to convert a nonconvergent specification into a different estimator are commendable.

My reservations are about what the paper *claims*, not how it computes. Three problems recur.

First, the contribution is framed almost entirely negatively. The abstract and conclusion consist largely of statements about what cannot be inferred. A reader finishing the paper knows that the public CPS is uninformative about the AI hypothesis but does not come away with a positive, portable result.

Second, the paper undercuts its own headline decomposition. Section 7.1 rejects preperiod equality in *both* the pooled and family-conditioned specifications. If neither specification survives its own parallel-evolution diagnostic, the interest in decomposing −0.132 into −0.022 plus a "movement" is unclear. The paper needs to say why a decomposition of an unidentified quantity is worth reporting, and to do so early.

Third, several of the reported "detections" are fragile in ways the paper's own diagnostics reveal but do not act on. The stress simulation and the endpoint sensitivity are the sharpest examples (points 4 and 8 below).

I think the paper is publishable after substantial restructuring. Whether it is publishable *here* depends on whether the author can convert the audit into a positive claim. If not, a field outlet oriented toward measurement and specification sensitivity would be a better home.

---

## 3. Major comments

### 3.1 The family-conditioning result is close to mechanical, and the paper leads with the wrong number

Appendix Table 5 shows that only 4 of 22 SOC two-digit families span both exposure tails; many families occupy two or three adjacent quintiles. Exposure is therefore largely a *between-family* characteristic. Conditioning on family × young × month removes most of the treatment variation by construction, and Table 6 quantifies exactly this: 29.7 percent of nuisance-adjusted target information survives.

Given that, the movement from −0.132 to −0.022 tells the reader something Table 5 has already told them. The informative object is not the point estimate but the *support and information geometry*: 6.2 effective occupations in the direct-tail comparison, a top-five information share of 77.8 percent, an MDE80 of 0.458 log points.

I would restructure so that Tables 5 and 6 appear in the main text and carry the argument, with the coefficient movement demoted to a corollary. As written, the paper reports a near-zero conditioned coefficient prominently enough that casual readers will cite it as evidence against an AI effect, which the paper itself (correctly) says it is not.

Relatedly, the paper cannot distinguish "AI operates at the level of broad occupational families" from "family-level confounders drive the pooled estimate." These are observationally equivalent under the conditioning used. This should be stated in one sentence in the introduction, not left for the reader to assemble.

### 3.2 The preperiod test is likely uninformative because the preperiod contains the pandemic

The joint test that all 23 preperiod quarterly coefficients equal zero is rejected at p = .015 (pooled) and p = .005 (conditioned). But the preperiod spans 2017Q1–2022Q3 and includes 2020Q2. Rejecting joint equality across a window containing the largest labor-market disruption in the sample is close to guaranteed and does not discriminate between specifications.

Requests:

- Report the joint test on 2017Q1–2019Q4 only, and separately on 2021Q1–2022Q3 (post-reopening).
- Report the test excluding 2020Q2–2020Q4.
- Report which individual quarters drive rejection.

If rejection is confined to the pandemic quarters, the honest conclusion is that the CPS cannot evaluate parallel evolution over this window at all, which is a different and arguably stronger statement than "parallel evolution is rejected."

The same issue contaminates the HonestDiD exercise. The relative-magnitude restriction anchors on the largest preperiod violation, which will be a pandemic quarter. That is why the M̄ = 0.5 intervals in Appendix Table 12 are [−1.023, 0.789] and [−2.222, 1.884]. Those rows are not informative and should either be dropped or accompanied by a version that anchors on non-pandemic preperiod quarters.

### 3.3 The numerator/denominator decomposition is missing

The outcome is a within-occupation young-to-older stock ratio. Figure 1 Panel B shows Q5 older stock rising after January 2023 while Q1 older stock is flat or declining. A substantial share of the ratio movement may therefore originate in the *denominator*, which would be a different economic story from the one the motivating literature tells about entry-level work.

The paper acknowledges this ("the low-exposure reference trajectory is part of the result") but never quantifies it. Please report separate young and older log-stock regressions on the same exposure contrast, with a common normalization, so the reader can see how the −0.132 splits. If the older series carries half of it, that belongs in the abstract.

### 3.4 The stress simulation deserves a serious response, not a caveat

Appendix E.4 reports that under the calibrated adverse design, the nominal occupation-cluster interval rejects a true zero in 26.7 percent of replications for the pooled model. The paper labels this "a stress design, not the CPS sampling law" and proceeds. That is too quick. The pooled interval is [−0.221, −0.044]; it excludes zero, but not by a wide margin. Size distortion of anything approaching the simulated magnitude would eliminate the paper's one clearly detected primary result.

Please report:

- Size under a design calibrated to the *estimated* occupation-level dependence rather than an adversarial one.
- Which feature of the adverse design produces the distortion (cell sparsity, family shocks, influence concentration), and whether that feature is present in the data at comparable magnitude.
- A size-corrected or bootstrap-calibrated interval for the pooled coefficient, if one can be constructed.

If the answer is that the distortion is not a feature of the actual data, say so explicitly. If it is, the paper's headline should change.

### 3.5 The computer-use suppressor result is over-interpreted

The preperiod-weighted correlation between beta and O\*NET computer use is 0.794 on the 408-occupation support, with a target VIF-like ratio of 3.45 (Appendix Table 10). Under near-collinearity, coefficient inflation from −0.107 to −0.212 is close to what variance inflation alone would produce, and the residual variation being used is thin.

The paper draws a reasonable narrow conclusion (a single control does not necessarily attenuate) but presents it prominently enough to read as a substantive finding about computerization. Two requests:

- Report the coefficient on computer use × young × post itself. It appears nowhere, and without it the suppression is uninterpretable.
- Add a formal collinearity discussion and, ideally, a bounding exercise. Oster (2019) or Diegert–Masten–Poirier sensitivity to an unobserved family-level confounder would be more informative than another horse race, and the paper already cites Rambachan–Roth for trends without exploiting the analogous logic for confounders.

### 3.6 Enrollment and cohort composition are unaddressed

Employment stocks for ages 22–25 depend on college enrollment, graduation timing, and cohort size, all of which moved sharply between 2020 and 2023. If enrollment declines or delayed graduation shifted the occupational entry mix differentially across exposure groups, the observed pattern follows with no AI content. This is a first-order alternative and appears nowhere in the paper.

At minimum: report the exposure contrast restricted to non-enrolled respondents, and show the young-group education composition by exposure quintile over time. The CPS supports both.

### 3.7 Detection versus nondetection is applied inconsistently to the paper's own endpoint results

Appendix Table 13: the December 2024 endpoint gives a paired movement of 0.0211 with interval [−0.0073, 0.0495]; the September 2025 endpoint gives 0.0225 with interval [0.0053, 0.0397]. The point estimates are effectively identical; only the standard error differs. Yet the main text reports the first as "the design does not detect a change" and the second as detected. This is exactly the inference the paper warns readers against elsewhere. Please rewrite that passage to compare magnitudes rather than detection status.

More substantively: January 2025 and January 2026 population controls, the modified November 2025 collection, and the October 2025 gap all fall in the post period. Appendix Table 14 shows the official-weight and respondent-equivalent era comparisons diverge, with the latter detecting a 2025–26 shift that the former does not. I would make the December 2024 endpoint the primary specification and present the July 2026 window as an extension. The through-2024 coefficient is −0.111 [−0.201, −0.021], so this costs the paper very little and removes a real vulnerability.

### 3.8 The crosswalk bounds should be carried through to the coefficient

Appendix B.3 reports accounting bounds on the 2017–2019 young-to-older ratio of [0.1031, 0.1480] in Q1 and [0.0790, 0.1175] in Q5. These overlap substantially, which means the preperiod level of the key ratio is not pinned down by the data under age-agnostic routing. The paper says these are not bounds on the nonlinear coefficient and stops there.

Please compute bounds, or at least a worst-case odds-tilt sensitivity, on the *rebuilt-contract* coefficient. The odds-tilt exercise currently reported is for the superseded historical contract only. Since the paper's central methodological claim is that mapping determines what a coefficient measures, this is the natural place to demonstrate it quantitatively.

### 3.9 Differential link attrition in the flow analysis is a bias problem, not only a precision problem

The twelve-month link rate is 50.98 percent for young origins versus 70.55 percent for older origins. Workers who move address, change jobs, or exit employment are differentially unlinked, and those are precisely the outcomes under study. The paper treats the flow nulls as low-resolution nondetections, which is right as far as it goes, but the differential attrition could also generate attenuation toward zero in a systematic direction.

Please add a sign discussion and, if feasible, a bounding exercise or a comparison of linked-sample and full-sample characteristics by exposure group.

### 3.10 The paper avoids the comparison that matters most

BCC report public CPS and ACS evidence alongside their ADP results. The paper repeatedly and correctly disclaims any attempt to replicate the ADP analysis, but it never states whether *BCC's own public-data evidence* survives family conditioning. That comparison is feasible and is the actual scientific stake. As written, the paper audits a construct largely of its own making and gestures at BCC.

Relatedly, the Appendix H.1 bridge exercise (pooled −0.072, conditioned −0.017) is arguably the most policy-relevant material in the paper and receives one paragraph. Consider promoting it.

### 3.11 Two constructive suggestions on data

- **ACS.** With 26.25 percent of young cells containing zero respondent-equivalent records and 69.83 percent containing fewer than five, sparsity is the binding constraint on nearly every result. The ACS would materially improve the young-cell problem at annual frequency. The paper never explains why it is not used.
- **Adoption measures.** The paper concludes that causal work requires observed adoption. Publicly available adoption data now exist: the BLS Business Trends and Outlook Survey reports AI use by industry and state from 2023 onward, and Bick, Blandin, and Deming provide survey-based generative-AI use rates by occupation. An exposure × realized-adoption interaction would move the paper from "we cannot identify this" toward "here is the first step." Even a null would be more informative than the current characteristic horse races.

---

## 4. Minor comments

1. **Numerical inconsistency.** Main text Table 1 reports 6,188,956 route-expanded rows; Appendix A.1 states the analysis "creates 36,188,956 route-expanded descendants." Please verify and reconcile.
2. **"Chapter."** The conclusion reads "This chapter instead establishes…". Presumably a dissertation remnant.
3. The stratified industry baseline (−0.138) differs from the pooled baseline (−0.132) because the cell objective changes. This is explained in the Table 3 notes but will confuse readers who scan tables. Consider a distinct row label such as "industry-cell baseline (different objective)."
4. Appendix Figure 1 is not readable. The arts/media panel reaches 800 on an index scale because of tiny cells, and the series are visually indistinguishable. Either smooth (rolling three-month means), plot on a log scale, or drop the panel and report the underlying series in the archive.
5. The manuscript reports the beta–computer-use correlation as 0.794 (408 occupations) and the appendix as 0.807 (341 occupations). Consistent, but state the support in the main text so it does not read as a discrepancy.
6. The MDE80 statistics are introduced with a clear disclaimer and then used in roughly a dozen places. Consider collecting them in one diagnostics table rather than threading them through the text, where they invite exactly the misreading the paper warns against.
7. Prose density. Nearly every claim is followed by a disclaimer in the same sentence. The result is accurate and hard to read. I suggest a short "What the paper establishes / what it does not" subsection at the end of the introduction, with the per-sentence hedging correspondingly reduced.
8. Missing references worth engaging: Bick, Blandin, and Deming on generative-AI adoption; Hampole, Papanikolaou, Schmidt, and Seegmiller on firm AI investment and skill demand; Deming and Noray on technological change and early-career trajectories, which speaks directly to the entry-margin interpretation; Autor and Thompson on expertise and task displacement.
9. The abstract states coefficient values before establishing that the estimand is a young-to-older stock ratio rather than an employment probability. One clause fixes this.
10. Appendix I.3 is excellent and should be signposted from the main-text conclusion.

---

## 5. Summary of required revisions

**Essential:**

- Restructure around support and information (Tables 5–6), not the coefficient movement.
- Report the preperiod joint test excluding pandemic quarters; revise or drop the relative-magnitude HonestDiD rows.
- Decompose the ratio into young and older components.
- Address the 26.7 percent simulated size distortion substantively.
- Move the primary endpoint to December 2024.
- Report the computer-use coefficient; add a formal collinearity or confounder-sensitivity treatment.
- Address enrollment and cohort composition.

**Strongly recommended:**

- Carry crosswalk bounds through to the coefficient.
- State whether BCC's public-data evidence survives family conditioning.
- Add an ACS or adoption-measure extension.
- Fix the inconsistent detection language in the endpoint discussion.

I would be glad to look at a revision. The measurement work here is careful enough to be worth publishing; the paper needs to decide what it is claiming and then defend that claim rather than defending against every possible misreading at once.