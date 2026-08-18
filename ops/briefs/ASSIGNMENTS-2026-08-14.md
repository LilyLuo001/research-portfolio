# Seat assignments — 2026-08-14 (owner-issued after the W1 design audit)

Context: the 2026-08-14 audit (`dax/memo/design_audit_2026-08-14.md`) found
that the W1 stacking protocol yields **2 estimable events** from its own 4
eligible rows, and **1** if the registry is completed as planned. These
assignments were chosen to be zero-waste under any resolution of that rule.

**Update 2026-08-18:** D1 is now resolved — see the standing rule at the foot
of this file. The assignments below are unchanged and remain correct.

## Collision carve-out — read before claiming DAX-W2-data

`DAX-W2-data` is being executed as **two non-overlapping halves** so two
workers can run it concurrently without touching the same files. The
`dax_built_backbone` contract requires four files; ownership is split:

| File | Owner | Status |
|---|---|---|
| `dax/data_built/price_histories.csv` | **W2-infra worker** | claimed 2026-08-14 |
| `dax/data_built/cps_onet_crosswalk.csv` | **W2-infra worker** | **REASSIGNED 2026-08-18** (was seat A) |
| `dax/data_built/onet_timeshares.parquet` | **seat A** | unclaimed |
| `dax/data_built/oews_wages.parquet` | **seat A** | unclaimed |
| `dax/data_built/cps_extract.parquet` | **seat A** | unclaimed |

### Reassignment notice — 2026-08-18, PI-directed

The **employment-weighted CPS-O*NET-SOC crosswalk** (formerly item 4 of the
seat-A brief) is reassigned from seat A to the W2-infra worker, by PI
instruction. Seat A must **not** build it. Everything under
`dax/w2/crosswalk/` and `ops/contracts/cps_onet_crosswalk.yaml` belongs to the
W2-infra lane, alongside `dax/w2/prices/`.

Rationale: the crosswalk and the price panel share the same problem shape —
external public sources that must be fetched with locators and checksums,
parsed deterministically, and emitted under a frozen contract with honest
coverage reporting. Keeping them in one lane keeps that machinery in one place.
Seat A keeps the three data extracts, which are genuinely different work.

Seat A: do **not** write `price_histories.csv`, do not edit anything under
`dax/w2/prices/`, and do not modify `ops/contracts/price_histories.yaml`.
The price worker will not touch the other three files or the crosswalk code.
`DAX-W2-data` is marked complete only when **both** halves pass the backbone
contract.

## Seat A (DAX-prime, `dax/`) → `DAX-W2-data`, non-price half

Brief: `ops/briefs/opus/OPUS-DAX-W2-data-nonprice.md`.

Deliverables, all pre-period only (the outcome seal is closed and stays closed):
1. O*NET 2021 vintage task/IWA time-shares → `onet_timeshares.parquet`.
2. OEWS 2021 occupation wages → `oews_wages.parquet` (2019 baseline as the
   registered robustness vintage, not a replacement).
3. IPUMS-CPS pre-event extract → `cps_extract.parquet`. Extract 6 is already
   pulled and checksum-recorded in
   `dax/memo/power_calcs/ipums_preperiod_extract_receipt.json` — **reuse it,
   do not re-pull**, and verify the SHA256s match before building.
4. ~~Employment-weighted many-to-many CPS↔O*NET-SOC crosswalk.~~
   **REASSIGNED 2026-08-18 to the W2-infra worker. Do not build this.**
5. Frozen Felten / Eloundou / Webb static-score ensemble for the Decision-8
   convergent-validity check.

Every file gets a lineage JSON. Every external download gets a locator
(agency, table ID, vintage, retrieval date, checksum). No figure from memory.

Why this is safe to do now: none of these five items depends on the window
rule, the event count, or the price panel. They are required under every
candidate resolution.

## Seat B (E2-prime, `e2/`) → `E2-T4a-design`

READY, unblocked (`E2-T1-facts` complete). No brief exists yet — write one
into `ops/briefs/` as the first act of the session, per the working protocol,
then execute. Touch only `e2/`.

## Seat C (P1-prime, `p1/`, `refraction/`) → L1 dispatch + gate prep

No L2 P1 block is READY. Do the overnight-batch work instead:
- `make l1` (dry run) → `make l1-live` for the ready batches: `P1-T1-events`,
  `P1-T13-ant`, `P1-T0-monitor`, `REFR-R0-collide`, `REFR-R1a-verify`.
- Reap the two stale leases first: `DAX-W1-memo` (expired 2026-08-06) and
  `P1-T1-events` (expired 2026-07-16). `make reap`.
- Close `DAX-W0.5-legwork`: `ops/decisions.md` §3 records it superseded by the
  owner-run inline legwork, but the runner still advertises it READY and will
  re-spend on it. Close it explicitly in an operations-state commit.

## Owner / PI items (not delegable)

1. **Merge the stranded W1 work.** `7a6a401` and `5d26fe2` sit on
   `task/DAX-W1-memo` above the PR #35 merge point and never reached `main`.
   They contain the cross-vendor red team, its remediation, the memo revision,
   the updated PDF, and the IPUMS pull. Until merged, the PDF on `main` is the
   pre-red-team draft — do not review that one.
2. **Rotate the GitHub PAT.** Flagged in `progress_audit_2026-08-06.md` defect
   3, and a token was subsequently pasted into a chat session.
