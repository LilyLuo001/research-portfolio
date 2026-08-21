# PI decision packet: Canaries benchmark — 2026-08-21

## Evidence status

- `0.13` is verified in the August 26, 2025 authored paper (abstract p.1 and
  conclusion p.26) and is the value cited by the registered DAX proposal.
- `0.16` is verified in the official November 13, 2025 revision (abstract p.1
  and conclusion p.16).
- `0.19` has no located authored paper/proposal page, section, table, or exact
  quotation. It is therefore inadmissible under the project's source rule.

## Recommended decision

Freeze **0.13 as the primary benchmark** because it is both primary-source
verified and fixed in the proposal before the design's power result is known.
Register **0.16 as a version-update sensitivity benchmark**. Exclude `0.19`
from the executable standard unless a dated primary locator is later supplied;
if supplied after the primary freeze, report it only as a labeled sensitivity.

This is not the most favorable choice: 0.19 would loosen the pass bar by about
46% relative to 0.13. The recommendation therefore protects the design from a
post hoc adequacy threshold.

## Signature state

`NEED_HUMAN: PI must explicitly sign the 0.13-primary / 0.16-sensitivity
amendment before power_standard.json can be changed or frozen.`

Until that signature, `relative_decline` remains null, `version_status` remains
`UNRESOLVED`, and `adequately_powered` remains null.
