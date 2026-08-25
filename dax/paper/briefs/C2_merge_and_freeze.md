# C2 — Merge exposure to CPS, freeze the design, compute power

*Prepend `C0_CONTEXT_PACK.md`. Requires C1 complete. One task, one session.*

## Preconditions — verify, do not assume

1. `dax/data_built/exposure_soc2018.parquet` exists and passed C1's 90% gate.
2. The **wide CPS extract** (2017-01 → present, ages 16–75, spec at
   `dax/memo/power_calcs/ipums_ai_telework_extract_v1.json`) has been submitted
   and downloaded. If only the 2021-11 panel exists, say so and stop: the
   pre-trend and remote-work dimensions cannot be built on it, and building
   them on the short panel would produce a chapter that fails its own §6.

## Build

`dax/w2/build_analysis_panel.py` → `cps_analysis_panel.parquet`
**on the SCC private path only.** This file contains person-level records.
Call `assert_not_committable` before writing it. Commit the *receipt*, never
the panel.

Merge chain: CPS occupation code → (existing `build_occ2010_crosswalk.py`
route) → SOC 2018 → `exposure_soc2018.parquet`.

Report merge coverage honestly at every hop: unmatched CPS person-months and
their weighted share. An unmatched person-month is a row with null exposure,
never a dropped row.

Variables per `CHAPTER_SCOPE_v1.md` §5, which is binding:

- ages 16–75; young = 20–29 primary, 16–24 and 22–27 as pre-specified alternates
- employment from `EMPSTAT` ∈ {10, 12}
- `WTFINL` for employment; **`EARNWT` with `MISH` ∈ {4, 8} for any earnings
  outcome** — do not use `WTFINL` for `EARNWEEK` or `HOURWAGE`
- exposure standardised to mean 0, sd 1 over the **employment-weighted**
  occupation distribution
- telework = occupation-level Dingel–Neiman share only. **Do not construct a
  person-level telework treatment from `TELWRKHR`/`TELWRKPAY`**: they begin
  2022-10 and are asked only of people employed and at work, so they are
  post-treatment and conditioned on the outcome.

## Power — the open question

`dax/data_raw/person_level_power_receipt.json` reads `power_run_executed:
false`. Power has never been computed on the real structure, because it was
gated on the DAX dose panel that was never built. That gate is gone.

Compute the **minimum detectable effect** for the §6 primary specification, on
the actual panel, clustering on occupation. Report MDE for:

- each of the three young-age definitions
- the primary exposure measure, repaired and unrepaired
- with and without the telework control

This is a design input, not a result, and it is computed on the pre-period
only. **Do not estimate the treatment effect in this task.**

## Freeze

Emit `dax/paper/DESIGN_FREEZE_v1.md`: the estimating equation as it will be
run, the table shells with empty cells, and the sha256 of the analysis panel.
Commit it. **Everything after this commit is an estimate, and the first run of
each table is the reported run.**

## Definition of done

- Panel built on the private path, receipt + lineage committed, panel not.
- Merge coverage table by hop, with weighted unmatched shares.
- MDE table.
- `DESIGN_FREEZE_v1.md` committed, with empty table shells.
- `pytest -q` green.

## Do not

- Do not estimate any treatment effect.
- Do not drop unmatched rows.
- Do not commit the panel.
