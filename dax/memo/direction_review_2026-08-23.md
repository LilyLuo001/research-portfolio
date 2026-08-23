# Independent review of the proposed DAX measurement direction — 2026-08-23

**Status:** advisory review. Signs nothing, freezes nothing, and does not
constitute a PI decision. No file under `dax/analysis/outcomes/` was opened;
the pre-registration seal is intact.

**Reviewing:** the proposed 10-point direction following the Mapping A v1/v2
failure and the S1 construct-validity pilot.

## 0. Verdict in one paragraph

The diagnosis is right and the headline move is right: GDPval whole-task
performance cannot be transported to O*NET activities, and the project should
stop trying. A point-identified estimand on digitally benchmarkable task mass,
with the remainder handled by partial identification rather than a zero-fill,
is the correct response. Three parts of the proposal are wrong as specified and
should be changed before anything is frozen: (1) the bound formula bounds the
wrong object and is directionally pathological; (2) the S3 Phase-1 sample
cannot produce the per-occupation quantity the bound formula needs; (3) the
sequencing loses the only irreplaceable asset in the project. Item 3 is
time-critical and outranks all S3 design work.

Agree: proposal items 1, 2, 3(a), 4, 7, 9. Rework: items 5, 6, 8, 10 and the
bound formula.

## 1. The bound formula bounds the wrong object, and it inverts

Proposed: `Lower = B*E`, `Upper = B*E + (1-B)`, where `B` is benchmarkable
task-mass share and `E` is exposure among benchmarkable tasks.

Two problems.

**It bounds the regressor, not the estimand.** Per design memo §4 the primary
estimand is a coefficient — the change in employment probability associated
with a 0.10 increase in occupation DAX level. Bounds on an interval-valued
regressor do not push through a regression monotonically; recovering an
identified set for the coefficient is the Manski–Tamer interval-regressor
problem and requires its own assumptions. Reporting `[B*E, B*E + (1-B)]` and
then running the primary specification at each endpoint does not produce a
bound on beta. It produces two coefficients on two different treatments.

**The upper endpoint inverts the treatment ordering.** Rewrite it:

    Upper_o = 1 - B_o * (1 - E_o)

For any `E_o < 1`, `Upper_o` is *decreasing* in `B_o`. The occupations with the
least benchmarkable task mass receive the highest upper-bound exposure. At the
S1 mass shares, an occupation that is mostly physical action gets an upper
index near 1.0 — maximum measured AI exposure for an electrician, minimum for a
data analyst. The upper-bound regressor is approximately a monotone transform
of the manual-task share, so the "upper bound" specification estimates
something close to the negative of the intended contrast. A referee will find
this immediately.

**And the width is uninformative anyway.** At the S1 pass mass of ~12.8%, mean
interval width is ~0.87 index units against an estimand defined per 0.10 index
units. The identified set is roughly 8.7 estimand-units wide. That is not a
bound, it is a statement that nothing is known.

## 2. Bound the dose *path*, not the level — the design already does most of the work

This is the substantive recommendation. Write the true index as

    DAX_ot = B_o * E_ot + (1 - B_o) * N_ot

with `N_ot` the unmeasured crossing share of non-benchmarkable mass. Decompose
`N_ot = N_o0 + dN_ot`. The primary specification (§3.1) carries occupation
fixed effects, calendar-month effects, and industry-by-month effects, and the
regressor is the cumulative level. **The additive time-invariant component
`(1 - B_o) * N_o0` is absorbed by the occupation fixed effect.** It is never
identified and never needs to be.

What must be bounded is only `(1 - B_o) * dN_ot`: the *change* in feasibility
of physical and interpersonal task mass across the 2023-02 to 2026 window. That
is a much smaller object than the level, and bounding it does not require
asserting that physical tasks have zero AI exposure — which is the objection
proposal item 4 correctly raises. It requires only a claim about the *rate of
change* over one 41-month window.

