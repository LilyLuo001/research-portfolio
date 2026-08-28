# YAX — research plan v5

**Young-worker AI Exposure.** Third dissertation chapter. Independently
authored. Not the job-market paper.

*Plan date 2026-08-27. Supersedes v4. v1–v4 are retained in full for revision
history and none is deleted.*

> **Naming.** The reframing brief asked for `RESEARCH_PLAN_v3.md`. This
> repository already contains v1–v4 on a different numbering lineage, and the
> same brief asks that revision history be preserved. Writing a second "v3"
> would collide with an existing file and destroy exactly what it asks to keep.
> **The brief's "v3" is this repository's v5.** Nothing else about the request
> is altered by the renumbering.

> **This plan amends a design that is already frozen.** `v1.0-design-freeze`
> (`5fcc502`) is tagged and pushed. **No post-period outcome has ever been
> opened** — the seal is intact and verified. Three frozen elements change here;
> §7 records each one, its reason, and its cost. See
> `FREEZE_AMENDMENT_2026-08-27.md`.

---

## 0. The reframe in one sentence

**AI-exposure measurement is the object of study; the young-worker employment
debate is the empirical laboratory.**

The paper should read as *an AI-exposure measurement paper with the young-worker
employment debate as its empirical test case*, not as *a young-worker
AI-employment paper with seven exposure robustness checks*.

**Pitch.** The labour literature speaks of "AI exposure" as if it were one
treatment. We show how widely used measures construct different versions of
that treatment, identify which occupational comparisons actually generate their
empirical variation, and test whether those definitional choices survive all the
way into the labour-market conclusions economists draw from them.

## 1. The question

> **What exactly is being measured when economists use an "AI exposure" index?
> Do widely used exposure measures represent the same latent economic
> treatment? Where does their identifying variation come from? And do the
> choices embedded in constructing, aggregating, mapping and applying those
> measures materially change the labour-market conclusions drawn from them?**

The motivating question is **no longer** merely whether AI exposure predicts
young-worker employment decline. That question is the laboratory, chosen because
it is a setting where the literature already reports conflicting magnitudes.

The logical sequence the paper must establish:

> **different constructs → different identifying variation → different or
> invariant economic conclusions**

## 2. The headline contribution, and three headlines that are now closed

**The contribution:**

> The empirical AI-and-labour literature treats "AI exposure" as a common
> treatment even though widely used indices are generated from different
> conceptual objects. This paper traces the full measurement pipeline from AI
> capability, to task or ability judgments, to occupational aggregation and
> mapping; identifies the variation that actually drives the resulting
> coefficients; and tests whether alternative definitions of the treatment lead
> to substantively different labour-market conclusions under a common design.

**Do not headline any of these — each is now too close to existing work:**

| retired headline | why it is closed |
|---|---|
| "Crosswalk decisions matter" | one transformation in the pipeline, and not yet shown to be a mistake any published paper made |
| "Different exposure measures give different coefficients" | Frank et al. (2025), Eckhardt--Goldschlag (2025), Pulito et al. (2026), and Brynjolfsson--Chandar--Chen (rev. 2026) already compare coefficient or outcome patterns across measures |
| "AI exposure indices contain measurement error" | Yin–Vu–Persico and Yin–Ogut both formalise non-classical measurement error in exposure scores |

## 3. Layer 1 — Construction: what is X?

The pipeline has three stages and the paper must keep them apart:

**construction → identifying variation → consequence.**

Document how each major measure is built. **These are not two noisy
implementations of an obviously identical construct.**

### 3.1 Felten–Raj–Seamans (AIOE)

    AI applications → relationships to occupational ABILITIES
      → O*NET ability importance and level → occupation-level exposure

Method introduced in *AEA Papers and Proceedings* (2018); the AIOE dataset
extending across occupations, industries and geographies developed in
*Strategic Management Journal* (2021).

### 3.2 Eloundou–Manning–Mishkin–Rock

    LLM capability → human and LLM judgments about task-level time savings
      → TASK exposure → occupation-level exposure

Asks whether an LLM, alone or with complementary software, could substantially
reduce the time required to complete occupational tasks. Both human and model
judgments are used.

**One begins from AI applications and occupational abilities; the other begins
from LLM capabilities and occupational tasks.** So the plan asks, without
assuming the answer:

> **Are these alternative exposure scores noisy measurements of one latent X,
> or are they measurements of different economic constructs?**

Formally: is `X_m = X* + ε_m` a reasonable representation, or is the evidence
more consistent with `X_1 ≠ X_2` because different measures encode genuinely
different occupational constructs?

### 3.3 The other families, classified separately and never pooled mechanically

| family | example | primitive unit |
|---|---|---|
| patent / text-overlap | Webb (2020) | patent–task text overlap |
| platform-usage / conversation-log | usage-derived indices | observed platform interactions |
| realised adoption / use | firm and worker adoption surveys | reported use |
| dynamic capability / benchmark-based | benchmark-tracking indices | model capability over time |
| evidence-grounded / deployment-based | Mouchel–Bouquet–Sheffi (2026) | externally observed deployment |
| capability-to-occupation institutional | OECD (2026) AI Capability Indicators | capability indicators mapped to occupations |
| RL-feasibility | Tomei–Klein Teeselink (2026) | reinforcement-learning trainability |
| commercial targeting | startup-based measure, *PNAS Nexus* (2026) | AI startup activity |

