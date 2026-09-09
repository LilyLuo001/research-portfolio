# YAX V3 execution state

Updated: 2026-09-09 Asia/Shanghai after validated Gate 3/4 result integration;
the final integration commit is pending.

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
- Authoritative Gate 2 support-inference run:
  `runs/gate2_support_inference_authoritative_20260908/`
- Gate 2 support-inference post-run validation:
  `gate2/support_inference/evidence/POSTRUN_VALIDATION_REPORT.json`
- Authoritative Gate 2 dynamic-core run:
  `runs/gate2_dynamic_core_authoritative_20260908/`
- Gate 2 dynamic-core independent validation:
  `gate2/dynamic/evidence/DYNAMIC_CORE_POSTRUN_VALIDATION.json`
- Authoritative Gate 2 broader-support run:
  `runs/gate2_broader_support_authoritative_20260908/`
- Gate 2 broader-support independent validation and findings:
  `gate2/broader_support/evidence/`
- Authoritative Gate 2 timing-extension run:
  `runs/gate2_timing_extensions_authoritative_20260908/`
- Gate 2 timing-extension independent validation and findings:
  `gate2/timing_extensions/`
- Gate 4 public-benchmark package and authoritative run:
  `gate4/public_benchmark/` and
  `runs/gate4_public_benchmark_authoritative_20260908/`
- Gate 4 CPS-flow package and authoritative run:
  `gate4/flows/` and
  `runs/gate4_flow_selection_authoritative_20260909/`
- Gate 4 annual-ACS package and authoritative run:
  `gate4/acs_extension/` and
  `runs/gate4_acs_authoritative_20260909/`
- Gate 3 characteristic findings and authenticated industry carry-forward:
  `gate3/characteristics/`
- Gate 3 mapping, architecture, and equal-occupation packages and runs:
  `gate3/mapping/`, `gate3/architecture/`, `gate3/equal_occupation/`,
  `runs/gate3_mapping_authoritative_20260908/`,
  `runs/gate3_architecture_authoritative_20260909/`, and
  `runs/gate3_equal_occupation_authoritative_20260909/`
- Gate 4 cohort/enrollment and HonestDiD packages and cohort run:
  `gate4/cohort_enrollment/`, `gate4/honestdid/`, and
  `runs/gate4_cohort_enrollment_authoritative_20260908/`
- Active manuscript, appendix, referee response, and revision diagnosis:
  `paper/main/`, `paper/appendix/`, and `paper/revision/`
- Draft delivery PDFs and hashes: `paper/build/`

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
- N03 numerical prerequisites are independently certified and the findings are
  integrated in Online Appendix E. N03 remains `RUN_UNVALIDATED` pending its
  upstream dependency and final compiled-document review. Gate 2 units named as
  `RELEASED` in
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
  package. S01, S02, D01, D03, and D04 have validated point/support evidence and
  are integrated in the current paper sources. They remain `RUN_UNVALIDATED`
  pending their upstream, inference, and final rendered-delivery checks.
- The outcome-free D02 identification implementation is frozen at specification
  `yaxgate2d02spec_v1_2357904781f082216bc398baadef1e2005bc0b1d4c40d0b7ed1c63250e09e0c3`.
  It proves that unrestricted occupation-by-calendar-month effects absorb all
  five single-age exposure-by-post columns on 52,884 rows and separately shows
  rank five for an additive occupation-plus-month companion. A pre-execution
  adversarial review found one fail-closed contract defect; the repaired
  producer/specification handshake passed re-review with 24 focused tests. D02
  was executed directly from clean SCC worktree commit `9c19741` and passed
  post-run artifact validation. D02 is integrated in Online Appendix C but
  remains `RUN_UNVALIDATED`, not `VERIFIED`; the outcome-bearing additive
  companion was not estimated and upstream/final render checks remain open.
- The authoritative Gate 2 support-inference execution, SCC job `7489785`, ran
  from authorization commit `62c3da6` and exited successfully. It published 40
  result artifacts plus a manifest and receipt under result ID
  `yaxresult_v1_b53fefb7dd5185f8a7d6d3e7cf45df938d6e5205bf75eacabc9e8ee26bfc496a`.
  All five required models passed their unchanged A1 certificates and all 26
  producer validation checks passed. A repository-side validator independently
  checked every artifact hash and content identity and reconstructed the
  published profile differences, covariance-based standard errors, confidence
  intervals, simultaneous critical values, and joint tests from the retained
  public objects. S03, S04, S06, and S07 are integrated in the current sources
  but remain `RUN_UNVALIDATED` pending upstream and final rendered review.
- The resulting profile changes materially after family-by-month conditioning:
  pooled Q5-by-post is -0.1321 (SE 0.0452), versus -0.0217 (SE 0.0713) in the
  family-month model. The paired Q5 movement is 0.1104 (SE 0.0519; marginal
  normal p=0.0333), but the four-coefficient paired profile does not reject
  jointly (chi-square 5.4169 on 4 df, p=0.2471; multiplier p=0.2368). These are
  validated run facts. The manuscript now presents them as conditional-estimand
  comparisons, not as a causal decomposition.