That claim is defensible and partly checkable from the project's own registry:
all 21 chronology rows are text/API capability or price events. No embodiment
or robotics deployment event appears, and none would enter under the §1.1
inclusion rule, which keys on accessible model capability and token price.
Under the design's own treatment definition, `dN_ot` for physical mass is
plausibly near zero *by construction of the treatment*, not by assumption of
convenience.

**Concrete replacement for the bound formula.** Parameterize

    kappa_o = dN_ot / dE_ot

the relative crossing rate of unmeasured mass, and report beta(kappa) as a
sensitivity curve over `kappa` in `[0, 1]`, with `kappa = 0` the point-identified
digital estimand and `kappa = 1` the case where unmeasured mass crosses at the
same rate as measured mass. This stays informative at every value, is a real
partial-identification report, is honest about what is unknown, and — unlike
the level bound — never inverts the treatment ordering. Pre-register the grid
and the reported summary before any outcome work.

**One choice to pre-register explicitly:** whether the regressor is `E_ot`
(exposure per unit of *benchmarkable* mass) or `B_o * E_ot` (benchmarkable-and-
crossed share of *total* wage bill). The occupation fixed effect does not
absorb the difference, because `B_o` multiplies the time-varying part. These
are different estimands with different comparability to the 0.13 external
benchmark. `B_o * E_ot` is the one comparable to the literature.

## 3. The 74% non-evaluable figure is partly a taxonomy artifact

The S1 buckets — interpersonal interaction 47.55%, physical action 22.84% —
conflate *content* with *delivery channel*. Advising a client, explaining a
finding, negotiating terms, triaging a complaint, tutoring: these are coded
interpersonal, but a large share is delivered through text or voice and is
benchmarkable at the same work-product boundary as a document task. This is
also precisely the segment where the existing displacement evidence is
strongest — the Canaries customer-support results the power benchmark is
calibrated against sit inside this bucket.

Re-classify on two axes before freezing S3:

1. **embodiment required** — does the task require physical action in the world?
2. **delivery channel** — in-person-only / remote-mediable / document-or-data.

Benchmarkable = not embodiment-required AND channel in {remote-mediable,
document-or-data}. This will move meaningful mass out of NON_EVALUABLE, the
resulting `B` will be materially higher than 12.79%, and — more important than
the level — the classification will be defensible to a referee in a way that a
single benchmarkability flag is not. Doing this *after* freezing S3 would be a
specification change; doing it before is design work.

## 4. S3 Phase 1 as specified cannot produce B_o

Phase 1 proposes classifying 1,067 O*NET tasks. There are 19,259 tasks across
923 occupations — about 20.9 tasks per occupation. A 1,067-task sample yields
**~1.15 tasks per occupation**. But `B` enters the bound *per occupation*:
`B_o` is an occupation-level quantity in every formula above. One task per
occupation cannot estimate it.

The instrument is wrong for the job. Classification is cheap; construction is
expensive. Therefore:

- **Phase 1 = census.** Classify all 19,259 tasks by machine on the two axes in
  §3, dual-vendor across different model families per meta-rule 2, machine-diff,
  third model plus human on splits.
- **Validation sample.** Stratified human/frontier-labeled sample of ~600–1,000
  tasks for the classifier's error matrix, with the PI-DECISION 7 bar reused
  unchanged: weighted Cohen's kappa >= 0.70 and >= 90% agreement on the binary
  benchmarkable label. Failure returns the rubric, it does not lower the bar.
- **Propagate classification error into `B_o`**, and carry it into the
  `beta(kappa)` report. `B_o` is estimated, not known.
- **Sampling belongs in Phase 2**, where per-unit cost is real.

This also largely dissolves proposal item 6. Excluding the 120 S1 tasks matters
only for unbiased estimation of the classification *rate*; keep them out of the
validation sample, but there is no contamination argument for discarding the 24
*constructed instances*. They are the only ones that exist. Separate the two
roles: S1 tasks are excluded from rate estimation, retained in the instrument.

## 5. Sequencing loses the only irreplaceable asset — act on this first

