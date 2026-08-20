# P1 — everything WRDS will NOT fix

_seat C, 2026-08-18. Written because the owner is procuring WRDS and asked which
problems survive it. Every claim below is checked against the repo or run in this
container today; nothing is carried over from another session's word._

WRDS clears a lot: it unblocks T2-on-permno, T4, T5, the data column of the T3
spec, and — usefully — two of the three semantic questions in `p1/wrds/tables.yaml`,
because WRDS's own variable documentation is on the platform. What follows is what
it does **not** clear.

Two groups. Group A needs someone or something outside this container. Group B is
blocked by nothing at all and is being worked now.

---

## GROUP A — survives WRDS, needs the owner or another lane

### A1. The literature package (文献包) — blocks T3, and later T9
The T3 prompt demands a literature locator for every variable's 口径, and T9's
writing rules say citations may only come from the T0 literature matrix
(`docs/Project_1.md` §60, §124-125, §187). **That matrix was never produced.** T0
executed 阶段B (the collision sweep) only; no queue id covers 阶段A. Itemised
CITE_REQUEST — ten conventions — is in `p1/t3_spec_preflight.md`.

WRDS is data, not literature. This blocker is completely orthogonal to it.

**Not doable here either:** literature retrieval needs egress this container does
not have. Verified today, not assumed — `papers.ssrn.com`, `export.arxiv.org`,
`api.semanticscholar.org`, `doi.org` and `www.federalreserve.gov` all return 000.
Needs a lane with web access, or the owner's browser.

### A2. The ConvExp denominator-recovery run — blocks a publishable ConvExp
`recover_denominators.py --online` needs SEC / Yahoo / Stooq. Same egress wall.
Until it runs, the coverage audit's central claim — that recovery leaves the
≥0.5% treated set unchanged — stays an expectation. Everything it needs is
committed and the sidecar that makes it computable landed in 570a6b8. Runbook:
`ops/briefs/P1-T2-recovery-BOX.md`.

WRDS could *substitute* for this (CRSP shrout supplies the missing denominators
directly), so this one is the exception: WRDS does not fix the free path, but it
may make the free path's gap moot. That is itself worth knowing — see B4.

### A3. The Saglam–Tuzun FEDS Note PDF — blocks half of T4
T4's output is a side-by-side of their coefficients (transcribed with page
numbers) against ours. The pipeline half needs CRSP; **the transcription half
needs the PDF**, which `docs/Project_1.md` §T4 says the owner provides. WRDS does
not contain it, and federalreserve.gov is behind the same egress wall.

### A4. Spine-three mechanism data — already degraded by design
Creation/redemption frequency, premium/discount half-life, ETF arbitrage
sensitivity. `docs/基金转换实验_博士研究计划.md` §7 calls these Bloomberg-dependent
and **degrades spine three to an enhancement layer, forbidding the main
conclusions from resting on it**. So this is a known, accepted limitation rather
than a new blocker — but WRDS does not lift it, and it should not be discovered
late.

### A5. The SUE fork — a human decision by design
Analyst expectations (IBES) vs a time-series model (Compustat). `Project_1.md`
§125 names this as the canonical DECISION_NEEDED. WRDS supplies *both* inputs,
which is precisely why it cannot make the choice.

---

## GROUP B — blocked by nothing; being worked now

### B1. Three artifacts in the §230 contract table have no contract
`docs/Project_1.md` §230 freezes seven handoff artifacts. `ops/contracts/` holds
four of them:

| artifact | producer → consumer | contract |
|---|---|---|
| events_merged.csv | T1 → T2 | ✅ |
| conv_exposure.parquet | T2 → T4,T5,T6,T7 | ✅ |
| main_results/ | T5 → T6..T9 | ✅ |
| robustness_results.csv | T7 → T8,T9,T10 | ✅ |
| **outcomes_panel.parquet** | **T3 → T5,T6,T7** | ❌ **missing** |
| **变量规格书.md** | **T3 → T5,T9** | ❌ **missing** |
| **fingerprint_*.csv** | **T6 → T8,T9** | ❌ **missing** |

CLAUDE.md rule 3 says tasks hand off through files with frozen column names. The
three busiest downstream consumers in P1 have no frozen target to write against.
This is pure schema work, needs no data, and should exist *before* the data
arrives — a contract written after the fact just ratifies whatever got built.

### B2. P1 has no panel-integrity guard
`refraction/pipeline/assert_panel.py` runs 14 asserts (look-ahead, no magic
shrinkage, leave-one-out). P1's equivalent does not exist, and P1 is the project
with an event-study panel whose whole validity rests on not peeking across the
event date. The WRDS assessment names look-ahead and report-period alignment as
*the* iteration risk of the borrowed window — which is an argument for writing
the guards before the window, not during it.

### B3. Spine two is specifiable now
`docs/基金转换实验_博士研究计划.md` §7 defines spine two's variables **itself**:
own- vs peer-announcement events, the CAR path [0,+120], permanent = CAR(+120),
reversal = the same-direction-decaying part of CAR(+5) − CAR(+120), DiD at every
path point, the treated−control wedge. Those carry a repo locator, so they need no
literature package. Spines one and four genuinely do (GNZ, FERC, IPT,
Hou-Moskowitz, Amihud, the spread convention) and stay out until A1 clears.

### B4. The Russell-reconstitution fallback design is checkable today
`P1_修订补丁_v1_1.md` §修订3 makes Russell handling a forced T5 sub-spec, and the
plan §133 gives three responses. Response (iii) — *replicate on 2022–2025 non-June
waves, and if the effect exists only in 2021-06 the conclusion is downgraded* — is
computable **right now** from `events_merged.csv`. Knowing whether that fallback
sample even has funds in it is a design fact worth having before committing to the
design, and it needs no data at all.

### B5. The free-vs-CRSP ConvExp reconciliation — done (14719f5)
Written before the data so the comparison is not improvised on arrival.

---

## What this means for sequencing

A1 (literature) and A2/A3 (egress) are independent of WRDS and can be procured in
parallel with it. **A1 is the one that actually gates T3**, and it is the cheapest
of the three.

Group B is being worked now, in the order B1 → B2 → B3 → B4. None of it needs the
owner, WRDS, or network.
