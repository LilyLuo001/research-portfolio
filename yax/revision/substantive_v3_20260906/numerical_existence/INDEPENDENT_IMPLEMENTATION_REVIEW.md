# Independent numerical implementation review

Review date: 2026-09-06

Runner SHA-256: `fe2a927f9cca2d6f1935178a4d6489244af83e18f7eaa877f0dc0038ce8cd876`

Analysis-spec SHA-256: `9b27c3b987a9f70bca3004dfe36141bb91e57890e9a481ecf23ee40271cceb82`

Test-file SHA-256: `e74f243fefe20f7c73da50d73319146cbe4b936676dd4a3e348959178805d195`

Disposition: **PASS for implementation; empirical production audit remains UNRUN**

The independent review reran all 43 tests plus 12 adversarial subtests and
found no remaining P0 or P1 defect. In particular, it verified:

- the near-dependent `1e-8` example has no separation, while the `1e-9`
  candidate fails independent primal certification rather than receiving a
  false PASS;
- signed `+1` and `-1` target LPs distinguish feasible and infeasible target
  directions, and a zero-gain unit-target direction is correctly classified as
  target-moving;
- all eleven registered models reproduce the byte-locked submitted regressor
  matrices, semantic labels, and both fixed-effect partitions;
- both dynamic models construct all 38 reported Q5 targets, all 23 pretrend
  coordinates, and 42 post months with weights summing to one;
- both post-2020 models and all four conditioned/unconditioned seasonal models
  pass parity;
- the family-post reference follows the all-analysis-period stock rule;
- receipt, producer/cell spec, source, runtime, Git, route, physical-record,
  and weight-once checks fail closed under mutation; and
- unsafe output paths and every blocked status produce nonzero failure rather
  than a report-only success.

The independent run used local macOS Python 3.10/SciPy 1.9, so it validates
the code and adversarial logic only. The production program correctly refuses
that runtime. The committed code must next be rerun under the declared SCC
CPython 3.13.8/SciPy 1.16.2 environment before any empirical model can be
described as executed or validated. No protected aggregate or microdata was
read during this review.
