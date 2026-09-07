# CLAUDE — YAX Gate 2 dynamic reconciliation preflight: adversarial review

Read-only adversarial numerical/econometric review. No repository file was
created, modified, staged, committed, or pushed. No SCC access, no protected
microdata, no aggregate cells. All adversarial fixtures were built in `/tmp`
and deleted. The only file written is this report.

---

## 0. Tree-state gate

| Check | Expected | Observed | Verdict |
|---|---|---|---|
| Branch | `task/yax-v3-execution-20260906` | `task/yax-v3-execution-20260906` | PASS |
| Tracked HEAD | `9c19741…` | `9c197418122623cd86f0a4990ffa4013ba93b656` | PASS |
| `git diff --check` | clean | exit 0, no output | PASS |
| Five review files present | yes | yes, all five read in full | PASS |

Untracked state at review time:

```
?? yax/revision/substantive_v3_20260906/gate2/d02/tests/test_d02_authoritative_evidence.py
?? yax/revision/substantive_v3_20260906/gate2/d02/validate_d02_artifact.py
?? yax/revision/substantive_v3_20260906/gate2/dynamic/
?? yax/revision/substantive_v3_20260906/gate2/support_inference/
?? yax/revision/substantive_v3_20260906/runs/gate2_d02_authoritative_20260907/
```

The prompt anticipated `gate2/dynamic/` and `gate2/support_inference/`. Two
further untracked paths appeared during the review (`gate2/d02/`,
`runs/gate2_d02_authoritative_20260907/`) — producer work in parallel. Not
reviewed, not touched, reported for completeness only. Tracked HEAD is
unchanged, so the gate passes and substantive review proceeded.

Focused test run: **13 passed, 0 failed, 0 skipped** (0.98 s), under
CPython 3.10.5 / numpy 1.22.4. Byte-compilation caches (`__pycache__`,
`cpython-310`) already existed at the producer's mtime 19:34 and were reused —
directory mtimes confirm the test run wrote nothing.

---

## 1. Verdict summary

**1 P1, 5 P2, 6 P3.**

The certified point arithmetic is correct to the last representable digit and
the reference-invariance algebra is exactly right. Every defect below is in the
machinery that has not yet been executed, or in the binding between the signed
contract and the runner. Nothing in the current preflight output is a wrong
number.

| # | Sev | One-line |
|---|---|---|
| P1-1 | P1 | `validate_design_nesting` default `lstsq` turns the predeclared Y02 exact-nesting test into a column-space-containment test and still stamps `PASS_EXACT_DESIGN_NESTING` |
| P2-1 | P2 | `rank_aware_wald` rank tolerance is absolute-clamped, not relative; contradicts the signed `conditioning_rank_relative`; inconsistent with `pinv(rcond=)`; can reject a full-rank covariance |
| P2-2 | P2 | `requirement_disposition` echoes `spec["requirements"]` verbatim; a re-sealed spec asserting `Y08: COMPLETE` is accepted and printed |
| P2-3 | P2 | `result_id` logical key is hardcoded; `outputs.declared_preflight_file` is never read; any output filename is accepted |
| P2-4 | P2 | 17 behaviour-relevant signed-spec fields are inert — the runner cannot detect that it contradicts its own contract |
| P2-5 | P2 | `pretrend.windows.full_excluding_2020Q2_2020Q4` does not encode the exclusion and contradicts the runner's 20-quarter window |
| P3-1 | P3 | `verify_equivalent_restrictions` is an algebraic tautology with zero power to detect a wrong rebasing matrix |
| P3-2 | P3 | `simultaneous_intervals` has no minimum-draw guard; `B = 1` yields a "95%" band |
| P3-3 | P3 | Test pins `P` at `1e-12` for one structure and `1e-9` for the other with no numerical justification |
| P3-4 | P3 | No interpreter/library pin for Gate 2 while A1 pins CPython 3.13.8 |
| P3-5 | P3 | `rank_aware_wald` silently discards the null-space component of the restriction target and can return a negative statistic |
| P3-6 | P3 | `validate_design_nesting` tolerance is scaled by `max\|Xs\|`, loosening the bar for large-magnitude designs |

---

## 2. Objective 1 — calendar and frozen weights

Reconstructed independently from `calendar.observed_window` without importing
the runner.

| Quantity | Spec | Independent | Verdict |
|---|---|---|---|
| Window months 2017-01…2026-07 | — | 115 | — |
| Observed (drop 2025-10) | 114 | 114 | PASS |
| Fit (drop transition 2022-12) | 113 | 113 | PASS |
| Pre 2017-01…2022-11 | 71 | 71 | PASS |
| Post 2023-01…2026-07 | 42 | 42 | PASS |
| Observed months in 2022Q4 | 2 | 2 (`2022-10`, `2022-11`) | PASS |
| Observed months in 2025Q4 | 2 | 2 (`2025-11`, `2025-12`) | PASS |
| Observed months in 2026Q3 | 1 | 1 (`2026-07`) | PASS |

**All 39 frozen quarter weights (24 pre + 15 post) are bit-exactly
`count / total`, zero mismatches.** Full pre quarters are `3/71 =
0.04225352112676056`, 2022Q4 is `2/71 = 0.028169014084507043`; full post
quarters are `3/42 = 0.07142857142857142`, 2025Q4 is `2/42 =
0.047619047619047616`, 2026Q3 is `1/42 = 0.023809523809523808`. Sums are
`0.9999999999999993` and `0.9999999999999997` — one-ulp accumulation, well
inside the runner's `abs_tol=1e-15` closure check at
`run_dynamic_reconciliation.py:167-170`.

Sensitivity probe: weighting the partial quarters as full and renormalising
moves `P` by `-9.08e-03` (unconditioned) and `+8.32e-03` (family-month), i.e.
any partial-quarter error is four orders of magnitude above the runner's
`target_absolute = 1e-6` guard. The guard is loose but functional.

---

## 3. Objective 2 — S, P, D recomputed independently

Source: `runs/gate1_numerical_a1_pass_7482383/numerical/MODEL_AUDIT.json`,
byte-bound at `authenticated_inputs.model_audit.sha256 = ffb4364a…`.