- The authoritative Y01--Y05 dynamic-core execution, SCC job `7489898`, ran
  from clean frozen commit `6c65820f9ba525ec31f97ead0d4db5fc6d60d668`,
  exited successfully in 223 seconds, and published 14 result artifacts plus a
  manifest and receipt under result ID
  `yaxresult_v1_b039944581f0da60fb7e8368bff687858b740a7e638c190a8c934369fc10defe`.
  All four models passed fresh unchanged A1 certification. Repository-side
  recomputation reproduces all 18 reconciliation targets and their covariance,
  every event-study interval, all 16 pretrend tests, and all leave-one-quarter,
  level, drift, and seasonality diagnostics to at most `1.19e-12`.
- Exact nesting holds with zero design residual. The static-score discrepancy at
  dynamic fitted probabilities is below `9.0e-13` per total, and the pseudo-stock
  projection reproduces the static treatment targets exactly at reported
  precision. Full coefficient/covariance/influence rebasing changes governed
  quantities by at most `1.70e-15` relative.
- The reference-invariant dynamic contrast D agrees closely with the static S:
  unconditioned S is -0.1321 and D is -0.1314; family-month S is -0.0217 and D
  is -0.0217. The published-reference post functional P is -0.1199 and -0.2074,
  respectively, showing that its family-month discrepancy is driven by the
  2022Q4 reference-period level rather than by failure of static/dynamic nesting.
- Y01--Y05 computation, numerical validation, and source integration are
  complete. They remain `RUN_UNVALIDATED` until their dependencies and the
  final compiled-document review are closed.
- The authoritative S05 broader-beta/no-Webb execution, SCC job `7490033`, ran
  successfully and published four same-objective models. Removing Webb expands
  beta-valid support from 468 to 490 occupations but changes the coefficient by
  only -0.000601 when primary raw-beta cutoffs are held fixed. Recomputing the
  cutoffs on the broader support changes it by another -0.000458. Direct Q1--Q5
  support expands from four to five occupational families, so limited
  within-family tail support remains after relaxing Webb availability. All four
  numerical fits pass independent corroboration, and all 64 public artifact and
  calculation checks pass. The decomposition is integrated in Online Appendix C;
  S05 remains `RUN_UNVALIDATED` pending S01 and final compiled review.
- The authoritative N04/T05/Y08/Y09 timing-extension execution, SCC job
  `7490289`, ran at commit `4b298853f439fda1577a14f7dc598f7832f54466`
  and exited with scheduler `failed=0`, `exit_status=0`. It published 34 models,
  47 paired comparisons, their complete covariance and influence objects, and
  result ID
  `yaxresult_v1_cc076af4f71d56d02f4944b07bc69e93db2c10f369512aa83641be1e71e659e4`.
  All 34 fits pass fresh A1 numerical certification. Independent validation
  reconstructs all marginal, paired, and simultaneous intervals to at most
  `1.07e-14`.
- Timing choices do not materially alter estimates within either structure at
  the design's precision. The through-2024-minus-full movements are 0.0211
  (95% CI -0.0073 to 0.0495) unconditioned and 0.0097 (-0.0536 to 0.0730)
  family-month. Seasonality changes are below 0.0011 in absolute value, and
  every onset-grid paired change includes zero. The cross-structure movement
  remains about 0.088--0.134 across the declared variants. N04, T05, Y08, and
  Y09 are integrated in source and remain `RUN_UNVALIDATED` pending dependencies
  and final compiled review.
- The complete Gate 3 finite-sample program ran all eleven declared DGPs at
  799--1,599 outer replications and 9,999 common multiplier draws, with zero
  failed joint refits. Independent reconstruction passes. Occupation
  wild-score intervals under-cover all three empirical targets; family
  clustering is conservative for pooled and paired empirical targets but
  under-covers family-month and fails more broadly in the adverse designs. The
  near-nominal oracle is not implementable and, under the empirical structural
  null, still rejects zero for pooled and paired projections because those
  pseudo-targets are nonzero. The finite-sample findings are integrated in
  Online Appendix E; I02--I06 remain `RUN_UNVALIDATED` for their recorded
  dependencies and final delivery review. No universal correction or ad hoc SE
  inflation is adopted.
- The repaired pandemic-shortfall pipeline completed 399 linked-household
  full refits on a strict 363-occupation support, with zero failures and
  maximum endpoint MCSE 0.00979 against 0.01. Total-stock conditioning moves
  the pooled/family-month exposure coefficients by +0.00040/-0.00050;
  young-relative conditioning moves them by +0.00114/+0.00613. Regenerating
  the shortfalls roughly doubles some conditioning-movement sampling
  sensitivities but does not overturn those magnitudes. A two-direction
  linked-household split produces a similar average with heterogeneous
  directions. I08 and C05 calculations, public validation, and bounded source
  presentation are complete; they remain `RUN_UNVALIDATED` for their recorded
  dependencies and final delivery review.
