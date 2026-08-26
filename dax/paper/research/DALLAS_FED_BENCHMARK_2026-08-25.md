# Dallas Fed Chart 1 benchmark and estimand comparison

Checked: 2026-08-25

## Public artifacts

- Article: https://www.dallasfed.org/research/economics/2026/0106
- Downloadable chart-data workbook: https://www.dallasfed.org/-/media/documents/research/economics/2026/0106data.xlsx
- Chart 1 image: https://www.dallasfed.org/-/media/Images/research/economics/2026/0106/dfe0106c1.png
- Workbook SHA-256 at retrieval: `972bcab87986d08b6b05897a57fcaa4f0bc66964e37171fe06534e61dccf4c1a`

The workbook contains chart-ready monthly series, not person-level CPS observations, occupation-level exposure scores, a code crosswalk, or analysis code.

## Exact Chart 1 definitions

The chart note defines each line as:

> Employment in the occupation category as a percentage of the total population in that age range, shown as a 12-month moving average.

The two age panels are **20-24** and **25-55**. Occupations are grouped into least, moderate, and most exposed categories using **tertiles of the 2024 employment-weighted distribution** of occupational exposure. The chart identifies the exposure score as the **Eloundou et al. (2024) beta measure**. The article says category assignment is held fixed over time.

The underlying workbook series run monthly from **January 2004 through September 2025** (261 observations). It supplies six outcome series:

- ages 20-24 × least/moderate/most AI exposure;
- ages 25-55 × least/moderate/most AI exposure.

The page describes the source as public CPS microdata; the chart cites IPUMS CPS and Eloundou et al. (2024).

An algebraic representation is:

\[
S_{a,g,t}^{12MA}
=100\times MA_{12}\left(
\frac{\sum_{o\in g}\sum_i w_{it}1\{age_i\in a, employed_i=1, occupation_i=o\}}
{\sum_i w_{it}1\{age_i\in a\}}
\right),
\]

where `a` is one of the two age bands and `g` is a fixed 2024 exposure tertile. The denominator is the full population in the age band, not employment in the age band or employment in an older comparison group.

## Reproduced benchmark values

Values below come directly from the Dallas Fed workbook.

| Age × exposure group | Nov. 2022 | Sep. 2025 | Change, percentage points | Relative change |
|---|---:|---:|---:|---:|
| 20-24, least | 32.7191 | 32.7325 | +0.0134 | +0.04% |
| 20-24, moderate | 17.0189 | 17.4579 | +0.4391 | +2.58% |
| 20-24, most | **16.3644** | **15.5380** | **-0.8264** | **-5.05%** |
| 25-55, least | 23.7754 | 23.6349 | -0.1404 | -0.59% |
| 25-55, moderate | 28.2553 | 28.8157 | +0.5604 | +1.98% |
| 25-55, most | 27.5205 | 28.0173 | +0.4968 | +1.81% |

This exactly reconciles the article's rounded statement that the young/high-exposure share fell from 16.4% to 15.5% (about 0.9 percentage point).

## Exposure and crosswalk disclosure

What is public:

- Eloundou et al. beta is the stated occupation-level exposure concept.
- Occupations are placed in 2024 employment-weighted tertiles and remain fixed across time.
- The article lists representative occupations in each category.

What is **not** in the article or downloadable workbook, and was not located in the accompanying public search:

- the precise Eloundou column/rater variant (for example, human versus GPT-4 rating);
- the native SOC version used at each step;
- the SOC-to-Census occupation crosswalk file or treatment of many-to-many matches;
- the occupation-level score/category lookup table;
- executable replication code;
- coefficient or chart sensitivity to another exposure measure or crosswalk.

The public article links to Eloundou et al. and describes the CPS construction, but the downloadable data are final chart aggregates. Therefore the Dallas series can be benchmarked exactly, but its exposure merge cannot be reproduced exactly from the Dallas materials alone without obtaining clarification or code from the authors.

## Is Chart 1 algebraically equivalent to the proposed PPML estimand?

**No. It is adjacent, not algebraically equivalent.**

The proposed design uses occupation × age-group × month employment stocks as cells and estimates an exposure × young × post coefficient with PPML (plus occupational/time structure and formal inference). Dallas Chart 1 instead:

1. aggregates occupations into three exposure bins before analysis;
2. divides each aggregate employment count by the total population of the relevant age band;
3. smooths the resulting share with a trailing 12-month moving average;
4. uses ages 20-24 versus 25-55, rather than 22-25 versus the proposed older range;
5. reports six descriptive time series with no regression counterfactual, pretrend coefficient, uncertainty interval, or continuous-exposure estimate.

Aggregation is the decisive difference. Dallas observes

\[
\sum_{o\in g} E_{o,a,t}/P_{a,t},
\]

whereas occupation-cell PPML estimates a multiplicative conditional mean for each `E[o,a,t]` before aggregation. In general,

\[
\sum_o \exp(X_o\beta) \neq \exp\left(\sum_o X_o\beta\right),
\]

so the Dallas aggregate-share movement cannot be converted into the proposed PPML coefficient. It also weights the substantive result toward large occupations within a tertile, while an occupation-cell regression's implicit weighting depends on its likelihood and fixed-effect structure.

Chart 1 would become algebraically close only under a deliberately coarsened model whose observations were age × exposure-tertile × month cells, whose outcome/offset reproduced the age-population denominator, and whose fitted values were then smoothed identically. That is not the proposed occupation-level PPML.

## Implication for novelty and benchmarking

Dallas Fed already establishes the **descriptive fact** the CPS chapter might otherwise claim as new: young employment-to-population share fell in the most AI-exposed occupation tertile while the corresponding older share rose. A later-data PPML cannot claim novelty merely for finding the same direction.

The proposed design remains distinguishable if it contributes all of the following:

- occupation-level rather than pre-aggregated exposure variation;
- a pre-specified 22-25-versus-older relative-employment estimand;
- formal uncertainty and a power/MDE comparison with the ADP magnitude;
- explicit common-support sensitivity across exposure measures and crosswalks;
- a test of whether post-September-2025 data change the estimate or benchmark-exclusion conclusion.

For implementation validation, the first benchmark should reproduce the Dallas public series on Dallas's own ages, tertiles, denominator, and 12-month smoothing before changing any of those choices. A failure to reproduce 16.3644 in November 2022 and 15.5380 in September 2025 for ages 20-24/high exposure means the CPS weights, category assignment, denominator, crosswalk, or smoothing differ and must be reconciled before interpreting a PPML result.
