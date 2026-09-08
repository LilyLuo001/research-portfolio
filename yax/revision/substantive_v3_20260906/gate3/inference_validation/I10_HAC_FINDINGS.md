# I10 elapsed-calendar HAC findings

Status: **VERIFIED**

The same pooled and family-month coefficients were refit from the authenticated
Gate 2 aggregate cells and matched their certified checkpoints. The covariance
uses occupation meat plus Bartlett HAC of aggregate calendar-month influence
minus the sum of within-occupation Bartlett HACs. December 2022 and October
2025 are represented by zero-score placeholders, so positive lags measure
elapsed calendar time rather than adjacency in the observed array. Pooled and
family-month score objects are stacked before covariance construction, which
retains the cross-model blocks needed for the paired movement.

| Elapsed-month bandwidth | Pooled SE | Family-month SE | Paired-movement SE | Paired 95% interval |
|---:|---:|---:|---:|---:|
| 0 | 0.0456 | 0.0703 | 0.0519 | [0.0087, 0.2122] |
| 1 | 0.0459 | 0.0688 | 0.0517 | [0.0091, 0.2118] |
| 4 | 0.0457 | 0.0637 | 0.0505 | [0.0114, 0.2094] |
| 12 | 0.0450 | 0.0574 | 0.0478 | [0.0167, 0.2041] |
| 16 | 0.0445 | 0.0552 | 0.0450 | [0.0222, 0.1986] |

The estimate is -0.1321 in the pooled model, -0.0217 in the family-month
model, and 0.1104 for family-month minus pooled. Across all five bandwidths,
the pooled normal interval excludes zero, the family-month interval includes
zero, and the covariance-preserving paired-movement interval excludes zero.

Every unmodified 10-by-10 covariance is symmetric to machine precision, full
rank under the declared scaled tolerance, and positive definite. Minimum
eigenvalues range from 0.000015 to 0.000027. No eigenvalue clipping or PSD
projection was applied. The independent validator reconstructed all matrices
from the public long-form covariance, recomputed spectra and target variances,
and recovered every standard error and interval.

This is a same-target serial/cross-sectional covariance sensitivity. It does
not establish that one bandwidth is uniquely correct and does not replace the
finite-sample coverage exercise.

## Evidence

- Pre-execution specification: `HAC_VALIDATION_SPEC.md`
- Code: `run_hac_validation.py` and `validate_hac_outputs.py`
- Public run: `runs/gate3_hac_authoritative_20260908/`
- Independent validation: `INDEPENDENT_VALIDATION.json`
