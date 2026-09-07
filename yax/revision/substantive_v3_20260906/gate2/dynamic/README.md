# Gate 2 dynamic reconciliation core

This pre-result package implements the V3 Y01--Y05 reconciliation machinery
without writing to authoritative run, ledger, state, or manuscript locations.

Run focused tests with:

```sh
pytest -q yax/revision/substantive_v3_20260906/gate2/dynamic/tests
```

The CLI validates every signed input hash and prints a nonauthoritative
preflight report by default. Supplying `--output` is permitted only for a new,
nonexisting preflight path; the runner refuses overwrite and emits a
content-bound `result_id`. An authoritative analysis requires a future frozen
amendment binding the missing covariance, influence, common-draw, design,
fitted-probability, and full-parameter objects.

The focused implementation was tested with Python 3.10.5 and NumPy 1.22.4;
the declared minimums are Python 3.10 and NumPy 1.22. No production runtime pin
is available, and the spec requires one to be bound before authoritative use.
