# W2 finding — the task weight is not a footnote

**Date:** 2026-08-25. Measured on the real O*NET 26.1 build, 17,140 tasks
across 873 occupations. Source:
`dax/data_built/onet_task_weight_variant_sensitivity.json`.

W2-D4 froze two variants before anyone looked, to answer one question: is the
aggregation function doing work the data cannot support? **It is.**

## What was measured

Primary (`importance × frequency_score`) against importance-only, within each
occupation:

| | value |
|---|---:|
| rank correlation, median | 0.8761 |
| rank correlation, 5th percentile | 0.5710 |
| rank correlation, minimum | 0.0857 |
| mass reallocated, median | 7.66% |
| mass reallocated, 95th percentile | 12.60% |
| mass reallocated, maximum | 17.78% |

"Mass reallocated" is total variation distance — the fraction of an
occupation's task mass that must move to turn one weighting into the other.

The median hides the problem, so the spread matters more:

| threshold | share of the 873 occupations |
|---|---:|
| rank correlation below 0.95 | **89.0%** |
| rank correlation below 0.90 | **61.9%** |
| rank correlation below 0.80 | 29.1% |
| rank correlation below 0.70 | 14.0% |
| rank correlation below 0.50 | 3.2% |
| mass reallocated above 5% | **81.3%** |
| mass reallocated above 10% | 21.4% |

Against equal-weight the reallocation is larger still: median 10.85%, maximum
28.46%.

## What it means

`DAX_om` is a wage-bill-weighted share of an occupation's tasks. These weights
are that weighting. In the median occupation, **7.7% of task mass sits on
different tasks** depending on which of two equally defensible definitions is
used, and in three occupations out of ten the task ordering itself is only
loosely preserved.

Whether that moves the headline depends on whether the tasks that gain weight
under the primary are also the ones more likely to cross. There is a reason to
expect they are, and it is not reassuring: the primary differs from
importance-only precisely by the **frequency** term, and frequently-repeated
tasks are plausibly the more automatable ones. If so the difference is
systematic rather than noise, and it points the same way in every occupation.
That cannot be tested until crossing data exists.

## The hypothesis that failed

The obvious guess was that instability concentrates in the occupations S1
found non-evaluable — physical and interpersonal work — which would have
localised the problem. **Tested and not supported.** Median rank correlation
by SOC major group runs from 0.6477 to 0.9271, and the worst six include
management (11-) and computer/mathematical (15-) alongside protective service
(33-), while production (51-) and healthcare (29-) sit among the best.

The disagreement is **widespread rather than concentrated**, which is worse:
there is no subset that can be excluded or caveated to make it go away.

## Consequences

1. **[W2-D3] is load-bearing, not a recorded limitation.** The defect —
   `frequency_score` treats FT's ordinal bands as cardinal — sits in exactly
   the term that separates the primary from importance-only. Its fix path
   (obtain the published band definitions; if spacing is not near-linear,
   re-derive and re-run Mapping A coverage and the DWA bound together) moves
   from "recorded" to required work before any headline is reported.

2. **Every occupation-level result is reported across all three definitions.**
   W2-D4 already froze the variants for this; the finding is that the
   provision will be needed rather than ceremonial.

3. **The primary is unchanged.** W2-D1 fixes it, and this is a report, not a
   selection. A definition may not be adopted because its numbers look better.

## What was NOT established

The claim in W2-D2 that importance-weighted and unweighted occupation means
correlate at 0.999 **remains unverified and is not tested by any number
above.** That claim is a *between-occupation* correlation of occupation-level
aggregates; everything here is *within-occupation* agreement between task
shares. Aggregation averages within-occupation reordering away, so the two are
entirely compatible. An earlier version of the sensitivity record placed the
measured 0.876 beside the reported 0.999, which invited reading one as a
refutation of the other. It is not, and the record has been corrected.

Reproducing the published claim needs a task-level score to aggregate, which
needs crossing data that does not exist.
