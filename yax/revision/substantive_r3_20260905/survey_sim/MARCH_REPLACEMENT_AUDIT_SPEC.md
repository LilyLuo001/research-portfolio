# March 2017--2021 sample-replacement and survey-field audit

Status: **post-outcome implementation audit; written before the aggregate audit was run**

This module decides two prerequisites for the R3 sampling-oriented work.  It
does not estimate an employment coefficient.

## Question 1: does the current append operation double count March?

The wide IPUMS request selected the ASEC samples for March 2017--2021, while
the repair request explicitly selected the corresponding Basic Monthly
samples.  The existing cell builder concatenates both input files after
requiring a finite, strictly positive `WTFINL`.  Concatenation is equivalent to
replacement only if the ASEC records in the wide file have zero `WTFINL` and
there are no duplicate positive-weight person records after the Basic file is
added.

For each repaired month, the audit will report, separately for raw records and
the age-18--65 employed analysis records:

- counts and final-weight stock in each file;
- within-month overlap in `CPSID`, `CPSIDP`, and `CPSIDV`;
- duplicate active identifiers after concatenation;
- routed stock under the declared 2010-to-2018 bridge; and
- the active-stock difference between literal replacement and the existing
  positive-weight append implementation.

The gate fails closed if the wide ASEC file has any positive `WTFINL` in a
repaired month, if the active concatenation has duplicate person identifiers,
if the repair months or sample types differ from the two authenticated request
specifications, or if append and replacement yield different routed stock.
No individual identifier is written to the repository.

## Question 2: what sampling information is actually available?

The DDI metadata and file headers are the authority for extract contents.  The
audit distinguishes:

- `SERIAL`: a household identifier unique only within year and month;
- `CPSID`: an IPUMS longitudinal household identifier across the CPS 4-8-4
  rotation;
- `CPSIDP` and `CPSIDV`: person-link identifiers;
- `MISH`: month in sample; and
- `WTFINL`/`HWTFINL`: final calibrated weights.

It also checks for public stratum identifiers, PSU identifiers, or replicate
weights.  A later `CPSID`-cluster multiplier exercise is admissible only as a
sampling-oriented sensitivity conditional on final weights and observed
longitudinal links.  It is not full CPS design-based inference when public
strata, PSU, selection-stage, and replicate-weight information are absent.

## Binding sequencing rule

No household bootstrap may run until this audit passes and the cell
construction is shown to implement a genuine positive-weight replacement.
The bootstrap, if later executed, must give every observation of a `CPSID`
across all months one common multiplier and give every fractional crosswalk
descendant of a source record that same multiplier.

