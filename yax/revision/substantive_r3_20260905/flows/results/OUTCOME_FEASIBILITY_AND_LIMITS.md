# R3 flow and outcome feasibility

> **POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1**

The package uses official adjacent-month and adjacent-year IPUMS link weights
on stricter validated `CPSIDV` links. Adjacent and annual estimates describe
positive-weight linked populations, not the full monthly CPS population. The
annual endpoint is not a sum of monthly transitions and can miss intervening
jobs and spells. Ages are fixed at origin; annual young origins may be age 26
at the endpoint.

Employment exit is split into unemployment entry and labor-force exit from an
employed origin. This is the only occupation-exposure LFP margin executed:
nonemployed respondents are not assigned a fabricated current occupation.
Unemployment duration is reported descriptively only among selected observed
E-to-U endpoints and is not treated as an at-risk effect.

Usual-hours change is estimated only among workers employed with valid hours
at both adjacent interviews. Weekly earnings use the official `EARNWT` in a
cross-sectional outgoing-rotation sample. No linked annual earnings model is
reported because the available documentation gives separate link and earnings
weights but no validated combined longitudinal-earnings weight.

Occupation-cluster and route-lineage-component intervals describe declared
economic-shock dependence sensitivities. Neither is full CPS complex-survey
inference. Repeated households/persons are disclosed in the receipt. These
variances are not mechanically added to separate household-resampling results.

The CPS has no employer identifier. Entry destination conditions on becoming
employed and occupational outflow need not be an employer change. Therefore
BCC's new-employer-match hiring margin and the CPS stock coefficient cannot be
calibrated from these outputs without additional assumptions; BCC-04 remains
not identified.

Model failures recorded: **0**. They are retained in
`MODEL_FAILURES.json`; no alternative model was selected in response.
