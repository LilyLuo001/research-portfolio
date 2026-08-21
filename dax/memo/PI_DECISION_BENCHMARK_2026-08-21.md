# PI decision packet: Canaries benchmark — 2026-08-21

## Evidence status

- `0.13` is verified in the August 26, 2025 authored paper (abstract p.1 and
  conclusion p.26) and is the value cited by the registered DAX proposal.
- `0.16` is verified in the official November 13, 2025 revision (abstract p.1
  and conclusion p.16).
- `0.19` has no located authored paper/proposal page, section, table, or exact
  quotation. It is therefore inadmissible under the project's source rule.

The full history reconstruction is in
`power_calcs/benchmark_provenance_audit_2026-08-21.md`. It shows that `0.19`
first entered as an unverified search-summary claim and was then intentionally
selected by the PI while its locator remained pending. That establishes the
choice's history, not the claimed estimate's external provenance.

## Options requiring PI decision

### Option A — sourced proposal-vintage primary

Use `0.13` as primary, `0.16` as a prospectively labeled version-update
sensitivity, and exclude `0.19` unless a dated primary locator is supplied.

- **Preregistration:** requires a signed amendment because the prior PI choice
  was 0.19, though 0.13 is the value in the original proposal.
- **Power threshold:** stricter than 0.16 or 0.19.
- **Prior-version comparability:** maximizes comparability to the proposal and
  the authored 2025-08-26 paper.
- **Specification-search risk:** lowest if signed before real power results.
- **Deviation disclosure:** disclose the temporary 0.19 selection and its
  subsequent fail-closed removal.

### Option B — remain unresolved

Keep the executable benchmark null and continue looking for an authenticated
source explaining 0.19.

- **Preregistration:** no benchmark amendment yet.
- **Power threshold:** Gate 1 remains blocked; no adequacy verdict.
- **Prior-version comparability:** preserves the historical PI choice without
  pretending it is sourced.
- **Specification-search risk:** low only if no power-result-dependent choice
  is made later.
- **Deviation disclosure:** disclose the unresolved provenance and delay.

### Option C — historically justified 0.19 PI specification

Retain 0.19 only as an explicit **PI-chosen design target**, not as a verified
Canaries estimate, unless an authored locator is later found.

- **Preregistration:** requires a signed amendment stating that the value is a
  normative power target and not an externally verified empirical estimate.
- **Power threshold:** about 46% looser than 0.13.
- **Prior-version comparability:** preserves the 2026-08-18 PI instruction but
  is not comparable to a sourced paper version.
- **Specification-search risk:** highest; the amendment must document that the
  choice preceded any real outcome/power result and justify the target without
  relying on a nonexistent locator.
- **Deviation disclosure:** disclose the missing empirical provenance and the
  reclassification from reported estimate to PI-set target.

## Signature state

`NEED_HUMAN: PI must choose and sign Option A, B, or C before
power_standard.json can be changed or frozen.`

Until that signature, `relative_decline` remains null, `version_status` remains
`UNRESOLVED`, and `adequately_powered` remains null.
