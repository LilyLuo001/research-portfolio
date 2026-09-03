# Refraction Chapter Plan — Amendment v2.2

Applies to *One Shock, Many Prices: ETF Baskets and the Refraction of
Macroeconomic News* (`MacroEvent_Chapter_Plan_v2_1_FINAL.md`, v2.1 final,
2026-07-12). Delta document; unmentioned sections stand. Motivation: v2.1's
§2/§4/§5 commit the chapter to reusing P1's frozen event and exposure files
"as-is" at a stated scale that was a planning-time figure. Those files now
exist, and this amendment replaces the stated scale with counts recomputed
from them, so §9's Gate-0 lines are read against real treatment mass before
pre-registration freezes them.

**Provenance (meta-rule 1).** Every number below is produced by
`refraction/sample_scale_audit.py`, executed on the committed files
`p1/events_merged.csv` and `p1/conv_exposure_free.parquet`. Output of record:
`refraction/sample_scale_audit.json`. Reproduce with

```
python refraction/sample_scale_audit.py --json refraction/sample_scale_audit.json
```

The treated-cell counts reproduce P1's own independent audit exactly
(`p1/output/convexp_coverage_audit/treated_stock_counts_by_threshold.csv`:
pooled 398 / DFA anchor 361 / non-anchor 37 cells at ConvExp ≥ 0.5%), which is
the cross-check that licenses using them here.

**What this amendment does NOT do.** It changes no Gate-0 threshold, chooses no
specification, and re-frames no hypothesis. Where a fact bears on a
pre-committed line, it is flagged `[PI-DECISION]` and left for the owner. §9's
thresholds continue to come from `refraction/frozen_config.yaml`, and R3 still
may not choose them.

---

## Amendment 1 — §2's sample scale is replaced by reproducible counts

v2.1 §2 states "203 cumulative conversions ~$260B through 2025" and instructs
"reuse events_merged.csv and conv_exposure.parquet as-is". The file holds:

| Quantity | v2.1 §2 | `events_merged.csv` today |
|---|---|---|
| Conversion rows, all asset classes | 203 | **131** |
| `asset_class == equity_US` | — | **36** |
| equity_US inside the §sample wave window 2021-03→2025-12 | — | **32** |
| Distinct effective dates in window | — | **22** |
| Distinct fund families in window | — | **23** |
| `AUM_at_conversion_USD` populated | ~$260B | **0 rows** |

Two consequences for the text:

**1a.** §2's count and AUM figure are replaced by the counts above, stated as of
the file's current revision. The ~$260B figure is **not reproducible from the
committed file** — the AUM column is empty in every row — so it may not be
carried into the paper or the pre-registration until it is sourced. Either
populate the column from the filings or cite the Saglam–Tuzun FEDS Note figure
explicitly as an external descriptive, with locator.

**1b.** These counts are **provisional in a known direction**. `ops/decisions.md`
(FULL-REVIEW 2026-07-18) records 96 event rows quarantined to `recheck` pending
full-text proof that the target was an open-end fund, plus 11 to
`recheck_noevent`. The equity_US line can therefore rise when the recheck pass
lands. §2 should say so rather than presenting any count as settled; the
pre-registration must state the event-set revision it was frozen against.

---

## Amendment 2 — The binding scale constraint is wave count, not stock count

This is the finding that most affects the design, and v2.1 states its direction
but not its magnitude. §6 says "effective treatment shocks = conversion waves
(few, DFA-heavy)". At the frozen_config treatment line (`convexp_treated_min`
= 0.005):

| Scope | Treated stock-waves | Treated stocks | Waves |
|---|---|---|---|
| Pooled | **398** | 389 | **10** |
| DFA anchor W002 (2021-06-11) | **361** | 361 | 1 |
| Everything else | **37** | 36 | **9** |

**90.7% of all treated mass sits in the single DFA anchor wave.** Only 2 waves
carry ≥10 treated names; the second-largest carries 12, and five carry ≤3. At
the 1% threshold the non-anchor sample is 16 stocks.

The stock-level cross-section is healthy — 389 treated names is ample for a
within-announcement cross-sectional estimator. The scarcity is entirely in the
dimension the *inference* runs on. `frozen_config.yaml` already sets
`inference.effective_cluster_warning_below: 10`; the wave dimension sits **at**
that line pooled, and at an effective count near one once concentration is
accounted for.