Proposal item 8 has the right instinct and does not go far enough. Today is
2026-08-23. The registry's deadline-bound rows retire on **2026-10-23 (61
days)** and **2026-12-11 (110 days)**.

`dax/capability_panel/vintage_registry.json` holds 22 rows: **14 `direct`
rows, every one at `account_probe_required`**, plus 2 approved open-weight
stand-ins, 5 blocked aliases, and 1 binding exclusion. The 14 direct rows are
the deadline-bound set. The open-weight stand-ins (Llama-3.1-405B for
`GPT4_LAUNCH`, DeepSeek-R1 for `O1_PREVIEW_LAUNCH`) are *not* deadline-bound
and can be run at any time — they should be deprioritized relative to the
direct rows, which is the opposite of their current unconfigured-provider
status suggesting they are the blocker.

Meanwhile `dax/capability_panel/preflight.py:147` sets gate
`task_duration_complete = task_count > 0 and covered == task_count`, and
line 190 sets `full_capture_allowed = all(gates.values())`. Task duration is at
0/220, the metadata request bounced, and the three-human fallback is a
$2.6k–$7k pilot that has not started and may need BU human-subjects review.

**As the repo currently stands, an unstarted IRB-contingent duration pilot hard-
blocks all historical capability capture, against a 61-day irreversible
deadline.** Everything else in the project is recoverable later. Retired model
snapshots are not. If the duration pilot slips two months — an entirely ordinary
outcome for anything touching human subjects review — the historical capability
panel is permanently unrecoverable and no amount of subsequent benchmark work
restores it.

**The fix is small and the schema already supports it.**
`dax/capability_panel/contract.py:248` already accepts
`task_duration_status = "blocked_missing"` with null value, unit, and source.
The row-level contract therefore already tolerates duration-free capture. Only
the *preflight* gate conflates capture with cost-scoring. Split W4:

- **Capture** (deadline-bound): prompts, raw completions, token counts,
  reasoning tokens, latency, provenance hashes. Requires a frozen stimulus set,
  a signed budget ceiling, and encryption. **Does not require duration.**
- **Scoring** (not deadline-bound): rubrics, pi estimation, duration, wage
  comparison, crossing determination. Requires everything else.

This needs a signed amendment narrowing gate `task_duration_complete` to the
scoring stage. That amendment is the highest-value action available this week
and should precede all S3 design work.

**Capture on a deliberately over-inclusive stimulus set.** Raw completions are
storable and re-gradable forever; a dead snapshot is not re-runnable. Capture
against: the 24 constructible S1 instances, the GDPval open subset (by task ID,
under the §7 licence guard), the perturbation battery, and any S3 Phase-2
instances ready by the cutoff. Grading and rubric design happen afterward, at
leisure, against whatever benchmark the S3 process eventually freezes.

## 6. Do not overclaim what v1/v2 established

Mapping A v1 used `all-MiniLM-L6-v2`, a 384-dimension model with a 256-token
window, embedding a ~14-word O*NET statement against a ~276-word prompt plus
~780-word rubric. A frozen 0.80 cosine floor was never going to fire on text
that length-asymmetric. The 0-accept count is therefore *weak* evidence about
substitutability and *strong* evidence about the retrieval implementation.

The load-bearing evidence is the semantic work: D = 0/60 on the development
pairs, and 1 plausible D across 108 audited candidate pairs. Those judgments do
not depend on the embedding, and they support the conclusion. Write the finding
as the structural claim — *GDPval work products and O*NET activities are not the
same unit of analysis, so whole-task transport is unavailable* — rather than the
stronger claim that no semantic correspondence exists. The latter is not
established and invites an obvious referee objection.

There is also a cleaner argument that needs no diagnostic at all: **GDPval
covers 44 occupations; DAX requires 923.** Even a perfect mapping leaves a
coverage ceiling no retrieval fix could clear. This should lead the write-up.

## 7. Option C was dismissed too fast — the cheap version is 220 units

