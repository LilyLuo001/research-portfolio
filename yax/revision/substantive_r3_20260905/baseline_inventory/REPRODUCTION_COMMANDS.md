# Baseline reproduction commands

These commands contain no credentials and do not copy restricted data. Run
them only from a complete Git checkout containing the protected tags.

## Capacity gate

Before syncing or submitting to `/projectnb/econdept`, run:

```bash
pquota econdept
df -h /projectnb/econdept
```

At the inventory time this gate failed. Do not submit the commands below with a
`/projectnb/econdept/...` output root until the project quota is below its
limit. The verified R3 execution root is currently on `/project/econdept`.

## Historical production runner

```bash
COMPUTE_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums
PYTHON_BIN=/usr3/graduate/qluo/portfolio/.venv/bin/python

cd "$REPO_ROOT"
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages

"$PYTHON_BIN" yax/analysis/run_frozen_v11.py \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --preperiod-cells "$PRIVATE_ROOT/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --lookup yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv \
  --computerization yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv \
  --rule-b-values yax/measurement/RULE_B_VALUES_CENSUS2018.csv \
  --bridge yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv \
  --first-access-receipt yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json \
  --output-dir "$COMPUTE_ROOT/results/historical_production"
```

This runner is the full original analysis suite, not just the baseline model.
For a quick R3 checkpoint that jointly reproduces the historical and
calendar-corrected baselines, use the next command.

## Historical plus corrected-outcome checkpoint

```bash
COMPUTE_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums
PYTHON_BIN=/usr3/graduate/qluo/portfolio/.venv/bin/python

cd "$REPO_ROOT"
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages

"$PYTHON_BIN" \
  yax/revision/referee_round2_20260905/composition_influence/run_composition_influence.py \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --preperiod-cells "$PRIVATE_ROOT/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --output-dir "$COMPUTE_ROOT/results/baseline_reproduction"
```

The successful scheduler wrapper is
`yax/revision/substantive_r3_20260905/scc_reproduce_baseline.sh`. Its completed
SGE job was `7467125`; the log is
`/project/econdept/qluo/yax-substantive-revision-20260905/logs/baseline_reproduction.log`.

## Fully rebuilt corrected treatment

There is intentionally no executable command yet. No existing program
recomputes the eligible universe and every treatment object on the corrected
71-month preperiod. After the registered runner is implemented, its interface
should be:

```bash
"$PYTHON_BIN" \
  yax/revision/substantive_r3_20260905/run_rebuilt_corrected_baseline.py \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --historical-preperiod-cells "$PRIVATE_ROOT/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --lookup yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv \
  --computerization yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv \
  --rule-b-values yax/measurement/RULE_B_VALUES_CENSUS2018.csv \
  --bridge yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv \
  --first-access-receipt yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json \
  --output-dir "$COMPUTE_ROOT/results/rebuilt_corrected_baseline"
```

The runner must abort unless it emits all of the following before fitting:

- a 71-month corrected-preperiod calendar receipt;
- source-route conservation checks;
- the recomputed eligible-universe and exclusion-reason file;
- preperiod weight, scale, cutoff, tie, and membership files;
- hashes for historical and recomputed supports; and
- an explicit flag that no postperiod stock entered treatment construction.
