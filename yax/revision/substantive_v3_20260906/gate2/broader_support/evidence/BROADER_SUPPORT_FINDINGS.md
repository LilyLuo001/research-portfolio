# S05 broader-beta-support findings

The Webb availability requirement excludes 22 otherwise beta-valid
occupations, accounting for 1.88% of preperiod stock on the broader support.
The analysis separates three movements that the earlier three-model audit had
combined:

| comparison | coefficient movement | 95% paired interval where same-support inference is valid |
|---|---:|---:|
| Remove Webb, fixed 468 support and labels | -0.001676 | [-0.010219, 0.006867] |
| Add 22 occupations, retain primary raw cutoffs | -0.000601 | Descriptive population change; no paired interval |
| Recompute cutoffs, fixed broader support | -0.000458 | [-0.001785, 0.000868] |

The resulting Q5-versus-Q1 coefficients are -0.132109 with Webb on the primary
support, -0.133785 without Webb on that support, -0.134386 after adding the 22
occupations under the original cutoffs, and -0.134845 after recomputing the
broader-support cutoffs. Eight occupations, representing 1.51% of broader
preperiod stock, change quintile under the recomputed cuts.

The auxiliary-control requirement does affect direct-tail support, but only
modestly. Direct Q1-Q5 overlap rises from four occupational families
(`27`, `29`, `31`, `41`) on the primary support to five after removing the Webb
availability requirement; family `43` is newly spanning. Recomputing the cuts
does not add another spanning family. Thus the severe within-family tail-support
deficit is not wholly intrinsic to beta, because Webb availability removes one
spanning family, but it remains severe on the broader beta-valid universe.

All four models reproduce the historical checkpoints where available and pass
same-objective numerical corroboration. The largest scientific-engine versus
independent-reference coefficient-vector difference is
`3.13e-16`; the largest trust-versus-reference treatment-vector difference is
`1.16e-12`, both far below the frozen `1e-6` threshold. The independent public
validator passes all 64 checks.
