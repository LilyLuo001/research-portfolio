# The Wrapper and the Macro News: Do ETFs Change How Macroeconomic Information Enters Stock Prices?
## Standby dissertation chapter — detailed review + research design (v0.1, 2026-07-12)

> **Purpose.** Advisor-facing document. Chapters approved: P1 (fund conversions × earnings
> information) and DAX (AI exposure). E2 (RWA looping) is not yet approved. This document
> (a) reviews in detail the *original* two-part idea behind P1 — "during earnings, the stock
> leads the ETF; during macro events, the ETF leads the stock" — and what the literature has
> since occupied, and (b) designs the macro half as a standalone chapter at a top field-journal
> standard, to stand by as a replacement should E2 not be approved.
>
> **Citation discipline (house rule R1/R2).** Every paper cited below was verified online on
> 2026-07-12 with a working link (Appendix A). This is a single-channel sweep (one model
> family); per meta-rule R2, run the channel-B sweep (Kimi `$web_search`) before this document
> is used in any submission. No number in this document comes from memory; priors that still
> need data are marked `[VERIFY-IN-GATE-0]`.

---

# Part I — Detailed review: what happened to the original two-part idea

## I.1 The original idea, reconstructed

The original P1 conception was one economic idea split into two chapters:

- **Micro half (earnings):** around firm-specific news (earnings announcements), price
  discovery happens in the *individual stock*; the ETF holding it lags. Passive/ETF ownership
  should therefore matter for how firm-specific news gets into prices.
- **Macro half (macro events):** around economy-wide news (FOMC, CPI, employment), price
  discovery happens in the *index products*; individual stocks lag and inherit the macro news
  through the ETF/arbitrage channel. ETF-ization should therefore matter for how macro news
  gets into individual stock prices.

The advisor's original request — "Project 1 as two chapters" — maps exactly onto this split.

## I.2 The micro half: taken, and how P1 responded

**Sammon (Management Science, 2025, 71(6), 4582–4598), "Passive Ownership and Price
Informativeness"** is the collision. He shows passive ownership *reduces* the amount of
earnings information incorporated into prices ahead of earnings announcements (pre-announcement
price discovery falls by ~1/4 of its sample mean over 30 years of rising passive ownership),
using panel designs plus index-membership variation. This occupies precisely the micro half:
"passive/ETF ownership × pre-earnings price discovery at the stock level."

Two adjacent papers had already narrowed the space:

- **Glosten, Nallareddy, Zou (Management Science, 2021, 67(1), 22–47)**: ETF activity speeds the
  incorporation of the *systematic component of earnings* for weak-information stocks (with the
  opposite-sign literature in Israeli–Lee–Sridharan 2017 RAST).
- **Ernst (working paper, "Stock-Specific Price Discovery from ETFs")**: even stock-specific
  information partially discovers *in* the ETF when the stock is a large/volatile constituent —
  i.e., the naive "stock leads ETF on firm news" lead-lag fact is not clean either.

**P1's pivot (already executed, correctly, in my assessment):** keep the earnings-information
outcome family but replace the endogenous-ownership variation with the mutual-fund→ETF
*conversion* natural experiment (delegation, manager, holdings constant; only the wrapper
changes), and add the permanent-vs-reversal "fingerprint" to arbitrate information vs. pressure.
The 2026-07-09 collision sweep (p1/t0_collision_sweep_channelA.md) confirms the only occupant of
the conversion identification, Saglam–Tuzun (FEDS Note 2025-11-19), does market quality
(volatility/liquidity), not information incorporation. P1's boundary is documented and defensible.

**Verdict on the micro half: correctly abandoned as a standalone chapter; its salvageable core
now lives inside P1.** Nothing further to recover there.

## I.3 The macro half: what is known, what is genuinely open

The macro half was *not* killed by anyone — but it cannot be executed as originally phrased,
because the raw lead-lag fact is old news:

