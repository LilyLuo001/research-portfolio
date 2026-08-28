# refraction/CLAUDE.md — seat scope

This directory is owned by exactly one Claude seat (seat C, shared with p1/ —
see ../ops/accounts.yaml). Do not edit files outside refraction/.

P1 inputs are READ-ONLY, and most do not exist yet. Checked 2026-08-19:

| Input | State |
|---|---|
| `p1/events_merged.csv` | EXISTS — 131 events |
| `p1/conv_exposure_free.parquet` | EXISTS — free-EDGAR path, 6,377 cells. **`permno` is blank (`''`) on every row** pending the CRSP crosswalk |
| `p1/conv_exposure.parquet` | NOT PRODUCED — the WRDS-path artifact; blocked on P1-T2-wrds |
| `p1/holdings_weights.parquet` | NOT PRODUCED — needed by R2 for basket weights |
| `p1/ibes_sue.parquet` | NOT PRODUCED — blocked on WRDS |

Two consequences R2 must respect, both machine-enforced in
`pipeline/assert_panel.py`:

1. **ConvExp is keyed `[permno, wave_id]`** (`ops/contracts/conv_exposure.yaml`),
   not `wave`. CLAUDE.md rule 3 forbids renaming a frozen column, so refraction
   adapts on read via `_read_p1_convexp()`. Never rename it upstream.
2. **A blank `permno` is refused, not merged.** Blank is the empty string, so a
   `notna()` liveness check passes on an unusable key —
   `assert_p1_join_key_usable()` raises instead. R2 cannot run against the free
   path until the crosswalk lands.

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
