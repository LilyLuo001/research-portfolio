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
- [ ] Independent cross-vendor red-team **of this draft**. RETURNED TO
  UNCHECKED 2026-08-18: the three-round DeepSeek V4-Pro review reached
  `CONDITIONAL_GO` on the *superseded discrete design*. D1 replaced the primary
  specification, so that verdict does not transfer and must not be counted.
  The prior review is retained in `red_team_deepseek_v4_pro_round{1,2,3}.json`
  as history, not as evidence for this version.
- [ ] Rendered PDF reviewed line by line by PI.


## Amendments counter-signed 2026-08-18

The PI counter-signed the following on 2026-08-18. Each is a pre-tag amendment
to a draft; the outcome seal was closed throughout and no estimated treatment
effect existed or was consulted.

- [x] **D1** — primary specification changed from a stacked event study to a
  continuous cumulative-dose design; the stack is demoted to secondary
  corroboration. `PI_DECISION_D1_2026-08-18.md`.
- [x] **D3** — the power pass bar becomes a frozen absolute constant computed
  once over the pre-event window, replacing a bar derived from the sample it
  judged. `PI_DECISION_D3_2026-08-18.md`.
- [x] **D4 Part 1** — the primary estimand is named as an incumbent margin.
- [x] **D4 Part 2 — option (b) APPROVED**: the entrant-margin companion is
  included as a registered secondary design with a frozen pre-period entry mix.
  `PI_DECISION_D4_2026-08-18.md`, memo section 7.2.
- [x] **F2** — five event rows demoted to `pending_second_date_locator`, a
  `date_conflict` column added, and the release-dating standard enforced by
  `validate_event_registry.py` rather than applied by hand.

### Consequences still outstanding

- [ ] Continuous-dose power simulation run against a **FROZEN** standard.
  `power_standard.json` ships as `PLACEHOLDER_REQUIRES_REAL_CPS`; both engines
  return `adequately_powered: null` until `freeze_power_standard.py` is run on
  the real pre-event extract.
- [ ] Entrant companion power table, which requires the frozen entry mix
  `pi_go` and therefore the CPS extract.
- [ ] Fresh independent cross-vendor red team of this draft (see above).

### Adversarial pre-review findings, 2026-08-18 (must clear before the paid pass)

From `red_team_selfreview_2026-08-18.md` — a self-review, NOT the independent
cross-vendor pass, and not evidence for Gate 1.

- [x] **M1 (blocker) — FIXED 2026-08-18.** Decision 14 re-specified as a
  placebo-lead test on eventual exposure `D_o` at a frozen horizon. Estimable
  at all three registered horizons (regressor variance 0.058 / 0.196 / 0.588
  vs exactly 0.0 for the superseded form), implemented in
  `placebo_lead_design` and pinned by three tests.
- [x] **M2 — ADJUDICATED 2026-08-18.** The 0.13 is a relative decline in
  **employment** (headcount); "payroll" names the data source (ADP), not the
  outcome. Sourced to `docs/DAX_ERE_Proposal_v3.md:12` and `:100`
  (Brynjolfsson, Chandar & Chen 2025, "Canaries in the Coal Mine?"), confirmed
  by a second web channel. The D3 formula was already correct; the memo now
  states the distinction with its citation and a test pins it.
- [x] **M2b — DECIDED BY PI 2026-08-18: use 0.19** (August 2026 revision, ADP
  through June 2026), superseding the 0.13 the proposal cites. Recorded in
  `power_standard.json` with `locator_status: PENDING_EXCERPT` — the figure is
  PI-directed and **not yet sourced to a page cite**, because every host
  carrying the paper is egress-blocked. Any writeup citing this constant must
  say so until the `Canaries_August2026.pdf` excerpt is supplied. The choice
  was made before any outcome data existed and before the frozen baseline was
  computed, so it cannot have been informed by a result.
- ~~**M2b — NEW BLOCKER, PI decision required.**~~ The same paper's headline
  figure has moved across versions: 0.13 (the version the proposal cites),
  reportedly 0.16, and reportedly 0.19 in the August 2026 revision. The latter
  two are from search summaries only — every host carrying the PDF is
  egress-blocked, so **no version was read**. Choosing the larger figure
  loosens the pass bar ~46% and would be specification search if chosen after
  seeing the margin. `freeze_power_standard.py` refuses until
  `benchmark.version_status` is `RESOLVED`. **To settle it, provide the
  headline-figure excerpt from `Canaries_August2026.pdf` (and ideally the
  Nov 2025 version).**
- [ ] **M3** Entry mix `pi_go` may not be estimable at occupation granularity.
  Compute realised per-cell entrant counts and pre-register a pooling rule.
- [ ] **M4** The entrant sample conflates true entrants with CPSIDP
  linkage failures and long non-employment spells. Separate using
  month-in-sample before registering the companion.
- [x] **M5 — RESOLVED 2026-08-18.** The estimator is person-month; the power
  simulation is occupation-month cells. Section 7.4 states the distinction and
  the direction of the approximation: omitting `X_i` raises residual variance,
  so the simulated MDE is an **upper bound** — passing in simulation implies
  passing at person level, but failing does not condemn the design. The
  asymmetry is registered so it cannot be invoked selectively.
- [x] **M6 — RESOLVED 2026-08-18.** Section 9.2 now fixes the consequence in
  advance: a degenerate dose matrix means the paper drops the dynamic claim,
  argues the index's contribution on the crossing chronology instead of the
  regression, promotes Decision 8 convergent validity to load-bearing, and
  reports the statistic at summary level. Degenerate is still publishable — it
  is a different paper, named in advance.

M1, M2 and M5 are the same failure as the 2026-08-14 audit found: prose that
was never executed against the code or data it governs. The paid cross-vendor
pass should be spent on a v3 that has cleared them.
