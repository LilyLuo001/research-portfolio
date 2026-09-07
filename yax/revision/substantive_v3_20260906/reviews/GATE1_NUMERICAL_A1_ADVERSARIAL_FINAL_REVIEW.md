# Read-only adversarial final review — Gate 1 numerical amendment A1

Reviewer: independent adversarial numerical-methods and reproducibility pass.
Scope: commit `cb9310c5acf8ec814d4741495b08899e2e71d66b`.
Authority reviewed against:
`yax/revision/substantive_v3_20260906/revision_inputs/GATE1_NUMERICAL_ADJUDICATION_A1.md`
(SHA-256 `ff4963e66940741abc8a4eda87fd9050c51cae5cedfabb3ae1ab42c21f5836a9`).

Constraints observed: no files edited during the review, no protected data read,
no SCC access, no credential inspection, no access outside this Git worktree.

## Verdict

**No P1 issue found. One P2 issue remains.**

All 234 tests plus 17 subtests in
`numerical_existence/test_numerical_existence_audit.py`,
`tests/test_dependency_guard.py`, and
`gate1_transfer/tests/test_normalize_public_receipts.py` pass; the worktree is
clean. Every hash declared in the A1 artifacts matches the file bytes on disk,
so no finding below rests on a stale hash.

---

## P2-1 — `downstream_requirement_model_contract` is declared but never enforced, and requirement-level release is never computed

### Evidence

- `contracts/TARGET_DEPENDENCY_MAP_A1.json:10` declares
  `downstream_requirement_model_contract`, the per-requirement model
  prerequisite sets for S07, I02, I07, I10, Y01–Y04, Y08 (for example
  `Y08` requires six models, `Y01` requires four).
- `scripts/dependency_guard.py:197–381` `validate_target_dependency_map`
  validates `schema_version`, `unmapped_consumer_policy`, `whole_suite_rule`,
  `authorization`, `certification_contract`, `non_model_prerequisites`,
  `registered_model_ids`, and each consumer row — but never reads
  `downstream_requirement_model_contract`. The key appears in no `.py` or test
  file in the tree.
- `scripts/dependency_guard.py:364–371` shape-checks `downstream_requirement_ids`
  only (a list of unique nonempty strings). It is not constrained to be a key of
  the contract, and nothing requires a consumer naming requirement `R` to
  require `R`'s full declared model set.
- `scripts/dependency_guard.py:1284–1301` `validate_target_certifications`
  computes `release_status` **per consumer** and re-emits
  `row["downstream_requirement_ids"]` verbatim. The returned `result` contains
  no requirement-keyed release object.

### Impact

Review criterion 6 (release a downstream requirement before all of its actual
model and non-model prerequisites pass). A consumer row listing
`"downstream_requirement_ids": ["Y08"]` while requiring only
`post_2020_unconditioned` would be emitted as `release_status: "RELEASED"`
carrying `Y08`, even with five of Y08's six declared models blocked. A
downstream reader keying on `downstream_requirement_ids` of released consumers
would treat Y08 as releasable. The map states the correct rule; the guard does
not enforce it.

### Latency

This cannot be exploited in the current tree. For all nine requirements, every
consumer's `required_model_ids` equals its requirements' declared set exactly —
no consumer is short. The map is byte-bound to the pre-outcome authorization
commit by `validate_preoutcome_target_map_binding`
(`scripts/dependency_guard.py:449–456`, `459–469`), which requires the map bytes
to equal `auth_commit:<map>`, requires the authorization commit to change
exactly one file, and requires its parent to equal
`authorized_implementation_commit`. The map therefore cannot be edited after the
outcome is known.

The finding is P2, not P3, because the safety property is currently carried by
hand-checked JSON data rather than by code.

### Minimal correction

In `validate_target_dependency_map`, after `indexed` is built and before the
`return`:

