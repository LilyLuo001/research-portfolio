# YAX A1 targeted closure review

Reviewer: independent adversarial numerical-methods and reproducibility pass.
Scope: delta `efb714894c16ccd4e6dec645d6d6f6f5703d17cb..576133d86e9305726d0ceb78413fec2ac795cdb0`
on `task/yax-v3-execution-20260906`.
Constraints observed: no files edited in the repository, nothing committed or
pushed, no execution authorization generated, no SCC access, no protected data
or credential inspection.

## Verdict

**No P1 issue. No P2 issue.** Both review purposes are closed. Three P3 items
are recorded below; all three are documentation or test-coverage improvements,
not safety failures. In each case I verified by direct execution that the
underlying safety property already holds.

The delta is 13 files, +343/−44. The only production-code behavior change
outside `scripts/dependency_guard.py` is a single token: `np.row_stack` →
`np.vstack`.

---

## Purpose 1 — closure of the P2 finding

All six sub-claims verified. Evidence below is by line in
`scripts/dependency_guard.py` at `576133d8`.

### 1.1 `downstream_requirement_model_contract` is structurally validated — YES

`validate_target_dependency_map:337–371`. The block must be a nonempty dict;
each key a nonempty string; each value a nonempty list of nonempty strings with
no duplicates; and every named model must be in `known_models`. The function
signature changed to return the contract as a third value (`:444`), so the
contract is now load-bearing rather than inert data.

### 1.2 A consumer cannot name a requirement without the full model set — YES

`:413–427`, inside the per-consumer loop:

```python
missing_required = sorted(set(requirement_contract[requirement_id]) - set(required))
if missing_required:
    raise DependencyError(
        f"{consumer_id} claims {requirement_id} without its "
        "full declared model prerequisite set; missing: " + ", ".join(missing_required))
```

Verified in-process against the **real** `contracts/TARGET_DEPENDENCY_MAP_A1.json`
(not the test fixture). Setting
`gate2.sensitivity.complete_onset_and_seasonality`'s `required_model_ids` to
`["post_2020_unconditioned"]` while retaining `"downstream_requirement_ids":
["Y08"]` raises:

```
gate2.sensitivity.complete_onset_and_seasonality claims Y08 without its full
declared model prerequisite set; missing: post_2020_family_month,
seasonal_occupation_month_family_month, seasonal_occupation_month_unconditioned,
seasonal_quintile_month_family_month, seasonal_quintile_month_unconditioned
```

This is the exact exploit path described in the original P2-1 "Impact"
paragraph. It is now closed.

### 1.3 Unknown and orphaned mappings fail closed — YES, and broader than recommended

I exercised ten negative paths in-process against the real map. All ten raise
`DependencyError`; the unmodified map is accepted with 9 requirements and 20
consumers.

| Mutation | Result |
|---|---|
| unmodified real map | ACCEPTED — 9 requirements, 20 consumers |
| consumer names unknown requirement `ZZ9` | `gate2.static.pooled_target names unmapped requirement ZZ9` |
| requirement `Q99` with no consumer | `target map has downstream requirements with no consumer: Q99` |
| contract block deleted | `target map needs downstream_requirement_model_contract` |
| contract block empty `{}` | `target map needs downstream_requirement_model_contract` |
| contract value not a list | `invalid requirement model contract: Y01` |
| contract value `[]` | `invalid requirement model contract: Y01` |
| duplicate model in contract value | `invalid requirement model contract: Y01` |
| non-string model in contract value | `invalid requirement model contract: Y01` |
| contract names unknown model | `invalid requirement model contract: Y01; unknown models: not_a_model` |

The orphan check (`:436–443`) was **not** in my recommended correction. It is a
genuine strengthening: it makes the map bidirectionally total, so a requirement
cannot be silently dropped from the release computation by deleting its
consumers.

### 1.4 Requirement release is computed from actual certificates — YES

`:1327–1330` derives `certified` from `_a1_model_is_certified(row)` applied to
each row of the real `MODEL_AUDIT.json` registry. That predicate
(`:722–…`) requires `a1_certification`, `solver_comparison`, `target_profile`,
`fitted_full_hessian`, `fitted_information`, `fitted_reported_target_information`,
the dual-Hessian evidence, and the L-BFGS-B contradiction audit. The receipt's
self-reported `passed_model_count` is **cross-checked against** the
independently recomputed set at `:1333`, not trusted; the registry must equal
the frozen eleven exactly (`:1323`).

