# V3 Gate-1 cell builder

`run_gate1_cells.py` creates the authenticated `yax-numerical-cells-v1`
input required by `../numerical_existence`. Its committed tests are synthetic
or public-artifact checks only; they do not open CPS microdata.

Production invocation on SCC:

```sh
mkdir -p '<YAX_V3_RUN_ROOT>'
<YAX_PYTHON_BIN> \
  -I \
  yax/revision/substantive_v3_20260906/gate1_cells/run_gate1_cells.py \
  --repo-root '<YAX_REPO_ROOT>' \
  --microdata '<YAX_PRIVATE_ROOT>/ai_telework_2017_2026/cps_00009.csv.gz' \
  --repair-microdata '<YAX_PRIVATE_ROOT>/yax_referee_march_repair/cps_00011.csv.gz' \
  --output-parent '<YAX_V3_RUN_ROOT>'
```

This displayed command corresponds exactly to the placeholder-only immutable
command template in `CELL_BUILD_SPEC.json`; resolved paths are never written to
the receipt. The runner derives the unique output leaf from the numeric SGE
`JOB_ID`; callers cannot choose or restamp it. Production also requires the declared CPython/compiler/libc and
package payload, a Git HEAD descending from the declared ancestor, and a clean
worktree whose builder, cell spec, numerical spec, and environment lock equal
their committed blobs. Kernel release is recorded, not patch-equality locked.

The production router reads exactly the canonical six CPS fields
`YEAR,MONTH,AGE,EMPSTAT,OCC,WTFINL` and filters employed ages 22--65. It does
not import the historical general-purpose R3 helper. The historical helper and
its transitive files are hash-locked reference artifacts used by a synthetic
parity test only; its extra `OCC2010` and `IND1990` outputs are outside this
target object.

The output leaf must not exist. A successful leaf contains
`aggregate_cells.csv`, `ASSIGNMENT_FINGERPRINT.json`, and
`EXECUTION_RECEIPT.json`. The receipt deliberately contains identifiers,
hashes, counts, and checks rather than private paths or credentials.

Publication first attempts the kernel no-replace primitive. When GPFS
explicitly rejects that flag, the runner uses an ordinary same-parent atomic
rename under an exclusive sibling reservation for the SGE-job-derived unique
leaf, after immediately rechecking the reservation identity and target
absence. The fallback does not claim kernel no-replace; a noncooperating
same-user check-to-rename race is bounded but not eliminated.

The downstream numerical audit should consume the aggregate and receipt
directly. A production PASS means only that cell construction satisfied this
pre-result contract; it is not a numerical-existence or empirical-result PASS.
