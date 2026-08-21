# PI decision memo: DAX benchmark interpretation and value — 2026-08-21

**Decision state:** `NEED_HUMAN — UNSIGNED`. This memo does not change
`power_calcs/power_standard.json`, run power, or authorize a force override.

## Evidence that is currently supportable

| Value | Supportable statement | Unsupported statement |
|---:|---|---|
| `0.19` | It was an intentional PI design specification adopted in repository history while its locator was marked pending. | That it is an authenticated empirical estimate from a particular authored paper, version, sample, or table. External provenance remains unknown. |
| `0.13` | It is the sourced August 26, 2025 external estimate: a 13% relative employment decline for workers ages 22–25 in the most AI-exposed occupations, using ADP payroll data. | That it estimates the same parameter as the DAX continuous dose coefficient. |
| `0.16` | It is the sourced November 13, 2025 revision of the headline young-worker/high-exposure relative-employment estimate. | That a later revision automatically supersedes the proposal vintage for DAX design purposes. |

Primary locators and repository chronology are preserved in
`power_calcs/benchmark_provenance_audit_2026-08-21.md`. The DAX exposure,
outcome data, time window, comparison, and treatment scale differ from the
external paper, so 0.13 and 0.16 are effect-size scales rather than directly
transportable causal coefficients.

## Interpretation decision must precede the value decision

### Frame E — external empirical effect-size scale

Under this frame, the benchmark represents a dated, authored estimate from
outside DAX. A primary locator and explicit comparability caveat are required.

- `0.13` preserves the August 2025/proposal-vintage external result.
- `0.16` uses the sourced November 2025 revision and requires disclosing the
  version change.
- `0.19` is inadmissible under this frame unless an authenticated primary
  locator and estimand are later recovered.

Scientific consequence: power adequacy is compared with an observed external
effect-size scale, but not with the exact DAX estimand. Version selection must
be frozen prospectively to prevent choosing whichever value makes power pass.

### Frame N — normative PI design target

Under this frame, the benchmark is a minimum effect magnitude the PI considers
scientifically worthwhile to detect. It need not equal a published estimate,
but must not be represented as one.

- `0.19` can be retained only as an explicitly normative PI target with its
  unresolved external provenance disclosed.
- `0.13`, `0.16`, or another signed value can also be normative targets, but
  their sourced empirical origins do not make them the DAX estimand.

Scientific consequence: power addresses the PI's minimum worthwhile effect,
not replication of an external estimate. A larger target is easier to detect,
so the rationale must be substantive and recorded before the power run. The
report must separate normative adequacy from sensitivity to sourced empirical
scales.

### Frame U — remain unresolved

No value becomes executable. Source investigation and upstream work may
continue, but the real power verdict remains blocked.

## Consequences of the numerical choice

- Relative to 0.13, 0.16 is about 23% larger and 0.19 about 46% larger.
- Holding design/noise fixed, larger target magnitudes are mechanically easier
  to detect. This is not scientific evidence for selecting them.
- Selecting 0.13 under Frame E preserves the original authored/proposal
  vintage; selecting 0.16 under Frame E uses the later sourced revision.
- Selecting 0.19 under Frame N preserves the historical PI choice while
  correcting its interpretation; it requires a preregistration deviation that
  says it is normative and externally unsourced.
- Leaving the benchmark unresolved avoids premature specification but blocks
  an executable power gate.

## PI decision form — benchmark interpretation/value

1. Interpretation frame: external empirical scale (`E`) / normative PI target
   (`N`) / remain unresolved (`U`): ____
2. If `E`, source vintage: August 2025 `0.13` / November 2025 `0.16` / other
   authenticated source with locator: ____
3. If `N`, signed target value and substantive minimum-worthwhile-effect
   rationale: ____
4. Required sensitivities, stated prospectively: `0.13` / `0.16` / `0.19` /
   other: ____
5. Required deviation/comparability wording approved: YES / NO / REVISE
6. Authorize a separate commit to update the executable standard only after
   this form is signed: YES / NO
7. PI name/signature/date: ____

Until signed, `power_standard.json` remains unchanged and the executable
benchmark remains `UNRESOLVED`.
