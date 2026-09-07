# YAX Gate 1 A1 — final post-run numerical and release audit

Reviewer: independent adversarial artifact review (Claude, read-only session)
Date: 2026-09-07
Target commit: `d98371d5c52f86d961c69b8c20b4bfbf99b92136`
Branch: `task/yax-v3-execution-20260906`

## 0. Tree state gate

`HEAD` = `d98371d5c52f86d961c69b8c20b4bfbf99b92136` — matches the required commit.
Working tree clean; no modified, staged, or untracked files. Review proceeded.

One prompt/repo discrepancy, non-substantive: the prompt lists
`contracts/gate1_pre_execution/PRE_EXECUTION_AUTHORIZATION.json`. That path does
not exist. The authorization is at
`gate1_transfer/PRE_EXECUTION_AUTHORIZATION.json`, which is the file committed in
authorization commit `b7c9e1c2d165c88d185cf85559f83b6329204ceb`. I reviewed the
real file.

## 1. Verdict

**No P1. One P2 (labeling/disclosure in retained public evidence). Four P3.**

The numerical result stands. I independently recomputed the load-bearing
quantities rather than reading status flags, and every scientific and numerical
acceptance conjunct that I could recompute did recompute. The single P2 is a
vacuous boolean in a preserved evidence file; it changes no certification, no
release, and no coefficient.

Answers to the five required questions are in §7.

---

## 2. Purpose 1 — numerical certification of all 11 models

### 2.1 What I recomputed independently

- `MODEL_AUDIT.json` SHA-256 = `ffb4364af0bc55026fd6ebf0f0211938e71c41b382e62897263f1d437b4b8f89`,
  equal to the receipt's bound value and to the ledger's declared value.
- Receipt SHA-256 = `84aa54a8b194774cddf814baca8d13520382262373682c3732b1dbd739aa4383`.
- All 8 entries of `receipt.output_hashes` recompute against the retained files.
  No entry is asserted-only.
- Strict JSON parse with `parse_constant` trapping proves the audit contains no
  `NaN`, `Infinity`, or `-Infinity` token anywhere. There are no non-finite
  numbers hidden in the artifact.
- 11/11 models carry `classification = PASS_FINITE_EXTENDED_MLE_TARGET`,
  `finite_target_established = true`, and
  `a1_certification.status = PASS_A1_NUMERICAL_CERTIFICATE`, including
  `seasonal_occupation_month_family_month` and the previously
  double-failing `seasonal_quintile_month_unconditioned`.

### 2.2 Trust path vs. independent reference at the unchanged tolerances

The declared final tolerances in every model's `solver_comparison.same_final_tolerances`
are exactly the A1 values, not relaxed:

```
target_coefficient_absolute_difference : 1e-06
fitted_probability_max_abs_difference  : 1e-07
objective_difference_per_total         : 1e-10
```

I did not accept `comparison_pass`. For every model I re-derived
`|trust[label] − reference[label]|` from the two stored target vectors and
compared against the stored `identified_treatment_absolute_differences`.
**Zero mismatches across all 11 models and all labels.** Recomputed margins:

| model | ‖Δ treat vec‖∞ (≤1e-6) | Δ fitted prob (≤1e-7) | \|Δ obj/total\| (≤1e-10) |
|---|---:|---:|---:|
| dynamics_family_month | 7.633e-09 | 1.037e-08 | 5.551e-17 |
| dynamics_unconditioned | 4.545e-10 | 1.095e-10 | 0.000e+00 |
| family_month | 9.835e-12 | 8.214e-11 | 0.000e+00 |
| family_post | 9.817e-12 | 6.854e-12 | 0.000e+00 |
| pooled | 9.672e-13 | 6.957e-12 | 0.000e+00 |
| post_2020_family_month | 4.098e-11 | 9.920e-10 | 0.000e+00 |
| post_2020_unconditioned | 1.216e-10 | 5.153e-10 | 0.000e+00 |
| seasonal_occupation_month_family_month | 1.584e-13 | 3.057e-10 | 0.000e+00 |
| seasonal_occupation_month_unconditioned | 4.933e-13 | 5.034e-11 | 0.000e+00 |
| seasonal_quintile_month_family_month | 2.525e-10 | 4.282e-10 | 0.000e+00 |
| seasonal_quintile_month_unconditioned | 8.951e-16 | 7.175e-12 | 0.000e+00 |

