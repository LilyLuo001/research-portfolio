#!/usr/bin/env bash
# Sequential full R3 rebuild for an allocated restricted-data compute node.
# The script never copies licensed row-level data into the repository.

set -euo pipefail

REPO="${YAX_REPO_ROOT:?Set YAX_REPO_ROOT to a clean checkout}"
PRIVATE="${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the licensed IPUMS root}"
OUT="${YAX_RERUN_ROOT:?Set YAX_RERUN_ROOT to a new output directory}"
PYTHON="${YAX_PYTHON_BIN:-python3}"
RSCRIPT="${YAX_RSCRIPT_BIN:-Rscript}"
FIRST_ACCESS="${YAX_FIRST_ACCESS_RECEIPT:?Set YAX_FIRST_ACCESS_RECEIPT to the authenticated receipt}"
R_LIBRARY="${YAX_HONESTDID_R_LIB:?Set YAX_HONESTDID_R_LIB to the pinned R library}"

if [[ -e "$OUT" ]]; then
  echo "Refusing to overwrite an existing rerun root: $OUT" >&2
  exit 2
fi
test -f "$REPO/yax/revision/substantive_r3_20260905/rebuilt_baseline/run_rebuilt_corrected_baseline.py"
test -f "$FIRST_ACCESS"
[[ "$(git -C "$REPO" rev-parse 'v1.1-design-freeze^{}')" == \
  "22fbf7924809b7a535e31ae0ab68f5b113ce8078" ]]
[[ "$(git -C "$REPO" rev-parse 'v1.1-confirmatory-results^{}')" == \
  "b16109482c3bf5ca176f6f08976e120b04769945" ]]

WIDE="$PRIVATE/ai_telework_2017_2026/cps_00009.csv.gz"
REPAIR="$PRIVATE/yax_referee_march_repair/cps_00011.csv.gz"
PRECELLS="$PRIVATE/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv"
WEIGHT_PATCH="$PRIVATE/yax_phase2_weight_patch/cps_00010.csv.gz"
WIDE_REQUEST="$PRIVATE/ai_telework_2017_2026/ipums_ai_telework_extract_superseding_submitted.json"
REPAIR_REQUEST="$PRIVATE/yax_referee_march_repair/request.json"
WIDE_DDI="$PRIVATE/ai_telework_2017_2026/cps_00009.xml"
REPAIR_DDI="$PRIVATE/yax_referee_march_repair/cps_00011.xml"

for input in "$WIDE" "$REPAIR" "$PRECELLS" "$WEIGHT_PATCH" \
  "$WIDE_REQUEST" "$REPAIR_REQUEST" "$WIDE_DDI" "$REPAIR_DDI"; do
  test -f "$input" || { echo "Missing required input: $input" >&2; exit 2; }
done

check_hash() {
  local path="$1" expected="$2" observed
  observed="$(sha256sum "$path" | awk '{print $1}')"
  if [[ "$observed" != "$expected" ]]; then
    echo "Input hash mismatch for $(basename "$path")" >&2
    exit 3
  fi
}

check_hash "$WIDE" 3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9
check_hash "$REPAIR" a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911
check_hash "$PRECELLS" 4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800
check_hash "$WEIGHT_PATCH" 841e13798c34f74a8cd8e0ac1d913742aad5f24fce2c6876793ecf1dd8bd55a8
check_hash "$WIDE_REQUEST" bd798b9dfe11d00153856be3e05a7c52865a149dcc7405a5cbfd812eb3ca6c3a
check_hash "$REPAIR_REQUEST" 2ceeabc416f875c07bbfe9ae327310b9f4b5c3bc474473f459f26a503e7a7d26
check_hash "$WIDE_DDI" 5933bc48ed736a00fa70547ef503f571c6f1f9c03aef7d24ce511af3550fb319
check_hash "$REPAIR_DDI" e29c6c30a397357b927692af371b3fa77176f3d020f513343237d651bf3d3b03
check_hash "$FIRST_ACCESS" d13b1e1635433e8ef8f90c35667dedb24f503f9029d694557351e77b6904d9b3

