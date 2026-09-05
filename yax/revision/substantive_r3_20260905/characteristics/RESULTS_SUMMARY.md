# Occupational-characteristic conditioning: verified results

Status: **post-outcome exploratory**. SCC job `7472019` completed with exit status zero on 2026-09-05, and the rebuilt-treatment module self-check passes. The earlier historical-treatment results remain in Git; Amendment 2 reruns the complete registered grid under the canonical corrected-preperiod treatment without changing its supports, controls, or draw rules.

## Main numerical facts

- The corrected-calendar rebuilt-treatment baseline is -0.132109 (module-specific bootstrap SE 0.045333; 95% interval [-0.220746, -0.043472]) on 468 occupations. It exactly reproduces the canonical rebuilt-treatment point estimate. This interval comes from the characteristic module's fixed seed and is not substituted for the paper's canonical single-target interval [-0.220565, -0.043654].
- Adding SOC2-by-young-by-post terms on the same 468 occupations moves the coefficient to -0.021599 (bootstrap SE 0.071981; interval [-0.162112, 0.118914]). The paired movement is +0.110510 with interval [0.007998, 0.213023]. This is evidence that broad occupational-family composition accounts for much of the pooled Q5--Q1 contrast under this specification.
- O\*NET computer-use importance is available for 455 occupations covering 96.75% of rebuilt treatment-construction stock. On this fixed support the unaugmented coefficient is -0.095747; adding computer use makes it **more** negative, -0.196602. The paired change is -0.100855 with interval [-0.176474, -0.025236]. Computer use itself enters positively (0.046107; interval [0.011971, 0.080243]). This is a suppressor relationship, not evidence that the remaining coefficient is causally attributable to AI.
- Remotability, wage, education requirement, routine-task intensity, manual/physical content, and the two pandemic-shortfall measures do not produce a statistically distinguishable paired movement at the 5% level on their own maximal supports. This is a failure to detect a change, not equivalence.
- The all-characteristic common support retains only 341 occupations and 76.77% of rebuilt treatment-construction stock. It is therefore suitable for the declared cumulative sensitivity, not as a replacement primary population.
- In that 341-occupation panel, the parsimonious characteristic-plus-SOC2 model is -0.123730 with interval [-0.267944, 0.020483]. The model is imprecise and heavily parameterized; its coefficient must not be interpreted as a purified AI effect.

## Interpretation limits

Every characteristic is descriptive conditioning. A static occupation characteristic may be a confounder, mediator, or proxy for other occupational shocks. The generated pandemic regressors are estimated from related CPS outcomes, while the reported wild-score intervals condition on their realized values. The current results therefore do not establish that AI caused the young-worker employment change, and they do not establish economic equivalence when a paired interval includes zero.

Machine-readable estimates, all nuisance coefficients, paired-difference summaries, support maps, information diagnostics, failures, hashes, and the execution receipt are in `results/`. The receipt authenticates membership hash `c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1`, normalization hash `e756d597c12fc2b61ddf62e536b50d3edab32375980e7cea70e5de42fca57557`, and the assertion that no postperiod stock entered treatment construction.
