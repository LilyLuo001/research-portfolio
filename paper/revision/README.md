# V3 substantive referee revision

This directory contains the editable response materials for the current V3
revision of *Occupational AI Exposure and Young-Worker Employment: Support and
Comparisons in the CPS*. It is a working revision package, not a claim that the
paper is submission-ready or independently replicated.

## Editable deliverables

- manuscript: `paper/main/working.tex` and its files under `paper/main/`;
- online appendix: `paper/appendix/appendix.tex` and its files under
  `paper/appendix/`;
- responses to Referees A and B: `paper/revision/referee_response.tex`;
- revision diagnosis and unresolved-work record:
  `paper/revision/revision_diagnosis.tex`;
- change record: `paper/revision/source_diff.tex`, using the generated
  `paper/revision/source_diff.txt`.

After the source tree is finalized, the V3 document target is:

```sh
make -C paper substantive-revision
```

It produces:

- `paper/build/YAX_REVISED_MANUSCRIPT.pdf`;
- `paper/build/YAX_FOCUSED_ONLINE_APPENDIX.pdf`;
- `paper/build/YAX_REFEREE_RESPONSE.pdf`;
- `paper/build/YAX_REVISION_DIAGNOSIS.pdf`; and
- `paper/build/YAX_SOURCE_DIFF.pdf`.

Where `latexmk` is unavailable but Tectonic is installed, the existing
alternative is:

```sh
paper/scripts/build_substantive_revision_tectonic.sh
```

Both commands compile documents only. They do not rerun an empirical model.
PDFs already present under `paper/build/` are snapshots and must be rebuilt
after any source change before their hashes or visual checks are treated as
current.

## Aggregate-only exhibit build

The existing aggregate exhibit command is separate from both TeX compilation
and protected-data re-estimation:

```sh
python3 paper/scripts/build_r3_exhibits.py --only all
```

Despite its historical filename, this script reads retained aggregate results,
including V3 support-inference outputs. It rebuilds three `r3_` figures and the
family-support, profile, leave-one-family-out, and endpoint-sensitivity tables.
It does **not** regenerate every V3 table, rerun CPS estimation, or certify the
full revision. Other V3 exhibits remain tied to their phase-specific result
directories and validators under
`yax/revision/substantive_v3_20260906/`.

## Evidence and completion boundary

The V3 instruction, immutable seed, working status ledger, specifications,
sanitized receipts, and retained aggregate results are under
`yax/revision/substantive_v3_20260906/`. Start with:

- `revision_inputs/EXECUTION_PROMPT_V3.md`;
- `revision_inputs/requirements_seed.json`;
- `requirements_status.json`;
- `source_inventory.json`; and
- `runs/` plus the relevant gate specification and validator.

Those records provide internal traceability. They do not by themselves prove
an independent replication: licensed CPS microdata and the protected Gate 1
cell object are not distributed, and an aggregate exhibit rebuild is not a
fresh microdata re-estimation.

The current genuine external-input limits are:

- the authorized CPS extracts do not contain `EARNWEEK2`, so the requested
  full-window weekly-earnings extension requires a new authorized extract;
- no verified public artifact supplies exhaustive BCC occupation-to-quintile
  membership, so public-data comparisons are labeled independent
  reconstructions rather than exact BCC replications; and
- affiliation, email, acknowledgments, funding, conflicts, repository/archive
  identifiers, and journal-specific disclosures remain
  `[AUTHOR TO COMPLETE]`.

Final delivery also requires a clean rebuild, updated hashes, visual inspection,
status-ledger reconciliation, and the delivery checks described in the V3
prompt. The presence of a run directory or a polished PDF is not a substitute
for those checks.
