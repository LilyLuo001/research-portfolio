# onet_timeshares.parquet cannot be built as specified

**Date:** 2026-08-24. **Status:** blocker record. Requires a PI decision, not a
builder.

## The finding

`ops/contracts/dax_built_backbone.yaml` requires `onet_timeshares.parquet`, and
the W2 brief defines it as "O*NET 2021 vintage task and IWA structure with
occupation time-shares."

**O*NET 26.1 publishes no occupation time-share.** Established by a read-only
inventory of all 38 tables in the pinned zip
(`dax/w2/onet_gdpval_input_inventory_receipt_20260824.json`, archive sha256
`543d65fa…8017a`):

- The one "% Time" scale, **TI**, is defined in `Scales Reference.txt` but
  occurs in **zero data tables**. It appears only there and in
  `Survey Booklet Locations.txt`, and its nine items publish on CX/CXP and
  measure **body position**.
- `Duration of Typical Work Week` is whole-job, not per-task.
- No column anywhere in the release carries hours or minutes.

## What exists instead

Three candidate weights, all in `Task Ratings.txt`, none of them a time share:

| Scale | What it is | Why it is not a time share |
|---|---|---|
| **FT** Frequency of Task | seven rows per occupation-task giving percent of incumbents per frequency band; verified to sum to 100 across all 17,879 pairs | a distribution over *how often*, not *how long*; collapsing it to a scalar is an unstated modelling choice |
| **IM** Importance | 1-5 rating | importance is not duration |
| **RT** Relevance of Task | 0-100 | relevance is not duration |

A share constructed from any of these is a share of **rating mass**, not of
**work time**. Calling the result a time share would misname it in the one
artifact the whole wage-bill weighting depends on.

## Structure that does exist

`Tasks to DWAs.txt` is the only direct task link, and it goes to **DWA, not
IWA**. IWA is reachable only through `DWA Reference.txt`
(DWA ID → IWA ID → GWA Element ID). The brief's phrase "task and IWA structure"
is therefore a two-hop derivation, not a table.

## Vintage caveat for the write-up

O*NET 26.1 is a **cumulative** release. `Task Ratings` rows carry dates spanning
**2004-2021**, and Task Statements likewise. "2021 vintage" names the release,
not the survey year of each row. Any claim that the index rests on 2021 task
structure needs this stated, or a referee will find it.

## What this changes

This deliverable moves from *unbuilt* to *not buildable as specified*. It is
not a free item, and no builder should be written until the PI decides:

1. Which of FT, IM or RT defines the weight, or whether a combination does.
2. If FT: the exact rule collapsing its seven-band distribution to a scalar.
3. Whether the resulting quantity is renamed — `onet_task_weights` rather than
   `onet_timeshares` — since it is not a time share and the contract's column
   names are frozen once written.
4. Whether the 2004-2021 vintage spread is accepted, or rows are restricted.

Deciding these inside a data builder would bury a measurement choice in a
loader, which is the same fault the W3 reconciliation found in routing pi
through an unvalidated transport.

**Nothing is blocked behind this that is not already blocked.** W5 needs the
full backbone, and `cps_extract.parquet` is independently outstanding.