mkdir -p "$OUT"
cd "$REPO"
if [[ -n "${YAX_LEGACY_PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$YAX_LEGACY_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi
export OMP_NUM_THREADS="${NSLOTS:-1}"
export OPENBLAS_NUM_THREADS="${NSLOTS:-1}"
export MKL_NUM_THREADS="${NSLOTS:-1}"

LOOKUP="$REPO/yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv"
COMPUTER="$REPO/yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv"
RULE_B="$REPO/yax/measurement/RULE_B_VALUES_CENSUS2018.csv"
BRIDGE="$REPO/yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv"
CHARACTERISTICS="$REPO/yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv"
R3="$REPO/yax/revision/substantive_r3_20260905"

BASE="$OUT/01_rebuilt_baseline"
DATA="$OUT/02_data_audit"
FAMILY="$OUT/03_within_family"
CHAR="$OUT/04_characteristics"
INFERENCE="$OUT/05_inference"
HET="$OUT/06_heterogeneity"
BCC="$OUT/07_bcc_bridge"
DYN="$OUT/08_dynamics"
MARCH="$OUT/09_march_audit"
SURVEY="$OUT/10_survey_sim"
FLOWS="$OUT/11_flows"
FLOW_HH="$OUT/12_flow_household"
ARCH="$OUT/13_architecture"
mkdir -p "$BASE" "$DATA" "$FAMILY" "$CHAR" "$INFERENCE" "$HET" \
  "$BCC" "$DYN" "$MARCH" "$SURVEY" "$FLOWS" "$FLOW_HH" "$ARCH"

echo "[01/13] BASE-03 fully rebuilt baseline"
"$PYTHON" "$R3/rebuilt_baseline/run_rebuilt_corrected_baseline.py" \
  --repo-root "$REPO" --microdata "$WIDE" --repair-microdata "$REPAIR" \
  --historical-preperiod-cells "$PRECELLS" --lookup "$LOOKUP" \
  --computerization "$COMPUTER" --rule-b-values "$RULE_B" --bridge "$BRIDGE" \
  --first-access-receipt "$FIRST_ACCESS" --output-dir "$BASE"
"$PYTHON" "$R3/rebuilt_baseline/selfcheck.py" --output-dir "$BASE"

echo "[02/13] data/calendar/route audit"
"$PYTHON" "$R3/data_audit/run_data_audit.py" --repo-root "$REPO" \
  --microdata "$WIDE" --repair-microdata "$REPAIR" --bridge "$BRIDGE" \
  --contracts "$BASE/NATIVE_TREATMENT_CONTRACTS.csv" \
  --universe "$BASE/REBUILT_ELIGIBLE_UNIVERSE.csv" \
  --route-receipt "$BASE/ROUTE_CONSERVATION_RECEIPT.json" --output-dir "$DATA"
"$PYTHON" "$R3/data_audit/selfcheck.py" --output-dir "$DATA"

echo "[03/13] rebuilt-treatment within-family analyses"
"$PYTHON" "$R3/dynamics/rebuilt_family_harmonization/run_rebuilt_family.py" \
  --microdata "$WIDE" --repair-microdata "$REPAIR" --preperiod-cells "$PRECELLS" \
  --lookup "$LOOKUP" --computerization "$COMPUTER" --rule-b-values "$RULE_B" \
  --bridge "$BRIDGE" --first-access-receipt "$FIRST_ACCESS" \
  --characteristics "$CHARACTERISTICS" \
  --rebuilt-membership "$BASE/REBUILT_TREATMENT_MEMBERSHIP.csv" \
  --output-dir "$FAMILY" --draws 9999
"$PYTHON" "$R3/dynamics/rebuilt_family_harmonization/selfcheck.py" --output-dir "$FAMILY"

echo "[04/13] occupational-characteristic conditioning"
"$PYTHON" "$R3/characteristics/run_characteristic_conditioning.py" \
  --microdata "$WIDE" --repair-microdata "$REPAIR" --preperiod-cells "$PRECELLS" \
  --lookup "$LOOKUP" --computerization "$COMPUTER" --rule-b-values "$RULE_B" \
  --bridge "$BRIDGE" --first-access-receipt "$FIRST_ACCESS" \
  --characteristics "$CHARACTERISTICS" \
  --rebuilt-membership "$BASE/REBUILT_TREATMENT_MEMBERSHIP.csv" \
  --rebuilt-normalization "$BASE/REBUILT_NORMALIZATION_AND_CUTS.json" \
  --output-dir "$CHAR"
"$PYTHON" "$R3/characteristics/selfcheck.py" --results-dir "$CHAR"

echo "[05/13] rebuilt-treatment inference audit"
"$PYTHON" "$R3/inference_rebuilt/run_inference_rebuilt.py" \
  --microdata "$WIDE" --repair-microdata "$REPAIR" \
  --membership "$BASE/REBUILT_TREATMENT_MEMBERSHIP.csv" --bridge "$BRIDGE" \
  --computerization "$COMPUTER" --output-dir "$INFERENCE"
"$PYTHON" "$R3/inference_rebuilt/selfcheck.py" --results-dir "$INFERENCE"

echo "[06/13] industry, education, and exact-age heterogeneity"
"$PYTHON" "$R3/heterogeneity/run_heterogeneity.py" --repo-root "$REPO" \
  --microdata "$WIDE" --repair-microdata "$REPAIR" --bridge "$BRIDGE" \
  --membership "$BASE/REBUILT_TREATMENT_MEMBERSHIP.csv" \
  --specification "$R3/heterogeneity/ANALYSIS_SPEC_BEFORE_RESULTS.md" --output-dir "$HET"
"$PYTHON" "$R3/heterogeneity/selfcheck.py" --results-dir "$HET"

echo "[07/13] public BCC grouping bridge"
"$PYTHON" "$R3/bcc_bridge/run_bcc_bridge.py" --microdata "$WIDE" \
  --repair-microdata "$REPAIR" --preperiod-cells "$PRECELLS" \
  --lookup "$LOOKUP" --computerization "$COMPUTER" --rule-b-values "$RULE_B" \
  --bridge "$BRIDGE" --first-access-receipt "$FIRST_ACCESS" \
  --characteristics "$CHARACTERISTICS" --output-dir "$BCC"
"$PYTHON" "$R3/bcc_bridge/selfcheck.py" --output-dir "$BCC"

echo "[08/13] dynamics, paired structures, and official HonestDiD"
"$PYTHON" "$R3/dynamics/run_dynamics.py" --microdata "$WIDE" \
  --repair-microdata "$REPAIR" --preperiod-cells "$PRECELLS" \
  --lookup "$LOOKUP" --computerization "$COMPUTER" --rule-b-values "$RULE_B" \
  --bridge "$BRIDGE" --first-access-receipt "$FIRST_ACCESS" \
  --rebuilt-membership "$BASE/REBUILT_TREATMENT_MEMBERSHIP.csv" --output-dir "$DYN"
"$PYTHON" "$R3/dynamics/run_structure_pair.py" --microdata "$WIDE" \
  --repair-microdata "$REPAIR" --preperiod-cells "$PRECELLS" \
  --lookup "$LOOKUP" --computerization "$COMPUTER" --rule-b-values "$RULE_B" \
  --bridge "$BRIDGE" --first-access-receipt "$FIRST_ACCESS" \
  --rebuilt-membership "$BASE/REBUILT_TREATMENT_MEMBERSHIP.csv" --output-dir "$DYN"
export R_LIBS_USER="$R_LIBRARY"
"$RSCRIPT" "$R3/dynamics/run_honestdid.R" "$DYN"
"$PYTHON" "$R3/dynamics/selfcheck.py" --output-dir "$DYN" \
  --require-honestdid --require-structure-pair

echo "[09/13] March-source functional-replacement audit"
"$PYTHON" "$R3/survey_sim/run_march_replacement_audit.py" --wide "$WIDE" \
  --repair "$REPAIR" --wide-request "$WIDE_REQUEST" --repair-request "$REPAIR_REQUEST" \
  --wide-ddi "$WIDE_DDI" --repair-ddi "$REPAIR_DDI" --bridge "$BRIDGE" \
  --cell-builder "$REPO/yax/revision/referee_20260905/run_referee_cells.py" \
  --output-dir "$MARCH"
"$PYTHON" "$R3/survey_sim/selfcheck_march_replacement.py" --results "$MARCH"

echo "[10/13] household sensitivity and finite-sample stress test"
"$PYTHON" "$R3/survey_sim/run_inf03_inf05.py" --microdata "$WIDE" \
  --repair-microdata "$REPAIR" --bridge "$BRIDGE" --computerization "$COMPUTER" \
  --treatment-contract "$BASE/NATIVE_TREATMENT_CONTRACTS.csv" \
  --march-audit-receipt "$MARCH/MARCH_REPLACEMENT_AUDIT_RECEIPT.json" \
  --household-draws 199 --simulation-draws 199 --output-dir "$SURVEY"
"$PYTHON" "$R3/survey_sim/selfcheck_inf03_inf05.py" --results "$SURVEY" \
  --household-draws 199 --simulation-draws 199

echo "[11/13] linked flows and worker outcomes"
"$PYTHON" "$R3/flows/run_flows_outcomes.py" --microdata "$WIDE" \
  --repair-microdata "$REPAIR" --weight-patch "$WEIGHT_PATCH" \
  --membership "$BASE/REBUILT_TREATMENT_MEMBERSHIP.csv" --bridge "$BRIDGE" \
  --analysis-spec "$R3/flows/ANALYSIS_SPEC_BEFORE_RESULTS.md" --output-dir "$FLOWS"
"$PYTHON" "$R3/flows/selfcheck.py" --results "$FLOWS"

echo "[12/13] link-cluster sensitivity"
"$PYTHON" "$R3/flows/run_link_cluster_sensitivity.py" --microdata "$WIDE" \
  --repair-microdata "$REPAIR" --weight-patch "$WEIGHT_PATCH" \
  --membership "$BASE/REBUILT_TREATMENT_MEMBERSHIP.csv" --bridge "$BRIDGE" \
  --fixed-results "$FLOWS/FLOW_AND_WORKER_OUTCOME_RESULTS.csv" \
  --fixed-influence "$FLOWS/TARGET_OCCUPATION_INFLUENCE.csv" \
  --amendment "$R3/flows/HOUSEHOLD_CLUSTER_AMENDMENT_BEFORE_RESULTS.md" \
  --output-dir "$FLOW_HH"
"$PYTHON" "$R3/flows/selfcheck_link_cluster_sensitivity.py" --results "$FLOW_HH"

echo "[13/13] exposure-architecture audit"
"$PYTHON" "$R3/architecture/run_architecture.py" --repo-root "$REPO" \
  --microdata "$WIDE" --repair-microdata "$REPAIR" --lookup "$LOOKUP" \
  --computerization "$COMPUTER" --rule-b-values "$RULE_B" --bridge "$BRIDGE" \
  --characteristics "$CHARACTERISTICS" \
  --baseline-membership "$BASE/REBUILT_TREATMENT_MEMBERSHIP.csv" \
  --baseline-normalization "$BASE/REBUILT_NORMALIZATION_AND_CUTS.json" \
  --baseline-decomposition "$BASE/BASELINE_DECOMPOSITION.csv" --output-dir "$ARCH"
"$PYTHON" "$R3/architecture/selfcheck.py" --results-dir "$ARCH"

echo "[aggregate audit] committed distributable artifacts and paper build"
YAX_REPO_ROOT="$REPO" bash "$REPO/paper/scripts/run_substantive_revision_audit.sh"

printf 'PASS_RESTRICTED_R3_RERUN\n' > "$OUT/RESTRICTED_RERUN_COMPLETE.txt"
echo "Restricted-data R3 rebuild completed: $OUT"
