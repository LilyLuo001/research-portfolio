# Official CPS documentation audit for R3 flows and worker outcomes

Checked against live IPUMS CPS documentation on 2026-09-05. These are source
checks for the implementation; they are not empirical findings.

| implementation choice | official evidence | ruling in this package |
|---|---|---|
| person links | [CPSIDV](https://cps.ipums.org/cps-action/variables/cpsidv) is IPUMS's validated longitudinal identifier. It requires CPSIDP consistency plus stable sex/race and plausible age progression across the 4-8-4 rotation. | Match on nonzero CPSIDV, exact elapsed calendar month, and the required MISH progression. The additional MISH/calendar conditions make the target horizon explicit; they do not replace CPSIDV validation. |
| rotation structure and March files | [IPUMS linking guidance](https://cps.ipums.org/cps/cps_linking_documentation.shtml) documents four interviews, an eight-month break, and four return interviews. It also warns that including both March Basic and ASEC creates duplicate records for March Basic respondents. | Use Basic Monthly samples only; replace the five superseded March files before eligibility is evaluated; never stack March Basic and ASEC. |
| adjacent-month weight | [LNKFW1MWT](https://cps.ipums.org/cps-action/variables/LNKFW1MWT) is the longitudinal weight for two adjacent Basic Monthly samples; zero denotes a person not present in all required months or outside the universe. | Primary adjacent-month estimates require a positive origin LNKFW1MWT. Origin WTFINL and unweighted results are labeled sensitivities, not attrition corrections. |
| same-month adjacent-year weight | [LNKFW1YWT](https://cps.ipums.org/cps-action/variables/LNKFW1YWT) is the longitudinal weight for the same month in adjacent years; zero denotes nonlinkage/out-of-universe status. | Primary twelve-month endpoint estimates require a positive origin LNKFW1YWT and MISH 1–4 to MISH 5–8 progression. They are endpoints, not sums of monthly transitions. |
| validated-link population | IPUMS explains that its longitudinal weights rake the people who link from time 1 to time 2 to characteristics of the population eligible to link at time 1; see [Weighting Linked Datasets](https://cps.ipums.org/cps/cps_linking_documentation.shtml#weighting_linked). | Interpret estimates for the positive-weight linked population and report retention by age, period, MISH, origin state, and exposure quintile. Do not describe it as the full monthly CPS population. |
| weekly earnings | [EARNWEEK](https://cps.ipums.org/cps-action/variables/170007) is an outgoing-rotation current-job measure, has NIU code 9999.99, and directs researchers to use EARNWT. [EARNWT](https://cps.ipums.org/cps-action/variables/EARNWT) applies to earner-study variables and is positive for the relevant outgoing-rotation universe. | Restrict to employed MISH 4/8 records with positive EARNWT and valid positive EARNWEEK; use EARNWT. The result is a cross-sectional conditional weekly-earnings association, not a linked earnings change. |
| usual hours | [UHRSWORKT](https://cps.ipums.org/cps-action/variables/UHRSWORKT) measures usual weekly hours at all jobs; Basic Monthly codes include 997 for varying hours and 999 for NIU. | Require values 1–99 at both adjacent interviews and continued employment. Report a within-person change in hours per week, conditional on remaining employed. |
| unemployment duration | [DURUNEMP](https://cps.ipums.org/cps-action/variables/DURUNEMP) measures consecutive weeks without a job and looking, or continuous layoff duration; 999 is NIU/missing and its universe is people looking for work or on layoff. | Report duration only descriptively among observed employed-to-unemployed endpoints. It is selected on unemployment incidence and is not an at-risk exposure effect. |
| labor-force status | [LABFORCE](https://cps.ipums.org/cps-action/variables/LABFORCE) distinguishes labor-force participants from those outside the labor force; EMPSTAT provides the detailed employed/unemployed/NILF categories. | Estimate employed-origin to NILF transitions. Do not assign a current occupation to nonemployed respondents to manufacture a population exposure regression. |
| October 2025 | Current IPUMS variable pages state that October 2025 data were not collected during the federal shutdown. | Treat October 2025 as absent. An adjacent September-to-November record is never formed; no month is interpolated. |

## Boundaries the documentation does not solve

The official weights do not make linked samples identical to repeated
cross-sections, do not identify employer changes, and do not supply a combined
annual-link/earnings weight for the proposed linked earnings change. The CPS
has no employer identifier in these files. Occupation-cluster, person-cluster,
and household-cluster calculations therefore remain distinct model-based
sensitivity analyses rather than complete replicate-weight CPS inference.