Requirement release (`:1370–1392`) is computed from that same `certified` set
plus `non_model_pass` (`:1349–1351`), which requires
`non_model["status"] == "PASS_BOUND_NON_MODEL_PREREQUISITES"` from
`validate_non_model_prerequisites`. It is a genuine recomputation from
per-model certificates, not a re-emission of declared fields — which was the
substance of the original finding.

Consumer release at `:1361–1363` also now carries the `non_model_pass`
conjunct, closing a gap I had not flagged.

### 1.5 Partial certification cannot be mislabeled as requirement release — YES

`:1372–1382`. `blocking` is every contract model absent from `certified`;
`release_status` is `RELEASED` only when `not blocking and non_model_pass`.
The emitted object additionally carries `required_model_ids`,
`certified_model_ids`, `blocking_model_ids`, and `consumer_ids`, so a
downstream reader can see the partition rather than a bare verdict.

`test_requirement_release_blocks_when_any_contract_model_is_blocked`
(`tests/test_dependency_guard.py`) asserts the precise adversarial shape:
consumer `use.pooled` is `RELEASED` while requirement `Y01` is `BLOCKED` with
`blocking_model_ids == ["family_month"]` and
`consumer_ids == ["compare.pooled.family_month"]`.

### 1.6 The two mechanisms are separately exercised — YES

This was the sub-claim most worth checking, because a structural check that
short-circuits the Git-binding test would silently reduce coverage.

`test_post_run_weakened_target_map_cannot_release` was updated to weaken
**both** `downstream_requirement_model_contract["Y01"] = ["pooled"]` and the
consumer's `required_model_ids`. Without that paired edit the new structural
check at `:419` would raise first and the test would no longer reach
`validate_preoutcome_target_map_binding`. It still asserts the Git-binding
error (`"pre-outcome authorization commit"`), so the immutable pre-outcome
binding remains independently covered. The two new tests cover structural
validation. Structural validation and Git binding are therefore exercised by
disjoint assertions.

`tests/test_dependency_guard.py`: **27 passed**, matching the disposition's
claim.

---

## Purpose 2 — NumPy 2.5 compatibility correction

### 2.1 `row_stack` → `vstack` is exactly equivalent in that call — YES

The entire runner delta is one token:

```diff
-    target_matrix = np.ascontiguousarray(np.row_stack([
+    target_matrix = np.ascontiguousarray(np.vstack([
         np.asarray(target_functionals[label], dtype="<f8")
         for label in target_labels
     ]), dtype="<f8")
```

in `a1_shared_problem_binding` (`run_numerical_existence_audit.py:~5138`).
The list comprehension, label order, dtype, contiguity conversion, and
downstream hash construction are untouched.

Verified empirically on a NumPy where both symbols exist:

- `np.row_stack is np.vstack` → **True** (the same function object; `row_stack`
  was an alias, never a distinct implementation)
- `np.ascontiguousarray(np.row_stack(a), dtype='<f8').tobytes() ==
  np.ascontiguousarray(np.vstack(a), dtype='<f8').tobytes()` → **True**

The substitution is byte-semantically identical, so the recorded problem digest
is unchanged by the repair.

I also scanned every tracked `.py` file for the full set of NumPy 2.x removals
and deprecations — `row_stack`, `float_`, `complex_`, `unicode_`, `string_`,
`int0`, `NaN`, `Inf`, `infty`, `alltrue`, `sometrue`, `cumproduct`, `product`,
`round_`, `in1d`, `trapz`, `msort`, `issctype`, `AxisError`, `ComplexWarning`,
`asfarray`, and the removed methods `.ptp(`, `.itemset(`, `.newbyteorder(`,
`.tostring(`, plus `np.matrix` and `.A1`. **Zero matches.** `row_stack` was the
only removed-alias usage in the tree, and after this commit `row_stack` appears
in no production code path at all — only in prose and in the test's mock target.

### 2.2 The regression test exercises the path with `row_stack` unavailable — YES

`numerical_existence/test_numerical_existence_audit.py:1723–1745`, three wrapped
calls in `A1IndependentReferenceTests`:

```python
with mock.patch.object(AUDIT.np, "row_stack", None, create=True):
    left = AUDIT.a1_shared_problem_binding(active, design, ["x", "x2"], targets)
```

