#!/bin/bash -l

set -euo pipefail

mkdir -p yax/power/scenarios_v2 yax/power/logs_v2

beta_c=-0.05129329438755058

j1=$(qsub -terse -N y1e_b_oi -o yax/power/logs_v2 \
  yax/power/run_joint_power_scc.sh dv_rating_beta onet_computers_importance \
  "$beta_c" yax/power/scenarios_v2/beta_onet_primary.json)
j2=$(qsub -terse -N y1e_b_wb -o yax/power/logs_v2 \
  yax/power/run_joint_power_scc.sh dv_rating_beta webb_pct_software \
  "$beta_c" yax/power/scenarios_v2/beta_webb_primary.json)
j3=$(qsub -terse -N y1e_a_oi -o yax/power/logs_v2 \
  yax/power/run_joint_power_scc.sh dv_rating_alpha onet_computers_importance \
  "$beta_c" yax/power/scenarios_v2/alpha_onet_primary.json)
j4=$(qsub -terse -N y1e_a_wb -o yax/power/logs_v2 \
  yax/power/run_joint_power_scc.sh dv_rating_alpha webb_pct_software \
  "$beta_c" yax/power/scenarios_v2/alpha_webb_primary.json)
j5=$(qsub -terse -N y1e_pair -o yax/power/logs_v2 \
  yax/power/run_paired_equivalence_scc.sh \
  yax/power/PAIRED_EQUIVALENCE_PRECISION_v1.json)

qsub -terse -N y1e_agg -o yax/power/logs_v2 \
  -hold_jid "$j1,$j2,$j3,$j4" yax/power/aggregate_joint_power_scc.sh

printf 'joint_jobs=%s,%s,%s,%s\npaired_job=%s\n' "$j1" "$j2" "$j3" "$j4" "$j5"
