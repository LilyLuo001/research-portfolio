# YAX Revision Memo v2

## Major changes

### Contribution hierarchy

The introduction now makes three contributions rather than four:

1. **Different empirical X.** Test A establishes that prominent exposure measures encode different technological and occupational content without claiming that no latent AI factor can exist.
2. **Different identifying designs.** Test B is the paper's central methodological contribution. Mapping and common support are integrated into this contribution because they determine which occupations enter the estimand and which residual comparisons remain.
3. **What survives measurement divergence.** The common-design application is framed as sign robustness without magnitude invariance. The paired beta-alpha result is explicitly non-equivalence evidence.

The title is now *What Is AI Exposure? Measurement Architecture, Identifying Variation, and Early-Career Employment*.

### Abstract

The abstract was reduced to 170 words. It retains only three quantitative anchors: effective identifying support of 11.9–84.5 occupations, headline magnitudes of approximately 9%–19%, and a primary estimate of approximately 12%. The intellectual surprise is now explicit: **measurement disagreement need not imply outcome fragility**.

### Equations

Section 4 now distinguishes two parameters that the first draft risked conflating:

- the continuous-score coefficient used in per-SD, mapping, and remote-work analyses; and
- the headline quintile specification, which includes separate Q2–Q5 interactions with Q1 omitted.

The manuscript states that the primary -0.131 estimate is the Q5 coefficient relative to Q1, not the continuous beta coefficient near -0.038.

### Effective-support derivation

Section 6 now reproduces the implemented pre-outcome diagnostic exactly. AI exposure is projected on the named computerization measure with pre-period employment weights. Each occupation's residual-variation share is

\[
s_o=\frac{w_o\widetilde X_o^2}{\sum_j w_j\widetilde X_j^2},
\]

and the effective count is

\[
N_{\mathrm{eff}}=\frac{1}{\sum_o s_o^2}.
\]

The text distinguishes this object from regression leverage, an influence-function estimate, and an outcome-based diagnostic.

### Sign-robustness explanation

The revision uses the already-produced rank-overlap artifacts to explain how construct divergence can coexist with sign robustness. Within-family extreme rankings overlap substantially. Alpha and beta have moderate Q5 overlap and correlated weighted residuals. Cross-family Q5 overlap is much weaker, especially between AIOE and alpha. The conclusion is deliberately mixed: shared tails can help within families, while cross-family sign robustness remains nontrivial.

Table 3B now presents all 15 stored pairwise weighted-residual-correlation and Q1/Q5-overlap diagnostics. This is a presentation of existing confirmatory measurement evidence, not a new calculation.

### Computerization framing

The computerization section is now organized around the proposition:

> The empirical object “AI exposure net of prior computerization” is not defined until the comparison technology is itself defined.

The more-than-twofold beta magnitude range is treated as a limitation on invariant causal-sounding interpretation, not a specification from which one preferred estimate should be selected.

### Literature compression

The main literature discussion is organized around three nearest-neighbor groups:

- measurement instability;
- construct and comparative-exposure research;
- early-career labor-market evidence.

The inventory of emerging measures was reduced to one short boundary paragraph. The text states confidently that score comparison, harmonization, and young-worker evidence each have predecessors; YAX's contribution is their integration with effective identifying support and same-design inference.

### Terminology cleanup

Repeated “frozen” language was removed from the journal-facing prose. “Pre-specified,” “pre-outcome,” and “confirmatory” now carry the substantive discussion. Repository tags and the word “frozen” remain only where the research-integrity protocol itself is relevant or in immutable filenames.

### Conclusion and general relevance

The conclusion now leads with the broader measurement lesson for constructed treatments. It notes relevance to automation, trade, routine-task, climate-risk, technology, and policy-intensity indices without claiming universal external validity. Numerical repetition is reduced.

## No empirical changes

**No new empirical analysis was executed and no frozen result was changed.**

The revision only reformats and interprets existing artifacts. The new overlap table copies all 15 stored rows from `TEST_B_MEASURE_OVERLAP.csv`. A joint pre-trend test was not present in the confirmatory archive and was not created.

## Remaining manuscript vulnerabilities

1. **Observational identification.** The DDD does not isolate an exogenous AI-adoption or capability shock, so causal attribution remains limited.
2. **Stock interpretation.** The outcome cannot separate entry, employment exit, and occupational switching.
3. **Consequence divergence.** The paired beta-alpha interval includes zero and economically meaningful differences; the paper cannot claim either divergence or equivalence in magnitude.
4. **Combinatorial novelty.** Each component has predecessors, so demanding referees may view the integrated chain as a sophisticated audit rather than a sufficiently important new economic result.
5. **Comparison-technology sensitivity.** The computerization result strengthens the measurement argument but also shows that the headline magnitude is not invariant to the conditioning margin.
