# Independent exact-target implementation review

> Historical review preserved for the pre-correction implementation.  It no
> longer authorizes protected execution after retained job `7474597` exposed
> the zero-weight March boundary error.  The corrected hashes and disposition
> are in `INDEPENDENT_CORRECTION_REVIEW.md`.

Review date: 2026-09-06

Target spec ID: `yaxtargetspec_v1_a72f6e037e1709537683fa9042846d79f8e743eb63af021392f4ad5f86a2a3a5`

Target-spec SHA-256: `6e6fb72755baeaafd7f336e24de2f580c548136f1746d132b35107cc86c92332`

Runner SHA-256: `01ce88a080b816407aeabffc0c8a4e6eac5d950a917138e821cf8c0004616b24`

Test-file SHA-256: `6a679885bfe036187ac379ee7668307e746f1f709f937fead3a9e0e4a21435fe`

Disposition: **PASS for protected execution; empirical T01 remains UNRUN**

The independent terminal review found no remaining P0 or P1 defect. It
recomputed every identifier and byte hash, obtained 34/34 passing tests, and
obtained 7/7 passes on an isolated real-Git adversarial subset. Nonexistent
commits, incorrect trees, unrelated required ancestors, committed-blob
mismatches, consuming-HEAD mismatches, and dirty consuming worktrees all fail
closed; a valid object and matching clean checkout authenticate.

The review also reconfirmed exact producer schema and source maps,
authorization subchecks, code and SCC runtime locks, March-repair identity,
physical-record and route reconciliation, weight-once accounting, refusal of
dangling output symlinks, retention of both one-sided stock configurations,
and the absence of vacuous missing-value comparisons.

The estimand is correctly described as a conditional log mean-stock-ratio
contrast under a frequency-weighted grouped-binomial criterion. The audit does
not relabel it as an observed log ratio, individual employment probability,
hiring rate, or causal AI effect.

No protected data were read in this review. This PASS authorizes running the
audited code; it does not claim that the empirical target audit has already
run or that manuscript/table-note integration is complete.