The Q5 quarterly vector was extracted **twice** and cross-checked:
(a) the 38 top-level `Q5_x_<quarter>` keys of
`solver_comparison.reference_target_vector`, and (b) the 38 `Q5` entries parsed
out of the 190 `original_treatment::<idx>::<component>_x_<quarter>` keys. The
two extractions agree to **max |diff| = 0.000e+00** for both structures. 2022Q4
was pinned at exactly 0.0 under the published normalisation, giving a 39-length
vector over 24 pre + 15 post quarters. Weights are the ones I derived in §2, not
the ones read from the spec.

### Unconditioned (`dynamics_unconditioned` vs static `pooled`)

| Quantity | Value |
|---|---|
| `S` (certified static Q5×post) | `-0.1321094507921904` |
| `P` (observed-post-month mean rel. 2022Q4) | `-0.11988876533150444` |
| pre mean (rel. 2022Q4) | `+0.011483401593756796` |
| `D = P − pre` | `-0.13137216692526124` |
| `P − S` | `+1.222068546069e-02` |
| `D − S` | `+7.372838669292e-04` |
| `P − D` | `+1.148340159376e-02` |

### Family-month (`dynamics_family_month` vs static `family_month`)

| Quantity | Value |
|---|---|
| `S` | `-0.021674952018246887` |
| `P` | `-0.20743368917400506` |
| pre mean | `-0.1857443731553657` |
| `D = P − pre` | `-0.021689316018639354` |
| `P − S` | `-1.857587371558e-01` |
| `D − S` | `-1.436400039247e-05` |
| `P − D` | `-1.857443731554e-01` |

### Conditioning movements (family-month minus unconditioned)

| Movement | Value |
|---|---|
| `ΔS` | `+1.104344987739e-01` |
| `ΔP` | `-8.754492384250e-02` |
| `ΔD` | `+1.096828509066e-01` |
| `Δ(P−S)` | `-1.979794226164e-01` |
| `Δ(D−S)` | `-7.516478673216e-04` |
| `Δ(P−D)` | `-1.972277747491e-01` |

**Every one of these matches the runner's own emitted
`point_reconciliation` to the last printed digit.** The runner was executed
read-only to stdout with the eight bound inputs; exit 0; nothing written.

### Consistency of `P` with the A1 certificate

`dynamics_unconditioned.focal_target_label` is
`observed_calendar_month_weighted_post_Q5_functional` with
`focal_target_estimate = -0.11988876533150447`. My `P` differs by `2.78e-17`
(pure summation order: shuffling the 15 post terms 4000 times spans
`5.55e-17`). Family-month agrees at `0.0`.

**Caveat on what this proves.** Because A1 already certified the *same*
observed-month-weighted post functional, the runner's check that `P` equals the
certified value is a **weight-consistency check, not an independent
verification of `P`**. It confirms the Gate 2 frozen weights reproduce the
Gate 1 functional; it cannot confirm that either is the right functional. The
genuinely independent content of my §2 recomputation is that the weights are
exactly `count/total` on the declared calendar.

### Does `D` nearly reproduce `S`?

Yes, and the near-coincidence is striking, but **there is no algebraic identity
here and none should be claimed.**

* Unconditioned: `|D − S| = 7.37e-04`, i.e. **0.56 %** of `|S|`.
* Family-month: `|D − S| = 1.44e-05`, i.e. **0.066 %** of `|S|`.

Contrast this with `P`: `|P − S|` is 9.2 % of `|S|` unconditioned and **857 %**
of `|S|` for family-month. The mechanism is visible in the pre means. Under the
published 2022Q4 reference the family-month dynamic model carries a large
pre-period level of `-0.1857`; the static `Q5×post` dummy differences that level
away, whereas `P` does not. So `P` is simply the wrong comparator for `S`, and
`D` — which is reference-invariant precisely because both weight sets sum to one
— is the right one. That is the substantive reconciliation result and it is
correctly stated in `PRE_RESULTS_SPEC.md`.

Why it is nevertheless **not** an identity, and why the residual `7.4e-04` /
`1.4e-05` is real rather than numerical noise:

1. `S` is a **restricted MLE** of a single interaction parameter on the pooled
   grouped-binomial likelihood. It is not any linear functional of the
   unrestricted dynamic coefficient vector.
2. The link is **logit**, not identity. Even under exact design nesting, the
   restricted maximiser is not the weighted average of the unrestricted
   coefficients; that equality holds only in a linear model with orthogonal
   design and matching weights.
3. The two fits use **different nuisance normalisations** — the dynamic
   specification interacts Q2–Q5 *and* Webb-z with quarters
   (`models.dynamic_nuisance`), so the profiled likelihoods differ.

The residual is therefore an empirical finding about how little the dynamic
flexibility moves the summary, and quantifying it rigorously is exactly what
Y02 (score moment + pseudo-stock projection) exists to do. **Y02 is
implemented but unrun.** Nothing in the current package licenses a claim
stronger than "numerically close."

---

## 4. Objective 3 — reparameterization algebra

Audited with **500 randomised adversarial fixtures**: 9 period labels, all
ordered `(old_reference, new_reference)` pairs sampled at random, random
`beta`, random full-rank restriction matrices of 1–3 rows, and a random
influence matrix with `V = IFᵀIF` (required, see below).

| Identity | Max error over 500 trials |
|---|---|
| `beta_new = B beta_old` vs. ground-truth renormalised vector | `0.000e+00` |
| `V_new = B V_old Bᵀ` | `0.000e+00` |
| `IF_new = IF_old Bᵀ` | `0.000e+00` |
| `R_new = R_old B⁻¹` | `0.000e+00` |
| Target invariance `R_new beta_new = R_old beta_old` | `2.220e-15` |
| Restricted covariance invariance `R_new V_new R_newᵀ = R_old V_old R_oldᵀ` | `1.776e-15` |
| Restricted influence invariance `IF_new R_newᵀ = IF_old R_oldᵀ` | `2.776e-16` |
| Round-trip rebase `new → old` | `4.441e-16` |

The first four are exactly zero because `free_rebase_matrix` produces a matrix
with entries in `{0, ±1}`; the remainder are at machine epsilon. The
`old_reference` row — the case most likely to be wrong, since that label is
absent from `old_free` and must be synthesised as `−beta[new_reference]` — is
handled correctly by the `if label != old_reference` guard at
`run_dynamic_reconciliation.py:429`.

`transform_parameterization:460-471` additionally enforces `V = IFᵀIF` both
before and after the transform (`rtol=1e-9, atol=1e-12`). That is a genuinely
strong internal check and it is the reason my first fixture attempt, which
supplied an unrelated random SPD `V`, correctly raised
`covariance is not reproduced by influence`.