```python
requirement_contract = document.get("downstream_requirement_model_contract")
if not isinstance(requirement_contract, dict) or not requirement_contract:
    raise DependencyError("target map needs downstream_requirement_model_contract")
for requirement_id, required in requirement_contract.items():
    if (
        not isinstance(required, list) or not required
        or len(required) != len(set(required))
        or set(required) - known_models
    ):
        raise DependencyError(
            f"invalid requirement model contract: {requirement_id}"
        )
for consumer_id, row in indexed.items():
    for requirement_id in row.get("downstream_requirement_ids", []):
        if requirement_id not in requirement_contract:
            raise DependencyError(
                f"{consumer_id} names unmapped requirement {requirement_id}"
            )
        if not set(requirement_contract[requirement_id]) <= set(
            row["required_model_ids"]
        ):
            raise DependencyError(
                f"{consumer_id} claims {requirement_id} without its full "
                "declared model prerequisite set"
            )
```

Return `requirement_contract` as a third value, and in
`validate_target_certifications` after `releases` is built
(`scripts/dependency_guard.py:1301`):

```python
result["downstream_requirement_releases"] = {
    requirement_id: {
        "required_model_ids": required,
        "blocking_model_ids": [m for m in required if m not in certified],
        "non_model_dependency_status": non_model["status"],
        "release_status": (
            "RELEASED"
            if all(m in certified for m in required) else "BLOCKED"
        ),
    }
    for requirement_id, required in requirement_contract.items()
}
```

### Regression tests

In `tests/test_dependency_guard.py`:

1. `test_consumer_cannot_claim_requirement_without_full_model_contract` —
   deep-copy the real map, set one Y08 consumer's `required_model_ids` to
   `["post_2020_unconditioned"]` while retaining
   `"downstream_requirement_ids": ["Y08"]`; assert `DependencyError` matching
   `full declared model prerequisite set`.
2. `test_requirement_release_blocks_when_any_contract_model_is_blocked` —
   build a `MODEL_AUDIT.json` in which the five non-`post_2020_unconditioned`
   Y08 models carry `BLOCKED_*` classifications; assert the narrow consumer is
   `RELEASED` while
   `result["downstream_requirement_releases"]["Y08"]["release_status"]` is
   `BLOCKED` with five `blocking_model_ids`.

---

## Checks performed that produced no finding

