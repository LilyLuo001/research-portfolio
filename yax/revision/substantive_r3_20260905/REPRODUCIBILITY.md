# Substantive R3 reproducibility entry point

The public replication package contains code, aggregate cells and results where
redistribution is permitted, specifications, seeds, stored score/influence and
covariance objects, failure logs, table/figure generators, and hash receipts.
Licensed CPS microdata, credentials, and direct identifiers are excluded.

## One-command aggregate audit

From a clean checkout with Python dependencies installed:

```bash
bash paper/scripts/run_substantive_revision_audit.sh
```

The command regenerates exhibits, verifies the rebuilt-family artifacts, runs
the fail-closed numerical/prose audit, and executes the complete test suite.  If
`latexmk` is available, it also builds all five revision PDFs.

## SCC PDF build

On an SCC checkout with TeX available:

```bash
YAX_REPO_ROOT=/absolute/path/to/clean/checkout \
  bash paper/scripts/scc_build_major_revision_pdfs.sh
```

The script uses the pre-revision commit `6b8d85e` to generate the source diff
and writes five named PDFs plus SHA-256 hashes to `paper/build/`.

## Restricted-data reruns

Each empirical module has its signed analysis specification, executable runner,
SCC wrapper, output receipt, self-check, and failure record under
`yax/revision/substantive_r3_20260905/`.  The authenticated input hashes are in
`baseline_inventory/INPUT_MANIFEST.csv`; operational private paths are retained
only in the restricted SCC handoff.  A user with lawful IPUMS access may point
the wrappers to matching inputs.  The aggregate audit never reads restricted
microdata.

Random draws are reproducible from stored seeds and distributions; common-draw
paired comparisons additionally preserve score/influence or covariance
representations.  `NUMERICAL_CONSISTENCY_AUDIT.csv` identifies the source row
behind every load-bearing rounded manuscript quantity, and
`SUBSTANTIVE_REVISION_AUDIT.json` hashes the final aggregate evidence package.
