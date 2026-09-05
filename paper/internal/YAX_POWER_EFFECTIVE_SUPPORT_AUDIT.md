# Code-only audit of effective support and prospective power

## Question

Did the historical simulation mechanically treat information as diffuse across the nominal occupation count, or did it preserve the observed concentration, leverage, and weighting structure?

## Code facts

The prospective simulation used the observed treatment distribution, occupation employment stocks, grouped design matrix, weights, historical residual paths, and the estimator's fixed-effect structure. It did not replace those inputs with equal occupation weights or independent occupation-month noise. Treatment concentration and leverage therefore entered mechanically through the realized design. The simulation did not, however, target an effective-information count as a separate calibration object.

The pre-outcome residual-treatment diagnostic was 53.263 effective occupations; the fitted estimator-information diagnostic is approximately 43.3. These are different objects. The heuristic `sqrt(468/43.3) = 3.288` is close in scale to the realized/prospective headline SE ratio of 3.649, while `sqrt(53.263/43.3) = 1.109`. Neither expression is a decomposition, because the realized effective-information diagnostic depends on fitted information and the prospective model was calibrated to different objects.

## Decision

**POWER-E3: the code does not support excessive nominal-information diffusion as the explanation.** Prospective simulations materially overstated realized precision; the available audit does not isolate a unique cause.

No new outcome model, treatment definition, bootstrap multiplier, or empirical estimate was created for this audit.
