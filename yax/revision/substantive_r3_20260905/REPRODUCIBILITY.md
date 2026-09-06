# Substantive R3 reproducibility entry point

The versioned repository contains the code, specifications, seeds, stored
aggregate score/influence and covariance objects, failure records,
table/figure generators, and hash receipts needed to prepare a replication
release. It is not itself asserted to be the sanitized public package. The
positive release allowlist is
`baseline_inventory/PUBLIC_REPLICATION_MANIFEST.csv`; its scan contract and
provenance limitations are in
`baseline_inventory/INPUT_PROVENANCE_RECEIPT.md`. Only a separately staged
candidate that passes those checks may be called the public replication
package. Licensed CPS microdata, credentials, direct identifiers, account
metadata, download links, private provenance objects, and operational paths
are outside that package.

## One-command aggregate audit

From a clean checkout with Python dependencies installed:

```bash
bash paper/scripts/run_substantive_revision_audit.sh
```

The command regenerates exhibits from committed aggregate results, verifies the
committed rebuilt-family artifacts, runs the fail-closed numerical/prose audit,
and executes the repository test suite. If `latexmk` is available, it also
builds all five revision PDFs. It does **not** read CPS microdata or re-estimate
the empirical modules, so its success is an aggregate-package consistency
check rather than a raw-data reproduction.

## SCC PDF build

On an SCC checkout with TeX available:

```bash
YAX_REPO_ROOT=/absolute/path/to/clean/checkout \
  bash paper/scripts/scc_build_major_revision_pdfs.sh
```

The script uses the pre-revision commit `6b8d85e` to generate the source diff
and writes five named PDFs plus SHA-256 hashes to `paper/build/`.

## Restricted-data reruns

The initial inventory's statement that the rebuilt baseline was unimplemented
is superseded: BASE-03 has a successful runner, wrapper, results receipt, and
21-check PASS self-check under `rebuilt_baseline/`. The authenticated extract
numbers, hashes, and available request/DDI/codebook timestamps are in
`baseline_inventory/INPUT_MANIFEST.csv`.

A user with lawful IPUMS access can run the ordered restricted-data pipeline
from a clean checkout with:

```bash
export YAX_REPO_ROOT=/path/to/clean/checkout
export YAX_PRIVATE_ROOT=/path/to/licensed/ipums/root
export YAX_RERUN_ROOT=/path/to/new/empty/output-directory
export YAX_PYTHON_BIN=/path/to/python
export YAX_FIRST_ACCESS_RECEIPT=/path/to/authenticated/first-access-receipt.json
export YAX_HONESTDID_R_LIB=/path/to/pinned/R/library
bash "$YAX_REPO_ROOT/yax/revision/substantive_r3_20260905/run_restricted_full_rerun.sh"
```

The orchestrator authenticates inputs, refuses an existing output root, runs
BASE-03 before dependent workstreams, passes fresh named contracts downstream,
and requires each module self-check. Exact component commands and the
restricted/public boundary are documented in
`baseline_inventory/REPRODUCTION_COMMANDS.md`. Operational private paths are
supplied only through environment variables and the restricted handoff.

Random draws are reproducible from stored seeds and distributions; common-draw
paired comparisons additionally preserve score/influence or covariance
representations. `NUMERICAL_CONSISTENCY_AUDIT.csv` identifies the source row
behind every load-bearing rounded manuscript quantity, and
`SUBSTANTIVE_REVISION_AUDIT.json` hashes the final aggregate evidence package.