| Paper (verified) | What it established | What it leaves open |
|---|---|---|
| Hasbrouck (JF 2003, 58(6), 2375–2400) | ~90% of S&P 500 price discovery initiates in E-mini futures, diffusing to ETF and cash. Index products lead, mechanically and massively. | Aggregate-level lead-lag only. Says nothing about *consequences for constituent-stock efficiency*, and nothing causal about the wrapper. |
| Savor–Wilson (JFE 2014, 113(2), 171–201); Savor–Wilson 2013 | Scheduled macro-announcement days carry a premium; CAPM beta prices returns *only* on announcement days. | Whether the market structure (ETF-ization) changes how well the cross-section prices macro risk on those days. |
| Lucca–Moench (JF 2015; NY Fed SR 512), pre-FOMC drift | Equity index drifts up in the 24h before FOMC; no reversal. | Stock-level incorporation dynamics; role of index-product ownership. |
| Ben-David–Franzoni–Moussawi (JF 2018, 73, 2471–2535) | ETF ownership → higher volatility, negative autocorrelation: an *arbitrage-pressure* channel exists. | Whether at macro moments that channel transmits information or noise into constituents. |
| Baltussen–van Bekkum–Da (JFE 2019, 132(1), 26–48) | Index serial dependence flipped negative as index products grew, worldwide. | Same: aggregate signature, no causal wedge, no announcement conditioning. |
| Bhattacharya–O'Hara (SSRN 2740699) | Theory: with hard-to-trade underlyings, market makers learn from ETF prices; ETF-propagated signals can create herding and persistent dislocations from fundamentals. | The central *testable tension*: ETF-led macro discovery could be efficiency **or** fragility. No causal test exists. |
| "ETF Ownership and the Transmission of Monetary Policy" (J. Financial Research, 2025; Temple WP 2024) | Nearest neighbor on the macro side. ETF ownership → *asymmetric* stock-return transmission of MP surprises (amplifies cuts, dampens hikes), 101 FOMC meetings 2012–2023, via ETF premium/creation pressure. | Uses endogenous ETF *ownership levels*; outcome is return amplification, not the **speed/completeness/permanence of information incorporation**; no conversion identification; no efficiency verdict. |
| Sammon (MS 2025) | The mirror image on micro information (see I.2). | The macro side is explicitly *not* studied — and his result makes the macro question sharper (see I.4). |

**The open cell is precise:** *a causal estimate of how the ETF wrapper changes the incorporation
of scheduled macroeconomic news into individual constituent prices — its speed, its completeness,
its permanence (information vs. pressure), and its liquidity cost at the moment of the
announcement.* Nobody occupies it. The JFR 2025 paper shows the territory is warming; the
conversion identification and the efficiency/fingerprint outcomes remain untouched.

## I.4 Why this is now a *better* paper than the original phrasing

1. **From documentation to arbitration.** "ETF leads stock on macro days" is a mechanical fact
   since Hasbrouck (2003). The open question is welfare-relevant: when the wrapper hands macro
   price discovery to the ETF, do constituents become *macro-efficient* (faster, permanent,
   CAPM-consistent incorporation — the Glosten–Nallareddy–Zou logic extended to true macro news)
   or *macro-fragile* (fast but reverting moves, liquidity withdrawal at the announcement — the
   Bhattacharya–O'Hara/Ben-David–Franzoni–Moussawi logic)? Both outcomes are publishable; that
   two-sided structure is what made P1 attractive, replicated here.
2. **Samuelson's dictum as the dissertation arc.** Jung–Shiller (Economic Inquiry 2005) framed
   markets as "micro efficient, macro inefficient." Sammon shows the passive revolution *erodes
   micro efficiency*. This chapter asks whether the same revolution *builds macro efficiency at
   the stock level*. Chapter 1 (P1, earnings) + this chapter (macro announcements) = "the index
   revolution reallocates price discovery across the micro–macro boundary." That is a
   dissertation-level narrative an advisor can sell, and it is exactly the advisor's original
   two-chapter request, upgraded to causal designs.
3. **Identification is *cleaner* than P1's own setting.** Macro announcement timing (FOMC/CPI/NFP
   calendars) is exogenous, scheduled, and common to all stocks; the surprise is measured
   externally (fed-funds-futures windows; survey consensus). Unlike earnings events, there is no
   firm-side selection of event timing, no confound between the event and the firm. All
   conversion-side threats (DFA concentration, anticipation) are shared with P1 and already have
   engineered answers.
