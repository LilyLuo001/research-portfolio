# NEW48 model diagnostic aggregate: frozen V5 and V6

This report compares candidate flags from frozen V5 and V6 with 48 blind model-assisted reference labels. The labels are not human ground truth, and these counts are diagnostic rather than accuracy estimates.

The reference run requested `gpt-5.6-terra` at `medium` effort. Exact runtime build identity was not independently exposed.

## Reference composition

| Module | Explicit positive | Explicit negative | Not mentioned | Insufficient text | Unresolved |
|---|---:|---:|---:|---:|---:|
| Education | 30 | 0 | 17 | 1 | 0 |
| Experience | 35 | 2 | 10 | 1 | 0 |

## Frozen V5 comparison

| Module | Positive + not-mentioned support | Positive with candidate | Positive without candidate | Not mentioned with candidate | Not mentioned without candidate | Explicit negative support | Insufficient-text support | Unresolved support |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Education | 47 | 16 | 14 | 0 | 17 | 0 | 1 | 0 |
| Experience | 45 | 31 | 4 | 1 | 9 | 2 | 1 | 0 |

## Frozen V6 comparison

| Module | Positive + not-mentioned support | Positive with candidate | Positive without candidate | Not mentioned with candidate | Not mentioned without candidate | Explicit negative support | Insufficient-text support | Unresolved support |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Education | 47 | 17 | 13 | 0 | 17 | 0 | 1 | 0 |
| Experience | 45 | 32 | 3 | 1 | 9 | 2 | 1 | 0 |

## Explicit-negative limitation

The experience reference has 2 explicit-negative rows. V6 produced 0 explicit-absence flags; its ordinary candidate flag was positive on 1 and absent on 1. This diagnostic does not support a no-experience rate.

## V5 to V6 candidate transitions

- Education: 1 gained, 0 removed, 16 retained candidates, and 31 retained non-candidates.
- Experience: 1 gained, 0 removed, 33 retained candidates, and 14 retained non-candidates.

## Bounded missed-education audit

Among 13 V6 non-detections on model-positive education references, 11 are degree or educational-attainment clauses and 2 are license, training, or certification clauses. No missed clause in this bounded review was categorized as current enrollment, unclear, or a context-only mention.

The 11 degree-related misses may reflect recognition, context, or scope coverage; quote-only inspection cannot adjudicate the underlying cause. The two license/training clauses mark a measurement-scope boundary. This is a diagnostic classification of existing model-reference quotes, not new annotation or human adjudication.

Explicit-negative, insufficient-text, and unresolved references remain separate from the positive/not-mentioned diagnostic comparison. Current enrollment is an exploratory eligibility mention, not an attained degree or unconditional statement of general eligibility.

The 48-row calibration sample supports no full-corpus or per-period inference. The sealed test was not accessed.
