# DAX W1 — PI decisions open

**Status:** 17 decisions open; no item is binding until PI signature.

**Source memo:** `dax/memo/design_memo_v1.md`

**Rule:** decide each item before creating `v1.0-preregistered`.

| ID | Decision | Proposed default | PI response |
|---|---|---|---|
| 1 | Event eligibility | median-occupation wage-bill dose >= 0.01 | OPEN |
| 2 | Event window | max `[-6,+6]`, midpoint-trimmed, >=3 clean months per side | OPEN |
| 3 | Treated-bin minimum dose | `DeltaDAX >= 0.01`; smaller positive doses retained continuously | OPEN |
| 4 | Accumulation | event increment primary; prior DAX/dose as state controls | OPEN |
| 5 | Prior crossers | eligible for new dose, never zero-dose controls; all-prior-crossers-excluded robustness | OPEN |
| 6 | Mapping tiebreaker | GDPval primary; median standardized estimate descriptive only | OPEN |
| 7 | Mapping audit | 10% stratified; kappa >=0.70 and binary agreement >=90% | OPEN |
| 8 | Static-score validation | Spearman >=0.50 | OPEN |
| 9 | Usage first stage | >=5% relative usage-share jump; Doing materiality +2 pp | OPEN |
| 10 | Multiple testing | Holm 5% primary; BH 10% secondary/auxiliary | OPEN |
| 11 | Power | alpha 0.05, 80%; employment MDE <=6.5 pp or half baseline gap | OPEN |
| 12 | Crosswalk quality | within-code dose SD >0.10 or max weight <0.50 flagged | OPEN |
| 13 | Minimum estimability | >=70% weighted crossed mass, >=50 cells, >=3 events, max event weight <=50% | OPEN |
| 14 | Pre-trend diagnostic | joint p>=0.10 and no Holm-adjusted individual lead | OPEN |
| 15 | EIV bounds | median shift <=1 mo; p90 <=3 mo; <=10% bin changes; attenuation >=0.80 | OPEN |
| 16 | IV strength | robust effective F >=10; otherwise weak-IV inference only | OPEN |
| 17 | Delta calibration | 0.01 grid, `[0,1]`, 95% bootstrap CI; no estimate below estimability gate | OPEN |

## Non-numeric confirmations

- [ ] Primary hours outcome is unconditional weekly hours with zero for
  non-employed persons; conditional hours is secondary.
- [ ] GDPval remains primary; alternative mappings cannot rescue a sign
  conflict under the survive-all-three rule.
- [ ] The minimum-distance delta calibration supersedes a raw jump ratio.
- [ ] Official deprecation-page conflict for `gpt-4-1106-preview` is retained
  in provenance and W4 verifies actual API availability.
- [ ] No real OpenAI usage aggregate or derivative enters the repository.
- [ ] No outcome analysis runs before the signed tag.

## Evidence still required before PI signature

- [ ] Complete two-source event and price registry through 2026-08-06.
- [ ] W1 power simulation on pre-event CPS moments.
- [ ] Event-by-event table shell populated with W5-produced crossing counts
  before outcomes open, or an explicit signed rule for later mechanical fill.
- [ ] Independent cross-vendor red-team of the completed memo.
- [ ] Rendered PDF reviewed line by line by PI.
