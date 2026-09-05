# Reproduction commands

The project has two distinct reproduction surfaces. The aggregate-only command
validates committed, distributable results and regenerates exhibits. The
restricted-data command rebuilds those results from licensed IPUMS CPS files.
The first is not described as a substitute for the second.

## Required environment for restricted-data work

Use a clean checkout containing the protected tags and a new, empty output
directory. None of these variables should contain credentials.

```bash
export YAX_REPO_ROOT=/path/to/clean/checkout
export YAX_PRIVATE_ROOT=/path/to/licensed/ipums/root
export YAX_RERUN_ROOT=/path/to/new/empty/output-directory
export YAX_PYTHON_BIN=/path/to/python
export YAX_FIRST_ACCESS_RECEIPT=/path/to/authenticated/first-access-receipt.json
export YAX_HONESTDID_R_LIB=/path/to/pinned/R/library
```

The licensed root must contain the files represented by
`INPUT_MANIFEST.csv`, including extracts 9, 10, and 11, their request/DDI
metadata, and the historical sealed preperiod cells. The first-access receipt
is a restricted provenance object because its historical version contains
operational locators; its required SHA-256 is in the manifest.

Before computation, verify storage and the checkout without modifying either:

```bash
test -d "$YAX_REPO_ROOT/.git" || git -C "$YAX_REPO_ROOT" rev-parse --git-dir
test ! -e "$YAX_RERUN_ROOT"
pquota econdept
df -h "$(dirname "$YAX_RERUN_ROOT")"
git -C "$YAX_REPO_ROOT" rev-parse 'v1.1-design-freeze^{}'
git -C "$YAX_REPO_ROOT" rev-parse 'v1.1-confirmatory-results^{}'
```

## Completed BASE-03 runner

The fully rebuilt corrected-treatment row is implemented. The successful SCC
program and wrapper are:

- `rebuilt_baseline/run_rebuilt_corrected_baseline.py`;
- `rebuilt_baseline/run_scc.sh`;
- `rebuilt_baseline/selfcheck.py`.

The direct equivalent of the successful BASE-03 run is:

```bash
cd "$YAX_REPO_ROOT"
out="$YAX_RERUN_ROOT/rebuilt_baseline"
mkdir -p "$out"

"$YAX_PYTHON_BIN" \
  yax/revision/substantive_r3_20260905/rebuilt_baseline/run_rebuilt_corrected_baseline.py \
  --repo-root "$YAX_REPO_ROOT" \
  --microdata "$YAX_PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$YAX_PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --historical-preperiod-cells "$YAX_PRIVATE_ROOT/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --lookup yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv \
  --computerization yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv \
  --rule-b-values yax/measurement/RULE_B_VALUES_CENSUS2018.csv \
  --bridge yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv \
  --first-access-receipt "$YAX_FIRST_ACCESS_RECEIPT" \
  --output-dir "$out"

"$YAX_PYTHON_BIN" \
  yax/revision/substantive_r3_20260905/rebuilt_baseline/selfcheck.py \
  --output-dir "$out"
```

The expected self-check status is `PASS_BASE_03_SELF_CHECK`. The expected
fully rebuilt point estimate is `-0.13210945079219036`; it is an authentication
checkpoint, not a target to which code may be tuned. The runner must also emit
the 468-occupation support, 71-month construction calendar, 113-month static
calendar, no-postperiod-stock assertion, route-conservation receipt, treatment
memberships, paired draws, and failure file.

## Ordered one-command restricted-data rebuild

After setting the environment above, the complete ordered R3 rerun is:

```bash
bash "$YAX_REPO_ROOT/yax/revision/substantive_r3_20260905/run_restricted_full_rerun.sh"
```

The orchestrator fails if the output root already exists, authenticates inputs,
runs BASE-03 first, passes its named contracts to dependent modules, runs each
module self-check, executes the official pinned HonestDiD implementation, and
finishes with the aggregate audit. Its ordered stages are recorded in
`INPUT_PROVENANCE_RECEIPT.md`. It runs sequentially on an allocated compute
node; scheduler users may instead submit the corresponding versioned wrappers
with dependency holds in the same order.

No module is permitted to fall back silently to a committed result when a
fresh upstream output is required. Output receipts may differ in timestamps,
working paths, and git-state metadata. Scientific quantities, supports, seeds,
and authenticated input hashes must reconcile with the versioned evidence or
the rerun is a failure requiring investigation.

## Historical checkpoints

The original frozen suite remains reproducible separately:

```bash
cd "$YAX_REPO_ROOT"
"$YAX_PYTHON_BIN" yax/analysis/run_frozen_v11.py \
  --microdata "$YAX_PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --preperiod-cells "$YAX_PRIVATE_ROOT/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --lookup yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv \
  --computerization yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv \
  --rule-b-values yax/measurement/RULE_B_VALUES_CENSUS2018.csv \
  --bridge yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv \
  --first-access-receipt "$YAX_FIRST_ACCESS_RECEIPT" \
  --output-dir "$YAX_RERUN_ROOT/historical_production"
```

For only the historical and calendar-repaired checkpoint, the completed wrapper
is `yax/revision/substantive_r3_20260905/scc_reproduce_baseline.sh`. That
checkpoint does not rebuild the BASE-03
treatment contract and must not be described as doing so.

## Aggregate-only audit

From a clean checkout with the permitted derived results already present:

```bash
cd "$YAX_REPO_ROOT"
bash paper/scripts/run_substantive_revision_audit.sh
```

This command regenerates exhibit source files, checks the committed rebuilt-
family and numerical artifacts, runs the test suite, and builds PDFs when TeX
is available. It reads no restricted microdata and does not independently
re-estimate BASE-03, family, characteristic, flow, or dynamic models. A pass is
evidence that the committed aggregate package is internally consistent, not
evidence of a fresh raw-data reproduction.

## Sanitized public-package boundary

`PUBLIC_REPLICATION_MANIFEST.csv` is the positive allowlist for a staged public
package. A full Git checkout is not, by itself, asserted to be that sanitized
package. Before release, stage only the listed paths and apply the scan contract
in `INPUT_PROVENANCE_RECEIPT.md`. The scan rejects private absolute roots,
credentials, unapproved file types, and raw identifier-bearing tables. It does
not replace human disclosure review or the data provider's redistribution
terms.
