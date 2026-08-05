# DAX pipeline targets (W0 req 3). Run from dax/. Each stage script, once it
# exists, MUST end by emitting lineage: python ../ops/runner/lineage.py <out> <ins...>
# Stages that are not built yet fail loudly instead of pretending.

PY := python
STAGE_MISSING = @echo "stage '$@' not built yet — see docs/DAX_Execution_Plan_with_AI_Agents.md" && exit 2

.PHONY: data map panel index validate firststage_synth outcomes robustness paper guard memo_check memo_pdf synthetic_power

guard:  ## verify the pre-registration seal state
	$(PY) -c "import sys; sys.path.insert(0,'analysis'); import preregistration_guard; print('outcomes UNLOCKED')" \
	  || echo "outcomes SEALED (expected until GATE 1 tag)"

memo_check:  ## validate the W1 draft and print remaining Gate-1 blockers
	$(PY) memo/validate_event_registry.py
	$(PY) memo/validate_w1_readiness.py

memo_pdf: memo/design_memo_v1.pdf  ## render the Gate-1 review PDF

memo/design_memo_v1.pdf: memo/design_memo_v1.md memo/render_design_memo.py
	$(PY) memo/render_design_memo.py

synthetic_power:  ## smoke-test W1 power code; output is explicitly non-evidentiary
	$(PY) memo/power_calcs/make_synthetic_fixture.py
	$(PY) memo/power_calcs/simulate_power.py \
	  --cells memo/power_calcs/synthetic/preperiod_cells.csv \
	  --doses memo/power_calcs/synthetic/event_doses.csv \
	  --output memo/power_calcs/synthetic/power_results.json \
	  --reps 200 --seed 20260806 --synthetic

data:            ; $(STAGE_MISSING)   # W2: O*NET/OEWS/IPUMS-CPS pulls -> data_raw/ (+checksums), data_built/
map:             ; $(STAGE_MISSING)   # W3: mapping A/B/C -> mapping/
panel:           ; $(STAGE_MISSING)   # W4: capability/cost panel -> capability_panel/
index:           ; $(STAGE_MISSING)   # W5: DAX index -> index/
validate:        ; $(STAGE_MISSING)   # W6: validation suite
firststage_synth:; $(STAGE_MISSING)   # allowed pre-gate: synthetic first stage only
outcomes:                             # sealed until v1.0-preregistered (GATE 1)
	@$(PY) -c "import sys; sys.path.insert(0,'analysis'); import preregistration_guard" \
	  && $(STAGE_MISSING)
robustness:                           # same seal as outcomes
	@$(PY) -c "import sys; sys.path.insert(0,'analysis'); import preregistration_guard" \
	  && $(STAGE_MISSING)
paper:           ; $(STAGE_MISSING)   # W9/W10
