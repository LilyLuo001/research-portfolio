# P1 repository file audit — 2026-09-05 V3 checkpoint

## Checkpoint disposition

The canonical V3 SCC checkpoint is:

`/project/econdept/qluo/P1_Refraction_WRDS/GATE_RUN_20260905_CONTRACT_V3`

The V3 work stopped after the targeted data-contract pilot checkpoint. No full
Gate 0/1 rerun was submitted, Gate 2 remains disabled, and no Gate or
regression result is reportable. All earlier Gate 0/1 outputs remain
`INVALIDATED_PENDING_DATA_CONTRACT` and are excluded from the V3 checkpoint.

## Correct authority hierarchy

1. **Sole executable normative contract:**
   `p1/etf_weight_shape_gates/data_contract.json`,
   `p1/etf_weight_shape_gates/gate01_config.json`, and
   `p1/etf_weight_shape_gates/golden_sample_spec.json`. These three
   machine-readable files jointly control every execution decision.
2. **Private evidence and authorization:** the SCC-only `PILOT_PASS.json` and
   its hash-bound evidence bundle establish whether the frozen machine
   contract passed. They are receipts, not specification sources.
3. **Explanatory documentation:** the research plan, status files, audit
   memos, READMEs, and documentation-evidence files explain the design and
   evidence. They cannot amend or override the machine contract.
4. **Historical project material:** earlier strategy, status, universe,
   exposure, SEC, and lineage artifacts are retained only as dated context
   unless the current machine contract explicitly incorporates them.

If any human-readable statement conflicts with the machine bundle, execution
must stop, the prose must be corrected, and the machine bundle remains
controlling. A proposed change to the machine rules is a specification
amendment requiring a new frozen golden sample and targeted pilot.

## File dispositions

| File class | Disposition |
|---|---|
| V3 `data_contract.json`, `gate01_config.json`, and `golden_sample_spec.json` | Active and jointly normative for execution |
| `run_gate0_gate1.py` below its preflight | Quarantined pre-contract implementation; retained for code-hash visibility and unable to execute while `full_run_enabled=false` |
| Gate 2 launcher | Retained only as a fail-closed stub; Gate 2 is disabled |
| Earlier Gate 0/1 SCC outputs | Invalid research artifacts; excluded from the canonical V3 pilot directory |
| Public pilot receipt and input provenance | Git-safe, non-row-level checkpoint metadata; never sufficient to authorize a full run |
| Private pilot receipt and detailed evidence | SCC-only under the canonical V3 `pilot` directory; required as a complete, matching bundle for authorization |
| Raw WRDS/CRSP inputs | Read-only SCC data; never copied into Git |
| Human research plans, status notes, audit memos, and READMEs | Explanatory only; not executable authority |
| Earlier strategic, universe, exposure, SEC, and lineage artifacts | Retained as dated history; not promoted into the V3 executable contract |

Generated caches and local rendering scratch files are excluded from the Git
deliverable. User-owned operating-system metadata remains unmodified and
untracked.

## Public/private delivery boundary

The public Git delivery may contain the three normative machine files, code,
tests, explanatory documentation, `pilot/PILOT_PUBLIC_RECEIPT.json`, and
`pilot/pilot_input_files.json`. It must not contain licensed rows, licensed row
values, detailed case results, trace observations, detailed invariant output,
or the private authorization receipt.

The canonical private evidence remains at:

`/project/econdept/qluo/P1_Refraction_WRDS/GATE_RUN_20260905_CONTRACT_V3/pilot`

## Consistency result

These audited checkpoint documents now state the same boundary: the V3
machine bundle is the sole executable normative contract; human documents are
explanatory; private pilot evidence remains on SCC; earlier Gate results are
invalid; no full Gate 0/1 rerun was launched; Gate 2 is disabled; and every
scientific specification or code amendment requires a new golden sample and
targeted pilot before any future full run.
