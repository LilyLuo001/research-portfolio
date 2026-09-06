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

The first contract reconstructs the R3 corrected-treatment pooled baseline. It
records inherited clipping and normalization behavior rather than endorsing
it. Gate N01--N03 must determine whether the target has a finite optimum and
whether the same objective is reproduced by a second valid solver.

Example commands:

```sh
python3 scripts/spec_contract.py stamp \
  contracts/templates/canonical_baseline_reproduction.unstamped.json \
  contracts/specs/canonical_baseline_reproduction.json
python3 scripts/spec_contract.py validate \
  contracts/specs/canonical_baseline_reproduction.json
```