Every model clears each threshold by at least two orders of magnitude; the
tightest is `dynamics_family_month` at 1.037e-08 against 1e-07. The reference is
`independent-damped-sparse-newton-irls` with a zero start, which is a genuinely
distinct algorithm on the same objective, as A1 §5 requires.

### 2.3 Hessian, evaluator, profile, rank, boundary

- Raw **and** diagonally scaled fitted-Hessian certificates are present for both
  candidates in all 11 models. Every one passes with
  `smallest_certified_lower_bound > rank_threshold`, and I confirmed the
  threshold is genuinely derived as `1e-10 × largest_conservative_upper_bound`
  rather than hardcoded. `rank_deficiency = 0` everywhere.
- The six large models (up to 7,733 columns) use sparse `eigsh` with explicit
  eigenpair residual norms and conservative two-sided bounds — not an
  unexamined dense inverse.
- Cross-evaluation tolerances are the declared A1 values (1e-10 / 1e-7 / 1e-7),
  not inflated. External evaluator/derivative preflight passes for all 11.
- All 11 target profiles are `PASS_TWO_SIDED_FINITE_PROFILE` with 5 grid points
  each (55 rows in `TARGET_PROFILE.csv`, all `success=True`, all objectives
  finite). `center_fixed_target_equals_certified_full_optimum` holds.
- Extended-likelihood faces: all `PASS_FINITE_FACE_RESOLVED`. Separation `False`
  for all 11.
- Row accounting reconciles exactly for every model:
  `input_rows = positive_total_rows + zero_total_rows` and
  `core_rows = positive_total_rows − profiled_boundary_rows`. Boundary groups
  are profiled, not deleted; `BOUNDARY_PROFILING.csv`
  `sum(affected_rows_before_union)` equals `profiled_boundary_rows` exactly for
  each of the four models with boundary structure (77, 77, 770, 770).

### 2.4 L-BFGS-B remains diagnostic only

L-BFGS-B **actually ran** for all 11 models (present in `solvers` and
`OPTIMIZER_TRAJECTORIES.json` for every model). It fails the 1e-4 standardized
score threshold in every case, range **4.358e-04 … 2.953e-03**, and is marked
`numerically_valid: false` throughout. It is never promoted to a required
passing solver. Critically for A1 §5's "resolve the contradiction" clause:

- `diagnostic_candidate_independently_stationary` is `false` for all 11;
- all objective gaps are positive at machine epsilon — L-BFGS-B never attains a
  materially better objective;
- every `lbfgsb_diagnostic_contradiction_audit` check is true, and my own
  independent violation scan over the audit returned **NONE**.

So there is no better independently stationary contradictory target.

### 2.5 Newton polish

Exactly one model was polished: `seasonal_quintile_month_unconditioned`,
correctly gated on external-certificate failure (`trigger` recorded), with both
`before` and `after` metrics retained and a parameter change of 5.896e-06. The
polish is a warm-start refinement of the trust candidate; the independent
reference is unaffected, so corroboration is not circular.

### 2.6 Focal estimates and key solver differences

