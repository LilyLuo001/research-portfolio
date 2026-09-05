# YAX major mobility revision: analysis specification before results

> **POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1**

This specification was written before the new RR1-M11 / RR2-M8 computations
in this directory.  It does not alter the frozen employment-stock design or
replace the earlier Phase-2/Phase-3 mobility record.

## 1. Fixed inputs and sample

The analysis will rebuild the existing adjacent-month, employed-to-employed
switch frame from the authenticated wide CPS file and longitudinal-weight
patch on SCC.  It will retain the prior six-architecture common support,
official origin `LNKFW1MWT`, age groups, calendar exclusions, exposure maps,
and Phase-3 broad-family strata.  No raw or respondent-identifying record will
be written to the repository.

The six architectures comprise three AIOE implementations and the three task
shares alpha, beta, and broad (gamma).  A directional conflict requires one
strictly positive and one strictly negative occupation-score movement; exact
zeros remain ties.

## 2. Family-balanced disagreement

For every unordered pair, report official-weight conflict as (i) a share of
all switches on six-way common support and (ii) conditional on both movements
being nonzero.  Report the full symmetric six-by-six matrix.  Then average
pairs separately in three conceptual blocks: within AIOE, within task shares,
and between the two families.  The reported family-balanced scalar gives each
of those three blocks weight one third, rather than allowing the nine
between-family pairs to receive three times the weight of either three-pair
within-family block.  This is a declared descriptive normalization, not a
unique welfare metric.

Verify the task-family identity on raw occupation scores.  Because

`Delta beta = (Delta alpha + Delta broad) / 2`,

beta must share their sign whenever the alpha and broad endpoint movements
have the same strict sign.  Positive affine standardization cannot change
this implication.  Report any numerical or classification violations.

## 3. Exact represented support and bounds

Reconstruct the 200,000-unit Hamilton pseudo-population used by the sealed
hard benchmark.  Mark the detailed age x month x broad-origin x
broad-destination x detailed-origin x detailed-destination cells receiving at
least one pseudo-unit.  Recalculate the realized conflict rate on exactly
those cells, and compare it with the sealed no-self benchmark mean.

Let `s` be the represented official-weight share, `r_all` the observed
all-support realized rate, `r_rep` the represented-support realized rate, and
`b_rep` the represented-support benchmark.  Report:

- the conditional gap `r_rep - b_rep`;
- the all-support benchmark range
  `[s*b_rep, s*b_rep + (1-s)]` when omitted-support benchmark conflict is only
  bounded in `[0,1]`;
- the corresponding all-support gap range
  `[r_all - s*b_rep - (1-s), r_all - s*b_rep]`.

These are worst-case omitted-support bounds, not equivalence intervals.

## 4. Sampling uncertainty and Monte Carlo uncertainty

Use an SCC-only household-cluster multiplier bootstrap.  `CPSID` defines the
household cluster and preserves all transitions belonging to that household.
Draw 399 independent mean-one exponential cluster multipliers with seed
`2026090511`.  In every replicate, recompute the represented-support realized
rate and a 50,000-unit plug-in no-self benchmark from the reweighted detailed
cells.  Use five rematches per replicate and the original sequential repair.
The gap is recomputed within each replicate.  Percentile intervals and the
replicate standard deviations describe this declared empirical household-
cluster sampling model; they are not CPS replicate-weight or full complex-
survey inference.

Within-replicate rematch variance divided by five will be reported separately
as simulation noise.  A variance-subtracted gap SE,
`sqrt(max(var(gap replicate means) - mean(within variance)/5, 0))`, is the
primary sampling diagnostic.  The sealed 999-draw benchmark SD and its
standard error of the mean remain the canonical numerical Monte Carlo
diagnostic for the reported benchmark.  No simulation SE will be mislabeled
as sampling uncertainty.

If computational failures make the nested procedure unusable, the fallback is
a household-cluster multiplier bootstrap of realized conflict with the sealed
benchmark held fixed, labeled explicitly as conditional on observed benchmark
margins.  The fallback cannot be presented as unconditional gap uncertainty.

## 5. No-self algorithm sensitivity

Document the existing algorithm: a uniform random destination permutation
within every hard stratum, followed by first-bad-position feasible random
swaps, with a fresh permutation after an impasse.  This preserves detailed
origin and destination margins and eliminates self transitions, but it is not
a uniform draw over feasible derangements.

Run one alternative valid repair: after the same random permutation, choose a
bad position uniformly at random and then a feasible swap partner uniformly
at random, restarting after an impasse.  Use 999 draws and seed `2026090512`
on the same 200,000-unit pseudo-population.  Compare means and Monte Carlo
intervals; do not select between rules based on the result.

## 6. Entry and coding-instability interpretation

Surface the already executed Phase-2 official-weight entry-destination result
and its authenticated provenance.  It is the allocation of observed entrants
across destination occupations, conditional on a linked nonemployed origin
becoming employed.  It is not an employment-finding probability, and the
existing switch frame still cannot answer the hiring-risk question.

Do not interpret the immediate A-B-A reversal share as an occupation-coding
error rate.  A stock-coefficient misclassification correction will be adopted
only if the data identify or externally validate a latent-code error matrix.
Otherwise the output will record principled non-adoption: arbitrary symmetric
error scenarios do not identify attenuation in a five-category,
occupation-level treatment and can attenuate, amplify, or reassign the Q5-Q1
contrast depending on the unknown matrix.

## 7. Fixed outputs and checks

The program will write only aggregate files under `results/`:

- `FAMILY_BALANCED_PAIRWISE_DISAGREEMENT.csv`
- `TASK_ENDPOINT_IDENTITY.json`
- `HARD_SUPPORT_RECONCILIATION.json`
- `HARD_SUPPORT_CELL_SUMMARY.csv`
- `HOUSEHOLD_CLUSTER_BOOTSTRAP.json`
- `HOUSEHOLD_CLUSTER_BOOTSTRAP_DRAWS.csv`
- `REMATCH_RULE_SENSITIVITY.json`
- `REMATCH_RULE_DRAWS.csv`
- `ENTRY_DESTINATION_EVIDENCE.json`
- `CODING_INSTABILITY_DECISION.json`
- `EXECUTION_RECEIPT.json`

`selfcheck.py` must verify the task identity, support accounting and bounds,
margin preservation/no self under both repair rules, bootstrap decomposition,
entry labels, input/output hashes, and absence of microdata or identifiers in
committed outputs.
