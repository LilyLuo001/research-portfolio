# YAX R3 baseline and SCC inventory

Inventory time: 2026-09-05; reconciled 2026-09-06
Status: inventory and completed-run reconciliation; no protected artifact or private microdata modified
Local branch at audit: `task/yax-substantive-revision-r3-20260905`  
Local HEAD observed during audit: `33976a44ae42ac905cca0cc79b2cd76053f45999`

## Bottom line

The authenticated private inputs and the code needed to reproduce the historical,
March-repaired, and fully rebuilt baselines are present on SCC. Job `7467125`
(exit status 0) produced the first two historical checkpoints. The later
BASE-03 run, job `7468725` (exit status 0), implemented and independently
self-checked the corrected treatment construction:

| Construction | Months in static fit | Treatment/support construction | Q5-Q1 coefficient |
|---|---:|---|---:|
| historical production | 108 | historical 468-occupation support and classifications; five March Basic samples absent | -0.1310739764 |
| corrected outcomes, historical treatment | 113 | restored March outcomes but the same 468 occupations, quintile assignments, and normalization inherited from the historical fit | -0.1345539536 |
| fully rebuilt corrected pipeline (BASE-03) | 113 | corrected 71-month preperiod support, weights, cutoffs, ties, memberships, and normalization | **-0.1321094508** |

The earlier inventory statement that the third row was unimplemented is
superseded. The exact runner is
`rebuilt_baseline/run_rebuilt_corrected_baseline.py`; the scheduler wrapper is
`rebuilt_baseline/run_scc.sh`; and the durable outputs are under
`rebuilt_baseline/results/`. `rebuilt_baseline/results/SELF_CHECK.json` reports
`PASS_BASE_03_SELF_CHECK` with all 21 checks true. BASE-03 is explicitly
post-outcome exploratory and does not alter the confirmatory chronology.

## Storage finding

The requested path `<YAX_REQUESTED_STORAGE_ROOT>`
can hold tiny metadata files but is not viable for the revision computation.
At audit time:

- `pquota econdept` reported 30,100 GB used against a 30,000 GB
  `<YAX_PRIVATE_STORAGE_TIER>` quota;
- `df -h <YAX_PRIVATE_STORAGE_TIER>` reported zero available bytes;
- a real 64 MiB write followed by `fsync` failed with `Disk quota exceeded`;
- the named probe was removed immediately and its absence was verified.

This is a project-wide quota, so moving files from
`<YAX_PRIVATE_USER_ROOT>/...` to another directory on the same filesystem does
not create capacity. The tier that matches the owner's stated free-space figure
is `<YAX_SCC_STORAGE_TIER>`: `pquota econdept` reported 74.76 GB used against 200 GB
(about 125 GB free). The root execution process therefore placed new code,
logs, and results under
`<YAX_SCC_PROJECT_ROOT>`; the authenticated
private inputs remain read-only beneath `<YAX_PRIVATE_ROOT>`.

No old SCC checkout or private file was deleted to manufacture space.

## Authenticated private inputs

The paths below are operational locators and must not be published in the
replication package. Hashes, sizes, schemas, and nonrestricted manifests may be
reported; licensed microdata may not be redistributed.

| Object | SCC locator | Bytes | SHA-256 | Role |
|---|---|---:|---|---|
| wide CPS extract 9 | `<YAX_PRIVATE_ROOT>/ai_telework_2017_2026/cps_00009.csv.gz` | 267,021,345 | `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9` | January 2017-July 2026 wide file; original five March samples are ASEC, not March Basic |
| March Basic repair extract 11 | `<YAX_PRIVATE_ROOT>/yax_referee_march_repair/cps_00011.csv.gz` | 15,210,805 | `a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911` | `cps2017_03b` through `cps2021_03b` |
| sealed preperiod cells | `<YAX_PRIVATE_ROOT>/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv` | 6,447,466 | `4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800` | historical 490 by 66 preperiod panel; intentionally lacks the five repaired March Basic samples |
| longitudinal-weight patch 10 | `<YAX_PRIVATE_ROOT>/yax_phase2_weight_patch/cps_00010.csv.gz` | 179,455,840 | `841e13798c34f74a8cd8e0ac1d913742aad5f24fce2c6876793ecf1dd8bd55a8` | `LNKFW1MWT`; needed for flow work, not baseline stock reproduction |