4. **Power is better.** P1 leans on quarterly earnings (4 events/firm/year). Here: ~8 FOMC + 12
   CPI + 12 NFP scheduled releases per year × ~9 sample years ≈ 280–300 macro event days
   `[VERIFY-IN-GATE-0: exact calendar from USMPD + BLS/BEA schedules]`, each observed for the
   full treated cross-section, with a continuous measured surprise. Repetition × measured shock
   intensity is a power structure earnings designs cannot match.
5. **Cost is a fraction of a normal chapter.** The expensive assets — the verified conversion
   event list (T1), the ConvExp exposure panel (T2), the stacked-DiD estimation blueprints (T5),
   the inference machinery — are all shared with P1. The only new heavy input is intraday TAQ
   around ~300 announcement days.

**Honest risks, stated up front:** (i) the space is warming (JFR 2025); the window logic that
governs P1 (12–18 months) applies here too; (ii) intraday measurement for small caps is the
binding data risk (Gate 0, below); (iii) the chapter must defend against the "salami slicing"
charge relative to P1 (§11 has the defense).

---

# Part II — Research design (house format, mirroring 基金转换实验_博士研究计划.md)

## 0. Positioning

Saglam–Tuzun validated that conversions move stock-level market quality; P1 claims the earnings-
information cell; the JFR 2025 paper shows macro-transmission questions are being asked with
*endogenous ownership*. This chapter takes the last unoccupied cell: **conversion-identified,
constituent-level incorporation of scheduled macroeconomic news**, with the information-vs-
pressure fingerprint as the arbitrating evidence. Execution must assume the same "race" clock
as P1: working paper circulating within 12 months of Gate 0 passing.

## 1. Research question and contributions

**One sentence:** When a mutual fund becomes an ETF — manager, strategy, holdings, delegation
unchanged; only the wrapper (AP creation/redemption arbitrage + intraday tradability) changes —
do the underlying stocks incorporate scheduled macroeconomic news (FOMC, CPI, employment)
faster, more completely, and more permanently, or merely more violently?

**Three contributions:**

1. **First causal estimate of the wrapper's effect on macro-information incorporation at the
   stock level.** Extends the Glosten–Nallareddy–Zou "systematic information" result from
   earnings-derived systematic components to true, dated, externally measured macro shocks —
   under an identification where delegation is held constant.
2. **Arbitration of efficiency vs. fragility at macro moments.** Bhattacharya–O'Hara predict
   ETF-propagated signals can dislocate constituent prices (herding); Savor–Wilson show macro
   days are when beta should price. The permanent/transitory decomposition + announcement-window
   liquidity results decide which force dominates, causally. Both verdicts are positive results.
3. **Policy input on market resilience at macro events.** As conversions and dual-share-class
   approvals push trillions into ETF wrappers (203 conversions, ~$260B by end-2025; SEC
   multi-class relief 2025-12), whether constituent markets absorb macro news through the ETF
   channel without liquidity withdrawal is a first-order question for the SEC/Fed market-
   functioning agenda — the same audience already engaged by Saglam–Tuzun.

**Boundary table (referee will check line by line):**