`verify_reference_invariance:528-553` does **not** route through
`free_rebase_matrix`; it rebases directly (`coefficients −
coefficients[index]`) and sweeps all references. It correctly detects a broken
weight set — perturbing one pre weight so the block sums to 1.1 raises
`reference-invariant contrast changed after rebasing`.

**Answer: the reference-invariance algebra is correct for beta, covariance,
influence, and restrictions.** See P3-1 for the one check that has no power.

---

## 5. Objective 4 — nesting, score moment, pseudo-stock projection

### P1-1 — default least-squares mapping makes "exact predeclared nesting" misleading

**Locator:** `run_dynamic_reconciliation.py:566-587`, specifically

```python
if mapping is None:
    mapping = np.linalg.lstsq(xd, xs, rcond=None)[0]
```

**Mechanism.** The signed contract at `DYNAMIC_RECONCILIATION_SPEC.json`
`nesting.identity` declares `"X_static = X_dynamic A on the exact same active
rows and nuisance normalization"` — a statement about a *predeclared* map `A`
determined by the two specifications. When `mapping is None` the function
instead *solves for* `A`. It then verifies `Xs − Xd·Â ≈ 0`, which is true
whenever `col(Xs) ⊆ col(Xd)` — a strictly weaker proposition. The function
nonetheless returns `"status": "PASS_EXACT_DESIGN_NESTING"` and hands back the
fitted `Â` under the key `"mapping"`, where a downstream reader cannot
distinguish it from a declared map.

**Demonstrated numerically** (n = 200, 8 dynamic columns, `/tmp` fixtures):

| Fixture | Result |
|---|---|
| `Xs` = arbitrary random combination `Xd·N(0,1)` — no econometric relation to any static design | `PASS_EXACT_DESIGN_NESTING`, residual `7.1e-15` |
| `Xd` rank-deficient (11 columns, rank 8), `Xs` in its column space | `PASS_EXACT_DESIGN_NESTING`, residual `8.0e-15`; returned `Â` is the **minimum-norm** lstsq solution, not the declared map |
| `Xs` row-permuted relative to `Xd` | correctly raises |
| `Xs` perturbed out of `col(Xd)` by `1e-6` | correctly raises |

The rank-deficient case is the dangerous one: the two fixed-effect designs here
carry occupation and calendar-month absorptions with a nuisance normalisation,
so `Xd` being column-rank-deficient in its raw form is entirely plausible. In
that regime `Â` is not even unique, yet the report presents a single one.

**Impact.** Y02 is the predeclared falsification test that the static
specification is a restriction of the dynamic one. Today the check is unrun
(`nesting.available_now: false`, six missing objects) so **no current number is
affected**. But this is the exact code that the future object-binding amendment
will execute, and as written it would emit a `PASS_EXACT_DESIGN_NESTING`
receipt on evidence that does not establish the predeclared identity. That
satisfies "could permit a false authoritative result," hence P1 rather than P2.

**Minimal correction.** Make the declared map mandatory for any status that
claims exactness, and label the fitted variant honestly:

```python
if mapping is None:
    raise DynamicGateError(
        "exact nesting requires the predeclared map; refusing to fit one"
    )
```

If a fitted diagnostic is still wanted, return it under a separate status
`"PASS_STATIC_COLUMN_SPACE_CONTAINED_IN_DYNAMIC"` with
`"mapping_source": "FITTED_LEAST_SQUARES_NOT_PREDECLARED"`, and additionally
assert `matrix_rank(np.hstack([xd, xs])) == matrix_rank(xd)` so the weaker claim
is stated as what it is.

**Regression test.**

```python
def test_exact_nesting_refuses_to_fit_its_own_map():
    rng = np.random.default_rng(0)
    xd = rng.normal(size=(50, 6))
    xs = xd @ rng.normal(size=(6, 2))     # in col(xd) but not a declared map
    with pytest.raises(DYN.DynamicGateError, match="predeclared map"):
        DYN.validate_design_nesting(xs, xd)
    declared = np.zeros((6, 2)); declared[0, 0] = declared[1, 1] = 1.0
    with pytest.raises(DYN.DynamicGateError, match="nesting failed"):
        DYN.validate_design_nesting(xs, xd, mapping=declared)
```

### Score moment and pseudo-stock projection

`validate_static_score_moment:590-614` computes `Xsᵀ(y − T·p_dyn)` and scales
the max by `sum(total)` — a defensible normalisation, and it validates
`0 ≤ p ≤ 1` and `T ≥ 0` first. Correct as written.

`fit_grouped_logit_projection:626-675` is a clean IRLS: full-column-rank
precheck, Newton step via `solve` on the observed information, 40-step halving
line search with a `1e-12` slack, and a softplus-stable NLL via
`np.logaddexp(0.0, eta)`. Convergence is on `max|score| / sum(total) ≤ 1e-12`.
No boundary/separation handling, but the projection is warm-started at the
certified static beta on pseudo-stocks generated from a fitted probability
vector, so an interior optimum is expected. I found no defect.

`validate_pseudo_stock_projection:678-703` compares only `target_indices`
against the certified beta at `target_tolerance` defaulting to `1e-6`. Note the
default is a *function default*, not the spec's `nesting.target_tolerance` —
see P2-4.

### Executable now vs. implemented-but-unrun

| Utility | Bound objects available? | Status |
|---|---|---|
| Point reconciliation `S/P/D`, gaps, movements | yes — full dynamic coefficient vectors in the audit | **executes, verified** |
| Coefficient-level reference invariance (all 5 components, both structures) | yes | **executes, verified** |
| Y04 restriction construction + coefficient-target reparameterization | yes | **executes, verified** |
| Y05 contrast *definitions* (level, drift, seasonal) | yes | **executes** (definitions only) |
| `free_rebase_matrix` / `transform_*` on covariance & influence | no | implemented, unrun |
| `rank_aware_wald`, `simultaneous_intervals`, `leave_one_restriction_out` | no | implemented, unrun |
| `validate_design_nesting`, `validate_static_score_moment`, `validate_pseudo_stock_projection` | no | implemented, unrun |

---

## 6. Objective 5 — Y04 restrictions and rank-aware Wald

### Restriction construction is correct

Recomputed from the 23 pre labels `2017Q1 … 2022Q3` (2022Q4 excluded, correctly,
since it is the normalised reference and cannot be tested):

