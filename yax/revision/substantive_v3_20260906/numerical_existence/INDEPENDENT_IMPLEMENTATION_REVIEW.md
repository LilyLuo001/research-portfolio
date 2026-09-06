# Independent numerical implementation review

Review date: 2026-09-06 UTC.

Reviewed terminal objects:

- runner SHA-256:
  `26a1bec8cf9496fabec12c33b60361c95ed150ac217abbc6d3c2fed78866a1c3`;
- artifact-safety SHA-256:
  `91018c48dc37590fb831b808ea462796d9bdc85eefe1d0ec97e9b9ac007ebcc4`;
- test-file SHA-256:
  `e519fa0d46d5fd7b888158af3e68239fc1e23bb0875f352bcca46fb2da4b8da7`;
- analysis-spec ID:
  `yaxnumspec_v1_f5a1571b8ae9842d15a7334466cbbbf7d381a2f945b4c5517c3f25386f1977ec`;
- analysis-spec SHA-256:
  `86b1704dd774e89b395035dd8fdf5b0be6e18332c678d5943a44d4637e297f7a`.

Disposition: **PASS for implementation; fresh empirical SCC execution remains
UNRUN at the time of this review.**

The independent reviewer found no remaining P1 or P2 code defect. Fourteen
focused weak-direction, adjoint, large-sparse, profile, and dyadic tests passed;
the full code-scoped suite passed 66 tests and 17 subtests before the two
intentionally stale spec-binding checks were restamped. After the coordinated
restamp, the integrating agent ran all 68 tests and 17 subtests successfully.

The reviewer independently reproduced the previously missed nearly collinear
fixture. The zero candidate is now blocked with an attainable raw-NLL gain of
approximately `0.000749975` and a focal Newton correction of approximately
`0.24896564`. Native L-BFGS-B and trust-ncg fits both pass the full certificate
and recover the generating target within the declared coefficient tolerance.
The reviewer also confirmed that:

- target scaling and signs are correct in both primal and adjoint systems;
- the conservative maximum of primal and adjoint corrections is binding;
- the IEEE `gamma_k` sparse-dot floor does not relax the backward-error rule;
- a mocked omitted weak component fails its target-adjoint solve;
- an 8,000-column sparse system invokes neither dense conversion nor an
  approximate eigenvalue certificate;
- noncenter nuisance profile fits remain bound to the same stationarity logic;
- runtime and command attestations are acquired internally; and
- output leaves are derived from the scheduler job number.

This review used public/synthetic fixtures and local execution only. The
production program must still run under the authenticated SCC CPython
3.13.8/SciPy 1.16.2 environment before any empirical model is described as
executed or validated.
