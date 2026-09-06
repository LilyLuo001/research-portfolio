# YAX V5.1 power-simulation code audit

## Decision: POWER-C3 — serial-dependence omission not supported

The prospective simulations materially overstated realized precision, but the code does not support the referee's specific hypothesis that occupation-month residual shocks were simulated independently across months.

## What the headline code actually generated

`joint_computerization_power.py` first fits the pre-period young share with occupation and month fixed effects and no treatment slope. It stores the entire occupation-by-month arrays of totals, fitted young stocks, and residuals. For every synthetic draw it then:

1. selects one random cyclic offset through the 66 observed pre-period months;
2. uses the same resulting donor-month sequence for every occupation;
3. draws one Rademacher sign per occupation;
4. applies that single occupation sign to the occupation's entire selected residual time path;
5. adds the prespecified AI and Webb shifts in the 42 synthetic post months;
6. refits the planned model and evaluates occupation-cluster inference.

The paired code uses the same donor offset, the same occupation-level signs, and the same simulated outcome for beta and alpha in each paired draw.

| Feature | Code implementation |
|---|---|
| Occupation effects | Estimated in the pre-period fixed-effect fit and carried through fitted values |
| Month effects | Estimated in the pre-period fit; common cyclic donor months preserve the selected aggregate month pattern |
| Occupation×month shocks | Observed pre-period residual cells are recycled rather than drawn independently |
| Young/older structure | Total young-plus-older stock is taken from donor cells; fitted young stock plus signed residual defines the baseline young share |
| Serial dependence within occupation | Explicitly retained through an ordered donor residual path and one sign shared across all months for that occupation |
| Parametric serial process | None: no AR(1), block-length parameter, or estimated autocorrelation coefficient |
| Cross-sectional dependence | A common donor-month sequence retains common timing, but independent occupation signs do not preserve the sign of all cross-occupation residual covariance in expectation |
| Survey-cell noise | No new person- or cell-level sampling noise is generated; observed pre-period residual cells are recycled |
| Post-period shocks | No realized post-2022 shock is represented; synthetic post periods recycle the pre-period residual process and add fixed treatment shifts |
| Cluster dependence | The Rademacher multiplier is at occupation level, matching the final clustering dimension |

Accordingly, the answer to “were residual shocks independent across months?” is **no**. Occupation-level serial correlation was not parameterized as an AR process, but an occupation's selected residual path was kept intact and multiplied by one common sign. The final occupation-clustered covariance allows arbitrary realized within-occupation dependence, whereas the power DGP preserves only the historical pre-period path it recycles. That limitation may matter, but it is not an omission of all within-occupation dependence.

Other documented differences remain: no realized post-period shock, no structural occupation-composition change, no new survey-cell sampling noise, no exposure measurement error, and no allowance for post-period conditional-mean misspecification. The audit does not decompose their contributions.

## Heuristic design-effect arithmetic

For the descriptive formula

\[
D=\sqrt{1+(m-1)\rho},\qquad \rho=(D^2-1)/(m-1),
\]

using `m=42` observed post months gives:

| Comparison | SE ratio D | Mechanically implied rho |
|---|---:|---:|
| Primary headline | 3.649 | 0.3004 |
| Paired beta-minus-alpha | 3.167 | 0.2203 |

This is a **heuristic design-effect comparison**, not a causal explanation of the power miss. Repeated occupation-month cells, fixed effects, unequal stocks, nonlinear estimation, and occupation clustering do not reduce to the equal-cluster formula.

## Precision disclosure

- Primary prospective null mean SE: `0.01217`; realized SE: `0.04441`; ratio: `3.649`.
- Paired prospective SE: `0.01167`; realized SE: `0.03697`; ratio: `3.167`.

The prospective simulations materially overstated realized precision. The old MDEs remain design-history provenance only and do not alter realized confidence intervals or p-values. Because relevant within-occupation dependence was explicitly represented, retain the existing conclusion:

> The prospective simulation materially overstated realized precision; the available audit does not isolate a unique cause.

Authoritative code hashes:

- `joint_computerization_power.py`: `c6977ac8fcd05fc8a9279897f2368d7e9ef074903a98198ea8902e663eeb7472`
- `paired_equivalence_power.py`: `bf295a4092991335bc5dca7161c717373c3f79fabe9a82ccf494041dd183fa92`
- `beta_webb_primary.json`: `0444277942d1b4db1d54a11d4df1a3317797eab663307a1870e890066db596de`
- `PAIRED_EQUIVALENCE_PRECISION_v1.json`: `4898f452f1368796d141f142ecbc88e6963b2ec273ed47446adaa0934908df5e`

No new outcome specification or simulation was run for this code audit.
