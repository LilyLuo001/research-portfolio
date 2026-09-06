# Gate 1 canonical baseline reconstruction: pre-results execution specification

Status: written before the V3 fresh microdata reconstruction. This is a
post-outcome, referee-led diagnostic. It is neither preregistration nor a new
confirmatory analysis.

Canonical specification:
`contracts/specs/canonical_baseline_reproduction_v2.json`, identifier
`yaxspec_v1_83bb387f9fc28e2655db5101c7697989510475027d1dd5a9c361c797ed3925c3`.
The wrapper also pins its byte hash; `--spec` may point to an immutable copy but
cannot substitute another validly restamped specification.

The wrapper must validate that identifier and authenticate every source listed
in the contract, the BASE-03 runner and its transitive imports, the R3
environment lock and exact SCC runtime, and both declared reference
dependencies. The declared historical preperiod-cell input must match both its
own source hash and the hash authenticated by the declared first-access
receipt. A nonempty result
directory is an unconditional stop. No estimator option is exposed by the
wrapper.

The first stamped contract omitted that command input from `data.sources`.
Before this V3 run, the omission was corrected through a new immutable,
content-addressed contract. The original contract remains preserved, and
`CONTRACT_AMENDMENT_01.md` records the exact change and chronology. The wrapper
authenticates the file directly and cross-checks it against the separately
contract-authenticated first-access receipt.

The transitive-code lock is supplemental execution authentication, not an
amendment to the scientific specification. Its own byte hash is pinned inside
the wrapper. The SCC lock writes `x86_64` separately from the kernel build,
while `platform.release()` appends `.x86_64`; the runtime comparison permits
only that duplicated architecture suffix and otherwise requires exact fields.

Execution order is fixed:

1. refuse nonempty result and audit destinations;
2. validate the canonical JSON and recompute its `spec_id`;
3. authenticate the contract-hashed runner, its transitive imports, declared
   reference dependency files, the environment, all declared sources, and the
   historical-input cross-authentication, without loading reference checkpoint
   values;
4. invoke the existing R3 BASE-03 runner exactly once;
5. if and only if it exits zero, invoke the existing R3 self-check exactly once;
6. if and only if that exits zero, authenticate the fresh output manifest and
   only then authenticate and read the byte-pinned R3 reference receipt and
   self-check;
7. compare fresh membership, support, calendar, normalization, and the three
   BASE-03 checkpoint rows with the contract and authenticated R3 reference;
8. emit a sanitized V3 run receipt and retained stdout, stderr, and failure log.

The result and audit leaves must not already exist and must be outside the Git
repository. Their atomic creation is the concurrency reservation. A second job
cannot share them.

Comparisons happen only after estimation and self-checking. A mismatch fails
the run; it does not trigger tuning, a changed sample, a changed solver, or an
automatic retry. Membership and support identifiers are exact hashes.
Contract cut values use an absolute tolerance of `1e-12`. Other numeric
contract/reference comparisons use absolute and relative tolerances of
`1e-10`. These tolerances are engineering equality checks, not inferential
thresholds.

The three diagnostic checkpoint rows are:

- `historical_108_historical_treatment`;
- `corrected_113_historical_treatment`;
- `corrected_113_recomputed_preperiod_treatment`.

The wrapper compares their coefficient, analytic cluster standard error,
bootstrap standard error, interval endpoints, and bootstrap p-value, together
with support and calendar fields. It also requires an empty BASE-03 model
failure file. External reference-bundle checkpoint values are read only after
the fresh runner and self-check exit; they are never passed to the estimator.
The locked R3 programs themselves retain their historical post-fit checkpoint
assertions; those assertions abort on drift but do not tune or refit the model.
The two dependency
files named by the contract are authenticated by hash before execution but are
not parsed by the wrapper at that stage.

The V3 receipt creates one canonical `result_id` for each of the three
checkpoint rows from the immutable `spec_id`, the fresh decomposition-artifact
hash, and an exact row/field selector. It records Git HEAD and a hash/count of
worktree status, but does not edit the global result ledger or run DAG. Those
project-level registrations and the transfer of the sanitized receipt into the
contract-named repository location remain explicit prerequisites before the
corresponding requirement can be marked verified.

No successful execution is claimed by this document. Protected microdata have
not been read merely by adding the wrapper and its tests.