| Window | k | reference rows / rank | within rows / rank |
|---|---|---|---|
| `full_preperiod` | 23 | 23 / 23 | 22 / 22 |
| `2017Q1_2019Q4` | 12 | 12 / 12 | 11 / 11 |
| `2021Q1_2022Q3` | 7 | 7 / 7 | 6 / 6 |
| `full_excluding_2020Q2_2020Q4` | 20 | 20 / 20 | 19 / 19 |

The exclusion window drops exactly `{2020Q2, 2020Q3, 2020Q4}`. All matrices are
full row rank. `equality_to_reference` selects each coefficient to zero — correct
under the published normalisation where the 2022Q4 coefficient is identically
zero. `equality_within_block` anchors on `selected[0]` and emits `k−1`
differences — the correct rank-`(k−1)` encoding of "all equal to one another",
and the `len(selected) < 2` branch returning a `(0, n)` matrix is a sensible
degenerate case (though `rank_aware_wald` would then raise
`Wald test has no restrictions`, which is correct behaviour).

Lexicographic comparison on `YYYYQn` strings (`"2017Q1" <= label <= "2019Q4"`)
is order-correct for this fixed-width format.

Reparameterization of Y04 targets: the runner sweeps all 39 references × 8
restriction blocks × 2 structures and reports
`maximum_absolute_target_difference`. It ran clean. But see P3-1 — the check is
structurally incapable of failing.

### P2-1 — the rank tolerance is not relative, contradicting the signed spec

**Locator:** `run_dynamic_reconciliation.py:775-779`

```python
scale = max(1.0, float(np.linalg.norm(target_covariance, ord=2)))
rank = int(np.linalg.matrix_rank(target_covariance, tol=1e-10 * scale))
...
statistic = float(target @ np.linalg.pinv(target_covariance, rcond=1e-10) @ target)
```

**Mechanism, three distinct failures.**

*(a) `max(1.0, ‖V‖₂)` makes a "relative" tolerance absolute.* The spec declares
`tolerances.conditioning_rank_relative = 1e-10`. A covariance matrix of logit
coefficients has `‖V‖₂ < 1` in essentially every realistic case — SEs of 0.02
give `‖V‖₂ ≈ 4e-4`. The clamp then fires and the tolerance becomes a fixed
absolute `1e-10`, unrelated to the spectrum. Demonstrated: with `‖V‖₂ =
5.167e-05` and two eigenvalues at `1e-8` of the largest, the code reports
**df = 4** where the truly-relative criterion gives **df = 6**.

*(b) A full-rank covariance can be rejected outright.* Rescale a perfectly
conditioned rank-23 matrix so `‖V‖₂ = 1e-12` (SEs ≈ `1e-6`; reachable with a
large-`N` block or any standardised parameterisation). Every eigenvalue then
falls below the absolute `1e-10`, `rank` evaluates to 0, and the function raises
`restricted covariance has zero rank`. **Confirmed in `/tmp`.** That is a hard
false failure on a matrix whose true relative rank is 23.

*(c) `matrix_rank(tol=…)` and `pinv(rcond=…)` use different conventions.*
numpy's `rcond` is *relative to the largest singular value*; the `tol` passed to
`matrix_rank` here is absolute. So the reported `degrees_of_freedom` need not
equal the number of directions the quadratic form actually inverts.
Demonstrated on a 6×6 covariance with spectrum
`{1e-10, 1e-10, 3.9e-07, 4.9e-07, 7.5e-07, 1e-06}`: code reports **df = 5**
while `pinv` inverts **6** directions. Any downstream chi-square reference
applied to the reported df would then be applied to a statistic of a different
rank — anticonservative.

**Impact.** No covariance is bound today, so nothing currently computed is
wrong. The moment the amendment supplies `V`, this silently mis-states the
feasible degrees of freedom that `pretrend.rank_rule` explicitly designates as
the inferential df — and in the small-scale regime it will refuse to run at all.

**Minimal correction.** Compute rank and pseudo-inverse from one relative
criterion read from the spec, and symmetrise first:

```python
target_covariance = 0.5 * (target_covariance + target_covariance.T)
singular = np.linalg.svd(target_covariance, compute_uv=False)
relative = float(spec_conditioning_rank_relative)      # 1e-10, from the spec
cutoff = relative * float(singular.max())
rank = int((singular > cutoff).sum())
if rank == 0:
    raise DynamicGateError("restricted covariance has zero rank")
statistic = max(0.0, float(target @ np.linalg.pinv(target_covariance, rcond=relative) @ target))
```

**Regression test.**

```python
def test_rank_tolerance_is_relative_not_absolute():
    rng = np.random.default_rng(0)
    a = rng.normal(size=(200, 23)); v = a.T @ a
    v = v / np.linalg.norm(v, ord=2) * 1e-12      # full rank, tiny scale
    b = rng.normal(size=23) * 1e-6
    out = DYN.rank_aware_wald(b, v, np.eye(23))
    assert out["degrees_of_freedom"] == 23        # currently raises "zero rank"
    assert out["wald_statistic"] >= 0.0
```

### P-value handling is honest

`rank_aware_wald` returns `"p_value": None` and
`"inferential_procedure_required": True` (lines 787-788). No chi-square is
applied anywhere in the runner, and the spec's `pretrend.interpretation`
forbids p-value-selected prewindows. `build_y05_diagnostic_definitions:874`
emits `"selection_rule": "retain full grid; do not choose a window from viewed
p-values"`. **No dishonest p-value handling found.**

---

## 7. Objective 6 — Y05 simultaneous intervals and leave-out diagnostics

`simultaneous_intervals:792-819` is statistically sound.

* **Covariance scaling is consistent.** The band half-width uses
  `se = sqrt(diag(IFᵀIF))` and the draws are studentised by the *same* `se`
  vector. Verified `np.allclose` and that `lower`/`upper` are exactly symmetric
  about `beta`.
* **Common draws are genuine.** `draws = signs @ influence` applies one sign
  vector across *all* coefficients simultaneously, which is what makes the
  maximum a valid simultaneous statistic. `signs` must be supplied by the
  caller and is validated Rademacher at line 803 — the runner never generates
  draws, so it cannot fabricate the multiplier matrix.
* **Quantile convention is conservative.** `method="higher"` on
  `np.quantile(maxima, 0.95)` rounds up.