I confirmed by direct execution that inside the context manager
`np.row_stack is None`, that calling it raises, and that the original binding is
restored on exit. The targeted test passes. `create=True` makes the guard valid
on both stacks: on the pinned NumPy 2.5.1 the attribute does not exist, so the
patch creates and then removes it, leaving production semantics unchanged.

### 2.3 Hashes and IDs are internally consistent and non-stale — YES

Every declared hash in the delta recomputes correctly against the bytes on disk
at `576133d8`:

| Artifact | Declared | Recomputed |
|---|---|---|
| `scripts/dependency_guard.py` | `29f35dba…` | match |
| `tests/test_dependency_guard.py` | `46ef368c…` | match |
| `reviews/…_ADVERSARIAL_REVIEW_DISPOSITION.md` | `0232e03e…` | match |
| `reviews/…_ADVERSARIAL_FINAL_REVIEW.md` | `5fc64c81…` | match |
| `numerical_existence/NUMERICAL_AMENDMENT_A1_COMPATIBILITY_01.md` | `86df32f9…` | match |
| `numerical_existence/ANALYSIS_SPEC_A1.json` | `07d6053a…` | match |
| `numerical_existence/run_numerical_existence_audit.py` | `9f66a4f9…` | match |
| `numerical_existence/test_numerical_existence_audit.py` | `94c0e8ae…` | match |
| `contracts/TARGET_DEPENDENCY_MAP_A1.json` | `f8bb2630…` | match |

I independently recomputed the content-addressed spec ID from
`ANALYSIS_SPEC_A1.json` — SHA-256 over the canonical JSON serialization with the
`audit_spec_id` field removed — and obtained
`yaxnumspec_v1_5989d8d88e772711ff47c43011e9f90f4764dc8d89230ef5486b6687f59dc05c`,
equal to the declared value. The ID is self-consistent, not transcribed.

The reseal propagates to exactly four places and nowhere else:

- `ANALYSIS_SPEC_A1.json` — `audit_spec_id`, `software.audit_runner_sha256`,
  `software.synthetic_test_sha256`
- `contracts/TARGET_DEPENDENCY_MAP_A1.json` — `required_a1_audit_spec_id`,
  `required_a1_audit_spec_sha256`, `required_a1_runner_code_sha256`
- `gate1_transfer/TRANSFER_SPEC.template.json` — `expected_code_hash`,
  `typed_spec.id`, `typed_spec.sha256`
- `gate1_transfer/normalize_public_receipts.py` — `NUMERICAL_SPEC_ID`,
  `NUMERICAL_SPEC_SHA256`, `NUMERICAL_CODE_SHA256`

All twelve carry the same three new values. No stale `e0b71ceb…`,
`7d579854…`, `80cbf824…`, or `2f108a57…` remains in any binding position.

Corroborating the disposition's provenance claim: the failed run's declared
runner and spec hashes (`80cbf824…`, `7d579854…`) are exactly the blob hashes of
`run_numerical_existence_audit.py` and `ANALYSIS_SPEC_A1.json` at `cb9310c5`.
That is consistent with job 7482111 having executed the reviewed tree.

Note that the target-map bytes changed in this delta, so the pre-outcome
authorization must be regenerated against the new HEAD —
`validate_preoutcome_target_map_binding` requires the map bytes to equal
`auth_commit:<map>` and `auth_commit^ == authorized_implementation_commit`.
STATE.md's next-step item already says this. It is a procedural consequence, not
a defect.

### 2.4 Scientific-target fingerprint equals the parent exactly — YES

Parent payload fingerprint, A1 payload fingerprint, and the declared value are
all `f5cf1106872117c3c67ce85da2fc76f661093a500ad31bfdcd58dfadfe6956e0`, and a
direct object comparison of the two payloads returns `True` — byte-equal, not
merely hash-equal. `tolerances`, `models`, `likelihood`, `profile`,
`boundary_and_separation`, `normalization`, and `dynamic_target_scope` are
identical to the parent.

`input_contract` differs from the parent only in `receipt_authentication`
prose, which is excluded from the fingerprint payload — correctly, since it is
an authentication procedure rather than a scientific input. `hessian_diagnostics`
is likewise excluded, correctly, since it is the numerical policy A1 explicitly
amends.

### 2.5 No estimator, objective, model, support, input, target, solver, tolerance, or acceptance rule changed — YES

