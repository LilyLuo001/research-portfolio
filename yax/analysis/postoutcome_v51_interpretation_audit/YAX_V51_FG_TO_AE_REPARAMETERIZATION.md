# YAX V5.1 F/G to A/E exact reparameterization

**Decision: AE-R1 — strong family asymmetry.** This is algebra applied to the already-estimated frozen F+G model, not a new regression.

## Frozen scales

| Component | Weighted mean | Weighted SD |
|---|---:|---:|
| A | 0.007601579 | 0.998654124 |
| E | -0.000523011 | 0.866645912 |
| F | 0.003539284 | 0.877735855 |
| G | 0.004062295 | 0.322137185 |

## Implied family coefficients

| Family centroid | Per original unit | Covariance-transformed SE | Normal 95% CI | Per weighted SD | Normal 95% CI |
|---|---:|---:|---:|---:|---:|
| AIOE A | 0.024961 | 0.020356 | [-0.014936, 0.064857] | 0.024927 | [-0.014916, 0.064770] |
| Eloundou E | -0.070941 | 0.027601 | [-0.125039, -0.016844] | -0.061481 | [-0.108364, -0.014598] |

On the common original-centroid scale, A minus E is `0.095902` (SE `0.045639`; normal 95% CI [0.006451, 0.185352]). Because this contrast is exactly `b_G/s_G`, its transformed existing G wild-score interval is [0.005591, 0.186212] with unchanged `p=0.040`. The transformed A/E coefficient correlation is `-0.806907`.

The negative conditional stock association loads substantially more heavily on the Eloundou-family centroid. The implied AIOE-family coefficient is positive and imprecise, while the Eloundou-family coefficient is negative and its covariance-transformed interval excludes zero. This does not mean that only Eloundou matters, that AIOE has no effect, or that LLM exposure caused the employment pattern.

## Algebra and centering audit

The raw-unit map is $b_A=\frac12(b_F/s_F+b_G/s_G)$ and $b_E=\frac12(b_F/s_F-b_G/s_G)$. Means obey $\mu_A=\mu_F+\mu_G$ and $\mu_E=\mu_F-\mu_G$, so the centered A/E representation is exactly intercept-equivalent. The maximum discrepancy between the F/G and A/E linear-predictor contributions across the 444 occupations is `2.776e-17`.

## Inference boundary

The serialized V5.1 result retains the marginal common-draw bootstrap SDs and their centered covariance, which form the transformed covariance used here. It does not retain draw-level shifts or the analytic cluster covariance off-diagonal. Therefore no transformed wild-score interval or exact wild-score p-value is reported, and no multipliers were regenerated.

No new labor-outcome model was estimated. The A/E coefficients are exact algebraic transformations of the already-executed frozen F+G model.
