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

