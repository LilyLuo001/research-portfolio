# Joint AI-exposure and computerization power

This power exercise uses only the sealed 2017-01–2022-11 cells. Synthetic post months are generated from pre-period donors; no post-period outcome has been opened. The primary AI measure remains Eloundou β. Eloundou α is a frozen robustness measure, not a replacement chosen for lower collinearity.

The v5 static synthetic post window starts January 2023, excludes December 2022 as the transition month, ends July 2026, and omits the known October 2025 gap.

The computerization coefficient is fixed at `log(0.95)` per employment-weighted standard deviation. It is a design stress parameter, not an estimate from outcomes. Primary inference uses an independently calibrated occupation-cluster Rademacher critical value with 999 draws.

| AI exposure | computerization control | clusters | partial variance | effective occupations | null size | MDE80 | 95% Monte Carlo interval |
|---|---|---:|---:|---:|---:|---:|---:|
| dv_rating_alpha | onet_computers_importance | 465 | 0.908 | 31.1 | 0.070 | 1.36% | 1.34%–1.39% |
| dv_rating_alpha | webb_pct_software | 468 | 0.983 | 17.4 | 0.056 | 1.24% | 1.23%–1.25% |
| dv_rating_beta | onet_computers_importance | 465 | 0.365 | 63.2 | 0.041 | 2.33% | 2.29%–2.37% |
| dv_rating_beta | webb_pct_software | 468 | 0.997 | 53.3 | 0.036 | 1.25% | 1.24%–1.27% |

## Limits of the fitted-DGP exercise

The simulation preserves the observed joint exposure distribution and pre-period occupation/month structure, but it cannot reproduce an unobserved post-2022 aggregate shock, a structural change in occupation composition, measurement error in either exposure, or misspecification of the conditional mean. Its MDE is a design diagnostic under the fitted DGP, not evidence that the eventual association is causal.

The table reports conditional MDEs for this joint model only. It does not repeat the obsolete unconditional 3.44% figure, and no scenario is described as having ‘100% power.’
