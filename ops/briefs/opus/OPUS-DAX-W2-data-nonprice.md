# PROMPT — DAX-W2-data (non-price half)

_Paste below the line into a Claude Code session on seat A. This is the
public-data backbone: bulk acquisition and deterministic transforms, no
frontier judgment. The **price-histories** slice of W2 is claimed by another
worker — see the carve-out in `ops/briefs/ASSIGNMENTS-2026-08-14.md` and do
not write `price_histories.csv`._

---

You are the W2 Data Agent for the DAX project (seat A, DAX-prime). Read, in
order: `CLAUDE.md`, `dax/CLAUDE.md`, `ops/briefs/ASSIGNMENTS-2026-08-14.md`
(the collision carve-out is binding), `dax/memo/design_memo_v1.md` §§0, 2, 5,
6.1, 7 and Decisions 8 and 12, and `ops/contracts/dax_built_backbone.yaml`.

## Protocol
`python ops/runner/lease.py claim DAX-W2-data --account A` → branch
`task/DAX-W2-data` → touch only `dax/`. **Never open `dax/analysis/outcomes/`.**
Everything here is pre-period construction; the seal stays closed and no
`v1.0-preregistered` tag is created. No OpenAI NDA usage aggregates anywhere.

## Deliverables

Four files, three of which are yours (the fourth, `price_histories.csv`, is
NOT — leave it alone):

1. **`dax/data_built/onet_timeshares.parquet`** — O*NET **2021 vintage** task
   and IWA structure with occupation time-shares. The 2021 vintage is the
   frozen primary per §0; annually-updated bundles are a robustness variant
   and must be built as separate, clearly-named files if built at all.
2. **`dax/data_built/oews_wages.parquet`** — OEWS **2021** occupation wages.
   Carry the 2019 baseline as a registered robustness vintage in a separate
   column or file, never as a substitute for 2021.
3. **`dax/data_built/cps_extract.parquet`** — IPUMS-CPS monthly, ages 22–25,
   Nov 2021 → latest frozen month, person weights, `CPSIDP` retained (§7 needs
   it for the pre-event occupation lookback).
   **Extract 6 is already pulled.** Its definition and checksums are in
   `dax/memo/power_calcs/ipums_preperiod_extract_receipt.json` and
   `ipums_preperiod_extract_v1.json`. Reuse it. Verify every SHA256 in the
   receipt before you build on it, and fail closed on a mismatch rather than
   re-pulling silently. Only pull a new extract if a required variable is
   genuinely absent, and if you do, emit a new receipt in the same shape.

Plus two supporting artifacts:

4. **CPS ↔ O*NET-SOC crosswalk**, many-to-many, employment-weighted. Decision
   12's diagnostics are **columns, not a report**: per CPS code, the weighted
   within-code standard deviation of O*NET dose and the maximum mapping
   weight, so the low-quality flag (SD > 0.10 or max weight < 0.50) is
   computable downstream without re-deriving it.
5. **Frozen static-score ensemble** (Felten / Eloundou / Webb) at occupation
   level, for the Decision-8 Spearman ≥ 0.50 convergent-validity check. Freeze
   it now so the benchmark cannot drift later.

## Rules that bite here

- **Meta-rule 1.** Every figure comes from code you ran on a file you
  downloaded. Each download records agency, table/series ID, vintage,
  retrieval timestamp, and checksum. A number you cannot trace to a
  locator does not go in the file.
- **Meta-rule 3.** `dax_built_backbone.yaml` freezes the four filenames.
  Do not rename them. If a column name in a downstream contract is wrong,
  raise it — do not fix it by renaming.
- **Meta-rule 4.** Coverage gaps stay visible. Unmatched occupations, missing
  wage cells, and unmapped CPS codes are reported with their wage-bill share,
  never imputed, never dropped silently.
- **Pre-period only.** Nothing in this task reads post-event outcomes.

## Known downstream context (do not act on it, just don't contradict it)

The 2026-08-14 audit found the W1 window rule leaves only 2 estimable events,
and that the power engine refuses below 3. That is an open `[PI-DECISION]`.
It does **not** change anything you build here — all five items are required
under every candidate resolution — but it does mean you must not start
`DAX-W3-mapA` when you finish. Stop, `make plan`, and report.

## Session end
Lineage JSON for every emitted file. `python ops/runner/contracts.py
dax_built_backbone dax/data_built/` will FAIL until the price half lands too —
that is expected; report your three files passing their own checks. Commit,
`make plan`, stop. Do **not** `--complete DAX-W2-data`: it completes only when
both halves are in.
