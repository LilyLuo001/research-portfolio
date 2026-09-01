# Shared and Architecture-Specific Exposure Components

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.**

This construction was fixed before opening any Phase 3 quantitative result.

For each of the six frozen exposure measures, standardize the score with its weighted mean and standard deviation on the frozen 463-occupation complete support using `preperiod_employment_weight`. Let the standardized scores be `Z_om`.

- `A_o` is the equal-weight centroid of the three AIOE-family `Z` scores.
- `E_o` is the equal-weight centroid of the three Eloundou-family `Z` scores.
- `F_o = (A_o + E_o) / 2` is the **shared family component**.
- `G_o = (A_o - E_o) / 2` is the **family-disagreement component**.
- `R_om = Z_om - F_o` is an architecture-specific residual used only for descriptive switch decomposition.

All source measures are mechanically oriented so higher values mean greater measured exposure. The sign of `F` is therefore fixed as written. There is no rotation, outcome-guided sign choice, alternative factor count, or post-result rescaling.

The 463-occupation reference sample fixes the six means and standard deviations. Current-taxonomy stock occupations are scored directly. Harmonized `OCC2010` switch occupations use the already frozen Phase 2.5 exposure maps with the same six fixed transformations; moments are not re-estimated on realized switches.

`F` is a shared statistical exposure component, not true, latent causal, or uniquely correct AI exposure. `G` and `R` are descriptive construction differences, not causal mechanisms.

