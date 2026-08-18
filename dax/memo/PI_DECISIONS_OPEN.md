# DAX W1 — PI decisions open

**Status:** All 17 decisions and six non-numeric confirmations approved by
the PI on 2026-08-06. Gate-1 evidence remains incomplete; approval does not
authorize the preregistration tag or outcome access yet.

**Source memo:** `dax/memo/design_memo_v1.md`

**Rule:** decide each item before creating `v1.0-preregistered`.

| ID | Decision | Proposed default | PI response |
|---|---|---|---|
| 1 | Event eligibility | median-occupation wage-bill dose >= 0.01 | APPROVED |
| 2 | Event window | max `[-6,+6]`, midpoint-trimmed, >=3 clean months per side | APPROVED |
| 3 | Treated-bin minimum dose | `DeltaDAX >= 0.01`; smaller positive doses retained continuously | APPROVED |
| 4 | Accumulation | event increment primary; prior DAX/dose as state controls | APPROVED |
| 5 | Prior crossers | eligible for new dose, never zero-dose controls; all-prior-crossers-excluded robustness | APPROVED |
| 6 | Mapping tiebreaker | GDPval primary; median standardized estimate descriptive only | APPROVED |
| 7 | Mapping audit | 10% stratified; kappa >=0.70 and binary agreement >=90% | APPROVED |
| 8 | Static-score validation | Spearman >=0.50 | APPROVED |
| 9 | Usage first stage | >=5% relative usage-share jump; Doing materiality +2 pp | APPROVED |
| 10 | Multiple testing | Holm 5% primary; BH 10% secondary/auxiliary | APPROVED |
| 11 | Power | alpha 0.05, 80%; employment MDE <=6.5 pp or half baseline gap | APPROVED |
| 12 | Crosswalk quality | within-code dose SD >0.10 or max weight <0.50 flagged | APPROVED |
| 13 | Minimum estimability | >=70% weighted crossed mass, >=50 cells, >=3 events, max event weight <=50% | APPROVED |
| 14 | Pre-trend diagnostic | joint p>=0.10 and no Holm-adjusted individual lead | APPROVED |
| 15 | EIV bounds | median shift <=1 mo; p90 <=3 mo; <=10% bin changes; attenuation >=0.80 | APPROVED |
| 16 | IV strength | robust effective F >=10; otherwise weak-IV inference only | APPROVED |
| 17 | Delta calibration | 0.01 grid, `[0,1]`, 95% bootstrap CI; no estimate below estimability gate | APPROVED |

## Non-numeric confirmations

- [x] Primary hours outcome is unconditional weekly hours with zero for
  non-employed persons; conditional hours is secondary.
- [x] GDPval remains primary; alternative mappings cannot rescue a sign
  conflict under the survive-all-three rule.
- [x] The minimum-distance delta calibration supersedes a raw jump ratio.
- [x] Official deprecation-page conflict for `gpt-4-1106-preview` is retained
  in provenance and W4 verifies actual API availability.
- [x] No real OpenAI usage aggregate or derivative enters the repository.
- [x] No outcome analysis runs before the signed tag.

## Approval record

- PI instruction in the Codex task: "approve all 17 and all six
  confirmations".
- Recorded: 2026-08-06 (Asia/Shanghai).
- Scope: approves the proposed defaults and confirmations above. It does not
  waive the evidence checklist or authorize `v1.0-preregistered` before the
  remaining Gate-1 work passes.

## Evidence still required before PI signature

- [ ] Complete two-source event and price registry through 2026-08-06.
- [ ] W1 power simulation on pre-event CPS moments.
- [x] Event-by-event table shell populated with W5-produced crossing counts
  before outcomes open, or an explicit signed rule for later mechanical fill.
- [x] Independent cross-vendor red-team completed in three SCC1 rounds; the
  final review is `CONDITIONAL_GO`, its mechanical findings are incorporated,
  and its separate registry, empirical-power, and PI PDF-review blockers remain
  open.
- [ ] Rendered PDF reviewed line by line by PI.
