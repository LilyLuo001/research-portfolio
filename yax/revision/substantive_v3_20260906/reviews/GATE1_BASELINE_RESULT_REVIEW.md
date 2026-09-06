# Gate 1 baseline result review

Review date: 2026-09-06 UTC

Review scope: committed, sanitized Gate 1 artifacts only

Reviewer: separate challenge agent, independent of the implementation task but
within the same execution team

Protected data read: none

## Verdict

No coefficient, arithmetic, support, assignment, or published-hash failure was
found. Requirement T02 must nevertheless remain `RUN_UNVALIDATED`. The public
artifact set does not satisfy every item in V3 section 6.1 and the required
manuscript/appendix presentation does not yet exist.

## Independently reproduced checks

- Canonical V2 byte hash and content-derived specification identifier.
- The sanitized wrapper receipt; all 16 published result hashes; all six audit
  hashes; the duplicated sanitized receipt; and the locked runner, wrapper,
  specification, self-check, and transitive source hashes.
- All three result-ledger identifiers, selectors, and values.
- Pooled coefficients of `-0.1310739764223351`,
  `-0.1345539535732939`, and `-0.13210945079219036`.
- Every scalar confidence-interval identity and both paired-difference
  identities. The sample standard deviations, critical values, p-values, and
  intervals recompute from the 9,999 stored centered draws. The implied
  common-draw correlations are 0.998815 and 0.998794.
- The 468-occupation support, support hash, fixed-membership hash, total
  preperiod stock, beta/Webb normalizations, tie-preserving cuts, quintiles,
  and quintile aggregates.
- Exactly nine changed occupations: 0845, 1350, 3620, 3655, 3710, 4461, 4500,
  5410, and 8730. The support itself is unchanged.
- Calendar arithmetic: 115 nominal months, 114 observed after the missing
  October 2025 file, 113 static months after excluding December 2022, and 71
  preperiod months from January 2017 through November 2022.

## Unresolved validation gaps

1. The canonical V2 contract declares ages 22--65 and six raw variables. The
   delegated historical builder first ingests ages 18--65 and also reads
   `OCC2010` and `IND1990`. Later code drops ages 18--21, does not use the
   stable/industry branches for this target, and fits the declared age groups,
   so the review found no demonstrated coefficient contamination. The literal
   upstream contract and executed builder nevertheless differ.
2. V3 section 6.1 also requires the family-month checkpoint near `-0.0217`.
   The present Gate 1 package contains only the three pooled rows.
3. The sanitized package omits the delegated runner's fresh cell-build
   counters. Source rows, eligible records, expanded/routed rows, fractional
   contributions, and one-time weight application therefore cannot be traced
   independently from the public artifacts.
4. The centered paired draws are consistent with the declared common
   Rademacher design, but the component influence vectors are absent. The
   public package cannot independently prove each vector equals common signs
   times the left-minus-right influence difference.
5. The 2025--2026 population-control, file, and identifier changes have not
   been independently documented here.
6. The T02 presentation role remains absent from the manuscript and appendix.

The new V3 six-field cell builder is intended to repair gaps 1 and 3 for
subsequent runs. It does not retroactively change the provenance of the
already executed historical reconstruction.
