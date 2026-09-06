# Canonical contract amendment 01: enumerate the historical cell input

Date: 2026-09-06 UTC

Timing: before the first V3 protected-data or empirical Gate-1 run

Classification: provenance-only correction; no scientific design change

The original immutable contract,
`specs/canonical_baseline_reproduction.json`, named the historical preperiod
cell file in its exact execution command. Its content hash was enforced by the
contract-hashed R3 runner and authenticated through the separately listed
first-outcome-access receipt. It was nevertheless omitted as its own row in
`data.sources`.

The current contract,
`specs/canonical_baseline_reproduction_v2.json`, adds exactly one source row:

- source ID: `historical_preperiod_cells`;
- SHA-256: `4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800`;
- role: the January 2017--November 2022 occupation-month aggregate used by the
  two historical-treatment diagnostic checkpoints.

The amendment changes no data values, eligibility rule, mapping, exposure,
support, age group, calendar, objective, nuisance space, solver, target,
uncertainty procedure, command, code, or environment. The old stamped file is
preserved rather than overwritten. The content-derived identifier therefore
changes from
`yaxspec_v1_a9f56e292c5964f6cf77447d845466859b04612e0be3e77492add3c00ed04e4b`
to
`yaxspec_v1_83bb387f9fc28e2655db5101c7697989510475027d1dd5a9c361c797ed3925c3`.
All unrun V3 modules are bound to the corrected identifier before execution.
