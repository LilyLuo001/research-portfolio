# p1/t2_wrds — the WRDS/CRSP path for P1-T2

> **LEGACY VALIDATION PATH (2026-09-03).** Retained and tested for
> reproducibility, but it is not the frozen treatment source. Current
> Exposure^pre uses exact-series strict-PRE N-PORT plus CRSP security data; see
> `p1/exposure/`.

Referenced from `holdings_pipeline.py` ("WRDS creds via ~/.pgpass or
WRDS_USER/WRDS_PASS; see README"). Written 2026-08-18, before access was
delivered, so the rules exist before the first pull rather than after.

## Where this runs, and why never here

The `wrds` package speaks **PostgreSQL to `wrds-pgdata.wharton.upenn.edu:9737`**;
WRDS Cloud is **SSH**. Neither is HTTP, so an HTTPS CONNECT proxy cannot carry
them however the allowlist is set — this is structural, not a temporary sandbox
quirk. Claude Code sessions therefore write and test this code; the box (or a
WRDS Cloud batch job) runs it where the credentials live. Test coverage in
`p1/tests/` injects a fake connection, so every line here is exercised with zero
credentials.

Credentials: `WRDS_USER` / `WRDS_PASS`, or `~/.pgpass`. They live on the box and
are never committed, never logged, and never passed on a command line.

## Run order

```
python p1/t2_wrds/build_waves.py         # offline, from events_merged.csv
python p1/t2_wrds/coverage_census.py     # FIRST after access lands — see below
python p1/t2_wrds/holdings_pipeline.py   # the ConvExp build
python ops/runner/contracts.py conv_exposure p1/conv_exposure.parquet
```

**Run the census before the pipeline.** Mutual-fund holdings coverage has known
lags and gaps; whether every one of the 131 conversion funds has a usable
pre-conversion holdings report is a fact to establish with code on real data, not
to assume. A pipeline run that silently drops a third of the funds looks like a
successful run.

## Data policy — licensed data (READ BEFORE THE FIRST PULL)

The free EDGAR path could commit its outputs freely: every number carried a
public locator and no paid source was involved. **That premise does not hold
here.** CRSP and its WRDS siblings are subscription data under an agreement that
does not permit redistribution, and this repository is not a safe container for
row-level extracts.

**May be committed**
- Derived aggregates that are the study's own measures: `conv_exposure.parquet`
  (ratios, counts, deciles) as specified by `ops/contracts/conv_exposure.yaml`.
- A **manifest of query locators**: library.table, columns, filters, pull date,
  row count, checksum — enough for an auditor to re-run the identical query with
  their own subscription. This is the WRDS analogue of an EDGAR accession, and it
  is what satisfies meta-rule 1 without shipping the data.
- Counts, diagnostics, coverage tables, `NEED_HUMAN` lists keyed on identifiers.

**May NOT be committed**
- Any row-level extract of a licensed table — holdings rows, `msf`/`dsf` rows,
  security master dumps — in any format, including "just a sample".
- Any file under `p1/t2_wrds/raw/` or `p1/t2_wrds/cache/` (both gitignored).
- Any file named `*.raw.csv` / `*.raw.parquet` (gitignored).

**Marker convention.** Any file written from a raw licensed pull carries the
string `WRDS-RESTRICTED` in its header or its sidecar JSON. This mirrors the DAX
NDA-marker discipline: a guard greps tracked files for that marker, so a raw pull
that escapes the ignore rules still fails CI rather than being published. The
guard is `p1/tests/test_wrds_data_policy.py`.

**If licensed data is ever committed**, treat it as a disclosure, not a mistake to
quietly amend: git history is public once pushed, so removing the file is not
sufficient — the owner decides whether history rewriting or a subscription-desk
notification is required. That judgement is deliberately not automated.

**Seat D**: `ops/COMPLIANCE.md` currently says nothing about WRDS. This section
is the source text to fold into it (item W-06 of
`ops/briefs/WRDS-independent-workplan.md`).

## Files here

| file | role |
|---|---|
| `build_waves.py` | offline wave construction from `events_merged.csv` (waves.csv + waves_members.csv) |
| `holdings_pipeline.py` | the CRSP ConvExp build, against the frozen `conv_exposure.yaml` contract |
| `coverage_census.py` | day-one coverage census — run before the pipeline |
| `waves.csv`, `waves_members.csv` | committed, derived from public T1 output — not licensed data |
