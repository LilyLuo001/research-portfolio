# P1-T3 pre-flight — what the variable spec needs before it can be written

_seat C, 2026-08-18. Written after the runner reconciliation put P1-T3-spec on
the board as seat C's L2 item. **T3 channel A is not startable today.** This
document is the "don't know → stop" (CLAUDE.md #4) response: it does every part
of T3 that does not depend on the missing input, and reduces the block to one
precise owner ask._

## The block, stated exactly

The T3 task prompt (`docs/Project_1.md` §120–125) requires, per variable:

> 数学定义 | 数据表与字段 | **已知文献口径出处(仅限文献包)** | 边界情形处理 | 合理值域

and:

> 凡**文献包**中口径有分歧处(如 SUE 用分析师预期 vs 时序模型),列出选项并给推荐 + 理由,标记 DECISION_NEEDED

**There is no 文献包 in this repo.** It was to be produced by T0 阶段A — the
structured literature matrix, `作者|年份|期刊/状态|数据|识别|结果变量|与本文边界`
(`docs/Project_1.md` §72–79). What P1-T0 actually executed was 阶段B only, the
Saglam–Tuzun collision sweep (`p1/t0_collision_sweep_channelA.md`,
`ops/l1/out/P1-T0-crash-B.json`). No queue id covers 阶段A: `queue.yaml` has
P1-T0-crash, P1-T0-crash-B and P1-T0-monitor, all collision work.

So the third column of every row of the spec has no admissible source. Filling it
from model memory is precisely what meta-rule 1 forbids, and `docs/Project_1.md`
§60 gives the prescribed alternative: **CITE_REQUEST**.

Second, weaker block: T3's data column. BU WRDS access is gone
(`ops/briefs/WRDS-access-assessment.md`), and that assessment maps T3 to TAQ IID
+ CRSP DSF + IBES SUE + possibly Compustat. The spec can still be *written*
against those sources before they are procured — that is the whole point of the
"pre-write offline, borrow for one sprint" plan in the same brief — but exact
table and column names must be **pasted by the owner**, never guessed (the
refraction R2 entry in `queue.yaml` already carries this as a standing
`PRE-DISPATCH NEED_HUMAN: CRSP table/var list pasted`).

## What is NOT blocked, and is done here

The variable inventory itself is repo-sourced, from
`docs/基金转换实验_博士研究计划.md` §7. Enumerating it needs no literature package,
and it is what makes the CITE_REQUEST below specific rather than a shrug.

Note the T3 prompt covers spines **一, 二, 四** only. Spine 三 (dose–response /
mechanism) is deliberately excluded: §7 degrades it to an enhancement layer when
mechanism data is Bloomberg-dependent, and forbids the main conclusions from
resting on it. It should not be specified now.

### 脊柱一 — pre-announcement incorporation of systematic earnings news (H1)
| variable | §7 says | data needed | available today? | what the 文献包 must settle |
|---|---|---|---|---|
| systematic / idiosyncratic earnings decomposition | earnings split into a systematic component (predicted from market/industry earnings-factor loadings) and an idiosyncratic residual, "按 GNZ 构造" | quarterly earnings (Compustat), plus whatever GNZ uses to form the factors | **no** | the GNZ decomposition regression itself: exact LHS earnings measure and scaling, the factor construction, estimation window, sample filters |
| FERC-style coefficient | pre-announcement window return on *future* systematic earnings component | CRSP DSF returns + the above | **no** | which FERC specification (the literature has several), and the control set |
| IPT (intraperiod timeliness) | reported alongside FERC | same | **no** | the IPT definition and its normalisation |
| Hou–Moskowitz price delay | auxiliary | CRSP DSF (+ market return) | **no** | number of lags, weekly vs daily, the R²-ratio form |
| peer-announcement response | immediate reaction to same-basket earlier announcers' earnings surprise | announcement dates + SUE + CRSP DSF | **no** | **the known fork: SUE from analyst expectations (IBES) vs a time-series model** — `docs/Project_1.md` §125 names this one explicitly as DECISION_NEEDED |

### 脊柱二 — return fingerprint, permanent vs reversed (H2, main evidence)
| variable | §7 says | data needed | available today? | what the 文献包 must settle |
|---|---|---|---|---|
| event set | own announcement **and** earlier-announcing basket peers, run separately | announcement dates; basket membership | partial — basket membership is derivable from our own N-PORT holdings | peer-event definition conventions |
| CAR path [0, +120] | characteristic-adjusted benchmark (per the T3 prompt) | CRSP DSF + characteristic benchmark portfolios | **no** | which characteristic adjustment (size/BM/momentum grid vs matched-portfolio), and the compounding convention |
| permanent component | CAR(+120) | as above | **no** | — (defined in §7; needs no citation) |
| reversal component | CAR(+5) − CAR(+120), restricted to the part that decays in the same direction as the initial reaction | as above | **no** | whether the literature has a standard operationalisation of "same-direction decay" or this is ours to define |
| reversal-strategy return | Jegadeesh-style short-horizon reversal, before vs after conversion | CRSP DSF | **no** | the exact portfolio formation rule and rebalancing |
| variance ratio | daily/weekly | CRSP DSF | **no** | the variance-ratio estimator and its bias correction |

### 脊柱四 — cost side (H4)
| variable | §7 says | data needed | available today? | what the 文献包 must settle |
|---|---|---|---|---|
| effective spread | TAQ | **WRDS Intraday Indicators (IID)** | **no** | which IID field, and the effective-spread convention behind it |
| price impact | TAQ | IID | **no** | which measure |
| Amihud illiquidity | — | CRSP DSF (return + dollar volume) | **no** | scaling and the treatment of zero-volume days |
| 1 − R² (idiosyncratic information content) | — | CRSP DSF | **no** | the market-model specification and whether R² is logit-transformed |
| future earnings response coefficient | — | Compustat + CRSP DSF | **no** | overlaps the 脊柱一 FERC choice — settle once, use twice |
| analyst coverage & forecast dispersion | — | IBES | **no** | coverage counting rule; dispersion scaling |

**Availability summary: zero of the T3 outcome variables are computable on the
current free path.** ConvExp (T2) is the treatment variable and exists; every
*outcome* variable needs CRSP daily, TAQ IID, IBES, or Compustat. This is not a
new discovery — it is the WRDS assessment's own conclusion — but it means T3's
"数据表与字段" column is written for a sprint that has not been booked, and T5
cannot run at all until it is.

## CITE_REQUEST (the owner ask)

Per `docs/Project_1.md` §60. Minimum viable literature package to unblock T3 —
one entry per row, each with a working link, in the T0 阶段A matrix format:

1. **GNZ** — the systematic/idiosyncratic earnings decomposition paper the plan
   abbreviates as GNZ (author-year + link), plus any companion that states the
   decomposition regression in estimable form.
2. **FERC** — the future-earnings-response-coefficient specification to follow.
3. **IPT** — intraperiod timeliness definition.
4. **Hou–Moskowitz** price delay.
5. **SUE** — one entry for the analyst-expectation convention and one for the
   time-series convention, so the DECISION_NEEDED fork has both sides on file.
6. **Characteristic-adjusted CAR** — the benchmark-adjustment convention.
7. **Jegadeesh** short-horizon reversal.
8. **Amihud** illiquidity.
9. **1 − R²** idiosyncratic information content.
10. **TAQ/IID effective spread** — the convention the WRDS IID field implements.

**11. Multiway wild cluster bootstrap** — ✅ **CLOSED 2026-08-28, owner-supplied.**
Unlike items 1–10 this is not a 口径 for an outcome variable; it is the procedure
behind every p-value in the paper.

* Roodman, MacKinnon, Nielsen & Webb (2019), "Fast and wild: Bootstrap inference
  in Stata using boottest", *Stata Journal* 19(1):4–60.
* Cameron, Gelbach & Miller (2008), *Review of Economics and Statistics*
  90(3):414–427 — the foundational clustered-bootstrap reference.

Implementation family: **Stata `boottest`**, which supports multiway error
clustering and a separately specified bootstrap clustering. Python
`wildboottest` is **not** the primary implementation — its documentation states
multiway clustering is unsupported. Hand-rolling the loop stays forbidden.

Still open, deliberately: the `bootcluster()` argument. It is deferred until the
final analysis sample supplies the economic-sponsor count, the treated-sponsor
count, cross-sponsor stock reuse and cluster imbalance, and it must be justified
**before any headline coefficient is observed** —
`p1/t5_spec/BOOTCLUSTER-DECISION.md`. That is a hold on one parameter, not an
open literature question, so it does not belong on this list.

Alternatively, queue T0 阶段A properly as a dual-channel task (it is a
high-hallucination task under meta-rule 2 — the collision sweep already showed
one channel inventing an overlap verdict) and let it produce the matrix.

Also still needed, separately, for the "数据表与字段" column:
- the **CRSP / TAQ-IID / IBES / Compustat table + variable list, pasted**, once a
  WRDS window is booked.

## Recommended sequencing

1. Owner supplies the literature package (or authorises T0 阶段A as a queued
   dual-channel task).
2. T3-spec channel A (this seat) + T3-spec-B (deepseek, now dispatchable as an L1
   batch) run independently, diff, DECISION_NEEDED to the owner — the normal
   `P1-T3-decision` gate.
3. In parallel and *not* blocked by either: the WRDS-assessment standing offer to
   pre-write the offline pull scripts for T3/T4/R2, so a borrowed window is pure
   execution. That work needs no literature package — only the pasted table/var
   list at runtime, which the scripts should refuse to run without.

## Status

`NEED_HUMAN: P1-T3-spec cannot start — no 文献包 (T0 阶段A never ran, no queue id
covers it) and every T3 outcome variable needs WRDS data that lapsed. Itemised
CITE_REQUEST above; T3-spec and T4-replication both blocked on owner input.`

---

## Status update 2026-08-18 — 文献包 now available (partially)

`p1/lit/literature_matrix.md` was produced with WebSearch-sourced entries for all
10 CITE_REQUEST items. 12 cells are marked `[NEED_PDF]` for formula details that
require the actual paper. The URLs are confirmed; a browser session can fill them.

**T3-spec is now startable** for spines one, two, and four. The [NEED_PDF] cells
are treated as DECISION_NEEDED equivalents — the spec writer flags them for the
human reviewer to fill from the cited paper. This is the same as the SUE fork
handling already planned in §125.

Residual block: data column still needs WRDS table/var list (unchanged).