| Paper | They do | I do |
|---|---|---|
| Hasbrouck 2003 JF | Aggregate index price discovery (futures/ETF lead) | Constituent-level *consequences*, causal wrapper wedge |
| GNZ 2021 MS | ETF activity (endogenous) × systematic *earnings* info | Wrapper shock × *scheduled macro* news, intraday |
| Sammon 2025 MS | Passive ownership slows *micro* (pre-earnings) discovery | Whether the wrapper speeds *macro* discovery — the mirror cell |
| Saglam–Tuzun 2025 FEDS | Conversions → volatility/liquidity (unconditional) | Conversions → information dynamics *conditional on macro events* |
| JFR 2025 (ETF ownership & MP transmission) | Ownership levels × MP surprise return *amplification*, asymmetry | Conversion shock × incorporation *speed/permanence/liquidity cost*; efficiency verdict |
| Ben-David–Franzoni–Moussawi 2018 JF | ETF ownership → volatility (pressure channel exists) | Whether pressure or information dominates *at macro moments*, causally |
| Bhattacharya–O'Hara (theory) | Herding via information linkages, fragility | The empirical test their model calls for |
| P1 (Chapter 1) | Conversion → *earnings* information incorporation, quarterly outcomes | Conversion → *macro announcement* incorporation, intraday outcomes (§11 anti-overlap defense) |

## 2. Institutional background and events

- **Conversion side:** identical event set to P1 (2021-03 Guinness Atkinson first; DFA 2021-06-11
  anchor wave, ~$30B US equity in one day; 203 cumulative conversions ~ $260B through 2025;
  SEC dual-share-class relief 2025-12 → second wave = out-of-sample chapter extension). Reuse
  events_merged.csv and the honest framing: "one large-mass event + a time-series of smaller
  replications," not textbook staggered adoption.
- **Macro side:** scheduled FOMC statements (8/yr, 14:00 ET), CPI releases (monthly, 08:30 ET,
  pre-open), Employment Situation (monthly, 08:30 ET, pre-open). Surprises: (i) FOMC — 30-minute
  fed-funds-futures window changes from the SF Fed U.S. Monetary Policy Event-Study Database
  (public, verified); (ii) CPI/NFP — actual minus consensus, normalized (Bloomberg ECO or
  equivalent; access to be confirmed, `NEED_HUMAN: confirm consensus-survey license (Bloomberg
  terminal at BU vs. WRDS alternatives)`).
- The 08:30 pre-open releases and the 14:00 intraday release give *two distinct microstructure
  regimes* (opening auction absorption vs. continuous-session absorption) — a built-in
  replication and mechanism lever, not a nuisance.

## 3. Conceptual framework and hypotheses

What changes at a macro moment when the wrapper flips (all else constant): before conversion, a
macro surprise reaches the stock only through direct trading in the stock; after conversion, the
ETF price updates within seconds (Hasbrouck), opening an *arbitrage conduit* — AP/HFT tandem
trades push the constituent toward its beta-implied value — plus a *learning conduit* — the
stock's market makers re-quote off the observable ETF price without trades (Bhattacharya–O'Hara).
Confounds inherited from P1 (disclosure regime, fees/flows, clientele) are second-order here
because the outcome is measured in minutes around pre-scheduled announcements, but the P1
controls carry over anyway.

Each hypothesis is bound to a return/quote signature; the signature is the referee:

- **H1 (speed).** Post-conversion, high-ConvExp stocks incorporate the announcement surprise
  faster: a larger share of the stock's eventual announcement-day move (or of its beta×surprise
  benchmark move) is realized within 5/15/30/60 minutes; intraday intraperiod-timeliness (IPT)
  rises; announcement-day Hou–Moskowitz-style delay (intraday variant) falls.
