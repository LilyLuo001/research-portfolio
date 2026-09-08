# I01 stochastic-target verification

Status: **VERIFIED**

The Gate 3 implementation keeps four uncertainty objects distinct:

1. occupation-cluster wild-score inference for occupation-level economic
   shocks;
2. SOC2-family wild-score inference as a broad-family shock sensitivity;
3. linked-household mean-one multiplier full refits as a released-weight
   repeated-sample sensitivity; and
4. regenerated pre-period labels within the household refits as a limited
   construction-uncertainty sensitivity.

No code path mechanically adds these variances. Occupation and family
procedures are alternative reference distributions. Household results are
reported separately because the public extract lacks the variables required
for CPS design-based inference.

For pooled, family-month, and their movement, the same simulated outcome draw
is used. The paired influence is formed by subtracting model influences before
applying a common multiplier matrix. Rademacher and Webb draws are each drawn
once per cluster level and reused for both models and the paired target. Unit
tests verify the direct covariance identity and reject variance addition.

The simulation target is each fitted projection's analytic-DGP-mean
coefficient, not automatically the structural shock coefficient. The
household target is repeated-sample sensitivity conditional on the released
weights and linked positive CPSID approximation. The HAC target is a separate
same-coefficient covariance sensitivity. These statements match the V3
instruction's required stochastic-target distinctions.
