# YAX V3 execution state

Updated: 2026-09-07 Asia/Shanghai

## Authoritative locations

- Instruction root: `revision_inputs/`
- Immutable seed: `revision_inputs/requirements_seed.json`
- Working status ledger: `requirements_status.json`
- Source/access inventory: `source_inventory.json`
- Contract code: `scripts/spec_contract.py`
- Run dependency code: `scripts/dependency_guard.py`
- Numerical/claim ledger code: `scripts/validate_claim_ledger.py`
- Canonical stamped specifications: `contracts/specs/`
- Sanitized blocked Gate 1 run: `runs/gate1_numerical_blocked_b9a7dd1/`
- Preserved compatibility-blocked A1 run:
  `runs/gate1_numerical_a1_compat_blocked_7482111/`
- Candidate-passing A1 replacement run:
  `runs/gate1_numerical_a1_pass_7482383/`
- Authoritative Gate 2 support/accounting run:
  `runs/gate2_support_accounting_authoritative_20260907/`
- Gate 2 validation and findings:
  `gate2/evidence/`

## Authoritative Gate 1 identifiers

- Authorized execution commit: `b9a7dd1c8703397f1a6686ff9b1a55d4bb67cbde`
- Canonical specification:
  `yaxspec_v1_83bb387f9fc28e2655db5101c7697989510475027d1dd5a9c361c797ed3925c3`
- Cell-build specification:
  `yaxcellspec_v1_e08b69694a4ebb0b15919b6af989cca98cea9e86eea80ef252f93b5cfccaa08b`
- Exact-target specification:
  `yaxtargetspec_v1_e0598066c90d6b7efad743ea68e074b5be2b455fb12eddf4b998430c0081b83b`
- Numerical specification:
  `yaxnumspec_v1_4c784c23726ad5ce258af6151afdf83e1e05efe6d1086d43007e5d06a5843991`
- Owner-authorized A1 numerical specification (pre-execution):
  `yaxnumspec_v1_5989d8d88e772711ff47c43011e9f90f4764dc8d89230ef5486b6687f59dc05c`

## Stage state

- Package and repository inventory: completed and recorded.
- Gate 0 understanding contract: completed; reviewed by a separate agent on the
  same execution team, explicitly not independent scientific review.
- Gate 1 contract/dependency/ledger engineering: implemented, fully tested, and
  independently challenged within the same execution team. The GPFS-compatible
  publication path passed in the live execution.
- Gate 1 restricted-data cell reconstruction: passed. The restricted aggregate
  was not transferred into Git.
- Gate 1 exact-target integrity audit: passed on 52,884 static
  occupation-month rows and 51,891 positive-total estimating rows.
- The original Gate 1 numerical existence/convergence audit remains blocked on
  all 11 predeclared models. Its diagnostic coefficients remain unvalidated.
- The first owner-authorized A1 replacement attempt, SCC job `7482111`,
  completed at the scheduler level but retained all 11 models as
  `BLOCKED_UNEXPECTED_NUMERICAL_FAILURE_NO_SUBSTITUTION`: pinned NumPy 2.5 had
  removed the `row_stack` alias used by the shared-problem digest. No solver or
  coefficient was certified. The exact same-operation `vstack` repair and its
  regression test are recorded in
  `numerical_existence/NUMERICAL_AMENDMENT_A1_COMPATIBILITY_01.md`.
- The standard PASS-only transfer normalizer correctly rejected the blocked
  numerical receipt. A separate sanitized receipt-only evidence package was
  validated and retained under `runs/gate1_numerical_blocked_b9a7dd1/`. A
  separate-agent same-team review found no P1/P2 defects in that package or its
  ledger disposition.
- The compatibility-corrected replacement, SCC job `7482383`, completed with
  scheduler `failed = 0`, `exit_status = 0`. All 11 models emitted A1 numerical
  certificates at the unchanged thresholds, including the seasonal model that
  failed under both original solvers. The sanitized transfer passed.
