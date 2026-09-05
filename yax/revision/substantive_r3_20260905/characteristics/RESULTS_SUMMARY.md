# Occupational-characteristic conditioning: verified results

Status: **post-outcome exploratory**. The SCC rerun completed on 2026-09-05 and the module self-check passes. The initial 341-occupation common-support result remains preserved in Git at `8e3b876`; the amended run adds support-specific baseline/augmented pairs without changing the registered cumulative panel.

## Main numerical facts

- The corrected-calendar historical-treatment baseline is -0.134554 (bootstrap SE 0.045116; 95% interval [-0.222808, -0.046300]) on 468 occupations.
- Adding SOC2-by-young-by-post terms on the same 468 occupations moves the coefficient to -0.031474 (bootstrap SE 0.070961; interval [-0.170412, 0.107465]). The paired movement is +0.103080 with interval [0.002841, 0.203320]. This is the clearest evidence that broad occupational-family composition accounts for much of the pooled Q5--Q1 contrast.
- O\*NET computer-use importance is available for 455 occupations covering 96.42% of baseline employment. On this fixed support the unaugmented coefficient is -0.098687; adding computer use makes it **more** negative, -0.199339. The paired change is -0.100652 with interval [-0.175033, -0.026271]. Computer use itself enters positively (0.046141; interval [0.012630, 0.079653]). This is a suppressor relationship, not evidence that the remaining coefficient is causally attributable to AI.
- Remotability, wage, education requirement, routine-task intensity, manual/physical content, and the two pandemic-shortfall measures do not produce a statistically distinguishable paired movement at the 5% level on their own maximal supports. This is a failure to detect a change, not equivalence.
- The all-characteristic common support retains only 341 occupations and 76.34% of baseline employment. It is therefore suitable for the declared cumulative sensitivity, not as a replacement primary population.
- In that 341-occupation panel, the parsimonious characteristic-plus-SOC2 model is -0.134511 with interval [-0.276802, 0.007780]. The model is imprecise and heavily parameterized; its coefficient must not be interpreted as a purified AI effect.

## Interpretation limits

Every characteristic is descriptive conditioning. A static occupation characteristic may be a confounder, mediator, or proxy for other occupational shocks. The generated pandemic regressors are estimated from related CPS outcomes, while the reported wild-score intervals condition on their realized values. The current results therefore do not establish that AI caused the young-worker employment change, and they do not establish economic equivalence when a paired interval includes zero.

Machine-readable estimates, all nuisance coefficients, paired draws, support maps, information diagnostics, failures, hashes, and the execution receipt are in `results/`.
