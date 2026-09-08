# Gate 2 timing-extension failed execution 7490271

- Executed commit: `ba3d2457f59cb8aa98c36646edac58a9a147c707`
- Scheduler job: `7490271`
- Queue/host: `academic-pub` / `scc-gf3.scc.bu.edu`
- Scheduler state: `failed=0`, `exit_status=1`
- Wall time: 109 seconds
- Maximum virtual memory: 2.926 GB
- Scientific result published: **no**

The run completed the first two full-support fits and reached the coding-stable
post-2020 fit. That window has 457 occupations with at least one positive
estimating row within the frozen 468-occupation support. The estimator and its
finite-cluster covariance were computed correctly, but the new inference
wrapper attempted to multiply the 468-column common-draw matrix by the
457-element active-cluster influence vector and stopped on the dimension
mismatch. The runner creates its output directory only after every fit and
validation check passes, so no result package was published.

The repair retains the fixed 468-occupation support and common-draw order,
applies each model's own finite-cluster correction to its influence values, and
then aligns those values to the 468-occupation universe with zero influence for
support occupations having no positive estimating row in that model. A
regression test verifies that this alignment preserves the model covariance.
No treatment, outcome, sample window, objective, solver, or numerical threshold
changed.

The repaired runner was committed at
`4b298853f439fda1577a14f7dc598f7832f54466` and executed as fresh SCC job
`7490289`. That job exited with scheduler `failed=0`, `exit_status=0` and
published the complete 34-model package. The failed job and this diagnosis
remain preserved rather than being overwritten by the successful rerun.
