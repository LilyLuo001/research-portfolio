# CPS occupation-switching noise audit

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

No treatment-effect regression was run. The preferred feasibility structure is
the adjacent-month `CPSIDV` link. A switch requires employment at both
interviews and different nonmissing modal-harmonized Census-2018 occupation
codes.

| diagnostic | result |
|---|---:|
| matched employed-to-employed pairs | 3,090,795 |
| raw OCC change rate | 6.886% |
| harmonized OCC2010 change rate | 6.573% |
| modal Census-2018 change rate | 6.661% |
| modal switches within same SOC major group | 26.264% |
| immediate A→B→A reversal share | 9.865% |
| 2019-12→2020-01 modal-harmonized change rate | 11.486% |
| other-month modal-harmonized change rate | 6.609% |

The extract contains no same-employer identifier, so the requested
same-employer switch rate cannot be computed. `CLASSWKR` identifies class of
worker, not employer continuity, and is not substituted.

For pre-2020 records, the feasibility-only modal Census bridge selects the
highest-weight 2010→2018 route (stable code-order tie break). This is not the
probabilistic stock routing used by the main YAX estimator and is not approved
for a future treatment regression. The raw-code and OCC2010 comparisons, the
immediate-reversal rate, within-major-group share, and the 2019/2020 boundary
diagnostic jointly show how much apparent switching may be coding noise. No
correction is imposed in Phase 1.