* **Empirical coverage checks out.** 300 replications, k = 8, B = 999:
  simultaneous coverage of the true zero vector **0.960** against nominal
  0.95 — correctly conservative.
* Convergence of the critical value: `2.83` at B = 100, `2.729` at B = 1000,
  `2.726` at B = 20000.

### P3-2 — no minimum-draw guard

**Locator:** `run_dynamic_reconciliation.py:801-811`. `signs.shape[0]` is never
checked against `1/alpha`. With `B = 1` the function returns
`critical = 1.2911` — literally the studentised max of a single sign flip — and
labels it a 95 % simultaneous band. Small `B` is erratic in both directions:
`B = 2 → 1.746`, `B = 5 → 4.014`, `B = 19 → 2.860`.

**Minimal correction:** after the Rademacher check, add

```python
if signs.shape[0] < int(np.ceil(1.0 / alpha)) * 20:
    raise DynamicGateError("too few common draws for a simultaneous band")
```

and report `draws` alongside the achieved quantile index.

**Regression test:** `pytest.raises(DynamicGateError)` for
`signs` of shape `(1, n)` and `(19, n)`; pass for `(999, n)`.

### Additive-contribution labelling is correct

`leave_one_restriction_out:838` names the field
`descriptive_wald_change_not_additive_contribution`, and
`build_y05_diagnostic_definitions:864-867` repeats the caveat in prose. I
verified numerically that the changes do **not** sum to the full statistic
(sum of changes `-0.0008` vs full Wald `0.0009`). The naming is honest and no
output is mislabeled as an additive contribution.

### P3-5 — null-space component silently discarded; statistic can go negative

**Locator:** `run_dynamic_reconciliation.py:779`. With `V` exactly rank 4 out of
6 and the restriction target lying **entirely in `null(V)`**, the function
returns `wald_statistic = -2.25e-20` with `df = 4` and `rank_deficient = True`.
A restriction violated with zero sampling variance in that direction is the
strongest possible evidence against the null, yet it scores zero, and no field
reports the norm of the discarded component. Separately, `pinv` on a
roundoff-asymmetric matrix produced a *negative* Wald statistic.

**Minimal correction:** symmetrise `V` before `pinv`, clamp the statistic at
`0.0`, and add
`"target_component_outside_covariance_range": float(np.linalg.norm(target - P_range @ target))`
so the discarded magnitude is visible.

---

## 8. Objective 7 — hashes, identities, and spec/runner contradictions

### All bindings verify

| Role | Declared sha256 == actual | Tracked in HEAD |
|---|---|---|
| `dependency_release` | True | True |
| `model_audit` | True | True |
| `a1_spec` | True | True |
| `canonical_spec` | True | True |
| `target_dependency_map` | True | True |
| `focal_target_source_audit` | True | True |
| `execution_prompt` | True | True |
| `requirements_seed` | True | True |

* `spec_id` self-check: recomputed
  `yaxgate2dyn_v1_04d3acd4ef619880981277733ea66e506f3da2de5706aa231cc96c964e380e0f`
  over the canonical JSON minus `spec_id` — **match**.
* `execution.code_sha256` `2277690a…` — **matches the runner bytes**, and
  `validate_spec:190` re-derives it from `Path(__file__).resolve()`, so a
  swapped runner is caught.
* Model/certificate binding (`_model_index:300-331`) checks schema, status,
  `canonical_spec_id`, `audit_spec_id`, `cells_sha256`, duplicate model IDs,
  per-model `PASS_A1_NUMERICAL_CERTIFICATE`, `PASS_FINITE_EXTENDED_MLE_TARGET`,
  and `PASS_A1_TRUST_PATH_VS_ZERO_START_REFERENCE`. Thorough.
* Focal-target-source binding (`validate_contract_metadata:268-290`) requires
  the audit's own `source_model_audit.sha256` to equal the bound model-audit
  hash and requires `reported_value == focal_target_estimate` per core model.
  This artifact appears to have been added in response to the P3-3 finding of
  my earlier Gate 1 review; the binding is now correct.
* JSON loading is fail-closed: `object_pairs_hook` rejects duplicate keys and
  `parse_constant` rejects `NaN`/`Infinity` (lines 62-70).
* Output identity: overwrite is refused, the write is atomic via
  `NamedTemporaryFile` + `replace`, and the emitted `result_id` is
  `yaxresult_v1_ + sha256(spec_id, logical_key, artifact_sha256)`. Verified
  distinct result IDs for distinct artifact hashes.

### P2-4 — 17 behaviour-relevant signed-spec fields are inert

**Mechanism.** `validate_spec:174-208` pins only: the key set, the schema
string, the self-consistent `spec_id`, the runner byte hash, the four core
model IDs, the full calendar contract, all 39 weights, and exactly two
tolerances (`target_absolute`, `conditioning_rank_relative`). Everything else in
the signed document is decoration — the runner hardcodes the corresponding
behaviour and never compares.

I re-sealed the spec (recomputing `spec_id` after each mutation, i.e. the
attacker plays by the identity rule) and ran `validate_spec`:

| Mutation | Result |
|---|---|
| `tolerances.fitted_probability_max_absolute` `1e-7 → 1.0` | **ACCEPTED** (never read; `1e-12` hardcoded at `:632`) |
| `tolerances.objective_per_total_absolute` `1e-10 → 1.0` | **ACCEPTED** (never read) |
| `tolerances.coefficient_rebase_absolute` `1e-12 → 1.0` | **ACCEPTED** (`:496` hardcodes `1e-12`) |
| `tolerances.design_nesting_relative` `1e-12 → 1.0` | **ACCEPTED** (`:560` hardcodes `1e-12`) |
| `nesting.target_tolerance` `1e-6 → 1.0` | **ACCEPTED** (`:684` hardcodes `1e-6`) |
| `nesting.available_now` `false → true` | **ACCEPTED** |
| `pretrend.windows.2021Q1_2022Q3 → ["2021Q1","2021Q2"]` | **ACCEPTED** (`:735-746` hardcodes windows) |
| `pretrend.windows` deleted entirely (`{}`) | **ACCEPTED** |
| `outputs.declared_preflight_file → "OTHER.json"` | **ACCEPTED** (see P2-3) |
| `outputs.authoritative_output_forbidden_before_object_amendment → false` | **ACCEPTED** |
| `outputs.never_imply_requirement_completion → false` | **ACCEPTED** |
| `requirements.Y08 "UNMET…" → "COMPLETE"` | **ACCEPTED** (see P2-2) |
| `requirements.T05 "UNMET…" → "COMPLETE"` | **ACCEPTED** |
| `models.dynamic_nuisance` prose rewritten | **ACCEPTED** |
| `functionals.D` definition prose rewritten | **ACCEPTED** |
| `reparameterization.covariance_rule → "V_new = V_old"` | **ACCEPTED** |
| `execution.mode → "authoritative"` | **ACCEPTED** |
| `calendar.missing_months → []` | rejected — `signed calendar counts differ` |
| `tolerances.target_absolute → 1e-3` | rejected — `A1 target tolerance changed` |
| `tolerances.conditioning_rank_relative → 1e-6` | rejected — `A1 rank tolerance changed` |
| `post_quarter_weights["2026Q3"] → 3/42` | rejected — `frozen post weight differs` |
| spec not re-sealed (extra key) | rejected — `spec keys differ` |

