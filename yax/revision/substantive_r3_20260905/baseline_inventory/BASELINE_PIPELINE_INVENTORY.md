# YAX R3 baseline and SCC inventory

Inventory time: 2026-09-05 (Asia/Shanghai)  
Status: read-only audit completed; no protected artifact or private microdata modified  
Local branch at audit: `task/yax-substantive-revision-r3-20260905`  
Local HEAD observed during audit: `33976a44ae42ac905cca0cc79b2cd76053f45999`

## Bottom line

The authenticated private inputs and the code needed to reproduce the historical
and March-repaired baselines are present on SCC. The R3 baseline job has already
reproduced both checkpoints from raw microdata in 75 seconds (SGE job `7467125`,
exit status 0):

| Construction | Months in static fit | Treatment/support construction | Q5-Q1 coefficient |
|---|---:|---|---:|
| historical production | 108 | historical 468-occupation support and classifications; five March Basic samples absent | -0.1310739764 |
| corrected outcomes, historical treatment | 113 | restored March outcomes but the same 468 occupations, quintile assignments, and normalization inherited from the historical fit | -0.1345539536 |
| fully rebuilt corrected pipeline | 113 | corrected preperiod support, weights, cutoffs, ties, memberships, and normalization | **not yet implemented or estimated** |

The third row is not produced by any existing runner. It must be implemented as
a new, explicitly post-outcome R3 construction rather than inferred from the
first two rows.

## Storage finding

The requested path `/projectnb/econdept/yax-substantive-revision-20260905-qluo`
can hold tiny metadata files but is not viable for the revision computation.
At audit time:

- `pquota econdept` reported 30,100 GB used against a 30,000 GB
  `/projectnb/econdept` quota;
- `df -h /projectnb/econdept` reported zero available bytes;
- a real 64 MiB write followed by `fsync` failed with `Disk quota exceeded`;
- the named probe was removed immediately and its absence was verified.

This is a project-wide quota, so moving files from
`/projectnb/econdept/qluo/...` to another directory on the same filesystem does
not create capacity. The tier that matches the owner's stated free-space figure
is `/project/econdept`: `pquota econdept` reported 74.76 GB used against 200 GB
(about 125 GB free). The root execution process therefore placed new code,
logs, and results under
`/project/econdept/qluo/yax-substantive-revision-20260905`; the authenticated
private inputs remain read-only at their existing `/projectnb` paths.

No old SCC checkout or private file was deleted to manufacture space.

## Authenticated private inputs

The paths below are operational locators and must not be published in the
replication package. Hashes, sizes, schemas, and nonrestricted manifests may be
reported; licensed microdata may not be redistributed.

| Object | SCC locator | Bytes | SHA-256 | Role |
|---|---|---:|---|---|
| wide CPS extract 9 | `/projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/cps_00009.csv.gz` | 267,021,345 | `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9` | January 2017-July 2026 wide file; original five March samples are ASEC, not March Basic |
| March Basic repair extract 11 | `/projectnb/econdept/qluo/dax-private/ipums/yax_referee_march_repair/cps_00011.csv.gz` | 15,210,805 | `a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911` | `cps2017_03b` through `cps2021_03b` |
| sealed preperiod cells | `/projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv` | 6,447,466 | `4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800` | historical 490 by 66 preperiod panel; intentionally lacks the five repaired March Basic samples |
| longitudinal-weight patch 10 | `/projectnb/econdept/qluo/dax-private/ipums/yax_phase2_weight_patch/cps_00010.csv.gz` | 179,455,840 | `841e13798c34f74a8cd8e0ac1d913742aad5f24fce2c6876793ecf1dd8bd55a8` | `LNKFW1MWT`; needed for flow work, not baseline stock reproduction |

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

## Public/versioned inputs and immutable references

| Object | Repository path | SHA-256 |
|---|---|---|
| CPS exposure lookup | `yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv` | `c6eb70623ea598bfc41f2352391add7a342a8809a4e57b02f2af0e75dd0223f8` |
| computerization measures | `yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv` | `352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd` |
| Rule-B values | `yax/measurement/RULE_B_VALUES_CENSUS2018.csv` | `8092f0eef57aaf4271a7dc563a4820e2f9a6d13519bcac9372837bc7a2c991e6` |
| Census 2010-to-2018 bridge | `yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv` | `0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc` |
| first outcome-access receipt | `yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json` | `d13b1e1635433e8ef8f90c35667dedb24f503f9029d694557351e77b6904d9b3` |
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

### Fully recomputed corrected treatment

No current script performs this complete operation. The new runner must:

1. authenticate the same inputs and protected refs;
2. rebuild exact-age cells from extracts 9 and 11;
3. define the corrected preperiod as every observed month from 2017-01 through
   2022-11, now 71 months;
4. recreate the eligible occupation universe from the rebuilt corrected
   preperiod rather than starting from the historical fail-closed 490-code
   cell file;
5. apply the declared Rule-A exposure and finite Webb requirements;
6. apply the finite-fixed-effect support rule (positive preperiod stock for
   both ages 22-25 and 26-65), preserving valid one-sided zero cells within
   months;
7. compute preperiod employment weights, exposure normalization, weighted
   cutoffs, tie-preserving quintile memberships, and Webb normalization on this
   corrected support;
8. fit the 113-month static model, excluding December 2022 and leaving October
   2025 absent;
9. emit explicit support/membership/exclusion files and a decomposition that
   distinguishes calendar, fixed-support reclassification, and support
   expansion; and
10. compare rows using common multiplier draws on common support where a paired
    estimand exists. A coefficient difference that also changes support is not
    to be described as a pure paired treatment difference.

The reusable pieces are `build_exact_age_cells`, `panel_for_ages`,
`weighted_quintiles`, `fit_q_model`, and the V4.1 classification helpers. A new
test must fail if the fully rebuilt row accidentally reads the historical
sealed cell support or uses postperiod stocks to form its preperiod treatment
weights.

## Environment and queue

- Working Python used by the successful job:
  `/usr3/graduate/qluo/portfolio/.venv/bin/python` (Python 3.13.8).
- The runner requires NumPy and pandas; the observed environment reported
  NumPy 2.5.1 and pandas 3.0.3. The `pip` launcher in that environment has a
  stale interpreter shebang, so an environment receipt should use
  `python -m pip` or direct import/version capture rather than that launcher.
- The historical scripts set
  `PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages`. That path
  exposes an incomplete `scipy` namespace and should not be treated as evidence
  of a valid SciPy installation. The baseline code does not require SciPy.
- Successful R3 baseline job `7467125`: 60-second queue delay, 75-second wall
  time, 76.704 CPU seconds, maximum virtual memory 2.067 GB, four requested
  slots, exit status 0.
- A separate unrelated job (`7467005`) was running during the inventory and was
  not touched.

## Immediate execution order

1. Preserve the successful historical/corrected receipt and copy its output
   hashes into the R3 results ledger.
2. Implement the fully rebuilt corrected-treatment runner and unit tests.
3. Run a dry authentication/support build before estimation and inspect the
   occupation additions/deletions and quintile changes.
4. Submit the full model only after that support receipt is frozen within the
   post-outcome R3 registry.
5. Do not begin downstream within-family or characteristic comparisons until
   all modules read the same chosen baseline contract and named support files.

Exact commands are recorded in `REPRODUCTION_COMMANDS.md`.