The wide file has the baseline variables needed to rebuild cells, including
`YEAR`, `MONTH`, `SERIAL`, `CPSID`, `CPSIDP`, `CPSIDV`, `MISH`, `AGE`,
`EMPSTAT`, `OCC`, `OCC2010`, `OCC1990`, `IND1990`, `EDUC`, `WTFINL`, hours,
earnings, and telework fields. The repair file contains the variables needed by
the stock/crosswalk rebuild, including `SERIAL`, `CPSID`, `CPSIDP`, `CPSIDV`,
`MISH`, `AGE`, `EMPSTAT`, `OCC`, `OCC2010`, `IND1990`, `EDUC`, and `WTFINL`.

The combined raw rebuild receipt records 9,843,021 input records, 114 observed
survey months, and all five repaired March Basic samples. October 2025 is
absent because no CPS was collected during the federal shutdown; it is not
interpolated. December 2022 is present in the raw data, retained for dynamic
work, and excluded from the static model by design.

## Extract provenance that is actually verified

The input manifest distinguishes API event timestamps from filesystem
timestamps and leaves unavailable fields blank. In particular:

- Extract 9 was submitted at `2026-08-25T13:38:31.382050+00:00` and its
  completed files were recorded at `2026-08-25T13:42:35.789292+00:00`.
  Its submitted specification, data, DDI, and basic-codebook hashes are all
  preserved in existing versioned receipts.
- Extract 10 was recorded as complete when checked at
  `2026-08-31T10:14:52.354521+00:00`. Its request specification, returned
  extract definition, data, DDI, and basic-codebook hashes are preserved.
  The receipt does not establish a separate API completion timestamp, so none
  is reported.
- The authenticated March repair is IPUMS extract 11. A read-only metadata
  check verified its request, API response, data, DDI, and basic-codebook
  hashes. Neither the response nor the existing public receipt records an API
  submission/completion timestamp; file modification times are not relabeled
  as API event times.

`INPUT_PROVENANCE_RECEIPT.md` identifies the evidence source for each field.
No restricted file, download URL, account email, or credential is copied into
the public record.

## Public/versioned inputs and immutable references

| Object | Repository path | SHA-256 |
|---|---|---|
| CPS exposure lookup | `yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv` | `c6eb70623ea598bfc41f2352391add7a342a8809a4e57b02f2af0e75dd0223f8` |
| computerization measures | `yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv` | `352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd` |
| Rule-B values | `yax/measurement/RULE_B_VALUES_CENSUS2018.csv` | `8092f0eef57aaf4271a7dc563a4820e2f9a6d13519bcac9372837bc7a2c991e6` |
| Census 2010-to-2018 bridge | `yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv` | `0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc` |
| first outcome-access receipt (restricted provenance; excluded from sanitized package) | supplied through `YAX_FIRST_ACCESS_RECEIPT` | `d13b1e1635433e8ef8f90c35667dedb24f503f9029d694557351e77b6904d9b3` |
| design-freeze peeled commit | tag `v1.1-design-freeze` | `22fbf7924809b7a535e31ae0ab68f5b113ce8078` |
| confirmatory-results peeled commit | tag `v1.1-confirmatory-results` | `b16109482c3bf5ca176f6f08976e120b04769945` |

## Existing execution chain

### Historical production baseline

`yax/analysis/run_frozen_v11.py` authenticates the frozen refs and all private
and public hashes, reads the 66-month sealed preperiod file, drops the same five
March months while rebuilding the wide-file panel, excludes December 2022 from
the static fit, and estimates the grouped-binomial conditional equivalent of
the two-age PPML. Its `prepare_model` constructs employment-weighted exposure
quintiles using total young-plus-older stock over all supplied static months.
Thus the historical production classification uses the 108-month static
window, including postperiod employment. This temporal weighting rule was
classified as a freeze ambiguity in the V4.1 audit, not as a uniquely
prespecified choice.

