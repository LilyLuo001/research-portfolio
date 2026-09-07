# Claude adversarial re-review — YAX Gate 2 dynamic-reconciliation repair adjudication

Date: 2026-09-07
Reviewer: Claude (read-only adversarial re-review)
Scope: repaired Gate 2 dynamic-reconciliation preflight package, `gate2/dynamic/`

**Verdict: `SAFE_TO_COMMIT_AS_PREFLIGHT`**

- **Commit safety:** SAFE. The package may be committed as a preflight point
  reconciliation. P1 = 0, P2 = 0, P3 = 4.
- **Execution safety:** **NOT SAFE TO AUTHORIZE** authoritative object-bearing
  execution. This is a separate decision and is **not** implied by the commit
  verdict. See §7. The blocking item is P3-A, which is inert in preflight but
  becomes live the moment covariance and influence objects exist.

All three stated targets matched exactly. Focused suite: **37 passed** in 1.36 s.
The repository was not modified.

---

## 0. Byte gate and provenance

| Target | Expected | Recomputed | Result |
|---|---|---|---|
| Runner SHA-256 | `003374bc13f23afa775744dc2f06c2e27efb85cf68df90151d5e6536854f77ec` | identical | MATCH |
| Spec ID | `yaxgate2dyn_v1_73d2a2bac3e50ab53a116419e63d85d59fdc38a0375d9ea4d0f91324ed06bb62` | identical | MATCH |
| Signed behavior SHA-256 | `f144dba560a6bbfd0b9a6eb6fa7bcfa7eddffd2ac5e6f56b91be903016779215` | identical | MATCH |

Spec ID was recomputed independently as `sha256(canonical_bytes(spec minus spec_id))`
and the behavior digest as `sha256(canonical_bytes(spec minus spec_id minus
execution.code_sha256))`. Both reproduce. No byte instability.

Supporting digests: `DYNAMIC_RECONCILIATION_SPEC.json` =
`ac6f10781f18b42ae5588a97d2a92657eda73bc46db60ca71adc5bb0c7469241`;
`tests/test_dynamic_reconciliation.py` =
`69f507d85e3721d979cb3b3c4ea103d37a54fa0a1d6dd59902b636b3cac6e1b7`.

### HEAD deviation — adjudicated benign, not byte instability

