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

---

## Status 2026-08-28 — Group B is finished; nothing offline remains

Group B was worked B1 → B2 → B3 → B4, and all of it has landed:

| | item | where |
|---|---|---|
| B1 | three missing §230 contracts | `ops/contracts/{outcomes_panel,variable_spec,fingerprint}.yaml` |
| B2 | panel-integrity guard | `p1/pipeline/assert_panel.py` |
| B3 | spine-two outcomes builder | `p1/pipeline/outcomes_spine2.py` + tests |
| B4 | Russell non-June fallback check | `p1/design/russell_fallback.json` |
| B5 | free-vs-CRSP reconciliation | `p1/reconcile/convexp_reconcile.py` |

Landed since, and also needing nothing: Gate 0's continuity measures with the
as-of factor join and the non-circular direction test
(`p1/gate0_continuity/`, `p1/tests/test_gate0_continuity.py`); the dependence
measure (`p1/t5_spec/measure_dependence.py`); the spec-consistency guard
(`p1/tests/test_spec_consistency.py`); and the sponsor crosswalk proposal
(`p1/t5_spec/sponsor_crosswalk.py`).

**Every remaining P1 item is in Group A, plus three new owner items.** So the
next seat-C session should not go looking for offline work — there is none, and
inventing some is worse than saying so.

### A6. The sponsor crosswalk signoff — blocks headline inference
`p1/t5_spec/SPONSOR-CROSSWALK-GATE.md`. Name evidence took 84 registrants to 61
stems; the rest needs a locator per row. The two expensive ones share no tokens
with their siblings and cannot be found mechanically: `Undiscovered Managers
Funds` → JPMorgan, and `DFA Investment Dimensions Group` ↔ `Dimensional
Investment Group` (93.6% of treated mass). Blocks §15.3.1 and §15.3.0's
dependence measurement; blocks **neither Gate 0 nor B1/B2**.

### A7. The multiway wild-bootstrap citation — blocks every p-value
`CITE_REQUEST` item 11 in `p1/t3_spec_preflight.md`. Unlike items 1–10 this is
not a variable 口径, it is the procedure behind the headline result. Until it is
filled, §15.3.1 is `NEED_HUMAN`; a one-way stand-in "for now" is method selection
after the fact and is forbidden.

### A8. SEC egress — blocks B1/B2 execution and Gate 0's measured result
Re-verified in-container 2026-08-28: `www.sec.gov`, `data.sec.gov`,
`efts.sec.gov` and `api.openfigi.com` all return 403 at the proxy CONNECT
(`connect_rejected — gateway answered 403`). The code, contracts and tests are
committed and green offline; they need a lane with SEC egress, not more work
here. OpenFIGI is a coverage fallback only — step 2 of the builder uses it just
for holdings whose N-PORT carries no ticker — so it is not load-bearing.

### A9. The WRDS account — blocks T2-on-permno, T4, T5, and two integration tests
`p1/tests/test_gate0_continuity.py` has two tests that skip today and are the
only things that can verify the CFACSHR direction against data
(`test_direction_against_real_crsp_corporate_actions`,
`test_adjustment_cancels_a_real_action_on_a_real_holding`). The pull layer is
written, bounded and ordered; the runbook is `ops/briefs/P1-WRDS-SPRINT.md`.