**The paper does not invent a new "best" AI-exposure index unless the evidence
requires it.** The contribution is to diagnose what existing X's measure and
when they can legitimately be interpreted as the same treatment.

## 4. The three empirical tests

### Test A — Construct divergence

Do the major exposure measures load on the same underlying occupational
characteristics? For **every** measure, systematically document relationships
with:

- cognitive task / ability intensity
- manual task intensity
- routine task intensity
- education requirements
- wages
- teleworkability / remotability
- STEM / professional content
- computer use or digital intensity where available

**Do more than report pairwise correlations.** The substantive question is
whether `X_m = X* + ε_m` holds or whether the measures encode different
constructs.

**Rai (2026) is a nearest-neighbour paper, not a peripheral citation.** It
shows that AIOE and Eloundou's GPT-4 scores load heavily on a cognitive-ability
index (correlations 0.85 and 0.70 across 773 occupations), while Webb's
patent-based measure behaves very differently. These values were checked in the
latest MPRA version on 2026-08-28; see
`literature/NOVELTY_AUDIT_2026-08-28.md`. YAX must go **beyond** Rai by
connecting construct divergence to identifying variation and to downstream
labour-market estimates.

### Test B — Identifying-variation divergence

> **Which occupations actually identify an "AI exposure effect" under each
> index?**

For each major measure:

1. rank occupations by raw exposure;
2. residualise exposure against transparent occupational characteristics;
3. report effective concentration of identifying variation;
4. identify the occupations contributing most to the residual variation used by
   the employment regression;
5. compare whether **the same occupations** identify the coefficient across
   indices.

The paper must be able to answer: *when an applied paper reports "the effect of
AI exposure", which actual occupational comparisons generate that coefficient?*

**The existing audit's numbers are promoted from appendix facts to central
measurement results.** Exposure–telework R² runs from ≈0.09 for one Eloundou
measure to ≈0.58 for AIOE; residual variation for Eloundou α concentrates in
roughly 28 effective occupations. These are potentially the paper's core
findings, not technical footnotes.

### Test C — Consequence divergence

Hold **everything** fixed — same CPS data, population, occupation support,
occupation vintage, standardisation, time period, outcome, fixed effects,
inference and estimator — then **change only the definition of X**, and estimate
the young-worker employment coefficient under each exposure construction.

This is the bridge from measurement to economics. Both branches are
interpretable **ex ante**:

- **Divergent** → different definitions of "AI exposure" generate different
  identifying variation and therefore different substantive labour-market
  conclusions, even holding sample, outcome and specification fixed.
- **Invariant** → the exposure constructs differ, but the young-worker result is
  invariant to those differences.

**Do not infer that two coefficients differ merely because one is significant
and one is not.** "No statistically significant difference" is **not** an
equivalence result and may never be written as one.

### 4.1 How Δ is estimated — pre-specified

The object of inference is the **direct difference**

    Δ_{m,m'} = β_m − β_{m'}

not a comparison of significance.