| model | focal target | trust-ncg | trust-path | L-BFGS-B |
|---|---:|---:|---:|---:|
| pooled | -0.132109451 | -0.132109451 | -0.132109451 | -0.132109461 |
| family_post | -0.021598985 | -0.021598985 | -0.021598985 | -0.021598879 |
| family_month | -0.021674952 | -0.021674952 | -0.021674952 | -0.021674351 |
| dynamics_unconditioned | -0.119888765 | -0.119888765 | -0.119888765 | -0.119889666 |
| dynamics_family_month | -0.207433689 | -0.207433694 | -0.207433694 | -0.207432981 |
| post_2020_unconditioned | -0.118069092 | -0.118069092 | -0.118069092 | -0.118069089 |
| post_2020_family_month | -0.030402197 | -0.030402197 | -0.030402197 | -0.030402246 |
| seasonal_quintile_month_unconditioned | -0.132600724 | -0.132600738 | -0.132600724 | -0.132600705 |
| seasonal_quintile_month_family_month | -0.022570213 | -0.022570213 | -0.022570213 | -0.022570019 |
| seasonal_occupation_month_unconditioned | -0.132373672 | -0.132373672 | -0.132373672 | -0.132373640 |
| seasonal_occupation_month_family_month | -0.020605758 | -0.020605758 | -0.020605758 | -0.020605729 |

`CONVERGENCE_EXISTENCE_REPORT.md` and `MODEL_DIAGNOSTICS.csv` reproduce these
values and all 17 shared diagnostic fields with **zero mismatches** against
`MODEL_AUDIT.json`. See P3-3 for the focal-estimate provenance finding.

### 2.7 Run identity, authorization, and Git chain

- Scheduler record `27c79c0c…`: `failed = 0`, `exit_status = 0`; wallclock
  arithmetic is internally exact (1316 s and 605 s).
- Receipt `git_commit` = `b7c9e1c2d165c88d185cf85559f83b6329204ceb`; its parent
  is `576133d86e9305726d0ceb78413fec2ac795cdb0`, equal to
  `authorized_implementation_commit`. The pre-outcome binding is genuine: the
  authorization commit contains the target map and is an ancestor of the run.
- Run start/end lie strictly inside the authorization window
  2026-09-07T07:48:41Z → 2026-09-08T06:48:41Z.
- `audit_spec_id`, `audit_spec_sha256`, `code_sha256`, `canonical_spec_id`,
  `canonical_spec_sha256` all match the authorization and the target-map
  certification contract exactly. The runner hash `9f66a4f9…` matches
  `required_a1_runner_code_sha256` and the on-disk runner file.
- The pass run is distinct from both the original pre-A1 blocked run
  (`b9a7dd1`, spec `4c784c23…`) and job 7482111 (spec `e0b71ceb…`, runner
  `80cbf824…`). No artifact is shared or substituted.

**Purpose 1 conclusion: all 11 targets are independently certified at the
unchanged A1 thresholds. No missing, NaN, non-finite, inconsistent, or
merely-asserted field was found.**

---

## 3. Purpose 2 — post-run guard-schema correction

### 3.1 The correction is factually justified

I verified the premise rather than accepting it. `treatment_basis.original_columns`
is genuinely **absent** from every one of the 11 producer-emitted models; the
runner's full-rank branch emits `status`, `selected_original_columns`,
`selected_original_labels`, `dropped_dependent_original_columns`,
`dropped_dependent_original_labels`. The old guard therefore tested a
fixture-only field. The doc's account is accurate.

The dynamic null-basis point also checks out: `dynamics_*` models carry
`target_null_basis:`-prefixed entries in `selected_original_labels` that are
textually different from the original-regressor labels by design. Requiring
textual equality would have been wrong.

### 3.2 It does not weaken any scientific or numerical rule

The corrected conjunct is strictly a schema/partition check. It does not touch
any tolerance, objective, estimator, support rule, target, or threshold. I
confirmed by direct inspection that `_a1_model_is_certified` still applies the
numeric thresholds at lines 923–937 and still requires
`same_final_tolerances == {1e-6, 1e-7, 1e-10}` — none of that was edited.

