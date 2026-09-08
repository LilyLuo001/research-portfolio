# Gate 3 mapping-sensitivity results and validation

Status: **authoritative SCC run complete; public reconstruction passed; manuscript integration pending**.

This note records the current-contract execution of `MAPPING_SENSITIVITY_SPEC.md`.
It does not convert post-outcome diagnostics into confirmatory evidence, and it
does not treat an explored grid as an identified set.

## Provenance and execution

- SCC job: `7500525`, completed with exit status zero.
- Repository commit executed: `baeda97a9da64b46ff9dba68344e5e12a21a3959`.
- Analysis support: 468 occupations and 113 observed Basic CPS months.
- Models: 65; paired comparisons: 32; failed fits: 0.
- Inference: 9,999 common occupation and family score-multiplier draws.
- Protected-data rule: the run wrote aggregate outputs only; no microdata row
  or respondent identifier was written to the repository.

The runner reproduced the protected canonical cells to a maximum relative gap
of `3.15e-15`, the pooled coefficient at `-0.1321094508`, and the family-month
coefficient at `-0.0216749520`. The public validator independently reconstructed
all model and paired intervals from the stored influence vectors. Its largest
model-inference gap was `2.78e-16`; its largest paired-inference gap was
`1.11e-16`. It verified all 13 output hashes and all three carry-forward hashes.

## W01: service composition and inherited influence diagnostics

The current-contract local influence diagnostic has an effective contributing
occupation count of 14.54. Fast food and counter workers are the largest local
contributor, with 19.51 percent of squared influence. This is a local
influence-function diagnostic, not an exact leave-one-out estimate.

The exact inherited deletion fits remain materially dispersed. Excluding fast
food and counter workers changes the pooled coefficient from `-0.1321` to
`-0.1110`; the inherited top-five deletion gives `-0.1018`; the inherited
top-ten and top-twenty deletions give `-0.1543` and `-0.1571`. These deletion
sets were fixed by earlier outcome-informed work and are retained only as
diagnostics. Rule-based service exclusions give coefficients from `-0.1204`
to `-0.1388`.

## W02: jointly feasible symmetric bridge tilts

Thirty-one split source occupations are eligible for the tilt and account for
14.86 percent of supported early-period routed stock. For the prespecified
relative young-versus-older high/low allocation-odds grid
`K = {0.25, 0.5, 2/3, 1, 1.5, 2, 4}`:

- pooled, fixed-label coefficients range from `-0.1433` to `-0.1167`;
- pooled, rebuilt-treatment coefficients range from `-0.1446` to `-0.1163`;
- family-month, fixed-label coefficients range from `-0.0748` to `0.0409`;
- family-month, rebuilt-treatment coefficients range from `-0.0783` to
  `0.0439`.

At the two grid endpoints, occupation-clustered paired intervals for changes
from `K=1` contain zero for both the pooled and family-month specifications.
This means the design does not detect a difference at those comparisons; it
does not establish economic equivalence. Rebuilding treatment labels changes
at most two occupations at a grid point.

## W03: explored adverse envelope

The 25-point joint grid preserves each source-age-month routed mass and all
official structural route zeros. Across that finite grid the pooled coefficient
ranges from `-0.1599391` to `-0.0702179`. No outcome-directed optimization was
performed after inspecting the grid. These are extrema of an explored feasible
grid under the stated allocation rule, not sharp or global bounds and not an
identified set for true age-specific routes.

## W04: clean-route and stable-taxonomy alternatives

Removing every current target with a structurally possible inbound one-to-many
route leaves 369 occupations and changes 21 treatment memberships when labels
are rebuilt. The clean-route pooled estimates are `-0.1642` with fixed labels
and `-0.1468` with rebuilt labels; the corresponding family-month estimates are
`-0.0871` and `-0.0524`, with both family-month intervals containing zero.
These are support-changing estimands.

The run also authenticated and carried forward the successful post-2020
current-contract estimates (`-0.1181` pooled; `-0.0304` family-month) and the
earlier stable-Census-2010 estimate (`-0.1522`). The stable-Census-2010 row is
explicitly a different population, taxonomy, exposure map, and label set; it is
not adjacent-vintage validation.

## L02: coding-error feasibility disposition

No authenticated dual-coded CPS validation sample or external symmetric
misclassification matrix is available. Immediate occupation reversals mix real
mobility, proxy response, editing, and coding error, so they were not converted
into an error rate. No arbitrary symmetric-error simulation was fabricated.
The completed bridge-allocation sensitivities are related measurement analyses,
not a validated occupation-code error model.

## Validation and remaining work

The retained `PUBLIC_VALIDATION.json` has status
`PASS_GATE3_MAPPING_PUBLIC_VALIDATION`. The focused mapping suite has 10 passing
tests, including an end-to-end real-file schema contract. W01--W04 and L02
remain `RUN_UNVALIDATED` in the master ledger because their upstream
current-baseline dependencies and manuscript presentation have not yet been
closed together. The computations themselves are complete and no rerun is
currently indicated.
