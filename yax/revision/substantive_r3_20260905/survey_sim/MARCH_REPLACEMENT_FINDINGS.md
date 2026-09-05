# March replacement and survey-field findings

Status: **PASS -- functional replacement is verified**

## Correction to the initial alert

An initial inspection found that the wide request selected March ASEC samples
in 2017--2021 and that the repair file contains the corresponding Basic
Monthly samples.  Because many identifiers overlap in the two raw files, that
inspection raised a possible double-counting problem.  The alert was
premature: it compared identifiers before applying the analysis-weight rule.

The decisive fact is that **every record in the five wide-file ASEC samples
has `WTFINL=0`**.  The cell builder requires a finite, strictly positive
`WTFINL` before routing or aggregation.  The ASEC records therefore contribute
zero analysis records and zero employment stock.  Adding the positive-weight
Basic file is operationally identical to dropping the ASEC sample and
replacing it with Basic Monthly data.

This correction is preserved because raw overlap and active weighted overlap
are different objects; reporting only the former would have incorrectly
invalidated the corrected panel.

## Exact aggregate evidence

| month | raw CPSID overlap (% of Basic) | raw CPSIDP overlap (% of Basic) | active ASEC records | active Basic records | Basic routed stock | append-minus-replace stock |
|---|---:|---:|---:|---:|---:|---:|
| 2017-03 | 45,029 (85.88%) | 87,693 (68.91%) | 0 | 55,960 | 142,449,997 | 0 |
| 2018-03 | 43,387 (85.40%) | 84,329 (68.58%) | 0 | 54,009 | 144,573,112 | 0 |
| 2019-03 | 44,836 (91.72%) | 87,337 (73.95%) | 0 | 52,264 | 145,572,066 | 0 |
| 2020-03 | 39,842 (91.32%) | 77,576 (73.97%) | 0 | 45,539 | 144,781,047 | 0 |
| 2021-03 | 40,980 (91.21%) | 79,358 (73.94%) | 0 | 45,090 | 140,207,061 | 0 |

The raw overlap is expected because ASEC contains respondents from the March
basic sample.  Active overlap in `CPSIDP` and `CPSIDV` is zero in every month,
as are duplicate active person rows after concatenation.  The Basic file
contributes 717,583,283 routed weighted workers across the five restored
months; none is duplicated by positive-weight ASEC stock.

The authenticated request records independently confirm the intended sample
types: `cps2017_03s` through `cps2021_03s` in the wide request and
`cps2017_03b` through `cps2021_03b` in the repair request.  The repair request
description explicitly says that it replaces accidentally selected ASEC
samples.

## Implementation recommendation

The existing positive-weight filter is sufficient for these authenticated
files, but the intended rule should be expressed directly: exclude the five
wide-file ASEC months, then add the five Basic months.  A fail-closed test
should also retain the current assertions that the wide ASEC samples have zero
positive `WTFINL`, the active union has no duplicate person links, and explicit
replacement equals the positive-weight append result.  This guards against a future IPUMS
extract whose ASEC weight behavior differs.

## Survey inference implication

The DDI confirms `CPSID`, `SERIAL`, `CPSIDP`, `CPSIDV`, `MISH`, `WTFINL`, and
`HWTFINL`.  It contains no public stratum, PSU, or replicate-weight variable.
`SERIAL` is unique only within year and month; `CPSID` is the available
longitudinal household link.  A common-`CPSID` multiplier can therefore probe
co-resident and repeated-month sampling dependence conditional on final
weights.  It cannot reconstruct the CPS multistage design or calibration
uncertainty and must not be called design-based inference.

Machine-readable evidence is in `results/march_replacement_audit/`.
