# One concentrated validation repair

The historical failed implementation remains unchanged. The new wrapper reuses its projection but replaces input validation with exact rational principal-minor tests of the represented 4x4 binary floating-point matrix. Symmetry is exact; all fifteen principal minors must be nonnegative. There is no clipping, symmetrization or implicit nearest-PSD repair. Slight numerical indefiniteness is rejected even when its origin might be rounding. This can reject an intended singular Gram matrix after floating-point multiplication: callers must not interpret rejection as evidence against the scientific model, and cannot silently change the matrix.

This narrow change fixes the specific accepted-indefinite and accepted-asymmetric-input failures without inventing an empirical covariance policy. The box remains conservative conditional on a valid supplied simultaneous region and nonzero true denominators. Its off-diagonals do not tighten endpoints; exact Fieller-difference inversion is not implemented. Critical-value and actual issuer/date dependence calibration remain absent.

Coordinator fixed regression checks: seven pass under warnings-as-errors. Independent review is required before claiming implementation acceptance. No empirical inference is enabled by these tests.