The full delta is 13 files. Of those, six are prose or ledger
(`STATE.md`, `NUMERICAL_AMENDMENT_A1.md`, the new compatibility record, the new
disposition, `requirements_status.json`, and the review file itself), three are
hash propagation only, one is the one-token runner fix, one is the mock guard in
the runner tests, and two are the dependency-guard fix and its tests. Nothing
touches the objective, score, Hessian, design construction, active-row masks,
normalization, boundary or separation rules, model registry, target definitions,
solver settings, thresholds, or the acceptance conjunction. The eight unchanged
thresholds in `NUMERICAL_AMENDMENT_A1.md` are untouched. The
`downstream_requirement_model_contract` data in the target map is untouched —
only the guard that reads it changed.

### 2.6 The failed run is documented as blocked evidence, not a finding — YES

`NUMERICAL_AMENDMENT_A1_COMPATIBILITY_01.md` classifies all 11 models
`BLOCKED_UNEXPECTED_NUMERICAL_FAILURE_NO_SUBSTITUTION` and states "No coefficient
or target from this run is certified" and that a replacement "may not overwrite
or reinterpret job 7482111." `requirements_status.json` holds N03 at
`IMPLEMENTED_UNRUN` with an unchanged `approval.status`, and the blocker text
now reads "no coefficient is certified." No numerical value from job 7482111
appears anywhere as a finding.

Mechanically, certification is impossible regardless of the prose:
`required_a1_audit_spec_id` now pins `5989d8d8…`, so any artifact produced by
the `e0b71ceb…` runner is rejected by `validate_target_certifications` before
release computation begins.

The separately preserved pre-A1 blocked run under
`runs/gate1_numerical_blocked_b9a7dd1/` is unmodified in this delta and remains
byte-bound by `validate_a1_amendment`.

---

## P3 items

These are improvements, not safety failures. In each case I confirmed by
execution that the safety property already holds.

### P3-1 — Job 7482111's artifacts are not retained in the repository

`runs/` contains only `foundation`, `gate1_baseline`, and
`gate1_numerical_blocked_b9a7dd1`. Grepping for `7482111` hits only `STATE.md`,
`requirements_status.json`, and the compatibility record; grepping for the two
SHA-256s the compatibility record cites for the failed run — receipt
`d6bd6b5d…` and `MODEL_AUDIT.json` `18869185…` — hits only that same document.

So the record's factual claims (job number, 605 s, 1.932 GB peak vmem, exit
status 2, the 11 per-model classifications, and both hashes) are at this commit
unverifiable prose that no artifact or test binds. This contrasts with the
`gate1_numerical_blocked_b9a7dd1` precedent, where the blocked receipt and
`MODEL_AUDIT.json` are retained byte-for-byte and hash-bound in code.

Not P2: nothing certifies or releases anything on the basis of job 7482111, and
the spec-ID pin makes its artifacts unusable. This is an evidence-retention gap
against review criterion 7 and against the portfolio meta-rule that facts must
carry a locator.

Minimal correction: land the failed run's `EXECUTION_RECEIPT.json` and
`MODEL_AUDIT.json` under `runs/gate1_numerical_a1_compat_blocked_7482111/` and
extend the existing `validate_a1_amendment` byte-binding pattern to cover them.
Regression test: assert the two declared hashes equal the retained file bytes
and that `passed_model_count == 0`.

### P3-2 — `forbidden_audit_spec_ids` omits the failed A1 spec

`contracts/TARGET_DEPENDENCY_MAP_A1.json:35–37` lists only the pre-A1 parent
`yaxnumspec_v1_4c784c23…`. The now-known-bad A1 spec
`yaxnumspec_v1_e0b71ceb…` is not listed, even though it is a spec ID that
demonstrably produced a blocked run.

Redundant in practice — `validate_target_certifications` hard-requires
`audit_spec_id == contract["required_a1_audit_spec_id"]`, so a positive match on
the new ID is already necessary. But a denylist that omits a known-bad entry is
a documentation defect in an artifact whose purpose is to be read by humans.

Minimal correction: append `yaxnumspec_v1_e0b71ceb…` to the array. Regression
test: assert the failed spec ID is in `forbidden_audit_spec_ids`. Note this
changes the map bytes and so must land before the authorization commit.

### P3-3 — Automated coverage of the new fail-closed branches is partial

`tests/test_dependency_guard.py` covers the shortened-model-set branch and the
requirement-release computation. The unknown-requirement branch (`:413`), the
orphaned-requirement branch (`:436`), and the six malformed-contract branches
(`:341`, `:348`, `:353`) have no automated test. I verified all of them manually
against the real map (table in §1.3) and all fail closed correctly, so this is
coverage, not a defect.

