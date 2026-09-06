# CPS population-control, collection, and IPUMS revision audit

**Audit date:** 2026-09-05
**Scope:** official BLS and IPUMS CPS documentation relevant to January 2025, the October–November 2025 shutdown disruption, and January–February 2026. This audit does not infer subgroup corrections that the agencies did not publish.

## January 2025 population-control break

### Verified facts

The CPS began using updated population controls in January 2025. The controls incorporated the Census Bureau's Vintage 2024 population estimates, including an updated method for estimating net international migration. BLS published the effect of applying the new controls to the December 2024 sample:

| December 2024 quantity | Effect of new controls |
|---|---:|
| Civilian noninstitutional population age 16+ | +2.871 million |
| Civilian labor force | +2.106 million |
| Employment | +2.000 million |
| Unemployment | +105 thousand |
| Not in the labor force | +765 thousand |
| Labor-force participation rate | +0.1 percentage point |
| Employment–population ratio | +0.1 percentage point |

Primary sources:

- [BLS, Effects of Population Control Adjustments on CPS Estimates in 2025](https://www.bls.gov/cps/methods/population-controls/population-control-adjustments-2025.pdf)
- [BLS experimental series accounting for January 2025 control effects](https://www.bls.gov/cps/methods/population-controls/experimental-series-accounting-for-january-2025-population-control-effects.htm)

BLS did not revise official December 2024 or earlier estimates. Consequently, December 2024–January 2025 changes in **levels** are not directly comparable. The BLS experimental series use ratio adjustments for selected major labor-force aggregates back to April 2020; they are not detailed age × occupation corrections.

### YAX implication

The population controls incorporate age, sex, race, and Hispanic ethnicity, among other components, but do not furnish occupation-specific counterfactual factors. It would be invalid to multiply YAX age × occupation cells by aggregate BLS adjustments and call the result a recovered constant-vintage series. Appropriate responses are:

- mark January 2025 as a documented weight-vintage break;
- report endpoint/window sensitivities that avoid placing interpretive weight on that one boundary;
- distinguish estimates using final weights from unweighted fractional-record outcomes;
- avoid claiming the unweighted outcome reconstructs an alternative population-control vintage.

## October–November 2025 collection and weighting disruption

### Verified facts

The federal funding lapse ran from October 1 through November 12, 2025. CPS operations were suspended. BLS reports:

- October 2025 CPS data were not collected and no October 2025 public-use microdata file exists; October was not collected retroactively.
- The November reference week was November 9–15. Collection began November 17, one day later than usual, and continued through November 30.
- Sample rotation continued despite October's absence. November included two entering rotation groups and two returning-after-break groups, so one-half of sampled households lacked the usual prior-month overlap.
- Modified AK composite estimation used the two-month September-to-November change and an overlap of approximately 50 percent rather than the usual 75 percent. Normal procedures resumed in December.
- The November response rate was 64.0 percent, compared with a 68.4 percent average over the preceding 12 months.
- For the national unemployment level, BLS reported approximate standard-error multipliers of 1.04 for lower response, 1.06 for weighting, 1.12 for the two-month change, and 1.23 jointly.
- Annual 2025 CPS estimates use 11 months; BLS did not publish fourth-quarter 2025 CPS estimates.

Primary source: [BLS, Impact of the 2025 federal government shutdown on the CPS](https://www.bls.gov/cps/methods/2025-federal-government-shutdown-impact-cps.htm).

### YAX implication

October 2025 is a real missing survey month and must not be interpolated or treated as zero. Elapsed calendar lags in any HAC procedure must preserve the September-to-November gap. The BLS standard-error multipliers apply to named national estimates under BLS's production procedure; they are not transportable design effects for YAX age × occupation cells. Sensitivities excluding September and November 2025 can diagnose reliance on the disruption but do not reconstruct the missing month.

## January–February 2026 delayed control update

### Verified facts

The shutdown delayed the annual population-control update. Initial January 2026 estimates used Vintage 2024 projections. On March 6, 2026, with the February release, BLS revised all January 2026 estimates using Vintage 2025 controls and reissued the January public-use microdata file with revised weights.

Applying the new controls to the December 2025 sample produced the following effects:

| December 2025 quantity | Effect of new controls |
|---|---:|
| Civilian noninstitutional population age 16+ | −231 thousand |
| Civilian labor force | −1.417 million |
| Employment | −1.432 million |
| Not in the labor force | +1.185 million |
| Labor-force participation rate | −0.4 percentage point |
| Employment–population ratio | −0.5 percentage point |
| Unemployment rate | approximately unchanged |

Primary sources:

- [BLS notice, 2026 population-control revision](https://www.bls.gov/cps/notices/2026/population-control-revision-2026.htm)
- [BLS, Effects of Population Control Adjustments on CPS Estimates in 2026](https://www.bls.gov/web/empsit/cps-pop-control-adjustments.pdf)
- [BLS experimental series accounting for January 2026 effects](https://www.bls.gov/cps/methods/population-controls/experimental-series-accounting-for-January-2026-population-control-effects.htm)

BLS left official December 2025 and earlier estimates unchanged. Its experimental historical series combine a population-ratio adjustment with outcome-specific compositional factors under assumptions that do not recover the precise timing or detailed subgroup composition of the revision. BLS does not publish corresponding age × occupation series.

### YAX implication

The YAX extract must be checked for the **reissued January 2026 file**, not merely for the presence of January 2026. A pre-March-6 file can carry superseded weights. February 2026 shares the new control basis, while the official December-to-January level change crosses a discontinuity.

## IPUMS CPS revision chronology relevant to YAX

Primary source: [IPUMS CPS revision history](https://cps.ipums.org/cps-action/revisions).

| IPUMS posting date | Revision | Variables/analyses at risk |
|---|---|---|
| 2025-06 | Census corrected an April 2025 Basic Monthly CPS weighting error; IPUMS updated affected weights | April 2025 weighted stocks |
| 2025-12-22 | November 2025 Basic Monthly sample added; no October sample exists | late-2025 calendar and dynamics |
| 2026-04-10 | Revised January 2026 Basic Monthly sample processed | `WTFINL`, `PANLWT`, `EARNWT`, `COMPWT`, `LNKFW1MWT`, and related person/household fields |
| 2026-07-13 | Revised `HRHHID2` for January 2024–July 2025 processed | `CPSID`, `CPSIDP`, longitudinal links and linking weights |
| 2026-08-14 | A small number of `CPSIDP` values corrected for November 2025–March 2026 | longitudinal flows spanning those months |

The exact extract vintage is therefore load-bearing. A reproducible audit should record:

1. IPUMS extract number, creation date, DDI, and data-file hash;
2. all requested weight and linking-ID variables;
3. whether extraction occurred after the applicable IPUMS processing dates;
4. month-level counts and weighted totals around April 2025 and January 2026;
5. link counts around January 2024–July 2025 and November 2025–March 2026;
6. explicit confirmation that October 2025 is absent rather than coded zero.

If an older extract is used, it should be refreshed or the affected months/links should be disclosed and isolated. This is especially important for the CPS flow analysis, because later ID corrections affect the identity of linked observations, not only their weights.

## Manuscript-safe summary

> The public CPS series crosses documented population-control discontinuities in January 2025 and January 2026, and the October 2025 survey was not collected during the federal funding lapse. November 2025 used a modified collection and weighting procedure. We therefore treat these dates as survey-production discontinuities, verify that the extract incorporates the reissued January 2026 file and later IPUMS identifier revisions, and report pre-specified endpoint and month-exclusion sensitivities. Because BLS does not publish counterfactual age-by-occupation control factors, we do not mechanically rescale subgroup cells using aggregate adjustments.

This language does not imply that the discontinuities caused any YAX coefficient movement. That is an empirical sensitivity question.