- The annual ACS extension completed on seven ordinary one-year PUMS files and
  passes all 17 independent output checks. It uses all 80 replicate weights per
  perturbed endpoint year, separates ACS sampling uncertainty from
  occupation/family shocks, and pairs pooled and family-year estimates on fixed
  support. The results are integrated in Online Appendix H. B06 is
  `RUN_UNVALIDATED` pending S05 and final compiled-document review.
- The Gate 4 public-CPS benchmark is independently reconstructed and integrated
  as an analogue, not an exact BCC replication. Exact BCC occupation membership
  and proprietary payroll conditions remain unavailable.
- The Gate 4 flow run passes its recomputation validator with 300 baseline-rate
  rows, 120 eligibility rows, 84 destination rows, selection sensitivities,
  missing-outcome intervals, and annual-onset diagnostics. The paper distinguishes
  the risk sets and does not call entry allocation a hiring rate or a stock-flow
  decomposition. F01--F06 and F08 are `RUN_UNVALIDATED`; full-window EARNWEEK2
  evidence remains `BLOCKED_INPUT` under F07.
- The cohort/enrollment package validates 20 models, 14 paired comparisons,
  national and employed-young composition profiles, and no exposure assignment
  to nonworkers. The full composition exhibit is integrated in Online Appendix D.
- The current mapping, architecture, and equal-occupation runs all pass their
  public validators. The appendix separates their 369-, 408-, 444-, 455-, 468-,
  and 490-occupation estimands instead of presenting them as one support.
- The Gate 3 characteristic block and authenticated industry carry-forward are
  validated and integrated into the manuscript. On fixed 455-occupation
  support, adding pre-2022 computer use moves the pooled coefficient from
  -0.0958 to -0.1966, while adding family-by-month paths moves it to 0.0354.
  The combined-minus-baseline interval contains zero. These are non-additive
  conditional projections, not causal AI or computerization components.
- The retained 113-month lambda and E1/E2 architecture audit passes a fresh
  public carry-forward check. Lambda 0.5 reproduces literal beta within the
  signed `1e-10` tolerance; all memberships, paired draws, primitive
  covariance, and illustrative contrasts are complete. W06 remains
  `RUN_UNVALIDATED` until T02, final packaging, and rendered review pass.
- The active paper uses the comparison-centered title "Occupational AI Exposure
  and Young-Worker Employment: Support and Comparisons in the CPS." Both
  abstracts and the introduction define the exact conditional-mean stock-ratio
  estimand before reporting its value. The manuscript, appendix, referee
  response, revision diagnosis, and source diff now contain the validated result
  packages. The settled source tree has been rebuilt into five PDFs; all 126
  pages, including the new support and simulation tables, pass visual review.

All statuses remain conservative. Source integration does not by itself promote
an empirical row to `VERIFIED`; unresolved dependencies, external-input blocks,
and final rendered-delivery review remain explicit in `requirements_status.json`.

## Verified inputs and blockers

The source inventory records authenticated CPS extracts 9, 10, 11, and 12 and
the public/versioned measurement inputs. All seven required one-year ACS PUMS
files were acquired and used in the authoritative public extension; raw ZIPs
remain outside Git. `EARNWEEK2`, exact BCC occupation membership, and proprietary
BCC outcomes are not currently available. Author-controlled affiliation,
contact, acknowledgment, funding, conflict, journal-disclosure, repository,
license, and redistribution fields are separately retained as an E12
`BLOCKED_INPUT` item. Absence from the current authorized extracts is not
evidence that a survey variable does not exist.

## Operational rule

Use a fresh SCC worktree on the authorized project compute tier. Do not reuse a
stale dirty SCC checkout. Do not cancel or kill pre-existing SCC jobs or
sessions. Queue/resource corrections requested by the owner may be made without
deletion. Restricted inputs remain read-only. Do not publish restricted
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

The original and compatibility-blocked numerical runs remain preserved.

1. Retain F07 as `BLOCKED_INPUT` until an authorized `EARNWEEK2` extract exists,
   B02 as blocked on exact public BCC membership, and E12 as blocked on the
   author's metadata and disclosure decisions.
2. Complete G02 only after an exhaustive sentence-level source extraction can
   be demonstrated; the current 297-row matrix is internally valid but does not
   prove that premise.
3. Build a bounded sanitized executable export before advancing E10. The current
   research tree contains necessary provenance records with private compute-path
   strings and is not itself a public-release package.
4. Obtain the author fields, repeat the five-document build if they change the
   PDFs, and run a final end-to-end external review against the frozen package.
5. Commit and push the source, public run packages, ledger, state, and five draft
   PDFs together; verify the remote commit without claiming submission readiness.