| Prompt check | Verdict | Evidence |
|---|---|---|
| Independent objective/derivative implementation | Genuinely independent | `IndependentGroupedBinomialEvaluator` (`run_numerical_existence_audit.py:3457`) uses the success/failure softplus decomposition and never calls `BinomialObjective`; `fit_independent_sparse_newton` (`:4179`) starts from its own zeros; `test_numerical_existence_audit.py:1347` asserts it calls neither the canonical evaluator nor `minimize` |
| Exact original-coordinate treatment functionals after dynamic reparameterization | Correct | `target_coordinate_bundle:188–265`. Since `X_new = X_orig @ transform`, `θ_orig = transform @ θ_new`, so row *i* of `transform` is exactly original coefficient *i*. The identity `weights @ transform == e₁` is asserted at `atol=1e-13`; a functional loading on a dropped basis column raises at `:5972–5982` |
| Full-vector recession invariance | Enforced | `resolve_extended_likelihood_face:3213–3348` audits every `original_treatment::` functional and every reported event target. Incomplete audit yields `BLOCKED_INCOMPLETE_TREATMENT_VECTOR_DIRECTION_AUDIT`; a movable functional yields `BLOCKED_TREATMENT_VECTOR_MOVING_RECESSION_DIRECTION`; an empty or malformed family raises at `:3165–3175` |
| Dual-candidate raw/scaled Hessian residual bounds | Enforced | `dual_candidate_fitted_hessian_audit:5040` runs both candidates. `full_hessian_diagnostics:2589` requires `smallest_certified_lower_bound > threshold`, where the threshold is formed from the conservative induced-∞-norm upper bound rather than the Ritz estimate; ARPACK failure returns `-inf`/`+inf` and fails closed |
| Executed L-BFGS-B contradiction diagnostics | Enforced | `audit_lbfgsb_diagnostic_contradictions:4899` returns `binding_pass: False` when the diagnostic is absent, and `binding_pass is True` is a conjunct of `passed` at `:6337–6346`; `_a1_lbfgsb_diagnostic_evidence_passes` (`dependency_guard.py:1110`) requires `available is True`. `objective.function` is per-total (`:3438`), so the `1e-10` objective-gap rule is on the declared scale, and the stationarity certificate is present in L-BFGS-B diagnostics (`:4764`), so the stationary-target-contradiction trigger is live rather than dead code |
| Exact parent cell-receipt bytes | Enforced before parsing | `authenticate_cells:1766–1785` compares `sha256_file(receipt_path)` to the declared hash and raises before `load_json`; covered by `test_numerical_existence_audit.py:1905` |
| Target-map binding to the pre-outcome authorization commit | Strong | `validate_preoutcome_target_map_binding:414–527`. Map bytes must equal `auth_commit:<map>`; the auth commit must change exactly one file; its parent must equal `authorized_implementation_commit`; and the receipt summary must equal the reconstructed committed authority field-for-field |
| All 11 model statuses | Emitted | `run():6867–6907` iterates the full registry, and any exception yields `BLOCKED_UNEXPECTED_NUMERICAL_FAILURE_NO_SUBSTITUTION` with recovered boundary evidence rather than a dropped row. Suite status requires every `finite_target_established is True`. `dependency_guard.py:1259–1277` requires the audit registry to equal the frozen eleven exactly and cross-checks `passed_model_count` against independently recomputed certificates |
| Partial-run transfer behavior | Correct | `normalize_public_receipts.py:1833–1908` and `:2624–2625` emit `COMPLETE_SANITIZED_A1_PARTIAL_EVIDENCE_TRANSFER`; `TRANSFER_SPEC.template.json` replaces the hardcoded PASS with `<REQUIRED_NUMERICAL_RECEIPT_STATUS>`; covered by `test_normalize_public_receipts.py:583` and `:678` |
| Preserving the blocked historical run unchanged | Enforced | `validate_a1_amendment:772–955` byte-binds the blocked `MODEL_AUDIT.json` and receipt and requires `passed_model_count != 11`. `AtomicOutputLeaf.reserve` (`artifact_safety.py:184–200`) refuses any output leaf inside the repository or one that already exists, so the preserved run is unreachable as a write target |
| Unchanged scientific identity | Byte-identical | The parent payload, the A1 payload, and the declared fingerprint all equal `f5cf1106872117c3c67ce85da2fc76f661093a500ad31bfdcd58dfadfe6956e0`; direct payload comparison returns `True`. `hessian_diagnostics` is excluded from the fingerprint, correctly: it is prose numerical policy, which A1 explicitly amends, not a scientific input |

### Two constructs examined and cleared rather than reported

- `compare_trust_path_to_reference:5300–5301` falls back to all target
  functionals when no `original_treatment::` label is present. This is
  unreachable in production: both branches of `target_coordinate_bundle` always
  emit one functional per regressor, and `resolve_extended_likelihood_face:3165`
  raises on an empty family before this point. It is also non-weakening if it
  were reached.
- `a1_shared_problem_binding:5086–5168` always returns PASS — its two problem
  digests are computed from the same object — and `shared_problem_binding_pass`
  is absent from the `passed` conjunction at `:6337`. It is a recorded digest
  rather than a check; the actual binding is carried by the immutable
  specification and by the single shared `objective` instance passed to both
  paths.

---

## Operational note

This review file is committed on top of `cb9310c5`. The pre-execution
authorization must therefore be generated against the new HEAD:
`generate_pre_execution_authorization.py` requires
`head == --implementation-commit`, and
`validate_preoutcome_target_map_binding` requires
`auth_commit^ == authorized_implementation_commit`. The runner, specification,
and target-map bytes are unchanged by this commit, so
`required_a1_runner_code_sha256`, `required_a1_audit_spec_id`, and
`required_a1_audit_spec_sha256` all still match.