Atomic decomposition was rejected as complex and assumption-heavy. That is true
of the version that decomposes each *pair*. The direction matters: a GDPval task
*subsumes* several O*NET activities, so the tractable annotation runs downward
from the 220, not upward from the 19,259.

For each of the 220 GDPval tasks, annotate the set of O*NET task IDs it
consumes. That is **220 annotation units**, roughly two orders of magnitude
cheaper than S3, and it yields the many-to-one map directly. It will not solve
coverage — still capped at 44 occupations — but it is the natural way to
operationalize the proposal's own item that "GDPval remains useful as an
external/convergent benchmark." Without it, that convergent-validity claim has
no mechanism behind it. Run it in parallel; it is small enough not to compete
with S3 for resources.

## 8. Cost-check S3 before freezing it, and pre-register a fallback tier

GDPval built 220 tasks with a large expert panel and real funding. S3 proposes
384 constructed instances with rubrics — the same order of magnitude. The
project's own cost signal is the duration pilot: $2.6k–$7k for 40 tasks at three
humans each, for *timing*, which is far easier than *construction*. Extrapolating,
384 constructed and validated instances is plausibly a five-to-six-figure,
multi-month commitment.

If that is not funded, S3 as specified is not executable, and freezing it
guarantees a design that fails open — the worst outcome, because the freeze then
gets revisited after results are visible. Cost S3 before freezing, and
pre-register a **fallback tier** in the same signed document: a smaller
constructed set (~120–150 instances) stratified on *wage-bill mass* rather than
task count, so that a funding shortfall triggers a pre-committed smaller design
rather than an improvised one.

Stratifying on wage-bill mass rather than task count is worth doing regardless.
The estimand weights tasks by wage bill; a task-count-stratified sample spends
construction budget uniformly across tasks that contribute very unequally.

## 9. Recommended order of operations

1. **This week.** Draft the amendment splitting W4 capture from W4 scoring, and
   narrow `preflight.py` gate `task_duration_complete` to the scoring stage.
   Get the budget ceiling signed. Probe account availability on the 14 `direct`
   rows. Deadline: 61 days.
2. **Weeks 1–3.** Capture the deadline-bound rows against the over-inclusive
   stimulus set. Store encrypted raw completions with hashes. Do not grade yet.
3. **In parallel, weeks 1–4.** Re-classify the S1 taxonomy on the
   embodiment × channel axes. Re-derive `B`. Run the 220-unit GDPval-downward
   annotation.
4. **Weeks 2–6.** Census machine classification of all 19,259 tasks with the
   dual-vendor protocol; stratified validation sample; error matrix; `B_o` with
   propagated classification error.
5. **Weeks 4–8.** Cost S3. Freeze the S3 packet including the fallback tier, the
   `beta(kappa)` grid, and the `E_ot` vs `B_o * E_ot` regressor choice. Freeze
   before any Phase-2 construction begins.
6. **After.** Duration work, cost/displacement scoring, then W5.

Outcomes stay sealed throughout.

## 10. Where this review could be wrong

- If the `beta(kappa)` sensitivity is judged to be an assumption rather than a
  bound, then §2 is a weaker claim than partial identification and should be
  labelled a sensitivity analysis, not an identified set. I think the label
  matters less than the fact that the level bound in the proposal is not a
  usable bound either.
- The claim that `dN_ot ~ 0` for physical mass depends on the registry
  containing no embodiment events. That is true of the registry as frozen, but
  it is a property of the *inclusion rule*, not of the world. If the 2023–2026
  window in fact saw material physical-task automation driven by something the
  §1.1 rule does not capture, the restriction fails and the `kappa` grid must
  extend above 1.
- §3 predicts `B` rises materially under re-classification. If it does not —
  if the interpersonal mass really is in-person-dominated — then the coverage
  problem is worse than the proposal assumes and the honest conclusion may be
  that the digital estimand is the only reportable object, with occupation-wide
  claims dropped rather than bounded.
