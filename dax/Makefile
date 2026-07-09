# DAX pipeline targets (W0 req 3). Run from dax/. Each stage script, once it
# exists, MUST end by emitting lineage: python ../ops/runner/lineage.py <out> <ins...>
# Stages that are not built yet fail loudly instead of pretending.

PY := python
STAGE_MISSING = @echo "stage '$@' not built yet — see docs/DAX_Execution_Plan_with_AI_Agents.md" && exit 2

.PHONY: data map panel index validate firststage_synth outcomes robustness paper guard

guard:  ## verify the pre-registration seal state
	$(PY) -c "import sys; sys.path.insert(0,'analysis'); import preregistration_guard; print('outcomes UNLOCKED')" \
	  || echo "outcomes SEALED (expected until GATE 1 tag)"

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
