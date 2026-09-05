# YAX V5.1 final interpretation decision

## Decision: SUBMIT-S1

Retain the paper's statement-specific framing and the confirmatory categorical beta-by-Webb headline. Keep A/E/G as a bounded secondary result from one exploratory continuous joint model.

## Basis

1. **A/E is a presentation basis, not corroboration.** The exact identity `F=(A+E)/2`, `G=(A-E)/2`, combined with the frozen component scales, maps the already-estimated F/G coefficients to +0.02493 per weighted SD of the AIOE centroid and -0.06148 per weighted SD of the Eloundou centroid. The transformed predictor agrees with the original predictor to `2.78e-17`. No A+E model was estimated.
2. **Inference is labeled by what was actually retained.** The A-minus-E contrast exactly inherits G's existing wild-score interval `[0.00559, 0.18621]` and `p=.040`. Individual A and E intervals use the serialized common-draw covariance and a normal 1.96 critical value; they are not wild-score intervals.
3. **G remains bounded despite stable occupation influence.** The fixed-treatment LOCO audit is `LOCO-G1`: all 444 leave-one-occupation-out G estimates remain positive, from 0.02513 to 0.03599. The earlier outcome-free audit remains `G-PARTIAL` because alpha materially changes the construction's geometry. Stability to occupation deletion does not erase sensitivity to which measure defines the family centroid.
4. **The confirmatory headline survives the authorized influence check.** The primary audit is `LOCO-B2`: all 468 deletions remain negative, from -0.14238 to -0.11055, although the largest movement is 0.02052 (15.66%). This supports retaining the negative headline while disclosing moderate magnitude influence.
5. **Prospective power was optimistic for reasons not isolated by the record.** The audit is `POWER-C3`: the simulations did retain ordered within-occupation residual paths and one occupation-level sign across months, so the specific claim that they treated occupation-month shocks as independent is unsupported. The prospective-to-realized SE ratios are 3.649 for the headline and 3.167 for the paired contrast. The design-history MDEs are not evidence that the realized analysis was well powered.

## Binding prose boundary

Allowed secondary wording:

> In the exploratory continuous joint specification, the negative conditional association loads more heavily on the Eloundou-family centroid than on the AIOE-family centroid. This is an exact reparameterization of the same F/G model, not independent corroboration; an outcome-free construction audit shows that the contrast is materially influenced by Eloundou alpha.

Not allowed are causal or exclusivity claims, including that Eloundou drives the causal effect, that AIOE does not matter, that only LLM exposure matters, or that the confirmatory categorical result is Eloundou-only.

## Empirical closure

No new labor-outcome specification was estimated. LOCO refits only delete one occupation while preserving the exact previously defined treatment and model. No leave-one-measure-out labor-outcome model was executed. No new bootstrap multipliers were generated.

After this audit the empirical search remains closed. Remaining work is citation/version verification, prose compression, journal formatting, figures and tables, seminar slides, cover letter, and submission.
