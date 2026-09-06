# January 2025 population-control documentation and admissible checks

Status: written before the results from `run_population_control_audit.py` were opened.

BLS states that new CPS controls enter each January. The January 2025 controls use the Census Bureau's Vintage 2024 population estimates and incorporate a larger-than-usual revision to net international migration. Applied to December 2024, the revised controls add 2.9 million people (1.1 percent) to the civilian noninstitutional population and 2.0 million to employment. BLS warns that official January 2025 levels are not directly comparable with December 2024 because earlier official months were not revised.

Official sources:

- <https://www.bls.gov/cps/methods/population-controls/population-control-adjustments-2025.pdf>
- <https://www.bls.gov/cps/methods/population-controls/experimental-series-accounting-for-January-2025-population-control-effects.htm>
- <https://www.bls.gov/cps/documentation.htm#pop>
- <https://cps.ipums.org/cps-action/variables/170703>

BLS's experimental historical series uses an aggregate monthly population ratio for labor-force and employment levels. BLS explicitly does not produce the adjustment for demographic subgroups because the revised controls do not reveal the necessary detailed composition. It is therefore not a defensible replacement weight for YAX's age-by-occupation cells.

The admissible audit is limited to:

1. the repaired 113-month official-weight estimate;
2. the same design ending in December 2024;
3. respondent-equivalent (unweighted routed-count) versions of both;
4. joint 2023--24 and 2025--26 coefficients under official weights and respondent-equivalent counts; and
5. a raw December-to-January discontinuity diagnostic under both cell values.

None is called a literal “without the January 2025 revision” estimate. Such a result would require age-by-occupation counterfactual weights that are not published.
