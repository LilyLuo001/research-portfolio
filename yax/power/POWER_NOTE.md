# Joint AI-exposure and computerization power

This power exercise uses only the sealed 2017-01–2022-11 cells. Synthetic post months are generated from pre-period donors; no post-period outcome has been opened. The primary AI measure remains Eloundou β. Eloundou α is a frozen robustness measure, not a replacement chosen for lower collinearity.

The computerization coefficient is fixed at `log(0.95)` per employment-weighted standard deviation. It is a design stress parameter, not an estimate from outcomes. Primary inference uses an independently calibrated occupation-cluster Rademacher critical value with 999 draws.

| AI exposure | computerization control | clusters | partial variance | effective occupations | null size | MDE80 | 95% Monte Carlo interval |
|---|---|---:|---:|---:|---:|---:|---:|
| dv_rating_alpha | onet_computers_importance | 465 | 0.908 | 31.1 | 0.060 | 1.36% | 1.34%–1.39% |
| dv_rating_alpha | webb_pct_software | 468 | 0.983 | 17.4 | 0.058 | 1.23% | 1.21%–1.24% |
| dv_rating_beta | onet_computers_importance | 465 | 0.365 | 63.2 | 0.041 | 2.27% | 2.22%–2.32% |
| dv_rating_beta | webb_pct_software | 468 | 0.997 | 53.3 | 0.036 | 1.24% | 1.22%–1.25% |

## Sensitivity to the fixed computerization effect

The primary 5% decline is bracketed by zero and a 10% decline. These are transparent DGP stress values, not outcome estimates.

| computerization control | fixed computerization decline | MDE80 |
|---|---:|---:|
| onet_computers_importance | 10% | 2.22% |
| webb_pct_software | 10% | 1.19% |
| onet_computers_importance | 0% | 2.22% |
| webb_pct_software | 0% | 1.22% |

## Limits of the fitted-DGP exercise

The simulation preserves the observed joint exposure distribution and pre-period occupation/month structure, but it cannot reproduce an unobserved post-2022 aggregate shock, a structural change in occupation composition, measurement error in either exposure, or misspecification of the conditional mean. Its MDE is a design diagnostic under the fitted DGP, not evidence that the eventual association is causal.

The table reports conditional MDEs for this joint model only. It does not repeat the obsolete unconditional 3.44% figure, and no scenario is described as having ‘100% power.’