3. **Counter-sign D1.** Decided under delegation 2026-08-18
   (`dax/memo/PI_DECISION_D1_2026-08-18.md`); it does not bind until signed.
4. **Resolve the power bar (D3)** — still open, still `[PI-DECISION]`, and it
   blocks the power rebuild. D4 (entrant exclusion) and F2 (registry statuses)
   also remain open.

## Standing rule — UPDATED 2026-08-18

D1 is resolved (`dax/memo/PI_DECISION_D1_2026-08-18.md`): the primary
specification is now a continuous cumulative-dose design with **no event
selection**. Consequences for the queue:

- `DAX-W3-mapA` is **no longer blocked by the window rule** — but it is still
  blocked by its declared dependency on `DAX-W2-data`, which is not complete.
  CORRECTION 2026-08-18: an earlier revision of this file called it "unblocked"
  without that qualification, which was wrong. `make plan` does not list it as
  READY and will not until W2-data lands.
- Note also that `DAX-W3-mapA` is the **GDPval mapping protocol and
  adjudication**, per its queue entry. The employment-weighted CPS-O*NET
  crosswalk is a `DAX-W2-data` deliverable (item 4 of the seat-A brief) and is
  covered by the collision carve-out above. Whoever front-loads W3 must not
  write the crosswalk.
- W2 price work is now **strictly value-adding**. Under the old rule more
  verified events shrank the design; under the continuous primary every
  verified event adds dose variation. Finish the panel.
- `DAX-W1-power` must be **rebuilt**, not adjusted. The committed simulation
  models a discrete four-event stack and does not carry over. It is blocked on
  D3 (the pass bar is still estimated from the data it judges).
- The memo itself needs §§3, 4, 7, 9 rewritten so it carries one primary, and
  a fresh red-team pass — the existing `CONDITIONAL_GO` reviewed the discrete
  design and does not transfer.

---

# URGENT — the box has been dead since 2026-07-10 (found 2026-08-18)

`ops/box/inbox_log.md` ends at `2026-07-10T12:30Z`, and the last commit
authored by `portfolio-box` is the same day. That is **39 days** of no L0/L1
activity. Consequences:

- The Channel A payload merged in PR #36 will never fire. The price panel is
  stuck at `single_channel` for all 71 rows, and one channel can never certify
  a price, so no price row can reach `verified`.
- Every L1 batch `make plan` advertises as READY has been dispatching nowhere:
  `P1-T1-events`, `P1-T13-ant`, `P1-T0-monitor`, `REFR-R0-collide`,
  `REFR-R1a-verify`, `E2-T2-dune`, `E2-T6b-nav`, `REFR-R13-scan`.
- Stale leases were never reaped, which is why `DAX-W1-memo` and
  `P1-T1-events` still show in flight — `--reap` runs on the box's 30-min tick.
- The evening digest has not been produced for five weeks.

**Diagnosis order** (owner, ~15 minutes): is the host up; is cron running
(`crontab -l`, `ops/box/cron.log` tail); does `git pull --ff-only origin main`
succeed from the box checkout; is `ops/box/.env` still present after any
reboot; did the 2026-07-09 merge-wedge lock (`ops/box/.cron.lock`) get left
held by a killed process.

Until it is back, treat every "overnight batch will handle it" assumption in
the queue as false.

## Channel A is blocked three ways

| Route | State |
|---|---|
| This sandbox | `web.archive.org:443` denied by network policy (403 at the gateway) |
| The box | dead since 2026-07-10 |
| SSH to scc1.bu.edu | no ssh binary, no keys, TCP:22 blocked |

Any one of these unblocks it: revive the box, allowlist `web.archive.org` and
`archive.org` in the environment's network policy, or run
`python dax/w2/prices/build_price_panel.py --time-budget 600` on any host with
egress and commit the resulting `price_histories.csv`.


---

# Crosswalk reassignment REVERSED — 2026-08-19

The 2026-08-18 note reassigned the CPS-O*NET crosswalk to the W2-infra lane.
That is now moot: seat C's `build_occ2010_crosswalk.py` supersedes it and is the
canonical builder. `dax/w2/crosswalk/build_crosswalk.py`, `sources.py`,
`dax/tests/test_crosswalk.py` and `ops/contracts/cps_onet_crosswalk.yaml` were
removed on 2026-08-19.

The retired builder was wrong in a way that mattered: it split a SOC's OEWS
employment equally across O*NET-SOC children and, when every target lacked
employment, renormalised the whole CPS code to equal weights — turning an
unknown allocation into a confident-looking point estimate, and moving
`max_crosswalk_weight`, which drives the Decision 12 flag. The production
builder preserves unresolved components at original weight and emits
`dose_min`/`dose_max` intervals through `dose_bounds.py`, with a point estimate
only for `resolved_employment_weighted` codes. Its contract was orphaned anyway
— no queue task referenced it.

**Correction to the 2026-08-19 review:** `cps_onet_crosswalk.csv` being absent
from `data_built/` is deliberate policy, not an omission. Detailed crosswalk,
legacy fallback, gap audit and respondent-level CPS artifacts are restricted and
must stay out of git; only sanitized receipts and aggregate reports are tracked,
and `audit_standard_freeze.py` rejects tracked row-level restricted artifacts.
