# Independent review of the T01 March-boundary correction

Review date: 2026-09-06

Disposition: **PASS for a fresh protected cell rebuild and T01 rerun; empirical
T01 remains blocked until that rerun succeeds.**

## Reviewed terminal objects

- Target spec ID:
  `yaxtargetspec_v1_d5c530d22f2e0f18dc73c0106fa5acf3447ab3e7c48f510e5ae55156ba22e70c`
- Target-spec SHA-256:
  `c49ed1861b42d8c521837dba236c6cc91d48667207ae2629a1a2ebee37d459e7`
- Target runner SHA-256:
  `18eb1621f8b119de461c16d7c80bae6c4d36abf03f73b4d147ffdad4e192a1f1`
- Target test SHA-256:
  `04e01a6f565b2c85b136e7f4b8db6a5d75b49df0603ca5375af2ea9be70bff6f`
- Cell-producer test SHA-256:
  `43d6945229de66a45843c6aa80d2122b730df2f6bd62d613c2ef39602f6821b3`
- Retained failure memo SHA-256:
  `f0f241298b18f58dd9b8f8aff3a1f87155a9e69e2b39a7f807ac99a20507ed7b`

The independent reviewer recomputed the target-spec self-ID and every hash
above.  The runner lock and both added March-replacement evidence locks match
their files.  No P0 or P1 defect remains in the correction.

## Boundary and suite evidence

Four focused boundary checks pass: the real-shaped producer fixture reports
zero positive-weight superseded March rows; an unexpected positive-weight row
increments the producer counter; the T01 consumer accepts the authenticated
zero; and it rejects a nonzero value.  The independent producer-plus-target
run passed 56/56 tests with bytecode/cache writes disabled.  The integrating
agent separately ran the complete V3 suite after the correction: 167 tests and
12 subtests passed.  `git diff --check` and Python compilation pass.

The reviewer separately inspected the final producer-test hardening and ran
the affected test plus its historical-parity neighbor (2/2 passed).  The test
now also proves that changing a superseded wide March row to positive weight
increments the audit counter while leaving the normalized output cells exactly
unchanged; explicit replacement still occurs before eligibility and routing.

## Scientific and operational scope

The exact-zero requirement is supported by evidence created before this
failure: the hash-fixed wide source consists of the five relevant March ASEC
samples, all 621,589 superseded rows have `WTFINL=0`, and the separate Basic
source supplies the positive-weight replacement.  The correction changes no
cell value, exposure assignment, sample, calendar, estimator, coefficient, or
interpretation.

Job `7474597` stopped during receipt accounting after hashing, but before
parsing the cell table or estimating a coefficient.  Its failed logs and the
absence of an output leaf remain part of the record.  Because the provenance
contract requires the T01 checkout to equal the producer checkout exactly, the
corrected committed tree must rebuild the cell leaf before T01 is rerun.  The
old receipt must not be restamped.
