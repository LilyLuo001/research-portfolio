# Equal-occupation objective sensitivity

Status: **post-outcome exploratory; independently recomputed**.

The employment-stock-weighted baseline reproduces the current 468-occupation
contract: `-0.13210945` pooled and `-0.02167495` with family-by-month effects.
Giving each occupation total weight one, while retaining `WTFINL` to construct
young and older shares within occupation-month cells, changes the coefficients
to `-0.08326945` and `-0.00469279`.

The equal-occupation-minus-stock-weighted paired differences are `0.04884000`
with occupation-clustered 95-percent interval `[-0.06038873, 0.15806872]` for
the pooled model and `0.01698216` with interval
`[-0.15870972, 0.19267405]` for the family-month model. Both intervals contain
zero. The design therefore does not detect a difference between the two
objectives; it does not establish economic equivalence.

All four models and both paired comparisons use 9,999 common score-multiplier
draws. The public validator independently reconstructed every model and paired
interval with maximum absolute gap zero. No protected record or identifier is
in this directory.
