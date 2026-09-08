# Gate 4 public-data benchmark and population-alignment specification

Status: **post-outcome exploratory; written before this block is run**. This
block addresses B03 and B04 without changing the frozen v1.1 design or its
confirmatory results.

## 1. Published targets and the reproducibility boundary

The fixed August 12, 2026 Brynjolfsson--Chandar--Chen (BCC) paper reports
several different objects that must not be interchanged:

1. a descriptive November-2022-to-June-2026 kept-pace shortfall for employed
   workers aged 22--25 in the top two versus bottom three exposure quintiles;
2. an employment-weighted occupation-level long-difference regression for the
   same age group, with the Q5 coefficient measured relative to Q1;
3. an ACS 2022-to-2024 Q5-minus-Q1 growth contrast for all employed workers
   aged 22--25 and for full-time civilian wage-and-salary workers; and
4. volatile public CPS indexed stock plots.

BCC's exhaustive occupation membership, title-to-SOC universe, and tie
algorithm are not public. This run therefore uses an independently
reconstructed, equal-occupation, tie-preserving Rule-A GPT-4 beta quintile
assignment on YAX's fixed 468-occupation Census-2018 support. It is never
called BCC-exact. BCC's proprietary balanced-firm panel, positive-earnings
restriction, employer identifiers, firm controls, and worker--firm-match unit
cannot be reproduced in CPS.

## 2. CPS populations

The first population is all employed CPS respondents, defined by `EMPSTAT` 10
or 12 and positive `WTFINL`. The aligned-population sensitivity keeps only
civilian wage-and-salary workers who usually work full time:

- `CLASSWKR` in 20, 21, 22, 23, 24, 25, 27, or 28;
- `CLASSWKR` 26 (armed forces), 10/13/14 (self-employed), 29 (unpaid family),
  NIU, and unknown values are excluded; and
- `UHRSWORKT` is at least 35 and below the reserved code 997.

The definition follows the sequence in BCC Appendix Table H.1 and is only a
feasible CPS analogue. In particular, CPS usual hours are not an ADP employer
full-time designation, and CPS has no balanced-firm or positive-payroll-match
condition.

The 2017--2019 occupation codes are routed through the fixed official
Census-2010-to-Census-2018 bridge. Current codes are used directly from 2020.
Wide-file March observations in 2017--2021 are removed before the dedicated
March Basic repair is inserted. The all-employed young/older cells must
reproduce the protected current-contract calibration on its 113-month calendar
before any result is published.

## 3. Benchmark objects

The run first produces public-benchmark analogues using only employment stocks
of ages 22--25:

- monthly quintile stock indices normalized to November 2022;
- Q5-minus-Q1 differences in growth factors for calendar-year-average 2022 to
  calendar-year-average 2024, using all twelve 2022 months, including December;
- Q5-minus-Q1 differences in growth factors from November 2022 to June 2026;
- top-two/bottom-three kept-pace shortfalls from November 2022 to June 2026;
  and
- employment-weighted occupation long-difference regressions for Q2--Q5
  relative to Q1 over the two endpoint definitions.

The 2022 annual benchmark is a monthly-CPS average and therefore remains
different from a one-year ACS estimate. December 2022 is included there because
the object is annual alignment; it remains excluded from every YAX post model
as the frozen transition month. Long-difference inference follows BCC's
heteroskedastic-robust occupation-level setup. Aggregate contrasts receive
occupation-linearized multiplier intervals. Neither is CPS design-based survey
inference.

## 4. Separately defined conditional YAX extension

The BCC stock targets above are followed by a separate young-relative CPS
extension, not relabeled as their replication. For both CPS populations, and
on one common preperiod-positive occupation support, estimate:

- `pooled`: occupation and calendar-month fixed effects;
- `family_post`: pooled fixed effects plus SOC2-family-by-post slopes, omitting
  the preperiod-stock-largest family; and
- `family_month`: occupation and SOC2-family-by-calendar-month fixed effects.

Run both a Q5-versus-Q1 profile (Q2--Q5 post slopes) and the BCC headline
top-two-versus-bottom-three binary contrast. The binary comparison has its own
paired intervals; no inference from the Q5--Q1 profile is transferred to it.
For every contrast, the three conditioning structures use identical fixed
exposure labels, rows, and common occupation/family multiplier draws.

The no-Webb specification is reported first because BCC's public benchmark does
not include the Webb software measure. The historical YAX Webb-by-post control
is a separately labeled extension, never an ingredient of the benchmark
reproduction.

## 5. Required outputs and refusal rules

The runner writes aggregate-only public files:

- `INDEXED_STOCK_SERIES.csv`
- `AGGREGATE_BENCHMARKS.csv`
- `LONG_DIFFERENCE_RESULTS.csv`
- `CONDITIONAL_MODEL_RESULTS.csv`
- `CONDITIONAL_PAIRED_COMPARISONS.csv`
- `SUPPORT_AND_POPULATION_AUDIT.csv`
- `BENCHMARK_DIFFERENCES.csv`
- `MODEL_INFLUENCE.csv`
- `MODEL_FAILURES.json`
- `FINDINGS.md`
- `EXECUTION_RECEIPT.json`

It refuses to publish if input hashes move, the all-employed calibration does
not reproduce, a sample code is ambiguous, the fixed labels or calendar move,
any contrast loses a quintile, paired models use different rows, or any model
fails. No person or household identifier is read or written.