Minimal correction: add table-driven cases over the fixture map asserting
`DependencyError` for each mutation in the §1.3 table.

Separately, the `row_stack` mock sets the attribute to `None`, so calling it
raises `TypeError`, whereas production raised `AttributeError`. Harmless — the
runner wraps per-model work in `except Exception` and both are subclasses — but
`mock.patch.object(AUDIT.np, "row_stack", mock.DEFAULT)` with deletion semantics
would reproduce the production failure exactly.

---

## Observation outside the delta, explicitly not a defect in this commit

`verify_runtime_contract` (`run_numerical_existence_audit.py:483–495`)
byte-locks the runtime to numpy 2.5.1 / pandas 3.0.3 / scipy 1.16.2 /
CPython 3.13.8 and raises `AuditBlocked("dedicated SCC numerical runtime differs
from the byte-locked contract")` otherwise. The local development and test stack
is numpy 1.22.4 / scipy 1.9.0 / Python 3.10.5, so the runner cannot execute
locally at all, and the passing test suite gives **no** assurance about the
pinned production stack beyond the one symbol the new mock covers.

That is exactly the mechanism by which job 7482111 consumed an authorization to
discover a one-token incompatibility, and it is unchanged. A cheap pre-flight
that imports the runner and runs the synthetic tests on the pinned stack —
before the full-data authorization is spent — would convert a future
authorization-burning mid-run failure into a fast local failure. This is a
process improvement for the owner to weigh, not a finding against `576133d8`.

---

## Checks performed

1. Full delta reviewed file by file: 13 files, +343/−44.
2. All ten negative structural paths exercised in-process against the real
   `TARGET_DEPENDENCY_MAP_A1.json`; unmodified map accepted at 9 requirements
   and 20 consumers.
3. Confirmed `certified` is recomputed from `_a1_model_is_certified` over the
   audit registry and that the receipt's `passed_model_count` is cross-checked
   against it rather than trusted.
4. Confirmed the requirement-release object is derived from that set plus the
   authenticated non-model status, and carries the full model partition.
5. Confirmed the updated tampering test still reaches and fails on the
   pre-outcome Git binding, so structural validation and Git binding are
   separately covered.
6. `np.row_stack is np.vstack` → True; `.tobytes()` equality of the two full
   expressions → True.
7. Whole-tree scan for all NumPy 2.x removed aliases and methods → zero matches.
8. Confirmed the mock makes `row_stack` unavailable inside the context and
   restores it after; targeted test passes.
9. Recomputed all nine declared artifact hashes → all match.
10. Independently recomputed the content-addressed spec ID → matches declared.
11. Verified all twelve hash/ID propagation sites carry the same three new
    values and that no stale value remains in a binding position.
12. Verified the failed run's declared runner and spec hashes equal the
    `cb9310c5` blob hashes.
13. Verified the scientific-target payloads are byte-equal parent-to-A1 and that
    the fingerprint equals the declared parent value.
14. Confirmed the target map's `downstream_requirement_model_contract` and all
    consumer rows are unchanged in this delta.
15. `tests/test_dependency_guard.py` → 27 passed.
16. `substantive_v3_20260906` suite → 366 passed, 17 subtests passed.
17. Repository suite → **1109 passed, 3 skipped, 17 subtests passed**, exactly
    matching the disposition's claim.
18. Confirmed N03 remains `IMPLEMENTED_UNRUN` with unchanged approval status and
    that no coefficient from job 7482111 appears as a finding.
19. Confirmed `runs/gate1_numerical_blocked_b9a7dd1/` is untouched in this delta.

## Disposition document accuracy

`reviews/GATE1_NUMERICAL_A1_ADVERSARIAL_REVIEW_DISPOSITION.md` describes the
correction accurately. Every claim in its "Correction" section is implemented as
stated; its test counts (27 focused, 1109/3/17 full) reproduce exactly; and its
closing instruction — that the corrected guard, not the reviewed
pre-correction guard, must be used for every post-run release decision — is the
right operational conclusion, since the pre-correction guard would not have
enforced the requirement contract on the fresh artifacts.

Its claim that job 7482111's authorization chain was rooted in a tree
byte-identical to `cb9310c5` is corroborated to the extent verifiable in this
worktree: the run's declared runner and spec hashes equal the `cb9310c5` blob
hashes. The remainder of that claim concerns a separate SCC worktree outside
this repository and is not independently verifiable here.
