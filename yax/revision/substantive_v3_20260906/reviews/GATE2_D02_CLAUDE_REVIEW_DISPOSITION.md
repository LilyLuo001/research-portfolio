# Disposition of Claude D02 final review

Date: 2026-09-07

## Review verdict received

The byte-preserved external-model review
`GATE2_D02_CLAUDE_FINAL_REVIEW.md` returned
`SAFE_TO_COMMIT_AFTER_LISTED_P2_REPAIRS`: zero P1, one P2, and six P3
findings. It independently upheld the D02 identification conclusion, every
authoritative run/input/code identity, the absence of protected-data access,
and the D02-versus-T04 ledger correction. It expressly found that no SCC rerun
was warranted.

## P2 repair

The retained validation report formerly included the locally observed maximum
cross-BLAS floating-point difference. That value was platform-dependent even
when all recomputed values were within the semantic tolerance, so exact report
equality could falsely fail on a different BLAS implementation.

The validator and retained report now publish only deterministic contract
fields:

- relative and absolute semantic tolerances;
- a fixed maximum-absolute-difference bound of `1e-12`;
- the finite-float comparison count; and
- a derived boolean confirming that the observed difference is within the
  bound.

The platform-specific observed difference is not pinned. A regression test
monkeypatches the recomputation to return the retained authoritative audit—the
same-BLAS zero-difference case—and requires the regenerated validation report
to remain exactly equal to the retained report.

## P3 dispositions

Four hardening items were implemented:

1. The cross-platform semantic check is derived from the comparison count and
   bound rather than assigned a literal `true`.
2. The report labels the saturated-model values as analytic geometry
   identities and states that no full-scale residual matrix was measured.
3. The ledger ownership test explicitly requires T04 evidence and response
   locations to remain empty and its review to remain null.
4. The report states that bounded semantic comparison and byte-exact ledger
   hash verification are distinct checks.

The missing in-receipt Git fields remain a disclosed documentation limitation.
The current run is still bound by exact specification, code, input, output,
result, and receipt hashes; its deterministic outcome-free result was
independently reproduced from public/sanitized inputs. No authoritative run
byte was changed.

## Scope ruling

The repair supports D02 status `RUN_UNVALIDATED` only. It does not validate a
manuscript presentation, estimate an age-specific coefficient, establish
coefficient additivity, or authorize an outcome-bearing companion model.
