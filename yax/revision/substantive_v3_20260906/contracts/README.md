# YAX V3 canonical contract layer

`scripts/spec_contract.py` is the executable authority for contract validation
and identifier construction.  A `spec_id` is the SHA-256 digest of canonical
JSON after removing only the top-level `spec_id`.  It therefore changes with
the data, eligibility, occupation mapping, exposure construction, calendar,
objective, nuisance space, target, uncertainty procedure, code, environment,
dependencies, command, or output destination.

Files under `templates/` are inputs to the stamping command and are not valid
analysis contracts.  Stamped files under `specs/` are immutable: the command
refuses to overwrite one.  A substantive alternative must receive a new file
and a new `spec_id`.

The current contract reconstructs the R3 corrected-treatment pooled baseline. It
records inherited clipping and normalization behavior rather than endorsing
it. Gate N01--N03 must determine whether the target has a finite optimum and
whether the same objective is reproduced by a second valid solver.

The original stamped contract is retained as
`specs/canonical_baseline_reproduction.json`. Before the first V3 empirical
run, an input-inventory audit found that the historical preperiod cells named
in its command were authenticated transitively but absent as their own
`data.sources` row. The corrected, current contract is
`specs/canonical_baseline_reproduction_v2.json`; `CONTRACT_AMENDMENT_01.md`
records the provenance-only amendment. No estimand, sample, solver, or
uncertainty choice changed.

Example commands:

```sh
python3 scripts/spec_contract.py stamp \
  contracts/templates/canonical_baseline_reproduction.unstamped.json \
  contracts/specs/canonical_baseline_reproduction_v2.json
python3 scripts/spec_contract.py validate \
  contracts/specs/canonical_baseline_reproduction_v2.json
```
