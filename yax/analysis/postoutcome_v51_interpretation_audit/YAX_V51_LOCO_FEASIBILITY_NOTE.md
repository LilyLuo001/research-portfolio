# YAX V5.1 leave-one-occupation-out feasibility note

## Recommendation: LOCO-WORTH-OWNER-DECISION

The existing grouped-binomial estimator can be recomputed deterministically after omitting each of the 468 occupations in the primary beta×Webb support. A point-estimate and analytic-SE audit would require 468 otherwise identical model fits after the full stock panel is constructed. Full repeated wild-score reporting would add inference work but is not necessary to learn which omission changes the coefficient most.

Runtime has not been benchmarked under the omission loop, so a precise number would be invented. The defensible planning estimate is **tens of minutes to a few hours on one SCC process**, or substantially less wall time if the 468 independent omissions are batched. The dominant cost is repeated nonlinear fixed-effect fitting, not rebuilding exposure measures.

LOCO would be a new outcome-dependent analysis. It would directly report maximum coefficient change, sign stability, and named influential occupations. Existing residual-treatment support and conditional-information support already show meaningful concentration: the primary prospective residual-treatment effective count is 53.3 occupations, while realized conditional-information support is 43.3 and the top five carry 24.6% of information. Those diagnostics establish concentration but are not deletion influence and cannot show how much the primary coefficient moves when a particular occupation is omitted.

The diagnostic is feasible and could answer a real remaining concentration objection, but it is not authorized by the current interpretation-audit prompt and is not required to interpret the existing F/G result. The owner should decide separately whether a submission-stage influence table justifies reopening the empirically closed program.

**LOCO was not executed.**
