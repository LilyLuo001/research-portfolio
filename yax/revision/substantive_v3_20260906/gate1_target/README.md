# V3 Gate-1 exact-target audit

This directory implements requirement T01 without reading raw CPS microdata or
estimating a coefficient. The runner consumes the authenticated aggregate-cell
leaf made by `gate1_cells`, reconciles physical rows with continuous weighted
stocks, and verifies the canonical age, calendar, schema, weight-once, and
mean-ratio interpretation.

The authenticated upstream receipt must identify the wide and March-repair
sources separately, reconcile total and by-source physical and eligible-record
counts, and certify that the production router read only `YEAR`, `MONTH`,
`AGE`, `EMPSTAT`, `OCC`, and `WTFINL`. The audit treats routed descendants as
rows, not people, and never constructs a respondent-equivalent count.

Before reading the aggregate CSV, the runner authenticates the producer's full
canonical and authenticated source maps, authorization subchecks, code maps,
SCC runtime payload, committed-Git receipt, repair-month and route identities,
and the colocated assignment-fingerprint artifact. Missing receipt fields fail;
they cannot pass because a corresponding expected field is also absent.
Git commit and tree strings are resolved against the object database and every
declared producer blob; the consuming checkout must equal that commit and be
clean.

Placeholder SCC command:

```sh
<YAX_PYTHON_BIN> -I yax/revision/substantive_v3_20260906/gate1_target/run_exact_target_audit.py \
  --repo-root <YAX_REPO_ROOT> \
  --cells <YAX_GATE1_CELLS_LEAF>/aggregate_cells.csv \
  --cells-receipt <YAX_GATE1_CELLS_LEAF>/EXECUTION_RECEIPT.json \
  --output-parent <YAX_V3_RUN_ROOT>
```

The runner derives the unique output leaf from the numeric SGE `JOB_ID`. The
leaf must not exist and must be outside the repository and disjoint from the
input leaf. Publication first attempts kernel no-replace. When the mounted
filesystem explicitly rejects that flag, the runner uses an ordinary
same-parent atomic rename under an exclusive sibling reservation, after an
immediate reservation-identity and target-absence recheck. This fallback does
not claim kernel no-replace and retains a bounded noncooperating same-user
check-to-rename window. The successful leaf contains:

- `EXACT_TARGET_AUDIT.json`;
- `ROW_ACCOUNTING.csv`;
- `EXACT_TARGET_AUDIT_REPORT.md`; and
- `EXECUTION_RECEIPT.json`.

Existing files, directories, and dangling symlinks are all refused as output
destinations.

Run the public/synthetic regression tests with:

```sh
<YAX_PYTHON_BIN> -m pytest -q \
  yax/revision/substantive_v3_20260906/gate1_target/tests
```

No successful empirical execution is claimed merely because this code or its
synthetic tests pass. A fresh authenticated aggregate receipt and a retained
outside-repository T01 receipt are required.
