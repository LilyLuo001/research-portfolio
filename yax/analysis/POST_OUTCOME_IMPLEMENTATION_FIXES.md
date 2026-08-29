# Post-outcome implementation fixes

The protected outcomes were first opened by the command authenticated in
`FIRST_OUTCOME_ACCESS_RECEIPT.json`. Every implementation change after that
opening is recorded here before a confirmatory rerun.

## Fix 1 — conditional-likelihood iteration ceiling

- **Failure time:** 2026-08-29 UTC, first authorized execution.
- **What failed:** the frozen 2017-01 through 2019-12 placebo model reached the
  grouped-binomial solver's default 300-iteration ceiling and returned
  `converged = false`; `run_frozen_v11.py` stopped with
  `RuntimeError: frozen conditional PPML did not converge`.
- **Why implementation, not specification:** the patch changes only the maximum
  allowed Newton/absorption iterations from 300 to 1000. The likelihood,
  convergence tolerance, outcome, sample, treatment, fixed effects, controls,
  scaling, and inference are unchanged.
- **Results seen before the fix:** none. The program writes outputs only after
  all frozen analyses succeed. It printed no coefficient and created no output
  directory before stopping. Intermediate in-memory estimates were discarded
  when the process exited.
- **Exact patch:** pass `max_iterations=1000` to the existing frozen
  `fit_grouped_logit_fe` engine.
- **Rerun rule:** every headline, alternative-X, paired, remote, event-study,
  placebo, extension, and crosswalk model is rerun from the beginning.

## Fix 2 — first ceiling increase remained insufficient

- **Failure time:** 2026-08-29 UTC, complete rerun after Fix 1.
- **What failed:** the same frozen 2017–2019 placebo model reached the amended
  1,000-iteration ceiling without satisfying the unchanged `1e-8` convergence
  tolerance.
- **Results seen before the fix:** none. As in Fix 1, the process printed no
  estimate and wrote no output directory; all intermediate objects vanished on
  exit.
- **Exact patch:** increase only `max_iterations` from 1,000 to 5,000. The
  tolerance, algorithm, likelihood, data and specification remain unchanged.
- **Stopping rule:** if 5,000 iterations do not converge, do not relax the
  tolerance or alter the placebo; report an implementation blocker.

## Fix 3 — separated occupation fixed effects in the placebo window

- **Failure time:** 2026-08-29 UTC, complete rerun after Fix 2.
- **Diagnosis:** the authenticated pre-period cells show that Census-2018
  occupations `3256` and `8335` have positive older employment but exactly zero
  young employment throughout 2017–2019. Two additional frozen clusters have
  no employment observations in that subwindow. Their placebo-window
  occupation fixed effects have no finite maximum-likelihood estimate. Raising
  the iteration ceiling cannot resolve separation.
- **Why implementation, not specification:** a conditional PPML/logit can be
  estimated only on fixed-effect groups with an existing finite likelihood
  solution. The patch applies that mechanical existence rule within the frozen
  placebo window: positive employment stock in both age groups. It does not
  change the dates, variables, equation, controls, or inference. Every excluded
  code is stored in the result.
- **Results seen before the fix:** none. The third attempt again printed no
  coefficient and created no output directory.
- **Exact patch:** before fitting the placebo only, drop occupations with zero
  window-total stock in either age group and record the code list.

## Fix 4 — coverage sensitivities were constrained to Rule-A support

- **Discovery time:** after preserving the first successful output directory.
- **What failed:** Rule B and Rule C returned the exact Rule-A estimates and
  cluster counts because the runner used the authenticated pre-period cell file
  as the universe. That file was deliberately built fail-closed for Rule A and
  therefore contains no occupation that Rules B/C are meant to re-admit.
- **Why implementation, not specification:** the frozen documents require all
  three support rules as separate columns. Starting every column from Rule-A
  support made those frozen sensitivities impossible by construction.
- **Results seen:** the entire first successful output exists permanently at
  `yax/analysis/outcomes/frozen_v11_first_run`; it is never overwritten.
- **Exact patch:** rebuild the complete vintage-aware occupation×age×month cell
  universe from the authenticated raw microdata and frozen Census 2010→2018
  bridge. Before estimation, require the rebuilt Rule-A slice to reproduce the
  frozen pre-period cells to numerical tolerance. Apply each frozen coverage
  rule only after that validation. No outcome, weight, date, mapping, exposure,
  or estimator changes.
- **Corrected output:** write to a new directory,
  `yax/analysis/outcomes/frozen_v11_corrected_run`.

## Fix 5 — result ledger completeness

- **Discovery time:** audit of the preserved first successful output.
- **What failed:** the first ledger contained headline targets, remote targets,
  and paired Delta, but omitted alternative-X control coefficients, event-study
  months, the placebo, crosswalk rows, and the extension Wald object.
- **Why implementation, not specification:** the owner instruction requires a
  ledger of every frozen primary coefficient and diagnostic. Adding already
  frozen results to the ledger changes no estimate.
- **Exact patch:** emit one ledger row for every coefficient/diagnostic above,
  and include the frozen Webb-conditioned AI+computerization+remote model in
  Table 6 so its computerization column is populated.
