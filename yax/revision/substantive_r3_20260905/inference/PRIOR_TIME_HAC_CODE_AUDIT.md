# Audit of the prior time-HAC implementation

The submitted implementation in `yax/revision/referee_round2_20260905/precision_rotation/run_precision_rotation.py` constructs occupation-cluster meat, Newey--West meat of aggregate month scores, and a cell meat. It then uses `occ_meat + time_meat - cell_meat` at every requested lag.

That subtraction is an exact overlap correction only at lag zero (up to the implementation's differing finite-cluster factors). At positive lags, occupation clustering already contains same-occupation cross-month covariance, while the aggregate-month HAC adds the same same-occupation covariance again. Subtracting only contemporaneous cell meat leaves the positive-lag within-occupation overlap double counted.

The prior code also indexes the retained month rows consecutively. Consequently, missing calendar months are treated as adjacent: for example, September and November 2025 are one retained-row lag apart although two calendar months elapsed. The R3 implementation uses a complete calendar grid with zero-contribution placeholders for absent/excluded months and subtracts `sum_o HAC_L(psi[o,t])` at the same elapsed-calendar lags.

This is an implementation correction, not evidence that the new standard errors must be larger or smaller. The sign and magnitude are determined only by the rerun.