I stress-tested the new conjunct with **12 adversarial mutations** of the
treatment-basis / parameterization schema (duplicate indices, overlapping
selected/dropped sets, non-integer and boolean indices, partition gaps and
overshoots, label/index length mismatches, wrong functional weight length,
missing keys). **All 12 were rejected.** The check is load-bearing and
fails closed, not decorative.

Two honest caveats, neither adverse:
- All 11 models have zero dropped columns, so on *this* data
  `len(selected_columns) == len(original_regressor_labels)` and the
  weights-length change from `original_regressor_labels` to `selected_columns`
  is numerically inert. It is the correct generalization, but it is currently
  unexercised on real rank-deficient data.
- `guard._a1_model_is_certified` is block-gating: `original_labels = []` at
  line 814 combined with `or not original_labels` at line 855 means an empty
  parameterization fails closed. Confirmed correct.

### 3.3 Independent re-execution against the retained artifacts

I ran the corrected guard directly on the retained pass audit + receipt. It
reproduced `DEPENDENCY_RELEASE.json` **object-equal**:

- `PASS_ALL_11_MODELS_CERTIFIED`, `certified_model_count = 11`
- **20** consumer releases, all `RELEASED`
- **9** downstream requirement releases, all `RELEASED`
- 3 non-model prerequisites → `PASS_BOUND_NON_MODEL_PREREQUISITES`
- `PASS_PREOUTCOME_TARGET_MAP_BYTE_BINDING`

**Fault injection:** for each of the 11 models in turn I invalidated its
certificate and re-evaluated. In all 11 cases the guard blocked **exactly** the
dependent consumers and requirements of that model and no others (exact set
equality, 11/11). One-model failure does not over-block or under-block.

**Stale ledger labels:** `T01`–`T03` are still `RUN_UNVALIDATED` in
`requirements_status.json`. The guard does not read those labels as pass
evidence; it authenticates the bound prerequisite artifacts by hash directly.
The correction document is accurate on this point.

**Purpose 2 conclusion: the correction is valid, non-scientific, and
strengthens rather than weakens the check.**

---

## 4. Purpose 3 — provenance, sanitation, failed evidence

- **Transfer spec:** all six declared inputs located and byte-matched — four
  from the retained parent run `gate1_numerical_blocked_b9a7dd1`, two from the
  new pass run. `TRANSFER_SPEC.json` = `885a9cd9…`.
- **Transfer validation:** `TRANSFER_VALIDATION.json` = `26d0fc5a…`; all three
  normalized receipts and all three receipt projections recompute to their
  declared hashes. 6/6.
- **Cross-receipt checks:** every claimed-true check is supported by a real
  comparison *except* the two identified in P2-1 below.
- **Sanitation:** recursive scan of both retained run directories for absolute
  private paths, credentials, tokens, and keys returned exactly one hit —
  `TRANSFER_VALIDATION.json:156  "PATH": "/usr/bin:/bin"` — a benign sanitized
  environment value. **Zero** matches inside either `MODEL_AUDIT.json`. No
  `aggregate_cells.csv`, no microdata, no credential material. The five CSVs are
  aggregate numerical outputs only. `scc-w*` hostnames appear only in the two
  scheduler accounting records and the normalized numerical receipt, which is
  expected scheduler provenance, not a private path.
  `aggregate_cells_csv_opened` is `false` and consistent with the contents.
- **Job 7482111:** retained with `passed_model_count = 0`, all 11 rows
  `BLOCKED_UNEXPECTED_NUMERICAL_FAILURE_NO_SUBSTITUTION`,
  `finite_target_established = false`. Receipt `d6bd6b5d…`, MODEL_AUDIT
  `18869185…`, scheduler `cc6cc450…` — all three match the previously
  unverifiable documented hashes **exactly**. `exit_status = 2`. No coefficient
  is certified anywhere in it. This closes P3-1 from my prior review.

