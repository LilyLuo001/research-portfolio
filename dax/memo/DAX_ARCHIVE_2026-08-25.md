# DAX — archive record, 2026-08-25

**Status: PAUSED / ARCHIVED — feasibility-blocked. Not scientifically refuted.**

This record closes the DAX full-task-displacement index as an active work
stream. It does not retract the design, the estimand, or any finding. The
index failed an operational feasibility condition that the project itself
wrote down and signed in advance. That is the whole of the claim being made
here.

## The binding condition and how it failed

`dax/memo/design_memo_v1.md` §0 records the signed 2026-07-10 feasibility
decision. Condition 1:

> W4 capture of accessible historical model snapshots must finish before the
> applicable 2026-10-23 and 2026-12-11 shutdown dates.

Mechanical status as of the last verified recheck, `dax/data_raw/
w4_free_availability_recheck_20260821.json` (2026-08-21):

| | |
|---|---:|
| target vintages | 22 |
| **mechanically verified as captured** | **0** |
| unprobed, missing key | 14 |
| blocked, no approved snapshot rule | 5 |
| stand-in provider unconfigured | 2 |
| excluded (binding) | 1 |

`status: UNPROBED_NO_APPROVED_CREDENTIAL_AVAILABLE_TO_PROCESS`.
`account_probe_performed: false` — the free `GET /v1/models` metadata probe
never ran, because `scc_inspection_status: APPROVED_PRIVATE_ENV_FILE_ABSENT`.

At archive date, 59 days remained to the first shutdown, with zero of 22
captured and the blocker being an absent credential environment rather than a
technical failure. The distinguishing property is that this blocker is **not
recoverable by effort**: the model vintages are withdrawn on fixed external
dates, so the measurement window closes whether or not the work is done.

Downstream state is consistent and fail-closed, as designed:

- `dax/data_raw/w5_dose_panel_blocker_receipt.json`:
  `BLOCKED_UNQUALIFIED_W3_AND_MISSING_W4_MEASUREMENTS`
- `dax/data_raw/person_level_power_receipt.json`: `PENDING_W5_DOSE_PANEL`,
  `power_run_executed: false`
- Event registry: 21 rows, 20 date-verified, **4 analysis-eligible**

## What this record does NOT say

- It does not say the estimand `pi_eff = 1 - delta*(1-pi)` is wrong.
- It does not say the missing-mass κ-family, the boundary-sensitivity result
  (B = 0.0000 / 0.1086 / 0.2572), or the task-weight variant sensitivity are
  invalid. They stand as computed.
- It does not say the price/capability decomposition is uninteresting. It says
  this project cannot measure it before the inputs disappear.

Anyone resuming this work should read the design memo as a live document whose
one unmet precondition is snapshot capture.

## Reusable assets, retained

These are verified, carry lineage, and remain usable by future work:

| asset | state |
|---|---|
| `dax/data_built/price_histories.csv` | 20 price-verified rows |
| `dax/memo/event_registry_v1.csv` | 21 rows, 20 date-verified |
| `dax/data_built/oews_wages.parquet` | OEWS 2021, 831 occupations |
| `dax/data_built/onet_task_weights.parquet` | + variant sensitivity measured |
| `dax/w2/crosswalk/build_occ2010_crosswalk.py` | 96.39% mapped component mass |
| `dax/w2/exposure_gate/` | full measurement audit, receipts and figures |
| CPS analysis panel (SCC) | 242,474 person-months, 2021-11 → 2026-07 |
| CPS pre-event panel (SCC) | 71,322 rows |

## What replaces it

`dax/paper/CHAPTER_SCOPE_v1.md` — a self-contained third dissertation chapter
built on the CPS panels and the public exposure measures, requiring none of
the blocked inputs above. The chapter needs no vendor API credentials, no
model snapshot capture, and no NDA-restricted data.

## Consequences to action on

1. **W4 capture is stood down.** No further credential provisioning is needed
   for this chapter. The exposed-credential rotation is still owed, but it is
   no longer on any critical path.
2. **The five-seat governance apparatus is oversized** for a solo chapter.
   `ops/accounts.yaml` partitions five seats with lease claims and dual-vendor
   requirements, and 10+ memos in `dax/memo/` await a counter-signature from
   the same person who would be signing them. Recommendation, for the owner to
   action in `ops/` (outside this seat's owned paths): retain lineage receipts
   and the no-specification-search rule, retire the rest.
3. **`analysis/outcomes/` stays sealed.** The chapter defines its own
   pre-registration in `CHAPTER_SCOPE_v1.md` §6; the `v1.0-preregistered` tag
   convention carries over unchanged.
