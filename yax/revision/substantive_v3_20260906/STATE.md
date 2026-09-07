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
- Gate 1 numerical existence/convergence audit: executed on all 11 predeclared
  models and blocked. Every model is classified
  `BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK`; the diagnostic coefficients are
  not validated estimates.
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
- Dependent Gates 2--5 have not run under V3. Unrelated feasible verification
  work may continue, but no downstream result may bypass the Gate 1 blocker.

No V3 coefficient is currently represented as verified. Existing R3 outputs
and the 11 new diagnostic focal values are reference artifacts only. The cell
and exact-target audits establish the estimating-data object, not a validated
coefficient.

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

Owner authorization A1 is now preserved at
`revision_inputs/GATE1_NUMERICAL_ADJUDICATION_A1.md`. The same-estimator repair,
new `ANALYSIS_SPEC_A1.json`, original-solver diagnostics, and target-level
dependency map are implemented and locally tested. The first A1 execution is
preserved as a compatibility failure, not numerical evidence; the corrected
replacement run has not yet executed. The old specification and blocked runs
above remain unchanged.

1. Commit and issue a fresh one-shot execution authorization for the
   compatibility-corrected A1 implementation.
2. Run all 11 models on the exact retained authenticated cell artifact without
   rebuilding or opening row-level microdata.
3. Preserve every model disposition and apply the target-level dependency map;
   never describe a partial set as suite completion.
4. Continue only the Gate 2 units whose exact target prerequisites certify.
