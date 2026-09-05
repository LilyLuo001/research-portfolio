# Analytical taxonomy for constructed-exposure comparisons

Status: referee-round-2 analytical work; treatment-side only. This note runs no
outcome model and does not reinterpret an outcome estimate. It separates
operations that the current manuscript sometimes collects under the single
word "robustness."

## 1. The object being compared

Write a constructed-treatment analysis as the pipeline

\[
  C \xrightarrow{M} x^{N}
    \xrightarrow{H} x
    \xrightarrow{\Omega,w} x|_{\Omega}
    \xrightarrow{R} Z
    \xrightarrow{Q,P} \theta
    \xrightarrow{B} b.
\]

- \(C\) is the economic construct: technology boundary, capability, horizon,
  and the meaning of "exposure."
- \(M\) is the measurement rule that turns source labels and occupational
  primitives into a score \(x^N\) on its native taxonomy.
- \(H\) is the taxonomy/harmonization operator that maps the native score to
  the outcome taxonomy.
- \(\Omega\) and \(w\) are the retained population/support and the weights used
  to define it.
- \(R\) is the statistical representation supplied to the outcome model:
  levels, standardized levels, ranks, bins, tails, or another feature map.
- \(Q\) is the economic comparison and outcome functional, and \(P\) is the
  target population distribution. Together they define the population
  estimand \(\theta=Q(P,Z)\).
- \(B\) is a coordinate system for an otherwise fixed model; \(b\) is the
  reported coordinate vector.

An audit should report a **change vector** over these layers, not force every
exercise into one mutually exclusive bucket. For example, correcting a wrong
taxonomy merge is an implementation repair; if that repair also re-admits
occupations, its downstream comparison additionally changes support. The
direct intervention and the induced consequences should be recorded
separately.

## 2. Exact taxonomy

| Category | Exact diagnostic | What must be held fixed for a clean comparison | What may be concluded | YAX example |
|---|---|---|---|---|
| **Implementation error** | Did executed code or data violate the declared algorithm, schema, source vintage, or identity? | Nothing converts the erroneous result into a defensible alternative. The corrected implementation must be identified first. | The erroneous result diagnoses a workflow failure; it is not evidence of economic robustness or sensitivity. | Literal exact-code matching across incompatible SOC vintages is documented as a failure mode, not an alternative estimate (`paper/main/sections/03_measurement.tex:11-17`). |
| **Same-construct measurement change** | Is \(C\) fixed while labels, source inputs, aggregation, or reconstruction in \(M\) change? | Population/support, representation, comparison, estimator, and conditioning set. If harmonization changes too, report it as an additional tag. | Differences measure operational sensitivity for a maintained construct; they do not by themselves establish that either implementation is closer to truth. | The three AIOE implementations retain the same ten-application/52-ability system but change reconstruction or aggregation (`yax/manuscript/v5_1/YAX_V51_ARCHITECTURE_MATRIX.md:5-9`). |
| **Construct change** | Does the operation change technology scope, occupational primitive, label meaning, intended horizon, or potential exposure versus realized use? | A matched downstream design can isolate consequences of asking the different construct questions, but cannot turn them into noisy measurements of one latent variable. | A coefficient difference shows that two economic questions give different empirical answers; it is not ordinary measurement error without an additional latent-variable argument. | Moving from direct LLM acceleration \(D\) to \(D+\lambda S\), from task acceleration to patent overlap, or from LLM tasks to a nine-domain capability gap changes \(C\) (`paper/main/sections/02_literature.tex:3-17`). |
| **Target-population/support change** | Does the set or weighting distribution of occupations, people, or dates entering \(P\) or \(\Omega\) change? | Score construction and representation on the overlap, outcome definition, comparison, and estimator. | The result is a composition/transport statement. It cannot be attributed to changed score values unless a fixed-support component is shown separately. | The repair decomposition distinguishes score correction on original support from occupation re-admission; native versus common support changes the occupational population (`paper/main/sections/03_measurement.tex:13-21`). |
| **Estimand/comparison change** | Holding the represented treatment fixed, does \(Q\) change the outcome, contrast, age comparator, time comparison, conditioning target, or causal/descriptive parameter? | Construct, measurement, harmonization, support, and representation. | The estimates answer different economic questions. Comparing their magnitudes is descriptive unless both are translated to a common target. | Q5--Q1 versus Q5--Q2, young-relative-to-older versus young-only, employment stocks versus hiring, and BCC top-two versus bottom-three versus YAX Q5--Q1 are different estimands (`paper/main/sections/04_data_design.tex:3-13`; `yax/literature/PUBLISHED_MEASUREMENT_AUDIT_2026-08-28.md:7-14`). |
| **Representation change** | Does \(R\) replace the score with a non-invertible or decision-specific feature such as quintiles, ranks, thresholds, or a continuous slope? | Construct, measured score, mapped support/weights, outcome population, and comparison logic. | The exercise shows sensitivity to how score information is consumed. A continuous slope and a tail contrast are not estimates of the same scalar parameter. | Standardized continuous exposure versus employment-weighted quintiles; natural groups used when tie-preserving quintiles collapse (`paper/main/sections/02_literature.tex:7-13`; `paper/main/sections/05_support.tex`). |
| **Pure reparameterization** | Is the new regressor matrix related to the old one by a full-rank coordinate change, with the same column space, observations, objective, weights, and constraints? | The entire fitted model; any penalty must also be invariant. | Fitted values, objective, and properly transformed contrasts are identical. New coordinates are not new empirical evidence. | \(F,G\leftrightarrow A,E\) is an exact basis change when its scales are carried through (`paper/main/sections/06_stock_results.tex:11-16`). Relabeling an omitted quintile is also a coordinate change; changing the requested Q5 contrast is not. |