- A post-run dependency-guard schema mismatch initially blocked release. The
  reader-only correction is recorded in
  `reviews/GATE1_NUMERICAL_A1_POSTRUN_GUARD_SCHEMA_CORRECTION.md`; it changes no
  producer, target map, result, estimator, or threshold. The corrected guard
  independently recomputed 11 model certificates, 20 consumer releases, 9
  requirement releases, the three non-model prerequisites, and the pre-outcome
  map binding.
- The final independent read-only artifact review at reviewed commit `d98371d5`
  found no P1 numerical defect and independently upheld all 11 certificates.
  Its one bounded P2 evidence-labeling defect and four P3 provenance/ledger
  defects are preserved and adjudicated in
  `reviews/GATE1_NUMERICAL_A1_POSTRUN_FINAL_REVIEW_DISPOSITION.md`. The closure
  commit is `85ac2d21023b1db09a39e2420447c953cd1630ee`.
- N03 remains `RUN_UNVALIDATED` only because manuscript/appendix integration
  and presentation validation have not occurred. The numerical prerequisites
  are independently certified. Dependent Gate 2 units named as `RELEASED` in
  `runs/gate1_numerical_a1_pass_7482383/DEPENDENCY_RELEASE.json` may now run;
  no unreleased or presentation claim is implied.
- The first Gate 2 support/accounting execution was retained outside the
  repository as provisional because its receipt lacked artifact-level result
  IDs. Its scientific values were not retrofitted or cited.
- A distinct authoritative Gate 2 execution ran directly in a fresh clean SCC
  clone at commit `9d49bba5a931b4d6c62bf41c81251f922b57c40e`. Its receipt authenticates 12
  aggregate-only result artifacts and their result IDs. The signed run package
  contains exactly those 12 artifacts plus the receipt; later validation and
  findings documents are kept separately under `gate2/evidence/`.
- Separate-agent artifact review found no P1 or P2 defect in the authoritative
  package. S01, S02, D01, D03, and D04 now have validated point/support evidence
  but remain `RUN_UNVALIDATED` pending their outstanding inference and
  manuscript/appendix presentation checks.

All 11 A1 numerical targets are now independently artifact-reviewed, but no V3
coefficient is yet manuscript-ready. Interpretation and presentation remain
separately governed. The cell and exact-target audits establish the estimating-
data object, not a causal or substantive manuscript claim.

## Verified inputs and blockers

The source inventory records authenticated CPS extracts 9, 10, 11, and 12,
the public/versioned measurement inputs, and SCC access. `EARNWEEK2`, ACS
microdata, exact BCC code membership, proprietary BCC outcomes, and an adopted
external-adoption analysis input are not currently available. Absence from the
current extracts is not evidence of absence from the survey.

## Operational rule

Use a fresh SCC worktree on the authorized project compute tier. Do not reuse a
stale dirty SCC checkout. Do not cancel, kill, or alter pre-existing SCC jobs or
sessions. Restricted inputs remain read-only. Do not publish restricted
aggregate cells or private compute paths.

## Gate 1 scientific decision

The frozen audit requires the declared KKT/full-Hessian checks and the
same-objective two-solver benchmark. Most trust-region fits passed their
certificate while L-BFGS-B did not; one seasonal model failed the original-
coordinate KKT rule under both solvers. An identical deterministic rerun cannot
turn that rule failure into validation. The blocked numerical finding is
retained and must not be replaced by an unapproved estimator, tolerance, or
selective subset.

## Next resumable tasks

The A1 execution, independent audit, finding disposition, and remote push are
complete. The original and compatibility-blocked runs remain preserved.

1. Complete Gate 2 support inference and heterogeneous pairwise contrasts
   (S03, S04, S06, S07) from the authenticated fixed-support contract; S05
   requires a separate broader-beta aggregate producer without Webb.
2. Complete the D02 single-age identification audit and the remaining D05--D07
   decomposition/inference work without relabeling exact stock accounting as a
   regression coefficient.
3. Execute the dynamic reconciliation core (Y01--Y05) from the four certified
   static/dynamic models. Keep the onset grid and through-2024 comparisons
   partial until their additional models receive same-objective numerical
   certification.
4. Integrate and validate all released evidence in the manuscript and appendix
   before changing any `RUN_UNVALIDATED` requirement to `VERIFIED`.
