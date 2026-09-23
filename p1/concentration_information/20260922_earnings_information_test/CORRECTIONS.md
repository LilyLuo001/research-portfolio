# Engineering corrections

## 2026-09-23: equal event mass under incomplete event/control support

The original model fitter used issuer → event → row weights. When an event had
only one usable EVENT/CONTROL sample while another had two, the latter received
twice the total event mass. This is a model-affecting error, not a reporting
issue.

The corrected fitter uses issuer → event → available sample within event → row.
It writes new SCC-only `model_parts_v2/` artifacts and leaves the original
`model_parts/` unchanged. It also writes fold-specific sample support and
event-weight masses, plus a finite two-event check where one event has two
samples and the other one; both must receive 0.5 mass.

The same pre-start correction fixes rest-basket coverage: the observed
weighted rest mean remains normalized over source-supported stocks, but its
coverage denominator is now the fixed approved rest-of-22 from the inherited
23-stock roster (excluding BF and the issuer), not the symbols that happened
to be present in a sample. Thus an entirely absent basket member lowers
coverage rather than disappearing from its denominator.

## 2026-09-23: path baseline, coverage, and persistence

The original path summary used the anchor grid (`t=0`) as the response
baseline, and silently omitted unavailable symbol/venue panels. The corrected
summary retains `t=0` as a labelled reference and computes responses from the
fixed `t=-1s` grid. It does not back-search for an earlier valid quote or
impute a target endpoint.

The corrected `PATH_COVERAGE.csv` separates all intended path cells from
missing source panels and invalid baseline/endpoint cells. Persistence now
reports nonzero same-direction comparisons separately from zero-to-zero paths.

## 2026-09-23: support counting and grid-boundary audit

The prior support table summed identical target centers across models,
comparisons, fit specifications, grids, and horizons. The corrected table is
deduplicated and reported per venue/grid/horizon/window/scoring cell.

For the 500ms grid, actual centers are offset by 500ms, but strict predictor
and target membership selects the same integer second-index sets at the stated
window boundaries. No model rerun is required for that boundary audit; the
weight correction independently requires all four cells to be rerun.

## 2026-09-23: scheduler duplicate cancellation

Corrected rerun array `7701966.1-4` was submitted, then erroneously submitted
again while it remained queued and had not yet created output artifacts.
`7701966` was cancelled before execution. Only `7701972.1-4` remains the
authorized corrected run targeting `model_parts_v2/`. Absence of artifacts is
not a retry condition; future status checks use `qstat`/`qacct` first.

## 2026-09-23: final-figure cache repair

Final-only job `7701989` passed the four-cell receipt/hash guard and completed
the corrected SCC model summary, but exited 1 before figures because
Matplotlib attempted to create its font cache in a quota-limited default
location (`OSError: [Errno 122] Disk quota exceeded`). No model fit failed or
was rerun. The repaired final-only job uses a unique job-local `MPLCONFIGDIR`
under `/tmp`. The first cache repair (`7702038`) still inherited a
quota-limited compute-node `TMPDIR`; the second and final repair pins the
cache path to `/tmp` explicitly, and also corrects the three figure filters to
TEST EVENT cells (and preserves venue/grid issuer sensitivity).
