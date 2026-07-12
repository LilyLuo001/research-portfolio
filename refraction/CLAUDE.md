# refraction/CLAUDE.md — seat scope

This directory is owned by exactly one Claude seat (seat C, shared with p1/ —
see ../ops/accounts.yaml). Do not edit files outside refraction/ (P1 frozen
inputs are READ-ONLY: events_merged.csv, conv_exposure.parquet,
holdings_weights.parquet, ibes_sue.parquet).

Paste the C0-R context pack (docs/Refraction_执行手册_v1_0.md §0.3) at the top
of every task prompt. Task prompts (verbatim) live in the 执行手册 — copy the
block for your task id (R0–R14) into your brief.

Two project iron rules, MACHINE-ENFORCED (do not rely on discipline):
1. Lookahead ban — β/lever/weights use only data strictly before the wave's
   effective date. Checked by pipeline/assert_panel.py::a4_no_lookahead and
   guards/prereg_guard.py::assert_no_lookahead. A4 failure = output void.
2. Prereg-before-outcomes — any estimation touching post-period outcome
   variables (R6+) must call guards/prereg_guard.py::assert_prereg_ok() at
   startup; it refuses to run until frozen_config.yaml carries the OSF
   timestamp committed at REFR-GATE-OSF, and refuses while w_shrink is null.

Every tunable lives in frozen_config.yaml — no magic numbers in code
(assert A6 does a static scan). Deliverable = outputs + manifest.md
(inputs+hashes, environment, limitations, UNKNOWN list) or it is not done.
