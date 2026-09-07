# Gate 2 authoritative support/accounting artifact review

Date: 2026-09-07

Reviewed run: `gate2_support_accounting_authoritative_20260907`

Review type: read-only artifact challenge by a separate agent on the execution
team. It is independent of the implementation task, but is not represented as
external scientific peer review.

## Verdict

No P1 or P2 finding. The core 13-file runner package passes. One P3 packaging
caveat was corrected after review: two later-authored validation documents were
relocated from the immutable run directory to `gate2/evidence/`. The run
directory now contains exactly the execution receipt and the 12 artifacts
covered by its output hashes and result IDs.

## Independently recomputed checks

- The specification ID, specification SHA-256, and runner SHA-256 reproduce.
- All 12 output hashes and all 12 result IDs reproduce exactly.
- The support matrix has 110 unique family-quintile cells, 468 occupations, 72
  supported cells, and occupation quintile counts of 129, 99, 82, 67, and 91.
- National, within-family, and within-quintile shares close to one on their
  stated denominators.
- All 89 family-specific edges reproduce; all ten quintile pairs occur; the
  five-node topology is connected with incidence rank four. This is support
  topology only, not regression estimability.
- Direct-tail support is exactly 29 unique occupations in families 27, 29, 31,
  and 41. Names, quintiles, exposure values, and both share definitions match
  the fixed membership and their declared denominators.
- The calendar contains 71 preperiod and 42 postperiod months. December 2022 is
  excluded from the accounting and October 2025 is absent. Period means
  reproduce within `2.33e-10`.
- `D_young=-0.10978431433527074`,
  `D_older=0.04833052969506634`, and
  `D_relative=-0.15811484403033707`; the stored identity residual is
  `-2.50e-16`.
- Level closures are approximately `1.5e-18` for Q1, `-8.7e-19` for Q5, and
  `-3.47e-18` for Q5 minus Q1.
- All eight log-Shapley hybrids per tail are strictly positive. Independently
  recomputed components and endpoints agree within `4.44e-16`; stored closure
  is zero.
- All 88 family-tail-period cells reproduce as 52 `VALID_POSITIVE` and 36
  `STRUCTURAL_ABSENCE`, with no undefined active ratio or omitted boundary
  mass.
- No private paths, credentials, API tokens, person/household identifiers, or
  occupation-month cell table are present.
- The receipt accurately states that the aggregate was opened, row-level
  microdata were not opened, and no inference was run. This statement is
  supported by code scope and authenticated inputs, not an operating-system
  access audit.

The focused implementation-plus-artifact test suite reported 15 passing tests
at review time.

## Scope

This review validates the aggregate artifact package, not sampling inference,
regression estimability from graph topology, or manuscript presentation. S01,
S02, D01, D03, and D04 must remain `RUN_UNVALIDATED` until their outstanding
presentation/inference dependencies are closed.
