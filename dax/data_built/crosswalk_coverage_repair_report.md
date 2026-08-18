# DAX OCC2010/O*NET coverage repair — 2026-08-18

## Result

The private production rebuild passes the approved coverage gate. Mapped
component mass increased from 78.91% to 96.39%. The largest unresolved
occupation contribution is 0.447%, below the 1% ceiling.

| Measure | Before repair | After repair |
|---|---:|---:|
| Mapped component mass | 78.91% | 96.39% |
| Fully resolved component mass | 65.52% | 77.17% |
| Bounded provisional component mass | 13.24% | 19.22% |
| Unresolved component mass | 20.58% | 3.44% |
| Absent from official crosswalk | 0.17% | 0.17% |
| Largest unresolved occupation contribution | above 1% | 0.447% |
| Coverage gate | fail | pass |

Totals can differ slightly because displayed values are rounded. “Mapped” is
the sum of fully resolved and bounded provisional components; it does not mean
that every mapped component is point-identified.

## Mechanical repair

- The production join now evaluates every Census/OEWS route component
  independently. An unavailable O*NET child remains unresolved at its original
  weight; it no longer invalidates the complete CPS occupation or causes the
  remaining weights to be renormalized.
- Current usable O*NET 26.1 task profiles remain preferred.
- Missing 2019 occupations can use dated O*NET 25.0 profiles only through the
  official O*NET-SOC 2010-to-2019 taxonomy crosswalk. These transfers are
  always provisional and never overwrite a current profile.
- When detailed OEWS employment is unavailable for multiple officially linked
  SOCs, equal shares provide only a diagnostic center. Downstream estimation
  must carry the minimum and maximum dose over the linked children.

This recovers the previously conspicuous gaps for occupations such as cooks,
software developers, and teacher assistants without inventing undated links.

## Evidence and lineage

- O*NET 25.0 archive (August 2020):
  `6a4b2448224f50686598f2dbdf91e4cac0a38e3c6bd588a3eb9f1957e4030f29`
- Official O*NET-SOC 2010-to-2019 taxonomy crosswalk:
  `8f026a33134bfde5770308d1c6117cf70d9dd41c2b3467e6dd271d65bdeecc5a`
- Private legacy fallback output:
  `ee7d339465bea8c9e31982f3932c931080251ce144219d98f586a8adb803ca66`
- Private repaired crosswalk output:
  `eb68890bcfb31855d6a8f0704aab022c13c842d09e01eb57acd94e28dac4ddeb`
- Private occupation gap audit:
  `cbce29635b163def2f990aee36153304a34f1bf810cd806a49a3365fc48a8236`

The detailed files remain on the private SCC backbone. The repository contains
only builders, tests, sanitized receipts, and this aggregate report.

## Downstream rule

The repaired mapping clears the coverage gate, but it does not authorize a
single unbounded point estimate. Fully resolved components account for 77.17%
of preperiod component mass. Another 19.22% is mapped provisionally and must
enter dose construction with preregistered min/max bounds. The remaining
3.61% (including the 0.17% absent code mass) stays fail-closed.

At the stricter whole-CPS-code level, only 65.36% of observed preperiod weight
is fully resolved because any unresolved component makes the entire code
ineligible for an unbounded point estimate. That conservative code-level flag
must remain intact.