- **H2 (fingerprint — the heart, mirroring P1's H2).**
  - H2a (information): faster incorporation with *no reversal* over [+1d, +20d] → the wrapper
    is a macro-efficiency technology; Samuelson's macro cell improves at the stock level.
  - H2b (pressure): the fast initial move partially *reverts* over days–weeks → ETF-propagated
    herding (Bhattacharya–O'Hara confirmed causally); "speed" is repricing noise, and the
    GNZ-style efficiency reading of ETF activity is rewritten at macro frequency.
  - Both partially true is itself the decomposition contribution.
- **H3 (dose–response).** Effects scale with |surprise| (zero on no-surprise days — a built-in
  placebo), with ConvExp intensity, and with post-conversion *measured* arbitrage activity
  (creation/redemption frequency, premium/discount half-life). Enhancement layer if Bloomberg-
  dependent, per the P1 "floor design" principle — the main results may not depend on it.
- **H4 (beta discipline).** Savor–Wilson: beta prices returns on announcement days. If the
  wrapper channels macro news through beta-weighted baskets, treated stocks' announcement-day
  responses should line up *more tightly* with beta×surprise after conversion (higher
  cross-sectional R², lower dispersion around the CAPM line). A sharpening of "the tale of two
  days" as a market-structure outcome — to my knowledge an untouched margin `[channel-B sweep
  must confirm]`.
- **H5 (liquidity cost / fragility).** In the first minutes after the release, do treated
  stocks' quoted/effective spreads and depth deteriorate more (liquidity migrates to the ETF
  exactly when macro uncertainty resolves) or improve (arbitrage knits the books together)?
  This is the Saglam–Tuzun market-quality result *conditioned on the moments that matter*, and
  the fragility half of the policy contribution.

## 4. Data

| Data | Source | Use | Risk |
|---|---|---|---|
| Conversion events + ConvExp | **Reuse P1** events_merged.csv, conv_exposure.parquet (T1/T2 outputs) | Treatment | Same as P1; no new risk |
| Macro calendar + MP surprises | SF Fed USMPD (public); FOMC/BLS/BEA schedules | Event set, FOMC shock | Low; public |
| CPI/NFP consensus | Bloomberg ECO (BU terminal) or equivalent | Surprise construction | **Gate-0 item**: license/coverage `NEED_HUMAN` |
| Intraday quotes/trades | TAQ via WRDS (NBBO midquotes, 1-min/5-min bars around releases) | H1/H4/H5 outcomes | Volume/quote quality for small caps pre-2021 — Gate-0 item |
| Daily panel | CRSP; Compustat | H2 fingerprint horizons, controls | Standard |
| ETF mechanics | Bloomberg shares outstanding, N-CEN | H3 dose | Enhancement layer only |
| Betas | Daily rolling market model + high-frequency betas on announcement days | H4 benchmark | Estimation noise → use shrinkage + portfolio-level checks |

Sample: announcements 2017-01–2026-06; conversions 2021-03–2025-12 (equity only, same filter as
P1); stock×announcement panel.

## 5. Treatment and controls

Identical to P1 (frozen contract): ConvExp_i,e continuous main treatment; the same three control
layers — (1) within-holdings intensity gradient (top vs. bottom terciles of ConvExp among held
stocks; family-level shocks difference out), (2) twin unconverted same-family funds' holdings +
placebo event dates, (3) characteristic-matched non-held stocks. Main table = layer 1.

## 6. Identification

Stock i, announcement a (with measured surprise S_a), wave e:

Y_{i,a} = β·(Post_{e,a} × ConvExp_{i,e}) + γ·(Post × ConvExp × |S_a|) + α_i + λ_a + δ_{ind×a} + θ'X_{i,t(a)} + ε

- λ_a (announcement fixed effects) absorb the common shock entirely — identification is purely
  cross-sectional within announcement, which is the great advantage over calendar-time designs;
  δ_{industry×announcement} kills industry-specific macro loadings.
- Stacked by conversion wave with clean controls, as in P1; never bare TWFE.
- **Inference:** the effective number of independent shocks is the number of announcement days
  (~300) *and* the number of conversion waves (few, DFA-heavy). Report three ways, as in P1:
  two-way clustering (announcement day × wave/industry), wild cluster bootstrap, and
  **randomization inference** — permuting conversion dates and permuting announcement labels
  (announcement vs. adjacent non-announcement days) — in the main table.
- **Threats and answers** (inherited from P1, with one addition): T1 fund-selection → within-
  holdings gradient + estimand stated narrowly; T2 anticipation → announcement-date t=0 is the
  *macro* calendar (exogenous), conversion anticipation handled by excluding the announce-to-
  effective transition window; T3 2021-06 confounds (Russell reconstitution two weeks after DFA)
  → far less binding here because outcomes are announcement-window measures repeated over ~300
  events, but run the P1 v1.1 reconstitution controls anyway; T4 flows/fees → P1 controls carry
  over. **New T5: announcement-day HFT/algorithmic trading trends** — secular growth in machine
  reaction speed could differentially affect index-heavy names; answer: layer-1 design compares
  stocks *within* the same announcement and the same holdings pool, plus matched-control placebo
  trends over 2017–2020 pre-period.

## 7. Outcome spines (four, mirroring P1's structure)

1. **Speed spine (H1):** share of [release, close] move realized by minute m ∈ {5,15,30,60};
   intraday IPT; time-to-half-adjustment; announcement-day delay measure. Both 14:00 (FOMC,
   continuous session) and 08:30 (CPI/NFP, opening absorption: fraction realized at open vs.
   first 30 min) variants.
2. **Fingerprint spine (H2, main evidence):** cumulative response at horizons {+1h, close, +1d,
   +5d, +20d} scaled by beta×surprise; treated−control wedge plot over horizon (the same visual
   grammar as P1's CAR wedge); reversal share; announcement-conditioned autocorrelation and
   variance ratios (links to Baltussen–van Bekkum–Da and BFM signatures).
3. **Beta-discipline spine (H4):** announcement-day cross-sectional regression R² and slope of
   realized response on beta×surprise, treated vs. control, pre vs. post.
4. **Liquidity spine (H5):** effective/quoted spreads, depth, price impact in [−15m, +60m]
   windows; ETF premium/discount half-life as the conduit gauge (enhancement layer).

## 8. Robustness (referee-ordered)

1. Drop DFA / DFA only (the shared soft spot with P1; same honest dual reporting).
2. Estimators: stacked / Callaway–Sant'Anna / Sun–Abraham; event-study dynamics with 8+
   quarters of pre-period announcements.
3. Inference: the three-way suite above.
4. Surprise measures: futures-window vs. survey-based; sign splits (the JFR 2025 asymmetry —
   *replicate their asymmetry as a validation*, then show the incorporation results are distinct).
5. Announcement types separately (FOMC vs. CPI vs. NFP) and pooled; pre-open vs. intraday regime.
6. Exclude 2021Q2–Q3 (meme/Russell); exclude COVID; exclude <$5 stocks.
7. Placebos: no-surprise announcement days; non-announcement days matched by weekday/time;
   twin-fund pseudo-events; already-high-ETF-ownership stocks (marginal wrapper effect → 0).
8. Multiple testing: Romano–Wolf within each spine.

## 9. Gate 0 — six-week kill-switch (all must pass before full commitment)

| Week | Task | Pass line |
|---|---|---|
| 1 | Macro calendar + surprise series assembled (USMPD public first) | ≥ 95% of 2017–2026 releases with usable surprise; consensus license resolved |
| 1–2 | **Reuse P1 T2a machinery**: simulated MDE for the speed/fingerprint outcomes given ConvExp distribution + announcement count | Detectable effect ≤ 0.5σ at baseline priors; else kill |
| 2–4 | TAQ pilot: 30 treated + 30 control stocks × 20 announcement days | Intraday outcome measurable (quote coverage, sensible IPT) for ≥ 70% of treated names incl. small caps |
| 4–5 | Pre-conversion announcement-day response estimable per stock | Cross-sectional dispersion of pre-period speed measures ≫ measurement noise |
| 5–6 | Pre-trend: speed/fingerprint outcomes flat in event time before conversion (announcement-stacked) | No systematic pre-trend over 8 pre-quarters |

Any failure → exit matrix, no forcing. Estimated incremental cost above P1: the TAQ pilot and
one seat-week `[VERIFY-IN-GATE-0]`.

## 10. Exit matrix (both main exits are positive results — same design philosophy as P1)

- **A (efficiency win):** faster + no reversal + tighter beta pricing → "the wrapper completes
  Samuelson's macro cell at the stock level." Target JF/JFE/RFS.
- **B (fragility win):** faster + reversal + liquidity withdrawal → causal confirmation of
  Bhattacharya–O'Hara herding; ETF-era macro moves in constituents are partly noise. Equally
  publishable; arguably higher policy salience.
- **C (DFA-only):** effects confined to the 2021-06 anchor → single-event study of the largest
  wrapper migration; JFQA/MS tier with honest external-validity boundary.
- **D (precise zero):** with ~300 events the design is powered; a tight zero says the wrapper is
  irrelevant for macro incorporation — micro erosion (Sammon) without macro compensation —
  a clean input to the passive-investing welfare debate and a strong prior for the dual-share-
  class second wave. Short-paper exit.

## 11. Dissertation fit, the anti-salami defense, and the E2 contingency

- **Contingency logic:** DAX (approved) + P1 (approved) + {E2 if approved, else this chapter}.
  This chapter's Gate 0 runs weeks 1–6 from approval-to-start and reuses the P1 seat and
  pipeline, so it can be held at "Gate-0-passed, spec-frozen" state at near-zero carrying cost
  until the E2 verdict.
- **Anti-salami defense (advisor and referees will ask):** (i) disjoint information events
  (firm earnings vs. scheduled macro releases), (ii) disjoint outcome technology (quarterly
  panel vs. intraday event windows), (iii) disjoint theory targets (GNZ–ILS arbitration vs.
  Savor–Wilson/Bhattacharya–O'Hara), (iv) precedent: the Fed's own team splits market-quality
  and information papers on the *same* conversion events; (v) the two chapters jointly answer
  one question neither answers alone — where price discovery *goes* when wrappers change —
  which is the dissertation's thesis, echoing the advisor's original two-chapter design.
- **Timeline:** M0–M1.5 Gate 0; M2–M7 main results (heavy reuse of T5 blueprints); M8–M12
  draft + red team; SSRN by M12. Compatible with the P1 race clock because the marginal
  frontier-model load is concentrated in spec design (T3/T5 analogues) and writing.

## 12. Referee FAQ (pre-drafted responses)

1. *"Index products leading is mechanical (Hasbrouck). What's new?"* → The outcome is not the
   lead-lag; it is the causal effect of the wrapper on constituent-level incorporation quality
   — speed, permanence, beta discipline, liquidity cost — under delegation-constant identification.
2. *"How is this not your Chapter 1 again?"* → §11 defense; different events, outcomes, theory.
3. *"The JFR 2025 paper already did ETFs × FOMC."* → Endogenous ownership levels; return
   amplification only; we replicate their asymmetry as validation and answer the question they
   cannot: is the amplified move *information*? (fingerprint + reversal + beta discipline).
4. *"DFA dominance."* → Same honest dual reporting as Chapter 1; C exit pre-declared.
5. *"Few conversion waves → fake stars."* → Randomization inference in the main table, both
   permutation directions (conversion dates; announcement labels).
6. *"Small-cap intraday measurement is noise."* → Gate 0 pilot published in the appendix;
   outcomes aggregated to portfolio level as a low-noise cross-check.

## 13. Self-scores (house standard)

- **Academic feasibility 8/10:** event calendar public, surprises public (FOMC) or licensed
  (CPI/NFP); all identification assets already built by P1; binding risk is TAQ small-cap
  quality (gated, week 2–4).
- **Agenda extension 8/10:** dual-share-class second wave gives out-of-sample replication; the
  micro–macro reallocation frame spawns follow-ups (options listing, futures-ETF-stock triangle).
- **Identification rigor 7.5/10:** announcement timing exogeneity + within-announcement
  cross-section is cleaner than any calendar-time design in this literature; residual weakness
  is the same DFA concentration as Chapter 1, with the same mitigations.

**All-in judgment: worth building to Gate-0-passed standby status now; promote to full
execution the moment E2's verdict arrives (either way — if E2 passes, this becomes the natural
fourth paper / job-market spare).**

---

## Appendix A — verified citation list (retrieved 2026-07-12, single channel; run channel-B per R2)

- Sammon, "Passive Ownership and Price Informativeness," Management Science 71(6), 2025:
  https://pubsonline.informs.org/doi/10.1287/mnsc.2023.00836 · SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3243910
- Glosten, Nallareddy, Zou, "ETF Activity and Informational Efficiency of Underlying Securities,"
  Management Science 67(1), 2021: https://pubsonline.informs.org/doi/10.1287/mnsc.2019.3427
- Ernst, "Stock-Specific Price Discovery From ETFs" (WP): https://terpconnect.umd.edu/~ternst/docs/Ernst_ETF.pdf
- Hasbrouck, "Intraday Price Formation in U.S. Equity Index Markets," JF 58(6), 2003:
  https://onlinelibrary.wiley.com/doi/abs/10.1046/j.1540-6261.2003.00609.x
- Savor, Wilson, "Asset Pricing: A Tale of Two Days," JFE 113(2), 2014:
  https://www.sciencedirect.com/science/article/abs/pii/S0304405X14000890
- Lucca, Moench, "The Pre-FOMC Announcement Drift," NY Fed SR 512 / JF 2015:
  https://www.newyorkfed.org/research/staff_reports/sr512.html
- Ben-David, Franzoni, Moussawi, "Do ETFs Increase Volatility?" JF 73, 2018:
  https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12727
- Baltussen, van Bekkum, Da, "Indexing and Stock Market Serial Dependence Around the World,"
  JFE 132(1), 2019: https://www.sciencedirect.com/science/article/abs/pii/S0304405X18302034
- Bhattacharya, O'Hara, "Can ETFs Increase Market Fragility?" SSRN:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2740699
- "ETF Ownership and the Transmission of Monetary Policy," J. Financial Research (2025):
  https://onlinelibrary.wiley.com/doi/10.1111/jfir.70015 · WP: https://sites.temple.edu/lnaveen/files/2024/11/Austin_Kleespie_paper.pdf
- Hou, Moskowitz, "Market Frictions, Price Delay, and the Cross-Section of Expected Returns,"
  RFS 18(3), 2005: https://academic.oup.com/rfs/article-abstract/18/3/981/1617714
- Jung, Shiller, "Samuelson's Dictum and the Stock Market," Economic Inquiry 43(2), 2005:
  https://onlinelibrary.wiley.com/doi/abs/10.1093/ei/cbi015
- Saglam, Tuzun, "Implications of Growth in ETFs: Evidence from Mutual Fund to ETF Conversions,"
  FEDS Note 2025-11-19: https://www.federalreserve.gov/econres/notes/feds-notes/implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-conversions-20251119.html
- SF Fed U.S. Monetary Policy Event-Study Database:
  https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/
- Israeli, Lee, Sridharan (2017 RAST) — carried over from the P1 literature pack (already
  verified there); Callaway–Sant'Anna / Sun–Abraham / Romano–Wolf — methods papers, cite from
  the P1 pack.

## Appendix B — pipeline reuse map (for ops/ when this is promoted to a task family)

| Need | Source | New work? |
|---|---|---|
| Conversion events | P1 T1 (events_merged.csv, frozen schema) | No |
| ConvExp panel | P1 T2 (conv_exposure.parquet) | No |
| Power simulation | P1 T2a machinery, re-parameterized to announcement counts | Light (M0) |
| Macro calendar + surprises | New task M1 (dual-channel extraction, USMPD + consensus) | Yes, cheap tier |
| TAQ announcement-window pipeline | New task M2 (Claude Code) | Yes — the main new build |
| Estimation blueprints | P1 T5 spec + announcement-FE amendment | Light (frontier, dual-channel) |
| Fingerprint plots | P1 T6 visual grammar, horizon axis in hours/days | Light |
| Robustness grid / figures / writing / red team | P1 T7–T10 templates verbatim | Config only |

Monthly collision monitor (extend P1 T0 phase B): add keywords
[ETF macro announcement price discovery; passive ownership macroeconomic news; FOMC ETF
transmission speed], and track Sammon, Ernst, the JFR 2025 authors, and Saglam–Tuzun–Wermers
for macro-side extensions. ALERT threshold unchanged (≥60% overlap).
