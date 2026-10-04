# LinkUp L1 design diagnostics

The frozen formal sample contains 10,075 arm-A and 30,225 arm-B records. Those counts are deliberately balanced at 1:3 within every one of the 69 common-support cells; the unweighted 25%/75% arm split is therefore a design composition and does not represent the pooled frame, where arm A is under 1%.

Arm-B inclusion probabilities range from about 0.24% to 19.46%, producing IPWs from about 5.14 to 421.59. The IPWs exactly reconstruct the arm-specific frame counts within numerical tolerance, but their concentration means that simple unweighted summaries do not recover frame composition. No trimming, capping, or resampling is applied because that would change the frozen design and estimand.

The comparison weights serve a different purpose from IPW: they give both arms the same original pooled-frame cell distribution, with each arm summing to one. Their descriptive Kish ESS is much lower than the selected count, especially for arm A, showing concentration in the standardized comparison. These ESS values are weight-concentration summaries only; they are not statistical power and do not account for employer, occupation, or other dependence.

Composition is concentrated within the supported frame: the largest cell has about 4.52% of pooled cell mass, the ten largest have about 34.26%, and the effective cell count is about 43.1 out of 69. The three largest occupation-major categories account for about 80.73% of pooled supported-frame mass. Comparisons therefore describe the frozen supported cells and should not be generalized to occupations, years, or regions outside that support.

The CSV and JSON contain only aggregate structural diagnostics. They contain no record keys, source-row identifiers, employer identifiers, job text, outcomes, or record-level weights.
