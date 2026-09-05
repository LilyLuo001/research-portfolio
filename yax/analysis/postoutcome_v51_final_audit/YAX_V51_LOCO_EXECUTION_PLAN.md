# YAX V5.1 final LOCO execution plan

**POST-OUTCOME INFLUENCE AUDIT. COMMITTED BEFORE THE DELETE-ONE REFITS.**

Exactly two coefficient-influence loops are authorized.

1. The confirmatory primary Eloundou-beta-by-Webb Q5-versus-Q1 coefficient on its frozen 468-occupation support.
2. The exploratory G coefficient from the already-executed joint continuous F+G+Webb model on its frozen 444-occupation support.

For each target, the implementation first constructs the full-sample outcome arrays and regressor matrix exactly once and reproduces the sealed full estimate. It then deletes occupations in lexicographically sorted Census-2018 code order. Each refit deletes the corresponding occupation row from the outcome arrays and the corresponding occupation-month block from the already-frozen regressor matrix. It does not reconstruct exposure scores, quintiles, quintile membership, F, G, Webb, standardization constants, age groups, post months, or fixed-effect structure.

Each deletion records only the point coefficient, its signed and absolute movement from the sealed full estimate, relative absolute movement, and the deleted occupation's frozen full-sample stock weight. No deletion-specific bootstrap or p-value is computed. No preferred model is selected and no occupation is removed from the reported headline.

The implementation must refuse to run unless the authenticated frozen inputs reproduce:

- primary full estimate `-0.13107397642233506` on 468 occupations;
- G full estimate `0.030893508600474132` on 444 occupations;
- literal common-support hash `1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462`;
- protected design and confirmatory tags at their recorded peeled commits.

No direct A/E model, leave-one-measure outcome model, new multiplier draw, alternative treatment, or other labor-outcome analysis is authorized.