Bearing on three pre-committed lines, all left for the owner:

- **§8.1 "drop DFA / DFA only".** Pre-declared as honest dual reporting. On
  these counts the drop-DFA arm runs on 37 treated stock-waves across 9 waves —
  it is a power-limited robustness arm, not a co-equal report, and §8.1 should
  say which it is before results are seen. `[PI-DECISION]`
- **§9 G5 power.** The MDE simulation is specified as "wave-clustered". It must
  be run at the realized wave count and concentration, not a nominal one, and
  the §10 exit-D power bar inherits whatever it returns. `[PI-DECISION]`
- **§10 exit C (DFA-only).** v2.1 treats exit C as a contingency. These counts
  make it the modal starting point rather than a fallback, which is a framing
  decision that must be made ex ante, exactly like the §10 framing gate.
  `[PI-DECISION]`

**Recommended addition to §9, for the owner's decision:** a wave-count line
alongside G2's lever line — a pre-committed minimum number of waves carrying
≥N treated names, and a pre-committed statement of what is claimed if only the
anchor clears it. Proposed as a gate line, not adopted; thresholds are the
owner's per meta-rule and R3's read-only contract.

---

## Amendment 3 — §4/§5's input contract names a file that does not exist

§4 and §5 name `conv_exposure.parquet`. The built artifact is
**`p1/conv_exposure_free.parquet`** — the free-data-path build, not a WRDS
build. R2's input list and `refraction/CLAUDE.md`'s frozen-input list must use
the real name, and the plan must record which build it froze against, because
the two differ in coverage. Per P1's own audit
(`p1/output/convexp_coverage_audit/coverage_audit_memo.md`):

- cell coverage **51.8%** (6,377 computed of 12,306 attempted);
- the 48.2% drop is dominated by international-equity conversions
  (`ticker_not_in_sec_map`, 82.9% of drops), so the **US-equity universe this
  chapter uses is the well-covered part** — the headline drop rate overstates
  the damage to refraction specifically;
- **value-weighted missingness is not reconstructible** from the pushed
  artifacts (dropped cells retain no shares or value). Any statement in the
  paper about coverage must therefore be cell-count coverage, explicitly
  labelled as such.

---

## Amendment 4 — `permno` is absent; R2 has an unrecorded blocker

`conv_exposure_free.parquet` carries `cusip`, `ticker` and `stock_cik`, but
`permno` is **blank in all 6,377 rows**. §4 puts CRSP daily prices (including
the open) on the critical path for every core spine, and the R2 panel joins on
CRSP identifiers. A CUSIP→PERMNO bridge is therefore a prerequisite for R2 and
does not currently exist in the repo.

This also gates R10 — `ops/runner/queue.yaml` already lists R10 as depending on
an "R2 permno list", so the dependency is acknowledged downstream but never
recorded as a build step. Added to `refraction/README.md`'s NEED_HUMAN list.
CUSIP→PERMNO requires a CRSP-licensed crosswalk; it cannot be constructed from
public files, so it belongs with the standing WRDS access item.

---

## Amendment 5 — Sample-window discipline for waves beyond 2025-12

`conv_exposure_free.parquet` spans 49 waves with effective dates running to
**2026-11-20**, i.e. 6 waves past the §sample window end (2025-12-31) and some
dated after the present. One of them carries treated names (2026-07-17).

This is not a lookahead-ban violation — assert A4 governs the timing of β,
lever and weights, not the sample frame — but it is a filter that R2 must apply
explicitly and record in its manifest, rather than inheriting whatever the
exposure file happens to contain. v2.1's dual-share-class extension (§2, §11)
is the natural home for those waves as a pre-registered out-of-sample arm; they
must not silently enter the main sample.

---

## Amendment 6 — Refraction is registered in the docs precedence order

`docs/README.md` documents precedence for P1, E2 and DAX and omits refraction
entirely, so nothing tells a fresh seat that the chapter plan outranks the
执行手册 on research substance. Corrected in the same commit as this amendment:
plan → 执行手册 → this amendment, matching the other three projects' pattern.

`refraction/sample_scale_audit.py` is committed as a standing check, not a
one-off: it is offline, touches no outcome variable, and re-running it after any
P1 T1/T2 revision re-derives every count in this document.
