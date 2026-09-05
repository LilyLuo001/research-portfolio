# Calendar correction and repair

## Correction to the pre-execution description

`ANALYSIS_SPEC_BEFORE_EXECUTION.md` correctly anticipated that March 2017--2021 might be extract-specific, but its statement that October 2025 was an extract-specification omission is wrong. That file is preserved as the dated pre-execution record; this correction supersedes only the calendar explanation.

IPUMS distinguishes the March basic monthly sample (`03b`) from the Annual Social and Economic Supplement (`03s`). The original wide extract requested `03s` for March 2017--2021. Those records have `ASECFLAG=1` and zero basic monthly final weights and therefore cannot replace the omitted basic samples. The repair extract requested `cps2017_03b` through `cps2021_03b`, preserving the original raw file and adding a separately hashed input.

October 2025 is different: no CPS was collected during the federal government shutdown. It is a real survey-calendar hole, not an extraction choice. Authoritative locators are:

- IPUMS CPS sample identifiers: <https://cps.ipums.org/cps-action/samples/sample_ids>
- IPUMS CPS sample selection: <https://cps.ipums.org/cps-action/samples>
- Repository documentation: `yax/measurement/webb_occ1990_feasibility_receipt.json`

## Audited calendars

- Raw combined files: 9,843,021 records and 114 observed survey months.
- Available basic months: January 2017--July 2026, including restored March 2017--2021, excluding October 2025.
- Frozen static model: 108 months because it omits March 2017--2021, October 2025, and transition month December 2022.
- Corrected-calendar static sensitivity: 113 months because March 2017--2021 is restored while October 2025 and December 2022 remain absent.

The frozen 108-month coefficient is -0.1311. Restoring five March basic samples gives -0.1346 with 95% interval [-0.2230, -0.0461]. The repair therefore does not explain the primary estimate. The post-2020 Census-2018 sensitivity covers 77 months and estimates -0.1211; it changes both taxonomy and temporal estimand. A stable Census-2010 aggregation estimates -0.1522 on 113 months and 408 occupations.

## Reconstruction audit

Pre-2020 one-to-many routes apply the same official conversion proportions to both age groups within a source occupation and month. This mechanically preserves the source young/older ratio across its target components before aggregation with other sources. Fifty-six source codes are one-to-many, the maximum multiplicity is seven, and 20.03% of early-period weighted employment is routed from one-to-many sources. This is why the paper reports both the stable coarser-taxonomy and post-2020 comparisons rather than treating an incompatible exact-code merge as a serious benchmark.