### 4.1 The declined denylist entry (disposition P3-2) is safe

The disposition deliberately did **not** add the failed spec
`yaxnumspec_v1_e0b71ceb…` to `forbidden_audit_spec_ids`, to preserve the
pre-outcome target-map bytes. I tested this adversarially by feeding the 7482111
artifacts to the guard.

Result: **blocked, with defence in depth.**

1. First block — `pre-outcome target-map Git binding is unavailable`
   (7482111's `git_commit` `1cba225e…` is not an authorization commit over the map).
2. With that check neutralized, second independent block —
   `numerical artifacts do not match the exact authorized A1 specification and runner`.
   The failed run's `audit_spec_id`, `audit_spec_sha256`, and `code_sha256` each
   independently fail the positive pins at `dependency_guard.py:1313–1319`.

Two independent mechanisms each block release. The disposition's reasoning is
verified, not merely asserted.

---

## 5. Tests — exact counts

| suite | measured at `d98371d5` | doc claim | verdict |
|---|---|---|---|
| `tests/test_dependency_guard.py` | **29 passed, 9 subtests passed** | 29 passed, 9 subtests | matches |
| `tests/test_a1_postrun_evidence.py` | **3 passed** | not stated | — |
| full repository (`python -m pytest -q` at repo root) | **1114 passed, 3 skipped, 26 subtests passed** | 1,111 passed, 3 skipped, 26 subtests | **off by 3** — see P3-2 |

Claimed artifact hashes, both **verified correct**:

```
d52bb764dc9cf842e3469ff01d4eecd21a88dff837bf263c9a758b0dfc6d9611  scripts/dependency_guard.py
3ffda2d815dc0171bb51eb35f0a59322965d60ba2bcedcba490f6a35346fca8f  tests/test_dependency_guard.py
```

The new test additions are genuine, not padding: `test_dependency_guard.py`
gains a table-driven fail-closed suite over 9 malformed
`downstream_requirement_model_contract` shapes plus
`test_runner_emitted_basis_without_legacy_count_certifies`, which asserts
`original_columns` is absent and the model still certifies — i.e. it directly
pins the regression the correction was written for.

---

## 6. Findings

### P2-1 — Two named authorization checks are hardcoded `true` in the preserved public evidence

- **Locator:** `gate1_transfer/normalize_public_receipts.py:2082–2086`
  (`validate_shared_execution_authorization`); emitted at
  `runs/gate1_numerical_a1_pass_7482383/public_transfer/TRANSFER_VALIDATION.json`
  → `/cross_receipt_hash_consistency/cells_matches_committed_authorization` and
  `/cross_receipt_hash_consistency/target_matches_committed_authorization`.
- **Mechanism:**
  ```python
  checks[f"{key}_matches_committed_authorization"] = (
      authorizations[key] == expected_receipt_summary
      if transfer_mode == FRESH_TRANSFER_MODE or key == "numerical"
      else True
  )
  ```
  In `a1_authenticated_parent_reuse` mode, `cells` and `target` take the `else
  True` branch and compare nothing. Relatedly, at `:2039–2041`,
  `authorization_keys` narrows to `("cells", "target")`, so the ten
  `shared_authorization_*` booleans compare cells against target only, despite
  names implying agreement across all three modules. The retained file publishes
  all twelve as flat `true`.
- **Impact — bounded, and I want to be precise about this.** The underlying
  safety property *is* enforced: `numerical_matches_committed_authorization` is
  genuinely evaluated (the `key == "numerical"` arm), and the parent cells/target
  receipts are byte-checked in `validate_a1_parent_reuse`
  (`normalize_public_receipts.py:1918–1975`). Skipping the cells/target
  comparison is also *correct by design* — those receipts come from parent run
  `b9a7dd1`, which predates this authorization and cannot match it. The defect
  is that a preserved evidence artifact asserts, under a specific verification
  name, a check that was not performed. `transfer_mode` is disclosed at the top
  level, so a reader who also reads the source can infer it — but the boolean
  itself is vacuous. **No certification, release, coefficient, or hash
  conclusion changes.** This is why it is P2 and not P1.
- **Aggravating detail:** the new `test_a1_postrun_evidence.py:88` asserts
  `all(transfer["cross_receipt_hash_consistency"].values())`, which passes
  vacuously for 2 of the 12 entries. The regression test inherits the
  overstatement.
- **Minimal correction:** emit a three-valued marker instead of `True` in the
  skipped branch, e.g.
  `"SKIPPED_PARENT_REUSE_BOUND_BY_VALIDATE_A1_PARENT_REUSE"`, and rename the
  narrowed keys to `shared_cells_target_authorization_*`. Keep the failure
  predicate as "not one of {True, SKIPPED_…}".
- **Regression test:** assert that under `a1_authenticated_parent_reuse` the
  cells/target entries are the skip marker and *not* `True`, and that under
  `FRESH_TRANSFER_MODE` all three are `True`; assert a corrupted parent cells
  receipt still raises `TransferBlocked` via `validate_a1_parent_reuse`.

### P3-1 — Five stale evidence hashes in `requirements_status.json`, unchecked by any test

- **Locator:** `requirements_status.json` — `G06` `scripts/dependency_guard.py`
  and `tests/test_dependency_guard.py`; `N01`, `N02`, `N03` (×2)
  `numerical_existence/run_numerical_existence_audit.py`.
- **Mechanism:** I recomputed all 90 declared `{path, sha256}` evidence pairs.
  85 match; 5 do not:

  | requirement | path | declared | actual |
  |---|---|---|---|
  | G06 | `scripts/dependency_guard.py` | `29f35dba…` | `d52bb764…` |
  | G06 | `tests/test_dependency_guard.py` | `46ef368c…` | `3ffda2d8…` |
  | N01/N02/N03 | `numerical_existence/run_numerical_existence_audit.py` | `23f4a4dd…` | `9f66a4f9…` |

  The first two are the reader correction landed in this very commit without a
  ledger update. The third is stale from before the vstack compatibility fix.
- **Impact:** the *authoritative* pins are correct — `9f66a4f9…` is exactly
  `PRE_EXECUTION_AUTHORIZATION.modules.numerical.code_sha256` and the target
  map's `required_a1_runner_code_sha256`, and the guard enforces it. So this is
  a working-ledger integrity defect, not an unsafe binding. The real concern is
  that **nothing validates these hashes**: `scripts/validate_claim_ledger.py`
  checks a different ledger (`source_sha256` rows), which is why the suite is
  green with five stale entries. Any future stale entry will also pass silently.
- **Minimal correction:** update the five values, and add a test that walks
  every `{path, sha256}` pair in `requirements_status.json` and recomputes it.
- **Regression test:** the walk-and-recompute test above, asserting 0 mismatches
  and 0 missing paths.

### P3-2 — Correction document's full-suite count does not reproduce at its own commit

- **Locator:** `reviews/GATE1_NUMERICAL_A1_POSTRUN_GUARD_SCHEMA_CORRECTION.md:61`
  — "Full repository suite: 1,111 passed, 3 skipped, 26 subtests passed."
- **Mechanism:** actual is **1114** passed at `d98371d5`. The delta is exactly
  the 3 tests in `tests/test_a1_postrun_evidence.py`, which was added in the
  *same commit* as the document. The count was recorded before the file landed.
- **Impact:** cosmetic but real — a retained verification document states a
  reproducibility number that does not reproduce at the commit containing it, and
  a future auditor re-running the suite will see a discrepancy and have to
  re-derive the cause. The focused count (29/9) and both SHA-256s are correct.
- **Minimal correction:** change to "1,114 passed, 3 skipped, 26 subtests passed"
  and note that 3 come from the newly added `test_a1_postrun_evidence.py`.
- **Regression test:** none warranted; instead record test counts as the last
  step before commit, or drop absolute counts from prose in favour of the
  hash pins.

### P3-3 — `focal_target_estimate` is the reference-path value for all 11 models, by an undocumented rule

- **Locator:** `MODEL_AUDIT.json` → `models[*].focal_target_estimate`; surfaced
  in `MODEL_DIAGNOSTICS.csv`, `CONVERGENCE_EXISTENCE_REPORT.md`, and
  `runs/gate1_numerical_a1_pass_7482383/README.md`.
- **Mechanism:** for **all 11** models, `focal_target_estimate` is bit-exactly
  `solvers["independent-damped-sparse-newton-irls"].focal_target`, and is *not*
  the trust-ncg value. Most visible in `dynamics_family_month`, where the README
  reports `-0.207433689` (reference) while trust-ncg/trust-path give
  `-0.207433694`. Meanwhile `GATE1_NUMERICAL_ADJUDICATION_A1.md` §5 frames
  trust-ncg as the retained candidate path and the Newton/IRLS fit as the
  *corroborating reference*, and `NUMERICAL_AMENDMENT_A1.md` never states which
  candidate supplies the reported number.
- **Impact:** bounded and small. The reported figure is a certified solution of
  the same objective, and trust-vs-reference agreement is certified at ≤1e-6
  with worst actual disagreement **4.632e-09**. No reported digit at publication
  precision is affected. But the reporting rule is currently implicit in code
  and is referenced by neither `dependency_guard.py` nor
  `normalize_public_receipts.py` — nothing pins it, so a future refactor could
  silently switch candidates.
- **Minimal correction:** add one sentence to `NUMERICAL_AMENDMENT_A1.md`
  declaring the reference path as the reported focal estimate and stating why
  (independent zero start, no warm-start inheritance), and emit an explicit
  `focal_target_source` field in `MODEL_AUDIT.json`.
- **Regression test:** assert `focal_target_estimate == solvers[<declared
  source>].focal_target` for every model, and that `focal_target_source` equals
  the declared constant.

### P3-4 — The dependency guard was edited after the outcome was known and is not byte-bound pre-outcome

- **Locator:** `scripts/dependency_guard.py`, diff
  `576133d8..d98371d5` (+29 lines inside `_a1_model_is_certified`).
- **Mechanism:** the target map is byte-bound to authorization commit
  `b7c9e1c2…` and cannot move post-outcome — that property is enforced and I
  verified it. The *reader* has no equivalent binding. It was modified after
  job 7482383's results were known, which is exactly the window in which a
  reader change is hardest to audit.
- **Impact:** governance/process, not substance. I verified this specific edit
  is a strict tightening (§3.2: 12/12 adversarial mutations rejected), changes
  no tolerance or scientific rule, and that the correction is *required* for the
  guard to accept any real producer output at all. The pre-outcome protection
  that actually matters — the target map and the specification/runner pins — is
  intact. Flagged so the execution agent records it explicitly rather than
  leaving it implicit.
- **Minimal correction:** state in the correction document that the guard is a
  post-outcome reader edit outside the pre-outcome byte binding, and record the
  before/after guard SHA-256 pair (`29f35dba…` → `d52bb764…`) in the ledger.
- **Regression test:** pin the guard SHA-256 in `requirements_status.json` (this
  is the same fix as P3-1) so any future post-outcome reader edit forces a
  visible ledger diff.

---

## 7. Required answers

**1. Are all 11 numerical targets independently certified at unchanged A1
thresholds?**
**Yes.** All 11, including `seasonal_occupation_month_family_month` and the
previously double-failing `seasonal_quintile_month_unconditioned`. The
tolerances are the unchanged A1 values (1e-6 / 1e-7 / 1e-10); I recomputed the
trust-vs-reference differences label-by-label for every model with zero
mismatches, and every model clears every threshold by ≥2 orders of magnitude.
Hessian certificates, evaluator checks, two-sided profiles, treatment rank, and
boundary handling all verify independently. L-BFGS-B ran, remains diagnostic
only, and reveals no better independently stationary contradictory target.

**2. Is the guard-schema correction valid and non-scientific?**
**Yes.** The premise is factually correct (`original_columns` is genuinely not
emitted by the producer; dynamic null-basis labels genuinely differ textually).
The correction validates the emitted selected/dropped partition and current-basis
functional dimensions, rejects all 12 adversarial schema mutations, and touches
no tolerance, estimator, objective, support rule, or threshold. It is a
tightening, not a weakening.

**3. Are all 20 consumers and all 9 requirement groups correctly released?**
**Yes.** My independent guard rerun reproduced `DEPENDENCY_RELEASE.json`
object-equal: 11 certificates, 20 consumers, 9 requirement releases, 3
non-model prerequisites, and the pre-outcome map byte binding. Per-model fault
injection blocked exactly the dependent set in all 11 cases — no over- or
under-blocking.

**4. Is the public evidence package reproducible and free of protected inputs?**
**Yes.** Every declared hash I could recompute did recompute: the receipt's 8
output hashes, the MODEL_AUDIT binding, all 6 normalized/projection hashes, the
6 transfer-spec inputs, and both 7482111 documented hashes. The sanitation scan
is clean — no aggregate cell file, microdata, credential, or private SCC path;
the sole absolute-path hit is `"PATH": "/usr/bin:/bin"`. The one exception to
"every declared hash recomputes" is the five stale *ledger* entries in P3-1,
which are working-state, not part of the transferred package.

**5. Is any claim currently overstated?**
**Yes, in three bounded ways, none affecting the numerical result:**
(a) `TRANSFER_VALIDATION.json` publishes
`cells_matches_committed_authorization` and
`target_matches_committed_authorization` as `true` when neither was evaluated
(**P2-1**);
(b) the correction document's "1,111 passed" does not reproduce at its own
commit — actual 1,114 (**P3-2**);
(c) `requirements_status.json` declares five evidence hashes that no longer
match the files, and nothing checks them (**P3-1**).

Conversely, several things that *could* have been overstated are **not**.
`STATE.md` and `N03` are appropriately conservative: N03 is `RUN_UNVALIDATED`,
not `VERIFIED`; the run is described as "candidate-certified" with independent
review explicitly listed as outstanding; and no coefficient is represented as
manuscript-ready or independently reviewed. The denominator discipline required
by the adjudication ("k of 11", never "Gate 1 PASS" for an incomplete suite) is
observed. The declined denylist entry is safe under two independent blocking
mechanisms. On the central question the package does not overclaim.

---

## 8. Prior-review items closed

- **P3-1 (prior, job 7482111 artifacts unretained):** closed. Receipt,
  MODEL_AUDIT, and a byte-pinned scheduler export are now retained and their
  bytes match the documented hashes exactly.
- **P3-3 (prior, fail-closed branch coverage):** closed. Table-driven coverage
  over 9 malformed contract shapes now exists and passes.
- **P3-2 (prior, denylist the failed spec):** declined by disposition, and the
  decline is **verified safe** — see §4.1.

## 9. Scope and limits of this review

Read-only. I made no edit, commit, push, or authorization, did not access SCC,
and did not open protected CPS microdata or aggregate cells. This is an
artifact-only audit: I verified internal mathematical consistency,
reproducibility of every recomputable hash, and the release logic. I did **not**
re-execute the estimator on the protected data, so this does not independently
confirm that the retained artifacts were produced from the authenticated cells —
that rests on the cells-hash chain and the scheduler record, both of which are
internally consistent. Statistical inference, causal interpretation, and
finite-sample coverage are out of scope and remain ungated by Gate 1.