**Impact.** The document's status line asserts it is an "immutable pre-result
contract," but only the numeric core is actually enforced. Seventeen fields can
be changed to say the opposite of what the runner does, and the runner will
validate and execute happily. This is a reproducibility and governance defect,
not a current numerical error.

**Minimal correction.** Read the tolerances instead of hardcoding them —
`design_nesting_relative` into `validate_design_nesting`,
`coefficient_rebase_absolute` into `verify_equivalent_restrictions` and
`verify_reference_invariance`, `nesting.target_tolerance` into
`validate_pseudo_stock_projection`, `fitted_probability_max_absolute` and
`objective_per_total_absolute` into the projection/score paths — and build the
Y04 windows from `spec["pretrend"]["windows"]` (see P2-5). For the fields that
are genuinely declarative, add explicit assertions in `validate_spec`:

```python
if spec["nesting"]["available_now"] is not False:
    raise DynamicGateError("nesting objects are not bound in this release")
if spec["execution"]["mode"] != "preflight point reconciliation only; no authoritative result claim":
    raise DynamicGateError("execution mode is not preflight")
if spec["outputs"]["authoritative_output_forbidden_before_object_amendment"] is not True:
    raise DynamicGateError("authoritative output must remain forbidden")
if spec["outputs"]["never_imply_requirement_completion"] is not True:
    raise DynamicGateError("requirement-completion suppression must remain on")
```

**Regression test.** Parameterise over each field above; for each, deep-copy the
real spec, mutate, recompute `spec_id` via `DYN.compute_spec_id`, and assert
`pytest.raises(DynamicGateError)`.

### P2-2 — a re-sealed spec can print "Y08 COMPLETE"

**Locator:** `run_dynamic_reconciliation.py:957`

```python
"requirement_disposition": spec["requirements"],
```

**Mechanism.** The requirement dispositions are copied verbatim from the spec
into the emitted report. They are never cross-checked against
`requirements_seed` (which `validate_contract_metadata:291-297` only checks for
*presence* of the eight IDs, never their status) nor against
`dependency_release.downstream_requirement_releases` (which `validate_release`
checks only for Y01–Y04). Combined with P2-4, a spec edited to say
`"Y08": "COMPLETE"` re-seals cleanly and produces a signed, content-addressed
`DYNAMIC_PREFLIGHT_REPORT.json` asserting completion of a requirement that needs
16 fits that do not exist. The spec's own guard
`outputs.never_imply_requirement_completion: true` is never read.

**Impact.** The report is otherwise hard-stamped
`analysis_status: PRE_RESULT_IMPLEMENTATION_NONAUTHORITATIVE` and
`authoritative_completion: False` (both literals, not spec-derived — good), so
this cannot manufacture an authoritative *result*. It can manufacture a
requirement-completion claim, which is precisely the thing the spec's last
line forbids. P2.

**Minimal correction.** Validate dispositions against a closed vocabulary and
enforce the two UNMET requirements structurally:

```python
ALLOWED = {"IMPLEMENTED_POINT_ONLY", "IMPLEMENTED_UNRUN",
           "IMPLEMENTED_COEFFICIENT_ONLY", "IMPLEMENTED_DEFINITIONS_ONLY"}
for key, value in spec["requirements"].items():
    if key in {"Y08", "T05"} and not value.startswith("UNMET"):
        raise DynamicGateError(f"{key} cannot be satisfied by this release")
    if key in {"Y01", "Y02", "Y03", "Y04", "Y05"} and value.split(";")[0].strip() not in ALLOWED:
        raise DynamicGateError(f"requirement disposition overclaims: {key}")
```

**Regression test.**

```python
@pytest.mark.parametrize("rid", ["Y08", "T05"])
def test_requirement_completion_cannot_be_asserted(spec_bytes, rid):
    spec = json.loads(spec_bytes)
    spec["requirements"][rid] = "COMPLETE"
    spec["spec_id"] = DYN.compute_spec_id(spec)
    with pytest.raises(DYN.DynamicGateError):
        DYN.validate_spec(spec, RUNNER)
```

### P2-3 — the result_id logical key is hardcoded and the declared filename is inert

**Locator:** `run_dynamic_reconciliation.py:1011`

```python
result_id = compute_result_id(spec["spec_id"], "DYNAMIC_PREFLIGHT_REPORT.json", digest)
```

**Mechanism.** `spec["outputs"]["declared_preflight_file"]` is never read. I ran
the runner with `--output /tmp/oid/TOTALLY_DIFFERENT_NAME.json`; it succeeded
and emitted

```json
{"path": "/tmp/oid/TOTALLY_DIFFERENT_NAME.json",
 "sha256": "4ab2d331…",
 "result_id": "yaxresult_v1_84b16fb7…"}
```

with the logical key stamped as `DYNAMIC_PREFLIGHT_REPORT.json`. The spec's
`outputs.identity_rule` says the identity is taken over "spec_id, logical key,
and artifact hash" — but the logical key here does not identify the artifact
that was actually written. Any number of differently-named files can carry
result IDs claiming the same logical key. (Overwrite refusal at `:1002` works
correctly.)

**Minimal correction.**

```python
declared = spec["outputs"]["declared_preflight_file"]
if args.output.name != declared:
    raise DynamicGateError(f"output name must be the declared {declared}")
result_id = compute_result_id(spec["spec_id"], declared, digest)
```

