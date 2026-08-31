# Amendment to `v1.0-design-freeze`

**Date:** 2026-08-27. **Trigger:** a reframing brief from the owner.
**Seal status at time of amendment: INTACT — zero post-period outcomes opened,
verified by `gates.py::gate_seal` and `git ls-files yax/analysis/outcomes`.**

`v1.0-design-freeze` (`5fcc502`) is **never deleted and never moved.** It is the
permanent record that the original specification preceded any outcome. This file
records what changed afterwards, while the seal still held, and what it cost.

## Why this is legitimate, and where the limit is

A design freeze proves one thing: the specification was not chosen in light of
the results. **No result exists.** The post-period file has never been opened.
An amendment made in that state does not damage the claim, provided the original
is preserved, the change is documented, and the reason is stated. All three hold.

**Terminology, corrected.** These are **pre-outcome amendments to the initial
design freeze**. An earlier draft of this record called them "post-hoc design
changes." That was wrong and prejudicial: in this literature *post hoc* means
*after seeing results*, and no result exists. The paper must disclose the full
revision history **and** distinguish pre-outcome design revision from
post-outcome specification search — they are not the same act and should not
share a word.

**This is nonetheless the second pre-outcome amendment in one day** — the
computerization dimension was added 2026-08-26 (plan §13a), and this is
2026-08-27. Each is individually defensible; the pattern is what needs watching.

> **Standing limit, recorded here so it can be held to:** further amendments
> after this one start to erode the claim even with the seal intact, because
> "the specification was fixed before any outcome" stays literally true while
> "fixed in advance" becomes hard to distinguish from "fixed whenever we last
> stopped changing it." The next amendment should be the last, or the paper
> should describe the design as settled at `v1.1` and claim no more than that.

## The three substantive changes

### 1. Treatment timing — a factual correction

ChatGPT was released **30 November 2022**, after the November CPS reference
week. `v1.0` set `Post = 2022-12 onward`, which treats a month containing one
day of general availability as fully treated.

| month | v1.0 | v1.1 |
|---|---|---|
| 2022-11 | pre | pre — unchanged |
| 2022-12 | **post** | **transition**; first event-study exposure month, excluded from the static post window |
| 2023-01 → | post | **primary static post period** |

**Cost:** the joint power simulation was run on a 43-month post window starting
2022-12. It must be re-run on the new window. The frozen MDEs do not describe
the amended design.

### 2. Coverage rule — primary moves from Rule B to Rule A

`v1.0` froze **Rule B** (sibling-imputed, `s_c ≥ 0.95`) as primary, following
`COVERAGE_RULE_PRESPEC_v1.md`. **v1.1 makes Rule A — strict — primary**, and
states the estimand as the full-component published-exposure support covering
**88.70%** of eligible employment.

The reasoning is the one recorded in plan v4 §6 and not acted on then: under
Rule B the sequence a reader sees is *gate failed → imputation adopted → gate
passes*, and ex-ante justification of the 0.95 threshold does not repair how
that reads.

Rules B and C stay as reported columns in every table; excluded occupations stay
named; the failed 90% rule and its receipt are preserved.

**Cost:** `COVERAGE_RULE_PRESPEC_v1.md` said in terms that "the primary is Rule
B, fixed here. It does not change because another rule gives a cleaner result."
That sentence is now overridden. It is overridden **before any result exists**,
which is the only circumstance in which it could be — but the override must be
disclosed in the paper, not quietly absorbed.

### 3. MDE estimand — must be recomputed on a literature-comparable contrast

The frozen MDEs are **per one weighted SD of AI exposure**:

| | O\*NET (VIF 2.74) | Webb (VIF 1.00) |
|---|---|---|
| β | 2.27% [2.22, 2.32] | 1.24% |
| α | 1.36% [1.34, 1.39] | 1.23% |

at β_C = log 0.95, bootstrap null sizes 0.036–0.060.

These **may not be compared to a published 19% high-versus-low exposure gap** —
different contrasts. Define **Q5–Q1** and compute both the benchmark and the MDE
on that one estimand.

**Nobody may write that conditioning improved precision from 3.44% to 2.27%.**
The 3.44% was a Q5–Q1 contrast; the 2.27% is per-SD. A Q5–Q1 gap spans several
SD, so the conditional MDE on that scale is *larger* than 3.44%, exactly as VIF
inflation predicts.

The **22–25 age specification is retained** as a frozen literature-comparable
benchmark.

## Two clarifications that change no numbers

**Unit of observation.** The primary unit is the **cell** — occupation ×
age-group × month employment stock, PPML on counts `N_oat`. `EMPSTAT ∈ {10, 12}`
defines who is counted when building the cell; it is not the unit. **A
non-employed person is never assigned an occupation** and never receives
occupational exposure. v4 §7 referred to individual employment and §5 to a stock
PPML; the ambiguity is closed in favour of the cell.

**And the limitation that follows from it.** A decline in an occupation ×
age-group employment stock can arise from **(i)** reduced entry into employment
in that occupation, **(ii)** exit from employment, or **(iii)** occupational
switching while remaining employed. **The primary stock design cannot
distinguish these three channels**, and channel (iii) is not an employment
effect at all. **The headline coefficient must not be interpreted as an
individual employment-probability effect unless a separate flow analysis
supports that statement.** Binding on the paper's prose, not merely on its
tables. See plan v5 §7.4.

