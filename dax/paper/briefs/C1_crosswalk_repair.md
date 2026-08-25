# C1 — Vintage repair: put every exposure measure on the OEWS 2021 taxonomy

*Prepend `C0_CONTEXT_PACK.md`. One task, one session.*

## Why this task exists

AIOE and Dingel–Neiman publish on an identical list of 774 SOC 2010 codes.
Merged against OEWS 2021 (SOC 2018) they drop 158 occupations carrying
**19.65% of employment**, concentrated catastrophically: SOC major group 15
matches 4 of its 21 OEWS occupations and loses **96.7%** of its employment.
Software Developers (15-1252), Computer Systems Analysts (15-1211), Computer
User Support Specialists (15-1232) and Project Management Specialists (13-1082)
have no AIOE value at all.

Until this is repaired, "is the young-employment finding robust across exposure
measures?" is unanswerable for AIOE, because AIOE structurally omits the
occupations where the finding is claimed to occur.

Measured evidence: `dax/w2/exposure_gate/AUDIT_RESULTS.md` §"Item 3".

## Inputs you must fetch

The session that wrote this brief had no network access to bls.gov. Fetch with
locators and checksums; record both in the receipt.

1. **BLS SOC 2010 → 2018 crosswalk.** The official detailed-occupation
   crosswalk. Record the exact URL and file date.
2. **OEWS national files** for **2019** and the most recent available year.
   Same columns as the existing `dax/data_built/oews_wages.parquet` build.

If either is unavailable, `NEED_HUMAN` and stop. Do not substitute an
unofficial crosswalk, a Census occupation crosswalk, or a fuzzy title match.

## What to build

`dax/w2/exposure_gate/repair_soc_vintage.py`, emitting
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

Re-run `dax/w2/exposure_gate/audit_common_support.py` twice more, with `--oews`
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