**Regression test.** Assert `DynamicGateError` when `--output` basename differs
from `declared_preflight_file`; assert the emitted `result_id` equals
`compute_result_id(spec_id, declared, sha256_file(path))`.

### P2-5 — the machine-readable exclusion window does not encode the exclusion

**Locator:** `DYNAMIC_RECONCILIATION_SPEC.json` `pretrend.windows`:

```json
"full_preperiod":                    ["2017Q1", "2022Q3"],
"full_excluding_2020Q2_2020Q4":      ["2017Q1", "2022Q3"]
```

The two are **byte-identical**. Read literally as an endpoint pair — the
convention used by all three sibling entries — the "excluding" window is the
full 23-quarter preperiod. The runner ignores the spec entirely and hardcodes
the exclusion at `run_dynamic_reconciliation.py:739-741`, correctly yielding 20
quarters. So the signed contract and the executed behaviour disagree, and any
independent reimplementation working from the spec would produce a
23-restriction test where the runner produces 20.

**Minimal correction.** Give the window an explicit shape and consume it:

```json
"full_excluding_2020Q2_2020Q4": {
  "span": ["2017Q1", "2022Q3"],
  "excluded_quarters": ["2020Q2", "2020Q3", "2020Q4"],
  "expected_quarter_count": 20
}
```

and have `build_y04_restrictions` take the window definitions and expected
counts from `spec["pretrend"]["windows"]` rather than from the module-level
literals at `:735-746`.

**Regression test.** Assert
`set(y04["full_preperiod"]["quarters"]) - set(y04["full_excluding_2020Q2_2020Q4"]["quarters"]) == {"2020Q2","2020Q3","2020Q4"}`
and that mutating the spec's window to a different exclusion changes the built
restriction set (currently it does not).

---

## 9. Objective 8 — no fabrication; Y08 and T05 remain unmet

**No fabrication.** A grep for `np.random`, `default_rng`, `randn`, `randint`,
`synth`, `placeholder`, `simulate` across the runner returns **nothing**. There
is no RNG anywhere in the module. `simultaneous_intervals` *requires* the
multiplier matrix as an argument and validates it is Rademacher; it cannot
invent draws. `transform_parameterization` refuses a covariance without a
matching influence matrix (`covariance and influence must be supplied
together`) and cross-checks `V = IFᵀIF`, so a fabricated covariance cannot be
smuggled in alone. The report's `object_availability` block marks all six
missing object classes `MISSING_NOT_FABRICATED`, and the `blocked` markers in
`restriction_reparameterization` (`"covariance_influence_checks":
"BLOCKED_MISSING_OBJECTS"`) are consistent with what actually ran.

**Y08 still requires 16 fresh onset fits.** The onset grid November 2022
through June 2023 is 8 monthly starts; times the two certified structures
(unconditioned, family-month) that is exactly 16. The dependency map's
`complete_onset_and_seasonality` consumer (`consumers[19]`) is described as
*"Claim complete onset and seasonality coverage only when all six post-2020 and
seasonal targets are certified"* — it binds **six** post-2020/seasonality fits
and says nothing about onset-grid fits. `requirements_seed.json` carries Y08
with `status: NOT_STARTED` and the acceptance check *"Numerical onset grid
Nov2022-Jun2023 not prose claim"*. The spec's Y08 statement is therefore
accurate, and N04's six certified fits do not discharge it.

**T05 still requires two through-December-2024 fits.** Seed status
`NOT_STARTED`, acceptance checks *"Hold preperiod labels fixed"* and *"Show both
core structures … for both windows"*. Two structures × one endpoint = 2 fits,
each needing same-objective numerical certification. Nothing in the bound
release supplies them.

I found no place where the runner, the README, or `PRE_RESULTS_SPEC.md`
implies otherwise. `PRE_RESULTS_SPEC.md` lines 53-58 state the position
correctly and explicitly reject the `complete_onset_and_seasonality` label as
sufficient.

---

## 10. Remaining P3 findings

### P3-1 — `verify_equivalent_restrictions` is a tautology

**Locator:** `run_dynamic_reconciliation.py:490-525`. The check computes
`old_target = R·β` and `new_target = (R·B⁻¹)·(B·β)`. These are algebraically
identical for **any** invertible `B`, so the comparison can only ever fail on
roundoff.

Demonstrated: the function returns
`PASS_EQUIVALENT_RESTRICTION_REPARAMETERIZATION` for a correct rebase matrix, a
matrix of random Gaussian noise, `2·I`, and a random permutation — all with
differences at `1e-16`. The covariance and influence branches are the same
tautology one level up.

**Impact.** `preflight_report:914-918` is the only place `free_rebase_matrix` is
exercised in the executed path, and it is exercised *exclusively* through this
powerless check. The reported "checks: 624" and
`maximum_absolute_target_difference` therefore carry no evidence about the
rebasing matrix at all. The algebra happens to be correct (§4), and
`test_full_reparameterization_preserves_covariance_influence_and_functional`
does pin `beta_new` against ground truth for one `(2021Q4 → 2021Q2)` pair — so
this is P3, a check with no power rather than a wrong result.

**Minimal correction.** Add an independent ground-truth arm inside the function:

```python
if period_labels is not None:
    embedded_old = np.insert(beta, labels.index(old_reference), 0.0)
    expected = embedded_old - embedded_old[labels.index(new_reference)]
    expected = np.delete(expected, labels.index(new_reference))
    if float(np.max(np.abs(beta_new - expected))) > tolerance:
        raise DynamicGateError("rebased coefficients differ from renormalized truth")
```

**Regression test.**

```python
@pytest.mark.parametrize("bad", ["scaled", "permuted", "random"])
def test_equivalent_restrictions_rejects_a_non_rebasing_transform(bad):
    ...  # assert DynamicGateError for 2*I, a permutation, and random invertible
```

### P3-3 — unjustified asymmetric test tolerance

**Locator:** `tests/test_dynamic_reconciliation.py` — `P_published_reference_post`
is pinned at `abs=1e-12` for `unconditioned` but `abs=1e-9` for `family_month`.
Measured achieved error is `2.78e-17` and `0.00e+00` respectively; summation-order
spread across 4000 random orderings is `5.6e-17` and `1.4e-16`. There is no
numerical basis for the thousand-fold looser pin, and at `1e-9` the test would
not detect a genuine regression three orders of magnitude larger than anything
attributable to floating point. Tighten both to `1e-12` (or `1e-15`).

