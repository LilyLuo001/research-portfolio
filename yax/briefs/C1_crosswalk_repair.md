# C1 — Vintage repair: put every exposure measure on the OEWS 2021 taxonomy

*Prepend `C0_CONTEXT_PACK.md`. One task, one session.*

## Why this task exists

AIOE and Dingel–Neiman publish on an identical list of 774 SOC 2010 codes,
with **full coverage of that taxonomy**. SOC 2018 renumbered essentially all of
major group 15, so an exact-code merge onto OEWS 2021 drops 158 occupations
carrying **19.65% of employment**, and **96.7%** of major group 15.

**Read that correctly.** Nothing is missing from AIOE. It covers Software
Developers at 15-1132 (+1.2009) and 15-1133 (+1.2833); OEWS 2021 calls that
occupation 15-1252. Computer Systems Analysts is 15-1121 in AIOE, 15-1211 in
OEWS 2021. The 96.7% measures the cost of merging without a crosswalk. An
earlier draft of this brief said AIOE "structurally omits" these occupations.
That was false — see `yax/CORRECTION_2026-08-25_vintage_gloss.md`.

So this task is a **crosswalk decision**, not a repair of a broken measure. It
matters because every paper in this literature makes this decision and none
reports it, and because C3 tests whether the decision moves the coefficient.

Measured evidence: `yax/measurement/AUDIT_RESULTS.md` §"Item 3".

## Step 0 — reconcile against prior work FIRST

**Do this before downloading anything from BLS.** Reported (unverified from
this repo): Eckhardt & Goldschlag, *AI and Jobs: The Final Word (Until the Next
One)* (2025), chose AIOE specifically because ability-level exposure makes
crosswalking more accurate, compared two crosswalk approaches, and published
their data on GitHub.

1. Locate that repository and their crosswalked AIOE file.
2. Merge it against `dax/data_built/oews_wages.parquet` and report coverage,
   especially major group 15.
3. **If their file resolves the target occupations**, adopt it as the primary
   crosswalked measure, cite it, and reduce the rest of this task to a
   documented comparison. You have saved a week and learned that the exact-code
   merge — not the measure — was the problem.
4. **If it does not**, proceed to build below, and record precisely what theirs
   does not cover.

Either way, record in the receipt: their repo URL, commit hash, file sha256,
and their stated crosswalk method. Emit `NEED_HUMAN` if you cannot find it
rather than assuming it does not exist.

## Inputs you must fetch (only if Step 0 does not resolve it)

The session that wrote this brief had no network access to bls.gov. Fetch with
locators and checksums; record both in the receipt.

1. **BLS SOC 2010 → 2018 crosswalk.** The official detailed-occupation
   crosswalk. Record the exact URL and file date.
2. **OEWS national files** for **2019** and the most recent available year.
   Same columns as the existing `dax/data_built/oews_wages.parquet` build.

If either is unavailable, `NEED_HUMAN` and stop. Do not substitute an
unofficial crosswalk, a Census occupation crosswalk, or a fuzzy title match.

## What to build

`yax/measurement/repair_soc_vintage.py`, emitting
`dax/data_built/exposure_soc2018.parquet`.

**Schema — frozen, do not rename:**

| column | meaning |
|---|---|
| `soc_2018` | 6-digit SOC 2018 code |
| `measure` | one of the seven measure names used in the audit |
| `value` | the measure on SOC 2018 |
| `mapping_method` | `direct` \| `split` \| `aggregate` \| `unresolved` |
| `source_soc_2010` | semicolon-joined contributing SOC 2010 codes |
| `weight_basis` | `identity` \| `oews_2021_employment` \| `equal` |
| `coverage_flag` | `resolved` \| `provisional` \| `absent` |

**Mapping rules, in this order:**

- **One-to-one** → carry the value, `mapping_method=direct`,
  `weight_basis=identity`.
- **One 2010 splits into many 2018** → the 2010 value is carried to every child
  unchanged, `mapping_method=split`. A split does not create information; do
  not interpolate between children.
- **Many 2010 collapse into one 2018** → employment-weighted mean using OEWS
  2021, `mapping_method=aggregate`, `weight_basis=oews_2021_employment`. If a
  contributing 2010 code has no OEWS employment, fall back to `equal` and mark
  `coverage_flag=provisional`.
- **No official link** → emit the row with `value` null,
  `coverage_flag=absent`. **Never drop it silently and never impute.**

**Fail-closed.** If resolved-plus-provisional employment coverage against OEWS
2021 is below **90%**, write the receipt, emit `NEED_HUMAN`, and stop rather
than proceeding to C2.

## Also produce

Re-run `yax/measurement/audit_common_support.py` twice more, with `--oews`
pointing at 2019 and the recent year. This closes **audit item 2**, which is
currently recorded as BLOCKED for exactly this reason. Save each receipt under
a year-suffixed name; do not overwrite the 2021 receipt.

## Definition of done

- `exposure_soc2018.parquet` + lineage + receipt with both source URLs and
  their sha256.
- Coverage table by SOC major group, showing group 15's before/after.
- Audit item 2 answered with three weight years, or `NEED_HUMAN` explaining why
  a year could not be obtained.
- A test in `dax/tests/` asserting: no silent drops (every OEWS 2021 code
  appears with some `coverage_flag`), splits preserve the parent value, and
  aggregates lie within the min/max of their contributors.
- `pytest -q` green.

## Do not

- Do not repair by matching occupation titles.
- Do not use this task to change any measure's definition.
- Do not look at any CPS outcome. C1 touches no microdata.