1. **Paired estimation.** For each bootstrap replication, draw **one** set of
   Rademacher cluster weights and apply the **same draw** to every exposure
   definition. Δ is then formed **within replication**, so the sampling
   covariance between β_m and β_{m'} is preserved. Estimating each β on
   independent draws and differencing afterwards overstates Var(Δ) and is
   prohibited.
2. **Same estimation sample.** Δ is computed only on occupations present in
   **both** measures' support. The differing-support comparison is reported
   separately and is never labelled Δ.
3. **Inference.** Percentile-t bootstrap CI for Δ from the paired draws,
   ≥999 replications, clustered on occupation, same seed discipline as the
   power runs.

### 4.2 Two different objects: difference-test precision and equivalence feasibility

**These are not the same quantity and the plan must not conflate them.**

| object | what it answers | role |
|---|---|---|
| **MDE_{Δ,80}** | how large a true difference the design could **detect** | **secondary** precision diagnostic |
| **Equivalence-test power at Δ = 0 under the primary SESOI** | whether the design could **establish** equivalence if the truth were exact equality | **binding feasibility object** |

**A small MDE_{Δ,80} is not by itself evidence that equivalence can be
established.** The difference test asks whether zero can be excluded; the
equivalence test asks whether everything economically meaningful can be
excluded. A design can be precise enough to detect a large difference and still
be unable to fit its interval inside the SESOI.

**Failure to reject Δ = 0 is not equivalence.** It is failure to reject, and it
is reported that way.

#### Why Δ needs its own precision object at all

Because the exposure-specific estimates share a sample and common bootstrap
draws (§4.1), the covariance is preserved:

    Var(Δ) = Var(β_m) + Var(β_m') − 2·Cov(β_m, β_m')

With strongly positively correlated estimates that term dominates, so **SE(Δ)
can be materially smaller — or larger — than the SE of either headline
coefficient.** MDE_β mis-states the design's ability to speak about Δ in either
direction and is never a substitute. *An earlier draft of this section used
MDE_β as the feasibility criterion; that was wrong.*

#### The equivalence claim

Assert that two exposure definitions are **economically equivalent** only when:

- **(a)** the paired CI for Δ lies entirely inside ±SESOI; **and**
- **(b)** the outcome-blind **equivalence-test power at Δ = 0 under the primary
  SESOI** is adequate.

If (b) fails, the design **cannot establish equivalence** and says so. It does
not say the measures are equivalent, and it does not say they differ.

#### The required artifact — outcome-blind, before the amended freeze

One artifact recording, all under **common bootstrap draws** per §4.1:

1. the **paired distribution / SE of Δ**;
2. the **pre-specified equivalence interval**;
3. **equivalence-test power at Δ = 0 under the primary SESOI** — the binding
   object;
4. the **12.5% / 25% / 50% benchmark-margin grid**, as design diagnostics only;
5. **MDE_{Δ,80}**, as a secondary precision statistic.

`gates.py::gate_paired_delta_power` requires all five and names any that are
missing. Item 5 alone does not satisfy it.

### 4.3 The SESOI — economic meaning first, and never widened for power

**Primary SESOI: 25% of the finalized literature-comparable Q5–Q1 benchmark
magnitude.**

> **The numerical value is determined mechanically, and only after that benchmark
> has been put on exactly the same age band, outcome, contrast and scale as
> Test C.** Until §7.3 has done that, the SESOI has no number — only a rule. A
> percentage of a benchmark measured on a different age band, outcome or scale
> is not the same bound and must not be used as one.

**The bound is chosen for economic meaning, not for the power it produces.**

> **Binding, and this is the rule most likely to be quietly broken.** If the
> paired equivalence test is **underpowered at that bound, report the design as
> unable to establish equivalence.** Do **not** widen the bound. A SESOI chosen
> so that the test passes is not a smallest-effect-of-interest; it is the
> largest effect the design happens to tolerate, and reporting it as the former
> is specification search.

The 12.5% / 25% / 50% grid documents feasibility and nothing else. **The primary
is 25% regardless of which point proves most flattering**, no selection among
them may be made on the basis of post-period estimates, and reporting the grid
once outcomes are visible is specification search.

**OWNER-SIGNED-SESOI-RULE (2026-08-28):** the owner approved the 25% rule before
the amended freeze and before any protected post-period outcome was opened. The
rule, economic interpretation and anti-widening commitment are recorded in
`SESOI_OWNER_SIGNOFF_2026-08-28.md`. The numerical SESOI remains mechanically
pending the common-scale benchmark required by §7.3; the sign-off does not turn
an unmatched headline magnitude into that benchmark.

**BENCHMARK-ALIGNMENT STATUS (2026-08-28): BLOCKED.** The latest BCC revision's
19% headline is Q4+Q5 versus Q1--Q3 with no pooled older comparator. Its Table 1
coefficient of −0.179 is Q5--Q1 for ages 22--25, but is a young-only
occupation-level percent-change long difference; older groups are fitted
separately. Neither is YAX's saturated young-relative-to-pooled-26--65
cell-stock PPML/log estimand. No exact published benchmark was located, so no
numerical SESOI is assigned. See `literature/BENCHMARK_ALIGNMENT_2026-08-28.md`.

## 5. Position relative to the nearest competing papers

The novelty claim must be narrower and more defensible than "AI exposure has
never been scrutinised."

| paper | what it establishes | how YAX differs |
|---|---|---|
| **Yin, Vu & Persico (2026)**, NBER 35110 | replicates an Eloundou-style rubric across frontier LLMs; mean exposure diverges ≈3.6×, agreement as low as 57%, downstream individual coefficients vary ≈2.4×, county conclusions can change sign or significance; formalises non-classical measurement error | they study **instability within a nominally fixed rubric when the annotating LLM changes**. YAX studies the **broader pipeline**: different underlying constructs + identifying variation + occupation mapping and common support + downstream consequences under one design |
| **Yin & Ogut (2026)**, arXiv:2605.21743 | platform-log exposure combines task applicability with platform-user composition; changing only the platform input moves the post-ChatGPT employment coefficient ≈1.9×; reweighting to BLS shares attenuates 42–93% | they diagnose **selection in observed-use measures**. YAX diagnoses whether measures from **different conceptual measurement architectures** can be treated as the same explanatory variable |
| **Rai (2026)**, MPRA 129904 | closest to "X may not be X": AIOE and Eloundou largely relabel cognitive content; Webb does not | YAX must go beyond by connecting **construct → identifying variation → mapping/support → economic coefficient** |
| **Frank et al. (2025)**, *PNAS Nexus* 4(4) pgaf107 | individual exposure scores are not strongly consistent and do not individually predict unemployment risk well; an ensemble does better | narrows any novelty claim resting merely on "different measures disagree" |
| **Lund, Euyang, Munyikwa & Fadaee (2026)**, arXiv:2606.23633 | static GPT-style scores have temporal, geographic and ontological limits; surveys dynamic, ensemble, task-extension, worker-centred and usage-based successors | positions YAX as an **empirical test of the consequences** of those ontological differences, not another conceptual critique |
| **Merola, Ernst, Samaan, del Rio-Chanona & Teutloff (ILO, 2026)** | exposure indicators differ conceptually by construction method and measure technological susceptibility, not realised employment effects | institutional validation of the conceptual distinction |
| **OECD (2026)**, AI Papers No. 59 | maps OECD AI Capability Indicators to occupations | another capability-to-occupation architecture for the Table 1 taxonomy |
| **Eckhardt & Goldschlag (2025)**, EIG report and public code | runs several CPS outcomes with five exposure measures and documents alternative SOC-to-Census mapping rules | its measure-specific analyses use separately available support and do not estimate paired coefficient differences or audit the identifying occupations |
| **Budget Lab (2026)** | harmonises seven exposure measures to SOC 2018, builds a PCA summary, and reports public-data labour-market nulls | it documents harmonisation and downstream results but does not run the full cross-family Test A--B--C chain with paired, common-support coefficient contrasts |
| **Pulito, Pytlikova, Schroeder & Lodefalk (2026)** | holds a Danish firm-adoption outcome and specification fixed while comparing five occupation-based exposure indices; predictive associations differ by measure | this is the closest same-outcome/same-specification predecessor. It validates indices against observed adoption, but does not audit construct content, mapping/common support, identifying influence, or paired coefficient differences, and does not study the contested young-worker labour-market conclusion |
| **Brynjolfsson, Chandar & Chen (revised August 2026)** | studies 22--25 employment stocks through June 2026, reports robustness across five alternative exposure measures, improves its SOC crosswalk, controls for remote work, and benchmarks against CPS/ACS | it establishes that alternative measures are already part of the live employment debate. It does not report a cross-family construct and influence audit, a fixed common-support comparison, or direct paired inference for coefficient differences |
| **Emanuel, Harrington & Pallais (QJE 2026)** | national CPS DDD shows the young-college-graduate unemployment increase concentrated in remotable jobs and robust to an occupational generative-AI control | remote work is therefore a core rival mechanism; the paper does not compare AI-exposure measurement architectures |

**Tracked but not central:** Mouchel–Bouquet–Sheffi (2026) on evidence-grounded
rather than model-prior measurement; Tomei–Klein Teeselink (2026) on
RL-feasibility exposure and its sharp divergence from existing indices; the
startup-based measure in *PNAS Nexus* (2026) moving from theoretical capability
toward realised commercial targeting.

### 5.1 Verification status — completed 2026-08-28

Every §5 and §14 source was opened at its primary source in a genuine
latest-version search on 2026-08-28. The source-by-source record, version dates,
locators, file hashes, search queries and boundary table are preserved in:

- `literature/NOVELTY_AUDIT_2026-08-28.md`;
- `literature/NOVELTY_AUDIT_RECEIPT_2026-08-28.json`;
- `literature/PUBLISHED_MEASUREMENT_AUDIT_2026-08-28.md`.

> **Version rule.** When a working paper has a later published or substantially
> revised version, the novelty audit must use the **latest** version and record
> the version and the date checked. Source verification without version
> verification is not verification.

The Emanuel–Harrington–Pallais case is why this rule exists: the v1.0 audit
opened NBER 31880 (November 2023), concluded the paper was far from this design,
and was wrong about the latest paper. The published QJE version (141(3), August
2026, 1825--1870) contains a national CPS young-worker analysis and was therefore
used in the completed audit.

**NOVELTY-GATE: all references opened at primary source.** This assertion is
backed by the receipts above; file sources carry sha256 values. The gate failed
open twice in earlier versions by keying on the absence of warning words, so the
positive assertion and receipts are retained together.

**The novelty gate must search working papers, not only published economics
journals.** The literature is moving fast enough that a published-only search
is not a search.

### 5.2 The revised novelty standard

> **Existing work has shown that exposure instruments disagree, may be unstable
> or selected, and can produce different predictive or labour-market patterns.
> What remains unresolved is the integrated chain: whether major exposure
> families represent a common economic treatment, which occupations identify
> their coefficients after transparent harmonisation, how mapping and common
> support alter that variation, and whether paired changes in X alone move the
> contested young-worker conclusion under one frozen public-data design.**

Search aggressively for any paper already doing the full
construct → identifying variation → downstream consequence exercise. **If one
exists, update or kill the claim before opening post outcomes.**

### 5.3 Novelty claims retired or narrowed

| claim | status |
|---|---|
| "Nobody has looked at young vs older in CPS" | **retired** at v4 — Dallas Fed and Anthropic publish related patterns |
| "The crosswalk decision is the contribution" | **retired** here — demoted to one pipeline layer, §6 |
| "Different exposure measures give different coefficients" | **retired** here — Frank et al. (2025), EIG, Pulito et al. (2026), and BCC (rev. 2026) |
| "AI exposure indices contain measurement error" | **retired** here — Yin–Vu–Persico, Yin–Ogut |
| "Computerization is not one interchangeable control" | **narrowed** — retained as a finding about controls, not the headline |
| "A pre-registered, power-stated public-data test does not exist" | **narrowed** — verified true for the employment question at v4; must be re-verified for the *measurement* question this plan now asks |
| Pre-registration, MDE and crosswalk hygiene as the contribution | **retired** — they are credibility devices, §10 |

## 6. Crosswalk demoted, and the published-measurement audit that must precede any claim

The v4 hierarchy made crosswalk vintage the central table and ran the seven
exposure measures as a separate robustness table. **Reverse that.**

Crosswalk and vintage remain important — a naive exact-code AIOE merge covers
**3.33%** of computer and mathematical employment where vintage repair raises it
to **97.7%**. But that is evidence about **one transformation in the measurement
pipeline. It is not yet evidence that any published paper made that mistake.**

**Before any claim about published estimates**, build a **published-measurement
audit** recording, for each benchmark study:

- exposure measure
- native occupation taxonomy / vintage
- outcome-data occupation taxonomy / vintage
- actual crosswalk procedure
- coverage / common support
- age definition
- outcome definition
- standardisation
- **whether the mapping can be replicated**

> **Do not compare serious published work to a deliberately naive merge unless
> the published work actually used that merge.** This is binding.

## 7. Amendments to `v1.0-design-freeze`

Three frozen elements change. The seal is intact — no outcome has been opened —
so these are legitimate pre-outcome amendments, documented rather than silent.
`FREEZE_AMENDMENT_2026-08-27.md` carries the full record.

### 7.1 Treatment timing — CORRECTED, this was an error

**ChatGPT was released 30 November 2022, after the November CPS reference
week.** Defining November 2022 as post is therefore wrong on the calendar, and
defining December 2022 as fully post treats a month containing one day of
availability as fully treated.

| month | v1.0 freeze | v5 |
|---|---|---|
| 2022-11 | pre | **pre** (unchanged) |
| 2022-12 | **post** | **transition — first event-study exposure month, excluded from the static post window** |
| 2023-01 onward | post | **primary static post period** |

This is a factual correction, not a preference.

### 7.2 Coverage rule — primary changes from Rule B to Rule A

v1.0 froze **Rule B** (sibling-imputed, `s_c ≥ 0.95`) as primary, from
`COVERAGE_RULE_PRESPEC_v1.md`. **v5 makes Rule A — strict — the primary
estimand**, with the population stated as the full-component
published-exposure support covering **88.70%** of eligible employment.

Reason, as the reframing brief puts it: use the strict support as the primary
estimand *rather than imputing in order to pass the old 90% gate*. The sequence
a reader sees under Rule B is gate failed → imputation adopted → gate passes,
and ex-ante justification does not repair how that reads.

Rules B and C remain **reported as columns in every results table**, and the
excluded occupations remain named. The failed 90% rule and its receipt are
preserved permanently.

### 7.3 MDE estimand — must be recomputed on a literature-comparable contrast

The frozen MDEs are **per one weighted SD of AI exposure**: β×O\*NET 2.27%
[2.22, 2.32], α×O\*NET 1.36%, β×Webb 1.24%, α×Webb 1.23%, at β_C = log 0.95,
bootstrap null sizes 0.036–0.060.

**Those may not be compared to a published 19% high-versus-low exposure gap.**
Different contrasts. Define a literature-comparable contrast — **Q5–Q1** — and
compute **both the benchmark and the MDE on that same estimand**.

Nobody may write that conditioning improved precision from 3.44% to 2.27%: the
3.44% was a Q5–Q1 contrast and the 2.27% is per-SD.

**Ages 22–25 are the frozen primary young definition, not an additional
benchmark.** `DESIGN_FREEZE_v1.md` §1 sets Young = 22–25 against a 26–65
comparison, and that is unchanged. It is *simultaneously* the
literature-comparable band, because the administrative-data literature uses that
range — so no separate benchmark specification is required and none is added.
Earlier plans (v1–v3) used 20–29 primary with 16–24 and 22–27 as alternates;
that scheme was superseded at v4 and is not revived. Any broader band would be
an addition to the frozen design and is therefore out of scope for this
amendment.

**Audit result (2026-08-28):** no published source located supplies that exact
common-scale benchmark. BCC's 19% and −0.179 candidates fail the required
contrast/pooled-comparator/estimator alignment described above. The numerical
SESOI and binding equivalence calculation remain blocked; no shortcut is used.
Full receipt: `literature/BENCHMARK_ALIGNMENT_RECEIPT_2026-08-28.json`.

### 7.4 Unit of observation — stated explicitly, ambiguity closed

v4 §7 referred to individual employment via `EMPSTAT` while §5 specified an
occupation-month stock PPML. **The primary unit is the cell, not the
individual:**

> **occupation × age-group × month employment stock**, estimated by Poisson
> pseudo-maximum-likelihood on counts `N_oat`.

`EMPSTAT ∈ {10, 12}` defines who is counted as employed **when building the
cell**; it is not itself the unit. **A non-employed person is never assigned an
occupation** and therefore never receives occupational exposure. Exposure is a
property of the cell's occupation.

**One observation** = one occupation × age-group × month cell. **The outcome**
is the weighted employment headcount in that cell, `N_oat` — an employment
*stock*, not an individual employment status.

**Exact interpretation of the headline coefficient.** β_AI is the difference
between the post-period change in log young-worker employment and the
post-period change in log older-worker employment, per one unit of AI exposure,
within occupation and within month, after conditioning on the same contrast for
computerization. Reported per one employment-weighted SD of exposure and, per
§7.3, on the Q5–Q1 contrast as well.

**Entrants and the non-employed.** Because the unit is a cell of employed
workers, a person with no occupation contributes to no cell. Entrants with no
prior occupation are therefore **not assigned exposure and do not appear in the
denominator**; they enter the data only once employed, in the cell of the
occupation they enter. Nothing is imputed.

**The interpretive limit this creates — three channels, not two.** A decline in
an occupation × age-group employment stock can arise from:

1. **reduced entry** into employment in that occupation;
2. **exit from employment** altogether;
3. **occupational switching while remaining employed** — a young worker moving
   out of a high-exposure occupation into a lower-exposure one, with no
   employment loss at any point.

**The primary stock design cannot distinguish these channels.** Channel 3 is the
one most easily overlooked and it is not an employment effect at all.

> **Binding on the prose.** The headline coefficient **must not be interpreted
> as an individual employment-probability effect** unless a separate flow
> analysis supports that statement. A stock decline is a statement about where
> employed young workers are, not about whether young workers are employed.

The hiring-versus-separation-versus-switching decomposition is a distinct
exercise on distinct outcomes and is out of scope for this design.

### 7.5 Saturated DDD — confirmed compliant, stated

**The frozen equation, quoted verbatim from `DESIGN_FREEZE_v1.md` §1:**

    E[N_oat] = exp[ γ_oa + δ_ot + λ_at
                    + β_AI (AI_o × Young_a × Post_t)
                    + β_C  (Comp_o × Young_a × Post_t) ]

**Every lower-order component is absorbed by a fixed effect. None is estimated
as a free parameter, and none is omitted.** Exposure is time-invariant — frozen
at its 2021 vintage — so each interaction is a function of exactly one
fixed-effect pair:

| lower-order term | is a function of | absorbed by | status |
|---|---|---|---|
| Young × Post | (age-group, month) | `λ_at` | **absorbed** |
| Exposure × Post | (occupation, month) | `δ_ot` | **absorbed** |
| Exposure × Young | (occupation, age-group) | `γ_oa` | **absorbed** |
| occupation × age-group | — | `γ_oa` | **included** |
| age-group × month | — | `λ_at` | **included** |
| occupation × month | — | `δ_ot` | **included** |

**What identifies β_AI.** Within a given occupation and a given month, take the
young-versus-older employment gap. `γ_oa` removes each occupation's own
time-invariant young-versus-older level, `λ_at` removes the economy-wide
young-versus-older path, and `δ_ot` removes everything that moves an
occupation's employment over time regardless of age. What survives is the
**change in the within-occupation young-versus-older gap across occupations that
differ in pre-defined exposure**, conditional on the same contrast for
computerization. That, and only that, is β_AI.

No change to the design; enumerated because assertion is not confirmation.

## 8. Tables and figures — new hierarchy

### Table 1 — Anatomy of AI Exposure Measures

For every major index: original paper; technology being measured; primitive unit
(task / ability / patent / observed use / adoption); source of AI capability
information; who labels exposure (crowd / human experts / LLM / observed
behaviour); exposure definition; aggregation rule; occupational taxonomy and
vintage; treatment interpretation.

### Figure 1 — Measurement Genealogy

    AI technology / capability
      → task or ability assessment
        → occupation exposure
          → taxonomy / crosswalk
            → common support
              → standardised treatment used in regression

Show where each existing measure enters the pipeline.

### Table / Figure 2 — Construct and Identifying-Variation Audit

Per index: correlations with transparent occupational characteristics; residual
correlations; effective number of occupations; occupations contributing most
identifying variation; overlap in high and low exposure rankings.

### Table 3 — Mapping and Common-Support Audit

Proper vintage mapping; published mapping where replicable; common support;
excluded employment mass.

### Table 4 — Same Y, Same Design, Different X — **the central downstream test**

Hold sample, specification and outcome fixed; vary only exposure construction.
Report coefficients; **paired** coefficient differences Δ per §4.1; percentile-t
bootstrap CIs from common draws; the §4.2 equivalence bound. **Never** infer a
difference from one coefficient being significant and another not, and never
report "no significant difference" as equivalence.

### Table 5 — AI Exposure vs Remote-Work Exposure

**Remote work is a core competing explanation, not a minor robustness row.**
Emanuel, Harrington & Pallais, **"The Power of Proximity to Coworkers,"
*Quarterly Journal of Economics* 141(3), August 2026, 1825–1870, DOI
`10.1093/qje/qjag027`**, reports that the post-pandemic rise in young college
graduates' unemployment is **concentrated in remotable occupations**, and
reports robustness to occupational generative-AI exposure with age × post
interactions.

**Correction to the v1.0 novelty record.** That audit verified only NBER working
paper 31880 (November 2023), a within-firm study of junior versus senior
software engineers whose outcome is not employment, and concluded on that basis
that EHP was "farther from this design than §9a previously implied." **The
published QJE version contains a national CPS young-worker analysis and is much
closer.** The NBER version is not the final state of the paper. The QJE article
and its published specifications were opened on 2026-08-28 and are recorded in
the novelty receipt.

**This paper is a principal reason remote work is a core rival explanation
rather than a robustness row.**

Estimate at least: (1) AI exposure only; (2) remote-work exposure only; (3) AI
and remote-work jointly; (4) the joint model under alternative AI-exposure
constructions.

## 9. What is established and what is not

**Established** (v1.0 freeze artifacts, all pre-period or simulation):

| fact | value |
|---|---|
| Wide CPS extract | 9,262,480 rows, 2017-01 → 2026-07 |
| Outcome-blind pre-period file | 6,188,956 rows |
| Pinned support | 490 balanced Census-2018 clusters × 66 months, cells sha256 `4b8c8b96…` |
| Joint-model conditional MDE80, per SD | β×O\*NET 2.27%, α×O\*NET 1.36%, β×Webb 1.24%, α×Webb 1.23% |
| Bootstrap null size | 0.036–0.060 against nominal 0.05 |
| Computer/math coverage, naive vs repaired | 3.33% → 97.7% |
| Strict coverage rule | 88.70% |
| Construct validity, five computerization measures | rankings coherent, documented |

**Not established:**

1. The Q5–Q1 MDE and benchmark on a common estimand — §7.3.
2. Any protected post-period YAX coefficient. The seal holds.
3. Whether future work appearing after the 2026-08-28 audit date duplicates the
   chain; the current search found no full-chain paper, but did find close
   component predecessors, especially Pulito et al. and BCC.

## 10. Credibility devices — preserved, and explicitly not the contribution

Retained in full: the outcome-blind seal; pre-specification; the machine-checked
freeze; wild-cluster bootstrap; MDE calculation; explicit common support; strict
88.70% support as the primary estimand; reporting of excluded occupations; no
specification search.

> **But preregistration, MDE and crosswalk hygiene are not the headline economic
> contribution.** They make the measurement conclusions credible. They are not
> the main intellectual claim. v4 had this backwards and said so about v2; v5
> corrects it one level further.

## 11. Kill conditions

1. **A paper already runs construct → identifying variation → consequence.**
   Update or kill the claim before opening post outcomes.
2. **A material 2017–2019 AI gradient**, conditional on computerization. Rejects
   the simple parallel-trends interpretation; report it and either estimate a
   pre-specified differential-trend model or restrict to descriptive
   decomposition. It does not by itself establish what the measure represents.
3. **The seal breaks before the amended tag.** The chapter can be written but
   must be labelled post-hoc.
4. **The Q5–Q1 MDE approaches the contested magnitude.**

## 12. Seal protocol — amended

1. `FREEZE_AMENDMENT_2026-08-27.md` committed. *(this change)*
2. Novelty gate re-run against every §5 primary source. *(complete 2026-08-28, §5.1)*
3. Coverage primary switched to Rule A in a `COVERAGE_RULE_PRESPEC_v2.md`,
   preserving v1 and its receipt. *(§7.2)*
4. Post-period redefined to 2023-01 static, 2022-12 transition; power
   re-simulated on the new window. *(§7.1)*
5. Q5–Q1 MDE and benchmark computed on one estimand. *(§7.3)*
5b. **The paired-equivalence precision artifact** — all five components of
   §4.2, outcome-blind, under common bootstrap draws. The binding object is
   equivalence-test power at Δ = 0 under the primary SESOI; MDE_{Δ,80} is
   secondary. *(§4.2–4.3)*
5c. **Owner decision on the primary SESOI** — **COMPLETE: 25% rule signed
    2026-08-28; numerical value still awaits the common-scale benchmark.**
    *(§4.3; `SESOI_OWNER_SIGNOFF_2026-08-28.md`)*
6. Published-measurement audit built. *(§6)*
7. `DESIGN_FREEZE_v2.md` committed; tag `v1.1-design-freeze`.
8. **Only then** may a post-period outcome be opened.

`v1.0-design-freeze` is **never deleted or moved.** It is the record that the
original specification preceded any outcome, and the amendment record explains
what changed while the seal still held.

Machine-checked: `python yax/gates.py --power-aggregate <aggregate>.json`.

## 13. Standing rules

- LLM output is not a source of facts.
- Don't know → stop. `NEED_HUMAN`, never guess-fill.
- Never specification-search. First run of a frozen table is the reported run.
- Licensed microdata never enters the git work tree. Never `git add -A`.
- A sentence describing a computed number must be checkable against the
  artifact that produced it.
- State which statistic answers the question before computing one.
- A measure agreeing with no other is a question, not a verdict.
- A plan may not assert as settled anything its own later sections list as
  pending.
- **A relayed citation is not a citation.** Every reference is opened at its
  primary source with a locator before it is used. Added at v5, because this
  reframe arrived with a dozen references attached and the novelty gate's whole
  value is that it refused to take relayed claims on trust.
- **A stale version is not the paper.** Where a later published or substantially
  revised version exists, the audit uses it and records version and date
  checked. Added at v5 after the EHP case, where the correct source was opened
  at the wrong vintage and produced a wrong conclusion — see §5.1.

## 14. Verified references in the YAX literature file

**All entries below were opened at their latest primary source on 2026-08-28;
locators and file hashes are in the novelty receipt — §5.1.**

Felten, Edward W., Manav Raj, and Robert Seamans. 2018. "A Method to Link
Advances in Artificial Intelligence to Occupational Abilities." *AEA Papers and
Proceedings* 108: 54–57. doi:10.1257/pandp.20181021.

Felten, Edward, Manav Raj, and Robert Seamans. 2021. "Occupational, Industry,
and Geographic Exposure to Artificial Intelligence: A Novel Dataset and Its
Potential Uses." *Strategic Management Journal* 42(12): 2195–2217.
doi:10.1002/smj.3286.

Eloundou, Tyna, Sam Manning, Pamela Mishkin, and Daniel Rock. 2024. "GPTs Are
GPTs: Labor Market Impact Potential of LLMs." *Science* 384(6702): 1306–1308.
doi:10.1126/science.adj0998.

Yin, Michelle, Hoa Vu, and Claudia Persico. 2026. "How (un)Stable Are LLM
Occupational Exposure Scores? Evidence from Multi-Model Replication." NBER
Working Paper 35110. doi:10.3386/w35110. **Nearest-neighbour / mandatory.**

Yin, Michelle, and Burhan Ogut. 2026. "Who Uses AI? Platform Selection and the
Measurement of Occupational AI Exposure." arXiv:2605.21743. **Nearest-neighbour
/ mandatory.**

Rai, Sudhanshu. 2026. "Do AI Occupational-Exposure Scores Measure AI? AIOE and
Eloundou (2024) Largely Capture Cognitive Content; Webb (2020) Does Not." MPRA
Paper 129904. **Nearest-neighbour / mandatory.**

Frank, Morgan R., et al. 2025. "AI Exposure Predicts Unemployment Risk: A New
Approach to Technology-Driven Job Loss." *PNAS Nexus* 4(4), pgaf107.

Lund, Campbell, Thomas Euyang, Zanele Munyikwa, and Marzieh Fadaee. 2026. "AI
Exposure Scores: What They Measure, What They Miss, and What Comes Next."
arXiv:2606.23633.

Merola, Rossana, Ekkehard Ernst, Daniel Samaan, Maria del Rio-Chanona, and Ole
Teutloff. 2026. "Workers' Exposure to AI: What Indicators Tell Us — and What
They Don't." International Labour Organization Research Brief.
doi:10.54394/00033279.

OECD. 2026. *The OECD AI Exposure Measure: Mapping the OECD AI Capability
Indicators to Occupations.* OECD Artificial Intelligence Papers No. 59.
doi:10.1787/f3da0f0a-en.

Mouchel, Luca, Pierre Bouquet, and Yossi Sheffi. 2026. "Jobs' AI Exposure Should
Be Measured from Evidence, Not Model Priors." arXiv:2605.15474.

Tomei, Philip Moreira, and Bouke Klein Teeselink. 2026. "What Jobs Can AI Learn?
Measuring Exposure by Reinforcement Learning." arXiv:2605.02598.

Eckhardt, Sarah, and Nathan Goldschlag. 2025. *AI and Jobs: The Final Word
(Until the Next One).* Economic Innovation Group, August 10. Public code
repository checked at commit `a65ce97d9fa6ed931af12fb37321fec363a9c15f`.

Budget Lab at Yale. 2026. "Labor Market AI Exposure: What Do We Know?"
February 19; and "What We Do and Don't Know About How AI is Affecting the Labor
Market," May 7.

Emanuel, Natalia, Emma Harrington, and Amanda Pallais. 2026. "The Power of
Proximity to Coworkers." *Quarterly Journal of Economics* 141(3): 1825--1870.
doi:10.1093/qje/qjag027.

Pulito, Giuseppe, Mariola Pytlikova, Sarah Schroeder, and Magnus Lodefalk.
2026. "Who Adopts AI? Evidence on Firms, Technologies and Workers." Örebro
University School of Business Working Paper 3/2026, March 27.

Brynjolfsson, Erik, Bharat Chandar, and Ruyu Chen. 2026. "Canaries in the Coal
Mine? Six Facts about the Recent Employment Effects of Artificial
Intelligence." Stanford Digital Economy Lab, revised August 12.

Fenoaltea, Enrico Maria, et al. 2026. "Follow the Money: A Startup-Based
Measure of AI Exposure Across Occupations, Industries, and Regions."
*PNAS Nexus* 5(6): pgag185.

del Rio-Chanona, R. Maria, et al. 2025. "AI and Jobs: A Review of Theory,
Estimates, and Evidence." arXiv:2509.15265.

Steele, Jennifer L., and Isabella Cruz. 2026. "Helping People Choose Careers in
the Age of AI." arXiv:2607.15506.
