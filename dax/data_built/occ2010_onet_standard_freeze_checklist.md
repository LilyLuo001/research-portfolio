# DAX OCC2010/O*NET standard freeze — 2026-08-18

## Decision

The OCC2010/O*NET standard is frozen for downstream implementation. The
approved component coverage gate passes, but the mapping is **not** fully
resolved. Mapped mass is 96.38887378%; fully resolved mass is 77.16899944%,
and another 19.21987433% is bounded provisional mass.

No W3/W5 production dose constructor exists in the repository at this freeze.
`dax/w2/crosswalk/dose_bounds.py` therefore defines the mandatory adapter and
fail-closed contract that the future constructor must use.

## Independently reproduced data audit

| Check | Result |
|---|---:|
| Crosswalk rows | 1,287 |
| CPS OCC2010 codes | 503 |
| Per-code weight sums outside tolerance | 0 |
| Whole-code status inconsistencies | 0 |
| Whole-code eligibility violations | 0 |
| Fully resolved component mass | 0.7716899944 |
| Bounded provisional component mass | 0.1921987433 |
| Mapped component mass | 0.9638887378 |
| Unresolved component mass | 0.0344065283 |
| Absent component mass | 0.0017047339 |
| Largest unresolved occupation contribution | 0.0044745164 (5940) |
| Coverage gate | PASS |

The observed preperiod whole-code point-eligible mass is 0.6536133662. Only
`resolved_employment_weighted` whole CPS codes are eligible for an unbounded
point estimate: 361 of 503 crosswalk codes, including 318 of 445 observed
preperiod codes. Partially unresolved codes remain ineligible even when most
of their component mass maps successfully.

OCC2010 7630 is observed but absent from the official crosswalk. It remains
fail-closed and has no point estimate or bounded provisional dose.

## Hash, lineage, and permission checks

| Private artifact | SHA256 | Mode |
|---|---|---:|
| Repaired detailed crosswalk | `eb68890bcfb31855d6a8f0704aab022c13c842d09e01eb57acd94e28dac4ddeb` | `0600` |
| Legacy fallback rows | `ee7d339465bea8c9e31982f3932c931080251ce144219d98f586a8adb803ca66` | `0600` |
| Occupation-level gap audit | `cbce29635b163def2f990aee36153304a34f1bf810cd806a49a3365fc48a8236` | `0600` |
| Preperiod CPS cells | `742ba1f94be7ee7a3ab5db63f1f929c35b97e297c8ec6b1084e2511202821b2a` | `0600` |

The private preperiod output directory was tightened to `0700`. Two detailed
W2 inputs (`onet_timeshares.csv` and `oews_wages.csv`) were also tightened from
`0644` to `0600`. The private detailed crosswalk, legacy fallback, and gap
audit hashes exactly match the handoff values.

The legacy fallback audit reproduced 908 rows, 41 O*NET-SOC 2019 targets, and
4 equal-source-mix targets. All task-profile shares, source weights, and final
fallback shares sum to one; every legacy row requires bounds.

## Frozen rules

- `mapped = fully resolved + bounded provisional`; mapped must never be called
  fully resolved.
- Equal SOC/O*NET weights and equal legacy-source weights are diagnostic
  centers only.
- Every provisional dose carries minimum and maximum values across all
  officially linked children or legacy source profiles.
- Only a whole CPS code with status `resolved_employment_weighted` can expose
  an unbounded point estimate.
- Unresolved, partially unresolved, and absent codes fail closed.
- A resolved code presented with any bounded O*NET input fails validation.

## Enforcement and hygiene checklist

- [x] Independent component and whole-code mass recomputation matches receipts.
- [x] All 503 crosswalk code weights sum to one within `1e-9`.
- [x] Output hashes match the sanitized build receipts and handoff values.
- [x] Private artifact modes are owner-only.
- [x] All eligibility flags obey the stricter whole-CPS-code rule.
- [x] OCC2010 7630 is explicitly absent and fail-closed.
- [x] Provisional SOC, O*NET-child, and legacy-source bounds have executable tests.
- [x] Restricted-data Git hygiene scan reports zero tracked row-level artifacts.
- [x] Focused crosswalk/freeze tests: 16 passed.
- [x] Full DAX regression suite: 93 passed.
- [x] No API key, token, raw respondent/outcome row, detailed crosswalk row,
  legacy fallback row, or occupation-level gap row is included in this freeze.

Machine-readable evidence is in
`dax/data_raw/occ2010_onet_standard_freeze_receipt.json`.