### Boundary rules

1. **Standardization is not automatically a substantive representation
   change.** On fixed support, \(z=(x-\bar x)/s_x\), \(s_x>0\), is a positive
   affine transformation. It leaves ranks and rank-defined bins unchanged. In
   an otherwise unchanged linear-index model it is a coordinate rescaling.
2. **A mapping repair can have two effects.** Compare repaired and unrepaired
   values on the original support to isolate implementation/measurement; then
   expand support to isolate composition. Calling the aggregate movement a
   "crosswalk effect" conceals the distinction.
3. **Changing an omitted category is not changing a comparison.** The fitted
   model and an explicitly computed Q5--Q1 contrast are invariant to the
   omitted category. Reporting Q5--Q2 instead changes \(Q\).
4. **A score family is not a validation sample.** High dependence among score
   implementations neither establishes one latent true exposure nor creates
   independent replications. The six-score treatment-side spectrum confirms
   that two components explain 96.11 percent of weighted variance on the exact
   444-occupation support
   (`yax/revision/referee_round2_20260905/architecture/ARCHITECTURE_STRUCTURE_FINDINGS.md:1-9`).

## 3. Short propositions

### Proposition 1: positive-affine invariance of ranks and weighted bins

Let \(\Omega=\{1,\ldots,n\}\) be finite, let fixed weights satisfy \(w_o>0\),
and let a deterministic ranking and weighted-bin rule depend only on the weak
ordering of scores, the weights, and a tie rule that is invariant to relabeling
score values. If

\[
  x'_o=a+b x_o,\qquad b>0,
\]

