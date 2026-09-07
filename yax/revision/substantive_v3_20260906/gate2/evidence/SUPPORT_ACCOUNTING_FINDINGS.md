# Gate 2 support and stock-accounting evidence

This directory contains the authoritative aggregate-only output from the
support/accounting runner at commit
`9d49bba5a931b4d6c62bf41c81251f922b57c40e`. It contains no CPS row-level
microdata and no occupation-by-month cell archive. The protected Gate 1
aggregate remained on SCC and is identified only by its SHA-256.

## Execution identity

- Specification:
  `yaxgate2sa_v1_6069f368581e958805977c30572cce09f6fabe8f6d0da70505682e68f8cdca5f`
- Runner SHA-256:
  `3bbc4b2c6fe234d2cb96427747badd78855e2a365d929a4972bf6fdae137b382`
- Protected aggregate SHA-256:
  `5e10dabf78b1b1cbc8b6aa9f8745435224b9fe3cb078e73cd9d9e27a9c292717`
- Execution receipt SHA-256:
  `5c39aaedfe33182a578a21c63047bef6c548be53c31b4ca682ca2246d165e9e1`
- The receipt authenticates 12 result artifacts and gives each a result ID
  derived from the signed specification ID, logical filename, and artifact
  hash.

## Support result

The fixed 468-occupation support forms a complete 22-family by 5-quintile
matrix. All ten quintile-pair edges appear somewhere, and the five-node
occupational-support graph is connected with incidence rank four. Direct Q1--Q5
support is much narrower: 29 occupations across SOC2 families 27, 29, 31, and
41.

This graph result is topology only. It does not prove full regression
design-matrix information, finite estimability, or absence of separation. Those
properties are governed by the separate Gate 1 A1 numerical certificates, and
the common-profile coefficient is not a family-weighted average of directly
observed Q5--Q1 effects.

## Exact descriptive stock accounting

Using equal observed-month averages over 71 preperiod and 42 postperiod months:

| component | log points |
|---|---:|
| young Q5--Q1 change, `D_young` | -0.109784 |
| older Q5--Q1 change, `D_older` | 0.048331 |
| relative change, `D_relative` | -0.158115 |

The identity `D_relative = D_young - D_older` closes to
`2.50e-16`. It is an exact aggregate-stock description, not the grouped-binomial
regression coefficient. For comparison, the separately certified pooled and
family-month regression targets are -0.132109 and -0.021675.

The exact log Shapley decomposition of `D_relative` assigns -0.129321 log
points to within-family young/older ratio change and -0.028794 to changing older
family weights; boundary mass is zero in the observed data. The corresponding
level-ratio decomposition is reported separately and must not be relabeled as
log points. All 88 family-tail-period denominator cells are retained: 52 are
valid positive cells and 36 are structural absences; no undefined active ratio
is present in this execution.

## Status limit

This package advances the model-free parts of S01--S02 and the point accounting
for D01/D03/D04. It does not execute sampling inference, finish D02, validate a
manuscript table, or make any of those requirements `VERIFIED`. They remain
`RUN_UNVALIDATED` until their remaining inference and presentation dependencies
are completed and checked.
