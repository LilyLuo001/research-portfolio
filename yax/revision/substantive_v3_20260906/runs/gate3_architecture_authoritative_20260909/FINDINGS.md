# Current-contract non-lambda architecture reconciliation

Status: **post-outcome exploratory; independently recomputed**.

The run fixes the current 113-month young-versus-older CPS outcome contract and
fits five non-lambda definitions on their native finite-score supports. Pooled
categorical Q5-minus-Q1 coefficients range from `-0.09908137` for direct-
ability AIOE to `-0.01447095` for the reversed OECD AI-skills gap. Every native-
support alternative-minus-Rule-A-beta paired occupation interval contains zero;
the closest boundary is the OECD comparison at `0.11870601` with interval
`[-0.00039959, 0.23781161]`. This is nondetection, not equivalence.

The three AIOE implementations are also compared on their common 444-
occupation support. In the family-month specification, administrative/equal-
component AIOE differs from direct-ability AIOE by `0.06884497`; its occupation-
clustered interval `[-0.00702278, 0.14471272]` contains zero, while its family-
clustered interval `[0.00567964, 0.13201030]` does not. Administrative/equal-
component minus source-employment-weighted AIOE is `0.05861565`, with
occupation-clustered interval `[0.01108223, 0.10614907]` and family-clustered
interval `[0.00815271, 0.10907859]`. Thus mapping implementations of one
construct can produce distinguishable conditioned estimates, but the result
does not make different constructs interchangeable or identify a technology.

The execution completed 56 models and 32 paired comparisons with zero failures.
The public validator reconstructed every point and paired interval with maximum
absolute gap zero, verified the fixed Rule-A-beta identity, and authenticated
the retained lambda and primitive carry-forward. Raw AIOE units and current-
support weighted-standard-deviation units are both preserved in the machine
outputs. No protected record or identifier is in this directory.