The prompt expected tracked HEAD to remain `9c197418122623cd86f0a4990ffa4013ba93b656`.
Observed HEAD is **`69d3c9eddc1174daeb06915b57d3168d8a041613`** ("Validate Gate 2 D02
authoritative audit").

I did not stop, for three reasons, and I flag the deviation explicitly rather than
silently accepting it:

1. The move is the **parallel D02 work**, which the prompt itself places out of scope.
   `69d3c9ed` sits on top of `9c19741`.
2. All three *stated* targets — the only bytes the prompt actually pins — match exactly.
3. `git status --porcelain` reports the entire dynamic package as untracked
   (`?? yax/revision/substantive_v3_20260906/gate2/dynamic/`), i.e. the reviewed bytes
   are not affected by the commit at all.

`git diff --check` is clean.

---

## 1. Baseline evidence reproduced

### 1.1 Focused suite

`python3 -m pytest tests/ -q` → **37 passed, 0 failed, 1.36 s**.

### 1.2 Calendar and frozen partial-quarter weights — recomputed from months, not read

I enumerated the observed window month by month and derived the weights independently
of any runner code.

- Observed 2017-01…2026-07 = 115 calendar months; minus the declared missing 2025-10
  → **114 observed**; minus the transition month 2022-12 → **113 fit**. Matches
  `expected_month_counts` exactly.
- Pre 2017-01…2022-11 → **71** months. Post 2023-01…2026-07 minus 2025-10 → **42** months.
- Equal weight per *actually observed* month gives quarter weights 3/71 and 3/42, with
  partials 2/71 (2022Q4), 2/42 (2025Q4), 1/42 (2026Q3).
- Every one of the 24 pre and 15 post frozen weights in the spec reproduces
  **bit-for-bit** (`==` on the float, not `isclose`).
- Derived partial quarters `{2022Q4:2, 2025Q4:2, 2026Q3:1}` match the declared
  `calendar.partial_quarters` exactly. No quarter is completed and 2025-10 is never
  interpolated.

### 1.3 S, P, D and conditioning movements — recomputed independently

I wrote a separate parser for `solver_comparison.reference_target_vector`, built my own
39-quarter label list, and applied my own month-derived weights. All eight authenticated
inputs named by the spec were located in-repo **by content hash** and all eight matched,
including `model_audit` = `ffb4364a…` at
`runs/gate1_numerical_a1_pass_7482383/numerical/MODEL_AUDIT.json`.

| Quantity | unconditioned | family_month |
|---|---|---|
| S (static) | −0.1321094507921904 | −0.021674952018246887 |
| P (published-reference post) | −0.11988876533150444 | −0.20743368917400506 |
| D (post − pre) | −0.13137216692526124 | −0.021689316018639354 |
| pre average rel. 2022Q4 | 0.011483401593756796 | −0.1857443731553657 |
| P − S | 0.01222068546068597 | −0.1857587371557582 |
| D − S | 0.0007372838669291726 | −1.4364000392466658e-05 |

Conditioning movements (family_month − unconditioned): S 0.11043449877394353,
P −0.08754492384250062, D 0.10968285090662189, P−S −0.19797942261644416,
D−S −0.0007516478673216392.

My independently rebuilt P reproduces the **certified** dynamic focal target to
2.776e-17 (unconditioned) and to **exactly zero** (family_month) — the runner's internal
cross-check against `focal_target_estimate` is therefore a real constraint, not a
restatement. Comparing all 14 structure values and 5 movements against the runner's
`build_point_reconciliation` output: **0 bitwise mismatches**.

### 1.4 Randomized rebasing invariance — all seven object types

400 randomized trials (K ∈ [3,9] quarters, random old/new reference pairs, random
restriction matrices, influence-generated covariance, coefficient scales spanning
1e-3 … 1e3).

| Object | Worst deviation |
|---|---|
| coefficient | 0.000e+00 |
| covariance | 0.000e+00 |
| influence | 1.332e-15 |
| restriction | 1.776e-15 |
| target | 9.095e-13 |
| restricted covariance | 1.421e-14 |
| round-trip β / cov / influence / restriction | 2.15e-16 / 3.63e-16 / 2.22e-16 / 6.70e-16 |
| ground-truth renormalization | **0.000e+00** |

"Ground truth" is computed outside the runner entirely: embed β in the full series,
subtract the new reference coefficient, re-extract the free block. The runner's
transform reproduces it exactly in all 400 trials.

Reference invariance of the P−pre functional on the **real** 39-quarter label set:
200 randomized full coefficient series, 39 references checked per trial, **0 violations**,
worst deviation 7.772e-16.

6 of the 400 trials raised `DynamicGateError`. These are **not** algebra failures — they
are the absolute-tolerance artifact documented as **P3-A** below.

---

## 2. Original findings re-tested behaviourally

Each was re-tested with an adversarial example against the actual bytes, not by reading
test names or spec prose.

**P1-1 — exact design nesting must require a caller-supplied predeclared map: CLOSED.**
`validate_design_nesting` (lines 762–806) raises
`"exact nesting requires a caller-supplied predeclared mapping"` when `mapping is None`;
there is no internal least-squares estimation of the map. Residuals are scaled
**per static-design column** (`scale_by_column`, `relative_by_column`), closing the
former global-magnitude scaling. `nesting.predeclared_mapping_required` is `true` and
deleting it is rejected with `"exact nesting must require a predeclared mapping"`.

**P2-1 — one eigendecomposition, one scale-relative cutoff: CLOSED.**
`rank_aware_wald` (1018–1121) performs a single `np.linalg.eigh` at line 1060. PSD, rank,
inverse, range, statistic and df all reuse that one decomposition and the single cutoff
`relative_eigenvalue_tolerance * spectral_scale`. Both tolerances are pinned against
`EXPECTED_TOLERANCES`; three caller-override attempts were blocked.

**P2-2 — dispositions must be closed behavior, not echoed spec prose: CLOSED.**
`REQUIREMENT_DISPOSITIONS` is a runner-source constant. Six re-seal attempts on `Y08`
and `T05` (`"COMPLETE"`, `"MET: done"`, `"COMPLETE: all fits delivered"`) were all
rejected with `"closed requirement dispositions changed"`, as were deletion of either key.
Both remain prefixed `UNMET:`.

**P2-3 — basename / logical key / artifact hash / result ID agreement: CLOSED.**
`validate_output_path` now returns the `logical_name` taken from the spec-declared
filename. `RESULTS.json` and the case-variant `DYNAMIC_PREFLIGHT_REPORT.JSON` were both
rejected with `"output basename differs from declared preflight file"`; the declared name
passed; overwriting an existing output was refused.

**P2-4 — signed-behavior anchoring: CLOSED.** See §5.

**P2-5 — structured pretrend windows: CLOSED.** Implemented behaviour, read out of the
built restriction objects rather than the spec text:

| Window | n | first | last |
|---|---|---|---|
| full_preperiod | 23 | 2017Q1 | 2022Q3 |
| 2017Q1_2019Q4 | 12 | 2017Q1 | 2019Q4 |
| 2021Q1_2022Q3 | 7 | 2021Q1 | 2022Q3 |
| **full_excluding_2020Q2_2020Q4** | **20** | 2017Q1 | 2022Q3 |

2020Q2/Q3/Q4 excluded: yes. **2020Q1 retained: yes.** Count == 20: yes. A mutated window
contract is rejected with `"Y04 window contract differs from the frozen specification"`.

**P3-2 — 9,999 common-draw minimum non-overridable: CLOSED.** 100 draws and 9,998 draws
both blocked (`"too few common multiplier draws"`); 9,999 accepted; a non-Rademacher
{0,1} matrix blocked (`"multiplier matrix is not Rademacher"`). `minimum_draws` is **not**
a parameter of `simultaneous_intervals` — its signature is
`(beta, influence, multiplier_signs, alpha)` — so there is no caller override surface,
and a re-sealed spec mutation of `pretrend.minimum_common_multiplier_draws` is rejected.

**Leave-one-quarter diagnostics: CLOSED.** `leave_one_label_out_diagnostics` (1165–1203)
omits a **quarter label** and rebuilds the null on the remaining labels. Omitting the
anchor `L0` replaces it (`rebuilt_anchor = L1`); omitting any non-anchor keeps `L0`. The
remaining-label set changes on every iteration, confirming this is leave-one-**quarter**
and not a mislabelled leave-one-restriction diagnostic. The output field is named
`descriptive_wald_change_not_additive_contribution`, which correctly refuses an additive
decomposition reading.

**Nonfinite fail-closed — CLOSED across every named object type.**
51 injections of NaN / +Inf / −Inf into design, score/projection inputs, covariance,
restriction, influence, transform and coefficient objects, across
`transform_parameterization`, `transform_restrictions`, `rank_aware_wald`,
`fit_grouped_logit_projection`, `simultaneous_intervals` and
`leave_one_label_out_diagnostics`: **51 blocked, 0 leaked.**

*Methodological note.* My first pass of the six `leave_one_label_out_diagnostics` cases
blocked on a label-count mismatch (`"leave-label-out coefficient labels differ"`), not on
nonfiniteness — the intended check was masked because β must be the **full-series**
length. I re-ran those six with a passing clean control; all six then blocked correctly on
`"Wald objects must be finite"`. Only the unmasked results are counted above.

**P3-4 — runtime metadata explicit without inventing a production pin: CLOSED.**
`production_runtime_pin` is `"UNAVAILABLE_REQUIRES_PREEXECUTION_BINDING"`. Four attempts
to substitute an invented pin (`"python 3.10.5 / numpy 1.22.4"`, `"3.10.5"`, `"BOUND"`,
`"PINNED_AT_EXECUTION"`) were each rejected with `"production runtime pin state changed"`;
only the honest sentinel is accepted. `tested_runtime` (`python 3.10.5 / numpy 1.22.4`)
and `runtime_requirements` (`python >=3.10 / numpy >=1.22`) are separately pinned and
independently mutation-blocked. The package states what it was tested on and refuses to
pretend it has a production pin.

**P3-1 — restriction-equivalence tautology: PARTIALLY CLOSED, carried forward as P3-B.**

---

## 3. The repaired covariance-range contract (the most important new check)

Reproduced the prompt's decisive case exactly: `V = 11ᵀ` (rank 1, p = 3), `R = I`,
`β = (0.2, −0.1, 0.3)`.

**Result: raises `BLOCKED_TARGET_OUTSIDE_ESTIMABLE_COVARIANCE_RANGE` before any Wald
statistic, degrees of freedom, or p-value is produced.** I verified this by ordering, not
by inspection: in `rank_aware_wald` the null-component block (`null_projection`,
`null_component`, `target_range_residual_relative`, the raise at ~line 1088) precedes the
line that forms `projected_target` and the statistic. No partial full-null result escapes.

**Shared spectral objects.** PSD, rank, inverse, range and statistic all consume the
single `eigenvalues, eigenvectors = np.linalg.eigh(symmetric_covariance)` and the single
`retained = eigenvalues > eigenvalue_cutoff` mask. There is no second decomposition and no
second threshold anywhere in the function.

**Dimensionless scale — verified invariant, not asserted.** The range residual is
`‖null_component‖₂ / max(‖target‖₂, sqrt(λ_max), tiny)`. Under coherent rescaling
β → cβ, V → c²V, the numerator and both live denominator candidates scale by exactly c,
so the ratio is invariant. I confirmed this numerically across **16 orders of magnitude**
of c: the computed `target_range_residual_relative` was **exactly** invariant. This is the
correct signed dimensionless construction.

**Adversarial cases — all behave correctly:**

| Case | Behaviour |
|---|---|
| Material out-of-range (`V = 11ᵀ`, `R = I`) | BLOCKED with the correct sentinel, before any statistic |
| Near-roundoff in range | Passes; residual reported |
| Nearly singular | Rank-reduced via the shared cutoff; df reduced accordingly |
| Zero scale | Fails closed |
| Asymmetric covariance | Fails closed |
| Indefinite covariance | Fails closed |
| NaN / Inf | Fails closed (`"Wald objects must be finite"`) |
| Coherent rescaling | Exactly invariant |

**No projected-range statistic is presented as the declared null.** The function returns
`"p_value": None` and `"inferential_procedure_required": True`, so no path converts the
projected statistic into a declared-null test. I found no code presenting a
projected-range statistic as anything other than a blocked or explicitly incomplete result.

One residual observation is carried forward as **P3-D**.

---

## 4. Transform semantics, not merely invertibility

`verify_equivalent_reference_rebase` never *uses* a supplied transform. It derives
`expected_transform = free_rebase_matrix(period_labels, old_reference, new_reference)`
from the labels alone, checks any supplied transform against it, and then reparameterizes
with the **label-derived** matrix. The returned
`transform_used: "EXACT_LABEL_DERIVED_FREE_REBASE_MATRIX"` is therefore an accurate
description of behaviour.

- **Semantic rejection:** 12 hand-built invertible-but-wrong transforms (`2I`,
  permutations, sign flips, random nonsingular) were all rejected with
  `"supplied transform does not equal unique reference-rebase map"`. A further 30
  randomly perturbed variants of the *correct* matrix (`B + 0.3·N(0,1)`) were rejected
  **30/30**. Invertibility alone buys nothing.
- **Correct maps pass and reproduce ground truth:** 200 randomized old/new reference
  pairs all passed, and the resulting coefficient renormalization matched the externally
  computed ground truth with worst deviation **0.000e+00**.
- **Scope is honestly labelled:** the generic entry point returns the distinct status
  `PASS_EQUIVALENT_GENERIC_LINEAR_REPARAMETERIZATION`, and the spec records that
  "arbitrary invertible transforms may pass only generic linear equivalence and cannot
  certify a reference rebase". The two claims are not conflated.

---

## 5. Signed-behavior mutation matrix

**Behavior-relevant fields tested: 185** — 149 leaf-value mutations plus 36 structural
mutations. Every mutation re-sealed the top-level `spec_id` so that a stale-hash rejection
could not be mistaken for a semantic one.

- **149 / 149 leaf mutations blocked.** Coverage included every tolerance (including
  `target_range_relative` and `conditioning_rank_relative`); all nesting availability,
  mapping, score and projection declarations; every pretrend span, exclusion list,
  expected count, null, rank rule, diagnostic and draw minimum; execution mode, command,
  runtime records, tested runtime and production-pin status; output filename, identity
  rule, authoritative-output guard and completion guard; all eight Y01–Y05 / N04 / Y08 /
  T05 dispositions; calendar and functional definitions, weights and gaps; and the model
  core and required-object declarations.
- **36 / 36 structural mutations blocked** (16 key additions at every nesting level, 16
  key deletions, 4 in-memory NaN injections), with **both controls accepted** — the
  unmodified spec and the merely-resealed spec both validate, so the blocks are semantic,
  not artifacts.
- **Loader-level fail-closed:** duplicate JSON keys rejected (`"duplicate JSON key:
  tolerances"`); raw `NaN` and `Infinity` literals rejected (`"non-finite JSON
  constant"`).

**Re-sealed contradictions still accepted: none.** Every mutation I could construct was
rejected after re-sealing.

**What anchors the digest — the decisive question.** The trust chain does *not* terminate
in a mutable digest stored in the same spec. `compute_signed_behavior_sha256` hashes the
whole spec **minus `spec_id` and minus `execution.code_sha256`**, and compares the result
to `EXPECTED_SIGNED_BEHAVIOR_SHA256`, a **string constant in the runner source at line
~22**. The runner file is itself externally hashed
(`003374bc…`, independently verified in §0). An attacker who edits the spec cannot re-seal
their way past this, because the expected value lives in different, separately hashed
bytes. This is a correct anchor and it is what closes P2-4.

Note that mutating `execution.code_sha256` is *excluded* from the behavior digest by
design — that field is checked directly against the hash of the runner file, so it is
anchored by a different mechanism rather than left unchecked.

---

## 6. Scope — the package remains a preflight point reconciliation only

- `build_point_reconciliation` returns status
  `PASS_CERTIFIED_POINT_RECONCILIATION_ONLY`.
- `execution.mode` = "preflight point reconciliation only; no authoritative result claim".
- `outputs.authoritative_output_forbidden_before_object_amendment` = `true`;
  `outputs.never_imply_requirement_completion` = `true`.
- Dispositions claim **no** authoritative results: Y01 `IMPLEMENTED_POINT_ONLY`, Y02
  `IMPLEMENTED_UNRUN`, Y03 `IMPLEMENTED_COEFFICIENT_ONLY`, Y04 and Y05
  `IMPLEMENTED_DEFINITIONS_ONLY`, Y08 and T05 both `UNMET:`.
- N04 explicitly does **not** complete Y08: the spec records that Y08 still requires 16
  fresh onset fits, and T05 still requires 2 through-December-2024 fits.
- `reparameterization.unavailable_now` lists full covariance, occupation influence and the
  common multiplier matrix; `nesting.available_now` is `false` with six missing objects
  enumerated.
- `README.md` and `PRE_RESULTS_SPEC.md` were scanned for overclaim; every occurrence of
  "authoritative", "complete" or "validated" appears in a *negating* construction
  ("does not execute or certify an authoritative Gate 2 result", "An authoritative
  analysis requires a future frozen…", "do not complete Y08").

No onset-grid completion, endpoint completion, dynamic covariance or influence inference,
or protected-data execution is claimed anywhere. **Scope confirmed.**

---

## 7. Findings

### P1 — none.
### P2 — none.

### P3-A — `coefficient_rebase_absolute` is an absolute tolerance gating two quantities of different units *(execution-blocking, preflight-inert)*

`verify_equivalent_linear_reparameterization` compares
`max|Rβ − R_new β_new|` **and** `max|RVRᵀ − R_new V_new R_newᵀ|` against the *same*
absolute number, `tolerances.coefficient_rebase_absolute = 1e-12`. The first quantity has
units of β; the second has units of β². A single absolute bar cannot be dimensionally
correct for both.

Measured behaviour — the relative error is pinned at roundoff (~1e-16) at every scale,
but the absolute bar is not:

| β scale | max abs difference | relative | verdict |
|---|---|---|---|
| 1e-6 … 1e0 | 4.2e-22 … 4.4e-16 | ~1e-16 | PASS |
| 1e2 | 5.68e-14 | 1.84e-16 | **BLOCKED** (covariance branch) |
| 1e3 | 1.14e-13 | 3.69e-17 | **BLOCKED** (covariance branch) |
| 1e4 | 3.64e-12 | 1.18e-16 | **BLOCKED** (target branch) |
| 1e6 | 3.49e-10 | 1.13e-16 | **BLOCKED** (target branch) |

The covariance branch fails **two orders of magnitude earlier** than the target branch,
exactly as the squared units predict. This is the cause of the 6/400 failures in §1.4.

*Why this is not a P2 today:* it is fail-**closed** (it produces spurious refusals, never
a wrong number); `reparameterization.unavailable_now` lists full covariance and influence,
so the restricted-covariance branch is not exercised in preflight at all; and the largest
dynamic coefficient in the bound audit is 0.4062, giving roughly **1100× headroom** at
production scale.

*Why it blocks execution authorization:* the moment covariance and influence objects
arrive — which is precisely what authoritative object-bearing execution means — the
restricted-covariance comparison goes live in β² units against a 1e-12 absolute bar, and
will refuse valid work for purely numerical reasons.

**Minimal correction:** divide each difference by its own scale before comparison —
`max|Rβ − R_newβ_new| / max(‖Rβ‖∞, tiny)` and
`max|RVRᵀ − ...| / max(‖RVRᵀ‖∞, tiny)` — and rename the spec key to
`coefficient_rebase_relative`, matching the already-relative `target_range_relative` and
`design_nesting_relative`. **Regression test:** assert that a rebase certified at β scale
1.0 is still certified at β scale 1e4 and 1e-6 with the same restriction matrix.

### P3-B — residual tautology in the target-equivalence comparison *(carried forward from P3-1, partially closed)*

Because `transform_restrictions` defines `R_new = R B⁻¹`, the quantity
`R_new(Bβ) − Rβ` is an algebraic identity in exact arithmetic. I confirmed this directly:
`R_new == R B⁻¹` is `True`, and `max|R_new(Bβ) − Rβ| = 8.88e-16`. So
`maximum_absolute_target_difference` is a **roundoff meter, not a test** — it cannot fail
for a semantic reason.

The finding is *partially* closed because the non-tautological content has been correctly
relocated: `verify_equivalent_reference_rebase` now derives B from labels and rejects
wrong transforms (42/42 across §4), and the returned `transform_used` field discloses
this. What remains is a presentational risk — a reader could mistake the reported
difference for evidence of semantic equivalence.

**Minimal correction:** rename the field to
`maximum_absolute_target_roundoff_not_semantic_test`, or document at the return site that
the semantic content lives in the transform comparison. **Regression test:** assert the
field remains below 1e-14 for a *deliberately wrong but invertible* transform passed
through the generic entry point, demonstrating it does not discriminate.

### P3-C — three spec-key deletions raise `KeyError` instead of `DynamicGateError`

Deleting `calendar.missing_months`, `functionals.pre_quarter_weights` or
`functionals.post_quarter_weights` produces an unhandled `KeyError` rather than the
package's own fail-closed exception type. Behaviour is still fail-closed — nothing
validates — but these three keys are not covered by the structural key-set check that
catches every other deletion, and a bare `KeyError` is harder to attribute during
triage.

**Minimal correction:** add the three keys to the explicit required-key assertion in
`validate_spec` alongside the existing checks. **Regression test:** parametrize deletion
over all required keys and assert `DynamicGateError` (not `KeyError`) in every case.

### P3-D — in-range-but-nonzero null component passes silently within the tolerance band

A target whose null-space component lies between machine roundoff (~1e-16) and the signed
`target_range_relative = 1e-5` bar passes the range check and proceeds to a statistic. The
statistic is then formed on the retained subspace only, so a genuinely non-estimable
component up to 1e-5 relative is discarded rather than flagged.

This is **disclosed, not silent** in the strict sense: the output carries both
`covariance_null_space_target_component_l2` and `target_range_residual_relative`, so a
reader can see exactly how much was dropped. That is why this is P3 and not P2.

**Minimal correction:** none required for preflight. Before authoritative use, add an
explicit `range_residual_within_tolerance_but_nonzero` boolean to the output so the
condition is machine-detectable rather than requiring numeric inspection.
**Regression test:** construct a target with residual 1e-7, assert it passes and that the
new flag is `True`.

---

## 8. Conclusion — the two decisions, kept separate

**Commit safety: `SAFE_TO_COMMIT_AS_PREFLIGHT`.** Every original P1 and P2 finding is
closed by demonstrated behaviour, not by producer claim, spec prose, or test naming. I
re-tested each with an adversarial example against the actual bytes. The point arithmetic
reproduces bit-for-bit against an independent implementation; the signed-behavior contract
is anchored in immutable externally-hashed runner bytes and survived 185 mutations; the
new covariance-range contract behaves correctly on the decisive case and on every
adversarial variant I could construct; and transform semantics reject invertible-but-wrong
maps 42/42 while reproducing ground truth 200/200. The four P3 findings are documentation,
naming, error-type and tolerance-scaling issues. None can change a reported number in the
preflight package.

**Execution safety: NOT SAFE TO AUTHORIZE.** This is a separate decision and I am
deliberately not collapsing it into the commit verdict. Three conditions must be met first:

1. **P3-A must be repaired.** It is inert only because covariance and influence objects do
   not yet exist. Authoritative execution is exactly the event that makes it live.
2. **`production_runtime_pin` must be bound.** It is honestly declared
   `UNAVAILABLE_REQUIRES_PREEXECUTION_BINDING`, and the runner correctly refuses to accept
   an invented substitute — but a package cannot be authoritatively executed against an
   unbound runtime.
3. **The objects the spec declares missing must actually arrive.** `nesting.available_now`
   is `false` with six enumerated missing objects, and Y08 and T05 remain `UNMET:`,
   requiring 16 fresh onset fits and 2 through-December-2024 fits respectively. Nothing in
   this package supplies them, and nothing in it claims to.

---

## 9. Review conduct

- **The repository was not modified.** No file was edited, staged, committed, reset,
  cleaned or pushed. The dynamic package remains untracked
  (`?? yax/revision/substantive_v3_20260906/gate2/dynamic/`) and `git diff --check` is
  clean.
- SCC was not run. No protected microdata or aggregate cells were opened. Only the eight
  authenticated public inputs named by the spec were read, each verified by content hash.
- All adversarial fixtures were created under temporary directories outside the repository
  and deleted on completion.
- Staged and untracked D02 and support-inference files were treated as out of scope.
- The one deviation from the prompt's stated preconditions (HEAD moved from `9c197418…`
  to `69d3c9ed…`) is reported in §0 rather than silently accepted, and was adjudicated
  benign because all three pinned targets matched and the reviewed bytes are untracked.
- Two of my own intermediate batteries produced masked results — the
  `leave_one_label_out_diagnostics` nonfinite cases (§2) and an initial structural
  mutation run whose control itself failed on a missing `code_path` argument (§5). Both
  were discarded and re-run with passing controls. Only unmasked results are reported.

**Counts: P1 = 0, P2 = 0, P3 = 4. Focused tests: 37 passed.**
