# YAX V5.1 treatment-only G-construction stability

**Decision: G-PARTIAL.** All diagnostics use only frozen exposure scores and frozen pre-period employment weights on the same 463-occupation support. No labor outcome is used.

| Alternative | Pearson | Rank corr. | SD ratio | Q1 retained | Q5 retained | Zero-sign agree | Median-side agree | Occ. direction change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| G_minus_alpha | 0.8650 | 0.8547 | 0.7674 | 72.5% | 69.5% | 82.1% | 81.5% | 17.1% |
| G_minus_beta | 0.9921 | 0.9897 | 1.0821 | 83.0% | 96.7% | 96.4% | 96.3% | 8.4% |
| G_minus_broad | 0.9778 | 0.9729 | 1.2913 | 79.1% | 93.7% | 92.8% | 93.5% | 11.0% |

G is highly stable to removing beta or broad but changes materially when alpha is removed. The minus-alpha level/rank correlations fall to about 0.865/0.855, only 69–73% of frozen tail weight is retained, and about 18% of employment changes zero-direction. The exploratory family-disagreement result therefore partly reflects alpha's distinctive position. No employment regression using an alternative G was run.

## Mechanical and covariance contributions

Each Eloundou component has arithmetic weight `1/3` in E and `-1/6` in G; the AIOE centroid has weight `+1/2` in G.

| Component | Share of weighted variance of E | Share of weighted variance of G |
|---|---:|---:|
| AIOE centroid | — | 0.7745 |
| Eloundou alpha | 0.2899 | 0.2993 |
| Eloundou beta | 0.3767 | 0.0261 |
| Eloundou broad | 0.3334 | -0.0999 |

These are covariance contributions, so correlated components can have negative or greater-than-one shares; the shares sum to one within each target. The leave-one-out changes reflect both each component's fixed arithmetic weight and its covariance with the remaining family geometry.