then the weak ordering, average ranks, weighted quantile boundaries after the
same transformation, and occupation-level weighted-bin assignments are
identical under \(x\) and \(x'\).

**Proof.** For every \(o,j\), \(x'_o\leq x'_j\) if and only if
\(x_o\leq x_j\), and equality is also preserved. Thus the ordered sequence,
ties, and cumulative weights are unchanged. A quantile value transforms from
\(c\) to \(a+bc\), so the same occupations lie on each side of every boundary.

**Scope.** The result fails to guarantee identical membership if support,
weights, missing-value treatment, or the tie rule changes. A negative slope
reverses order; \(b=0\) destroys it. For a continuous linear-index model, the
same transformation also preserves fitted values after coefficient/intercept
transformation, subject to the model containing the required constant or fixed
effects.

### Proposition 2: piecewise-constant categorical assignments along
\(D+\lambda S\)

Let \(x_o(\lambda)=D_o+\lambda S_o\) for a finite fixed support \(\Omega\),
fixed weights, a fixed deterministic tie rule, and \(\lambda\) in a compact
interval \(L\). Define the finite set of pairwise crossing values

\[
  \mathcal B=\left\{
  {D_j-D_o\over S_o-S_j}:o\ne j,\ S_o\ne S_j
  \right\}\cap L.
\]

On every connected open component of \(L\setminus\mathcal B\), all occupational
orders, weighted ranks, and rank-defined categorical assignments are constant.
Consequently, if an outcome estimator depends on \(\lambda\) only through
those categories and every other design element is fixed, its objective and
fitted estimate are constant on that component (when the fitted solution is
unique). Changes can occur only at crossing values relevant to a category
boundary.

**Proof.** For each pair, the sign of
\(x_o(\lambda)-x_j(\lambda)\) is affine in \(\lambda\) and cannot change away
from its sole possible zero. Excluding all pairwise zeros fixes the complete
ordering. Fixed weighted-bin assignments then follow from Proposition 1's
ordering logic.

**Scope.** The actual assignment-breakpoint set can be a strict subset of
\(\mathcal B\), because many crossings occur within a bin. The proposition does
not apply to a continuous exposure regression, whose coefficient can change
between crossings. It also does not imply a monotone sequence of categorical
coefficients across \(\lambda\).

### Proposition 3: exact invariance under a full-rank coordinate change

Let an estimator maximize an objective \(L(y,\eta)\) whose systematic index is
\(\eta=N\alpha+Z\beta\), where \(N\) contains fixed nuisance regressors. Let
\(R\) be nonsingular and define \(\widetilde Z=ZR\). If the sample, weights,
objective, nuisance regressors, constraints, and any penalty are unchanged (or
the penalty is transformed invariantly), then

\[
  Z\beta=\widetilde Z\widetilde\beta
  \quad\text{for}\quad
  \widetilde\beta=R^{-1}\beta.
\]

The two parameterizations therefore have the same attainable indices,
maximized objective, fitted values, residuals, and transformed covariance
matrix. Any linear contrast must be transformed with the coordinates.

For the implemented family coordinates

\[
 F={A+E\over2},\qquad G={A-E\over2},
\]

entered as \(F/s_F\) and \(G/s_G\), the same fitted predictor can be written
\(\gamma_A A+\gamma_E E\), where

\[
 \gamma_A={1\over2}\left({b_F\over s_F}+{b_G\over s_G}\right),
 \qquad
 \gamma_E={1\over2}\left({b_F\over s_F}-{b_G\over s_G}\right).
\]

This is an exact coordinate identity, not a second empirical specification.
Centering constants are absorbed only if the maintained nuisance space
contains the corresponding constant/fixed effects.

## 4. Reporting protocol implied by the taxonomy

Every robustness row should report:

1. the direct pipeline layer changed;
2. any induced changes in support, representation, or estimand;
3. the fixed comparator and shared support, if one exists;
4. whether the operation corrects an error or compares two defensible choices;
5. whether the displayed coefficient is the same parameter, a transformed
   coordinate, or a different population statistic; and
6. which uncertainty is covered (sampling/occupation shocks conditional on the
   constructed score versus construction or mapping uncertainty).

This protocol prevents three invalid inferences: treating a coding error as a
defensible specification, treating a different technology construct as noisy
measurement of one object without validation, and treating a change of basis
as corroborating evidence.