### Corrected outcomes with historical treatment

`yax/revision/referee_20260905/run_referee_cells.py::build_exact_age_cells`
combines extracts 9 and 11 and applies the frozen Census 2010-to-2018 routing
proportions to pre-2020 records. The current corrected runner
`yax/revision/referee_round2_20260905/composition_influence/run_composition_influence.py`
then restores the five March outcomes but deliberately carries forward:

- the historical 468-occupation support;
- the historical quintile assignments;
- the historical full-static weights used to normalize Webb; and
- the historical major-group map and post definition.

This is an informative calendar-only comparison, but it is not a fully rebuilt
corrected treatment construction.

### Fully recomputed corrected treatment (implemented BASE-03)

BASE-03 now performs the ten operations listed in the original inventory. It
authenticates the inputs, builds the corrected 71-month preperiod before
reading the historical sealed support, recomputes the universe and all
treatment objects, fits the corrected 113-month calendar, and emits named
support, membership, normalization, paired-draw, and failure artifacts. Its
prefit gate records that no postperiod stock entered treatment construction.

The rebuilt and historical native supports both contain 468 occupations, so
the realized comparison is on identical support. Nine occupations change
quintile. The recomputed-minus-historical-treatment coefficient movement on
the corrected calendar is `0.0024445028`, with the paired interval stored in
`rebuilt_baseline/results/PAIRED_COMPARISONS.csv`. This is a pipeline
sensitivity result, not an
economic-equivalence finding.

The implementation is guarded by unit tests and a module self-check that fail
if the rebuilt contract reads the sealed historical support before the prefit
gate, uses postperiod stocks, loses route mass, changes the declared calendar,
or labels unequal-support comparisons as paired.

## Environment and queue

- Working Python used by the successful job:
  `<YAX_PYTHON_BIN>` (Python 3.13.8).
- The runner requires NumPy and pandas; the observed environment reported
  NumPy 2.5.1 and pandas 3.0.3. The `pip` launcher in that environment has a
  stale interpreter shebang, so an environment receipt should use
  `python -m pip` or direct import/version capture rather than that launcher.
- The historical scripts set
  `PYTHONPATH=<YAX_LEGACY_PYTHONPATH>`. That path
  exposes an incomplete `scipy` namespace and should not be treated as evidence
  of a valid SciPy installation. The baseline code does not require SciPy.
- Successful R3 baseline job `7467125`: 60-second queue delay, 75-second wall
  time, 76.704 CPU seconds, maximum virtual memory 2.067 GB, four requested
  slots, exit status 0.
- Successful BASE-03 job `7468725`: 64-second wall time, maximum virtual memory
  1.899 GB, exit status 0. The exact output authentication is in
  `rebuilt_baseline/results/EXECUTION_RECEIPT.json` and `SELF_CHECK.json`.
- A separate unrelated job (`7467005`) was running during the inventory and was
  not touched.

## Immediate execution order

1. Treat `rebuilt_baseline/results/` as the completed BASE-03 reference and
   verify it with the module self-check.
2. For a fresh restricted-data reproduction, use a new empty output root and
   execute `yax/revision/substantive_r3_20260905/run_restricted_full_rerun.sh`;
   it runs BASE-03 first and passes its
   named treatment artifacts to downstream modules.
3. Compare fresh output hashes and declared numerical targets with the
   versioned receipts. Timestamps and git-state fields are expected to differ;
   numerical or support differences require investigation.
4. Run the separate aggregate-only audit after restricted computations are
   complete. It regenerates permitted exhibits and validates committed
   artifacts; it does not rerun the licensed-data pipeline.

Exact commands and the boundary between restricted and aggregate-only work are
recorded in `REPRODUCTION_COMMANDS.md`.