**Saturated DDD.** Already compliant — occupation × age-group, occupation ×
month and age-group × month fixed effects absorb all relevant lower-order
interactions. Identifying variation is the within-occupation, within-month
young-versus-older difference. Recorded because the brief requires it explicit.

## The novelty gate re-opens

`v1.0` passed its novelty gate because every §9a row was opened at its primary
source with a locator and, where applicable, a sha256. The reframe arrives with
a dozen references and a set of quoted figures — 3.6×, 57%, 2.4×, 1.9×, 42–93%,
0.85, 0.70, 773 occupations — **all relayed, none verified here.**

The gate is BLOCKED again until each is opened at source. That is a real cost of
the reframe and is recorded as one rather than waved through. It also produced a
new standing rule: **a relayed citation is not a citation.**

One specific item to check rather than assume: the brief cites *The Power of
Proximity to Coworkers* as a **QJE 2026** paper documenting adverse
post-pandemic outcomes for young workers in remotable occupations surviving
generative-AI controls. The v1.0 novelty gate verified only **NBER working paper
31880, November 2023**, a within-firm study of junior versus senior software
engineers whose outcome is not employment. Those may be different versions or
the attribution may be wrong. Open it before citing it.

## What is unchanged

The pinned support (490 balanced Census-2018 clusters × 66 pre-period months,
cells sha256 `4b8c8b96…`); β primary with α as the pre-specified contrast; all
five computerization measures reported as distinct constructs; the estimating
equation's fixed-effect structure; wild-cluster bootstrap as primary inference;
the outcome-blind seal; and the rule that the first run of a frozen table is the
reported run.

## Path to `v1.1-design-freeze`

Plan v5 §12. In short: this record, then the novelty re-verification, then
`COVERAGE_RULE_PRESPEC_v2.md`, then the re-simulated power on the 2023-01 post
window, then the Q5–Q1 estimand, then the published-measurement audit, then
`DESIGN_FREEZE_v2.md` and the `v1.1-design-freeze` tag. **Only then** may a
post-period outcome be opened.

## Owner sign-off added 2026-08-28 — Test C SESOI rule

Before any protected post-period outcome was opened, the owner approved:

    SESOI = 25% × |final literature-comparable Q5–Q1 benchmark|

This is a rule rather than a numerical value. The number is generated only
after the benchmark and Test C share the same age band, outcome, Q5–Q1 contrast,
unit/estimand and functional scale. It will not be widened if paired-equivalence
power is weak. In that event the paper reports that it cannot establish
equivalence. Full record: `SESOI_OWNER_SIGNOFF_2026-08-28.md`.

## Novelty and published-measurement audits completed 2026-08-28

The blocked state recorded above is preserved as the state at amendment time.
It was resolved before any protected post-period YAX outcome was opened. The
latest-version audit found no paper completing the full YAX chain, but found a
materially closer predecessor absent from the inherited plan: Pulito,
Pytlikova, Schroeder and Lodefalk (2026) hold a firm-adoption outcome and design
fixed while comparing five occupational exposure measures. The August 2026 BCC
revision also compares measures in the exact young-worker debate and documents
an improved crosswalk and remote-work controls.

Accordingly, YAX no longer claims novelty for comparing measures, harmonising
them, or obtaining different coefficients. Its remaining claim is the joint
construct → identifying-occupation → mapping/common-support → paired downstream
chain under one frozen public-data design. Source locators, version dates, file
hashes, the boundary table and the published-measurement audit are in
`literature/`. The novelty gate now passes on that narrower record.

## Common-scale benchmark audit completed 2026-08-28 — unresolved

The August 2026 BCC revision is the closest source, but its 19% headline is a
Q4+Q5 versus Q1--Q3 kept-pace comparison and its −0.179 Table 1 coefficient is
a Q5--Q1 percent-change long difference for ages 22--25 alone. The paper fits
older age groups separately; it does not publish YAX's young-relative-to-pooled-
26--65 saturated cell-stock PPML/log estimand. The separate older coefficients
cannot be mechanically pooled into that nonlinear estimand from the published
table.

No exact benchmark was located. The owner-signed rule is unchanged, the
numerical SESOI remains undefined, and the paired-equivalence/freeze gate must
remain blocked. Full source hash, alignment table and rejected shortcuts:
`literature/BENCHMARK_ALIGNMENT_2026-08-28.md`.

The outcome-blind SCC execution nevertheless completed the estimable precision
objects on 2026-08-28. Four corrected January-2023 joint-power scenarios pass
gradient and calibration gates. The paired beta-versus-alpha run used 999
common draws with zero failures: `SE(Delta)=0.011672` and
`MDE_{Delta,80}=0.032722` log points (3.326% relative magnitude). These numbers
do not resolve equivalence. The interval, equivalence power and margin grid
remain null, so `paired_delta_power` remains BLOCKED exactly as the signed rule
requires. See `power/PAIRED_EQUIVALENCE_PRECISION_NOTE.md`.