### P3-4 — no interpreter or library pin for Gate 2

`ANALYSIS_SPEC_A1.json` pins CPython **3.13.8**. The Gate 2 `execution` block
pins only the runner byte hash — no interpreter, no numpy version. The package
tests and the runner both executed here under **CPython 3.10.5 / numpy 1.22.4**
and passed, and the committed bytecode caches are `cpython-310`. This matters
because the numerics are version-sensitive: `np.quantile(..., method="higher")`
at `:811` requires numpy ≥ 1.22 (1.22.4 is the floor, only just satisfied), and
`np.linalg.matrix_rank` / `pinv` tolerance handling changed across the 1.x → 2.x
boundary — exactly the code paths implicated in P2-1. Add a `runtime` block to
`execution` pinning the interpreter and numpy, and assert it in `validate_spec`.

### P3-6 — nesting tolerance scaled by design magnitude

`run_dynamic_reconciliation.py:572` sets `scale = max(1.0, max|Xs|)`, so the
pass bar is `1e-12 · max|Xs|`. With a design whose entries reach `1e6` the
accepted absolute residual rises to `1e-6`; I confirmed a residual of
`6.37e-06` passes at that scale. For a design of indicator columns this is
harmless (`scale = 1`), but the Webb-z columns are continuous and unbounded.
Prefer a per-column relative criterion:
`max|Xs − Xd A|_j / max(1, max|Xs_j|)` over columns `j`.

---

## 11. Explicit answers

**1. Are the S/P/D values correct?**

Yes. I recomputed all of `S`, `P`, the pre mean, `D`, `P−S`, `D−S`, `P−D`, and
the six family-month-minus-unconditioned movements from the byte-bound
`MODEL_AUDIT.json`, using a Q5 vector cross-extracted two independent ways
(agreement `0.000e+00`) and weights derived independently from the calendar
rather than read from the spec. Every value matches the runner's emitted
`point_reconciliation` to the last printed digit, and `P` matches the A1
`focal_target_estimate` to `2.8e-17` / `0.0`. `D` reproduces `S` to 0.56 % of
`|S|` (unconditioned) and 0.066 % (family-month); this is an empirical
near-coincidence, **not** an algebraic identity — the logit link, the restricted
MLE, and the differing nuisance normalisations all break exactness, and the Y02
machinery that would quantify the residual is unrun.

**2. Is the reference-invariance algebra correct for beta, covariance,
influence, and restrictions?**

Yes, exactly. 500 randomised adversarial fixtures over arbitrary
`(old, new)` reference pairs give errors of exactly `0.000e+00` for
`beta_new = B beta_old`, `V_new = B V_old Bᵀ`, `IF_new = IF_old Bᵀ`, and
`R_new = R_old B⁻¹`, with invariance of targets, restricted covariances,
restricted influence draws, and round-trips at `≤ 2.2e-15`. The one caveat is
P3-1: the *check* that guards this in the executed path is a tautology, so the
correctness is a property of the code rather than something the receipt
evidences.

**3. Are Y04/Y05 definitions statistically valid as written?**

Y04's restriction *construction* is valid — correct counts (23/12/7/20), correct
full ranks, correct encoding of both nulls under the published normalisation,
and correct exclusion of the reference quarter from the testable set. Y04's
*inference* is not yet valid as written: the rank-aware Wald's rank tolerance
is absolute rather than relative (P2-1), which mis-states the feasible degrees
of freedom the spec designates as authoritative and can reject a full-rank
covariance outright. P-value handling is honest (`p_value: None`,
`inferential_procedure_required: True`).

Y05 is statistically valid: the studentization uses the same covariance as the
band, the common Rademacher draws are genuine and caller-supplied, the quantile
convention is conservative, empirical simultaneous coverage measured 0.960
against nominal 0.95, and the leave-out output is explicitly named
*not* an additive contribution. Two bounded defects: no minimum-draw guard
(P3-2) and silent discarding of null-space restriction components (P3-5).

**4. Does any code or prose overclaim execution/completion?**

The prose does not. `README.md` and `PRE_RESULTS_SPEC.md` are accurately hedged
throughout, correctly enumerate the missing objects, and correctly state that
N04's six fits do not discharge Y08. The emitted report hard-stamps
`PRE_RESULT_IMPLEMENTATION_NONAUTHORITATIVE` and `authoritative_completion:
False` as literals.

The code overclaims in two places. `validate_design_nesting` returns
`PASS_EXACT_DESIGN_NESTING` on evidence that only establishes column-space
containment (P1-1) — the word *exact* is not earned when the map is fitted. And
`requirement_disposition` is a verbatim echo of an inert spec field, so the
runner cannot prevent a re-sealed spec from printing `Y08: COMPLETE` (P2-2),
notwithstanding the spec's own `never_imply_requirement_completion: true`, which
is likewise never read.

**5. Is the package safe to commit as a pre-result artifact?**

**Yes, with P2-2, P2-3, P2-4 and P2-5 repaired first, and P1-1 repaired before
any object-binding amendment.** Nothing in the package fabricates a missing
object, no covariance or influence or design is synthesised, no authoritative
claim is made, and every number it currently emits is correct. As a *record of
the certified point reconciliation* it is sound and I would commit it.

The P2 items are contract-integrity defects rather than numerical ones, but they
undercut the artifact's central purpose — being an immutable, self-verifying
contract — so they should be fixed in the same commit. P1-1 does not affect any
current number, because nesting is unrun and the six objects are unbound; it
must be fixed before the amendment that binds them, because that is the moment
it would silently certify the Y02 falsification test on insufficient evidence.

---

## 12. Verification provenance

* Repository read-only throughout; `git status` unchanged, `git diff --check`
  clean, no file in the repository created or modified. Bytecode caches
  pre-existed at the producer's mtime and were reused.
* All adversarial fixtures were constructed under `/tmp` and deleted at the end
  of the review (`/tmp/oid`, `/tmp/specmut`, `/tmp/preflight_out.json`,
  `/tmp/preflight_err.txt`).
* The runner was executed twice: once to stdout with the eight bound inputs
  (exit 0, no write), and once with `--output` pointed **outside** the
  repository to test the identity rule.
* No SCC access, no protected CPS microdata, no aggregate cells, no credential
  inspection.
* Focused test suite: **13 passed**. `git diff --check`: **0 issues**.
