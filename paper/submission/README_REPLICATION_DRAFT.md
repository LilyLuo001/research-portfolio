# V3 replication-package draft

This file documents the current replication route for *Occupational AI
Exposure and Young-Worker Employment: Support and Comparisons in the CPS*.
It intentionally does not name a final replication commit, tag, archive DOI,
or public repository: none has yet been finalized for the V3 delivery.

## What is and is not distributed

- **CPS outcomes.** The analysis uses IPUMS CPS public-use microdata obtained
  under an authorized IPUMS account. The extracts and the protected Gate 1
  occupation-month cell object are not redistributed. A replicator must obtain
  an extract matching the documented variable, sample, and calendar contracts.
- **ACS extension.** The annual extension uses the public ACS one-year PUMS for
  2017--2019 and 2021--2024, including the 80 person replicate weights. The
  standard 2020 one-year file is not spliced into the analysis. Acquisition and
  construction rules are in
  `yax/revision/substantive_v3_20260906/gate4/acs_extension/ACS_EXTENSION_SPEC.md`.
- **Exposure and mapping inputs.** Versioned exposure lookups, computerization
  measures, Rule-B values, and official occupation bridge files are inventoried
  with checksums in
  `yax/revision/substantive_v3_20260906/source_inventory.json`. Redistribution
  still depends on each source's license.
- **BCC benchmark boundary.** The verified public BCC materials do not provide
  exhaustive occupation-to-quintile membership. The V3 CPS and ACS exercises
  are therefore independent public-data reconstructions, not exact BCC
  replications.

No credential, user-specific path, compute host, licensed record, or direct
identifier belongs in a public configuration or receipt.

## Document and aggregate-exhibit rebuilds

From the repository root, rebuild the subset of journal-facing exhibits with a
checked-in aggregate builder:

```sh
python3 paper/scripts/build_r3_exhibits.py --only all
```

This command reads aggregate result files only. It currently rebuilds the four
`r3_` figures and four selected appendix tables; it is not a full empirical
rerun and is not the producer for every V3 table.

Compile the five V3 revision documents with:

```sh
make -C paper substantive-revision
```

or, when using Tectonic rather than `latexmk`:

```sh
paper/scripts/build_substantive_revision_tectonic.sh
```

The resulting draft PDFs are the manuscript, focused online appendix, referee
response, revision diagnosis, and source diff under `paper/build/`. The
separate journal/circulation target remains `make -C paper all`; it does not
replace the five-file V3 revision build.

## Fresh re-estimation from authorized data

There is no truthful one-command full V3 rerun. The work is a dependency-ordered
set of authenticated modules. Use each signed specification, runner interface,
and retained execution receipt; create fresh output leaves rather than writing
over the archived results.

1. **Reconstruct and authenticate the CPS analysis object.** Follow
   `gate1_cells/CELL_BUILD_SPEC.json` and `gate1_cells/run_gate1_cells.py`, then
   `gate1_target/TARGET_AUDIT_SPEC.json` and
   `gate1_target/run_exact_target_audit.py`. The placeholder-only production
   commands and required authorization checks are documented in each module's
   `README.md`.
2. **Certify numerical existence and reconstruct the canonical baseline.** Use
   `numerical_existence/ANALYSIS_SPEC_A1.json` with
   `numerical_existence/run_numerical_existence_audit.py`, and use
   `contracts/specs/canonical_baseline_reproduction_v2.json` with
   `gate1_baseline/run_gate1_baseline.py`. Sanitized reference receipts and
   validation records are under `runs/gate1_*` and `gates/`; they are expected-
   output evidence, not inputs that authorize a new run.
3. **Run support and dynamic branches after their named Gate 1 prerequisites
   pass.** The relevant signed inputs and runners are in `gate2/`: support
   accounting (`SUPPORT_ACCOUNTING_SPEC.json`), support inference
   (`support_inference/SUPPORT_INFERENCE_SPEC.json`), dynamic reconciliation
   (`dynamic/DYNAMIC_CORE_SPEC.json` and
   `dynamic/DYNAMIC_RECONCILIATION_SPEC.json`), broader support
   (`broader_support/BROADER_SUPPORT_SPEC.json`), and timing extensions
   (`timing_extensions/TIMING_EXTENSIONS_SPEC.json`). Their retained reference
   outputs and receipts are the corresponding `runs/gate2_*` directories.
4. **Build the protected calibration object before Gate 3 refits.** The producer
   is `gate3/inference_validation/build_private_calibration.py`; its output is
   intentionally not versioned. Conditioning, inference, shortfall, mapping,
   architecture, and equal-occupation modules then use their own specifications
   and runners under `gate3/`. Several of these consume the protected
   calibration object even when they no longer read row-level CPS directly.
5. **Run the focused extensions separately.** The specifications and runners
   are under `gate4/public_benchmark/`, `gate4/cohort_enrollment/`,
   `gate4/flows/`, `gate4/acs_extension/`, `gate4/honestdid/`, and
   `gate4/adoption/`. CPS benchmark, cohort, and flow modules require authorized
   CPS inputs; ACS and adoption use separately acquired public inputs;
   HonestDiD consumes the validated dynamic objects. Authoritative reference
   outputs and execution/validation receipts are under the matching
   `runs/gate4_*` directories.

All paths in this section are relative to
`yax/revision/substantive_v3_20260906/` unless they begin with `paper/`. The
exact dependency map and active completion state are recorded in
`contracts/TARGET_DEPENDENCY_MAP_A1.json` and `requirements_status.json`.
Because V3 is an outcome-informed referee revision, it must not be described as
a preregistration.

## Traceability versus independent replication

The repository's signed specifications, checksums, sanitized receipts,
aggregate outputs, validators, and requirement ledger make the production
history internally auditable. Public-output recomputation and adversarial code
review can verify calculations from retained objects. Neither is equivalent to
an independent raw-data replication.

A clean independent replication requires the replicator to acquire the
authorized source data, rebuild Gate 1, follow the dependency order above,
compare fresh result identities with the retained run packages, regenerate the
exhibits, and rebuild the documents. Until that exercise is completed, the
package should be described as traceable and executable under authorized
access—not independently replicated.

## Current unresolved items before public release

- A new authorized CPS extract containing `EARNWEEK2` and its required weight
  and rotation fields is needed for the full-window weekly-earnings extension.
- Exact exhaustive BCC occupation membership is unavailable in the verified
  public artifacts; do not relabel the independent reconstruction as exact.
- The working requirement ledger, final source tree, PDF hashes, and visual QA
  must be reconciled together after the last substantive edit.
- [AUTHOR TO COMPLETE] affiliation, email, acknowledgments, funding, conflicts,
  journal disclosures, public repository URL, archive DOI, license, and
  redistribution permissions.
