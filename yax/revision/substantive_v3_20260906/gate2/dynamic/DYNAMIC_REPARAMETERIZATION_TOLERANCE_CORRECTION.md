# Dynamic reparameterization tolerance correction

This pre-object correction closes the execution-blocking P3-A finding in
`reviews/GATE2_DYNAMIC_REPAIR_FINAL_CLAUDE_REVIEW.md`. It was made before any
authoritative dynamic object-bearing execution and does not change an estimand,
sample, model, functional, treatment, reference period, or inferential null.

The superseded preflight used one absolute `1e-12` threshold for three
reparameterization differences: a coefficient target, a restricted covariance,
and an occupation-influence projection. Those quantities are expressed in
coefficient, squared-coefficient, and coefficient units respectively. Applying
one absolute threshold was therefore not invariant to a change in coefficient
units and could falsely block an algebraically correct transformation.

The corrected contract retains each absolute difference as a diagnostic but
divides it by the infinity norm of the corresponding old/new quantity before
applying the signed dimensionless `1e-12` threshold. Exact all-zero pairs have
relative difference zero. The supplied reference-map comparison remains a
separate dimensionless absolute comparison at `1e-12`. No numerical tolerance
has been weakened on the basis of an observed scientific result; the change
only restores unit invariance to a roundoff certification.

Superseded immutable identifiers:

- runner SHA-256:
  `003374bc13f23afa775744dc2f06c2e27efb85cf68df90151d5e6536854f77ec`
- spec ID:
  `yaxgate2dyn_v1_73d2a2bac3e50ab53a116419e63d85d59fdc38a0375d9ea4d0f91324ed06bb62`
- signed-behavior SHA-256:
  `f144dba560a6bbfd0b9a6eb6fa7bcfa7eddffd2ac5e6f56b91be903016779215`

Corrected immutable identifiers:

- runner SHA-256:
  `31d1c8eb3fcb900d6cffa14127662fa872a53bfc54da8030602a61bdf820a116`
- spec ID:
  `yaxgate2dyn_v1_53179466ec9e75d9cc6d9c3a2c71f365da0c89a0dd3c2f29bdf37af95288205e`
- signed-behavior SHA-256:
  `a5252b78dd1b38aa0edd861ef77b1683f84c7d12f4c08e17bb0d384ad6a80686`
- regenerated nonauthoritative preflight artifact SHA-256:
  `167538155d49945c5f7c370eb699d2a95bd44d4b3c755abc43cd91157abb314d`
- regenerated preflight result ID:
  `yaxresult_v1_5ad3882accad3598fc62eb12a8009e4f622294811e361c1db4d3e69173234896`

The focused dynamic suite passes 40 tests. An additional deterministic battery
of 500 independently generated reference changes, coefficient scales from
`1e-12` through `1e12`, covariance objects, influence objects, and restriction
matrices had maximum relative discrepancies of `8.80e-16` (target),
`1.64e-15` (covariance), and `7.90e-16` (influence), all below `1e-12`.
Authoritative object-bearing execution remains blocked on the production
runtime pin and the still-missing bound covariance, influence, common-draw,
design, fitted-probability, and full-parameter objects.
