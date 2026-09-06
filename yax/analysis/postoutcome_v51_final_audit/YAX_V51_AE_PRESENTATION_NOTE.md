# YAX V5.1 A/E presentation note

## Same model, clearer basis

The A/E presentation is not independent evidence. It is an exact change of basis for the already-estimated exploratory two-dimensional F/G model.

Before model-support standardization,

\[
F=(A+E)/2,\qquad G=(A-E)/2.
\]

The executed model standardized F and G separately. With frozen model-support scales

| Component | Weighted SD |
|---|---:|
| AIOE centroid A | 0.998654 |
| Eloundou centroid E | 0.866646 |
| Consensus F | 0.877736 |
| Disagreement G | 0.322137 |

the exact coefficient map is

\[
b_A=\frac12\left(\frac{b_F}{s_F}+\frac{b_G}{s_G}\right),\qquad
b_E=\frac12\left(\frac{b_F}{s_F}-\frac{b_G}{s_G}\right).
\]

Multiplying the original-unit coefficients by `s_A` and `s_E` gives:

| Family basis | Coefficient per weighted SD | Covariance-transformed normal 95% interval |
|---|---:|---:|
| AIOE centroid | +0.02493 | [-0.01492, 0.06477] |
| Eloundou centroid | -0.06148 | [-0.10836, -0.01460] |

The transformed fitted contribution reproduces the original F/G contribution across all 444 occupations to maximum absolute error `2.78e-17`. No A+E model was estimated.

## Inference labels

The AIOE-minus-Eloundou original-unit coefficient contrast is exactly

\[
b_A-b_E=b_G/s_G.
\]

It is therefore a monotone rescaling of the existing G coefficient and exactly inherits G's wild-score inference:

- A-minus-E contrast: `+0.09590`;
- transformed existing-G wild-score 95% interval: `[0.00559, 0.18621]`;
- wild-score `p=.040`.

The individual A and E coefficients combine both F and G. V5.1 serialized the marginal common-draw bootstrap standard deviations and their covariance, but not the draw-level F/G shifts or the analytic cluster-covariance off-diagonal. Their reported intervals therefore use the serialized joint common-draw covariance and a normal `1.96` critical value. They are **not wild-score intervals**.

For comparison only, the stored marginal effective wild-score critical values are `2.0530` for F and `1.9573` for G. G's value is essentially 1.96; F's is modestly larger. Neither number supplies the missing joint draw distribution needed for individual A and E wild-score intervals, and no bootstrap multipliers were regenerated.

## Interpretation boundary

Allowed:

> In the exploratory continuous joint specification, the negative conditional association loads more heavily on the Eloundou-family centroid than on the AIOE-family centroid.

Required companion disclosures are that this is the same exploratory model in another basis, that G is G-PARTIAL because alpha materially affects its outcome-free geometry, and that the categorical confirmatory Q5–Q1 coefficient is a different estimand.

This result does not establish that Eloundou drives a causal effect, that AIOE does not matter, that only LLM exposure matters, or that the confirmatory result is Eloundou-only.
