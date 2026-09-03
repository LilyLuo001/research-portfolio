# Y1b computerization measurement receipt

## Scope

This is an outcome-blind design diagnostic. It does not estimate a young-worker
employment coefficient. Employment weights come only from November 2021 through
November 2022; December 2022 through February 2023 rows in the private support
artifact are excluded.

The O\*NET 24.3 source calls element `4.A.3.b.1` **Interacting With Computers**.
Earlier project documents called it *Working with Computers*; those documents
have been corrected without changing the frozen element ID or scales.

## Measures built

| measure | native source | CPS OCC2010 codes with scores |
|---|---|---:|
| Webb software exposure | Webb `occ1990dd`, direct Dorn bridge | 482 |
| O\*NET computer interaction, Importance | O\*NET 24.3; SOC repair | 447 |
| O\*NET computer interaction, Level | O\*NET 24.3; SOC repair | 447 |
| routine-task intensity | Autor–Dorn `occ1990dd`, direct Dorn bridge | 467 |
| Frey–Osborne automation probability | published appendix; SOC repair | 418 |

The output contains 522 CPS OCC2010 rows. All source hashes, locators,
crosswalk rules and fail-closed ambiguous merges are recorded in
`COMPUTERIZATION_MEASURES_RECEIPT.json`.

Webb leaves three source occupations unscored: Auctioneers and sales support
occupations n.e.c.; Other telecom operators; and Supervisors of guards. Only
the last has positive weight in the frozen pre-period support. Together they
represent 0.0043% of that support.

## Partial-support findings

The diagnostic projects each AI measure on each computerization measure using
pre-period occupation employment weights. `partial` is the fraction of AI
exposure variance left after that projection. It is a support statistic, not a
causal estimate or a pass/fail separability threshold.

| AI measure | computerization measure | r | partial | VIF | effective identifying occupations | common-support employment |
|---|---|---:|---:|---:|---:|---:|
| Eloundou alpha | Webb software | 0.162 | 0.974 | 1.03 | 14.0 | 86.0% |
| Eloundou alpha | O\*NET Importance | 0.393 | 0.845 | 1.18 | 33.2 | 78.6% |
| Eloundou alpha | RTI | 0.189 | 0.964 | 1.04 | 9.5 | 85.0% |
| Eloundou beta | Webb software | 0.007 | 1.000 | 1.00 | 44.4 | 86.0% |
| Eloundou beta | O\*NET Importance | 0.802 | 0.357 | 2.80 | 50.2 | 78.6% |
| Eloundou beta | O\*NET Level | 0.721 | 0.480 | 2.08 | 53.8 | 78.6% |
| Eloundou gamma | O\*NET Importance | 0.826 | 0.317 | 3.15 | 34.9 | 78.6% |
| AIOE, administrative equal | O\*NET Importance | 0.839 | 0.296 | 3.38 | 54.7 | 88.5% |
| AIOE, OEWS-source weighted | O\*NET Importance | 0.852 | 0.274 | 3.65 | 54.7 | 86.9% |

The result depends on the computerization construct. Direct LLM exposure
(alpha) retains at least 84.5% of its variance against all five controls, but
its residual identifying variation can be concentrated: the effective number
falls to 9.5 against RTI. Broader software-complementary exposure (beta/gamma)
and AIOE overlap strongly with O\*NET computer interaction, yet overlap little
with Webb software exposure or RTI. Therefore the design must report the joint
model across the frozen measures and must not select a control or AI index by
which pairing produces the preferred coefficient.

All 30 pairings, major-group residual shares, and named divergence occupations
are in `computerization_support_receipt.json`.

## Execution correction

An initial uncommitted support-only run mistakenly used every weight row in a
private file labelled `preperiod`, which also contained December 2022 through
February 2023. No outcome field was accessed, and that output was discarded.
The committed script rejects those months before their weights enter the
support distribution; the replacement receipt records the excluded months.
