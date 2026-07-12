# One Shock, Many Prices: ETF Baskets and the Refraction of Macroeconomic News
## Standby dissertation chapter — complete research plan (v2.1 final, 2026-07-12)

> **Purpose.** Advisor-facing, self-contained plan. Chapters approved: P1 (fund conversions ×
> earnings information) and DAX. E2 is pending. This chapter is designed to top-field standard
> as a standby replacement should E2 not be approved, and as the natural fourth paper /
> job-market spare if it is. It descends from the advisor's original "Project 1 as two
> chapters" idea — micro events (earnings) and macro events — with the macro half rebuilt
> three times: to escape the mechanical lead-lag fact (v0→v1), to absorb the first external
> review (v1→v1.1), and to absorb a second review that surfaced the basket≈market threat and
> the Gate-0 shrinkage coupling (v2.0→v2.1). This document supersedes all prior versions and
> stands alone.
>
> **Citation discipline (house rules R1/R2).** Core citations were verified with working
> links on 2026-07-12 (Appendix A); entries added from external review are flagged
> `[VERIFY-CHANNEL-B]` pending the second-channel sweep, which must run before advisor
> submission. No number in this document comes from model memory; priors requiring data are
> marked `[VERIFY-IN-GATE-0]`.

---

# Part I — Background: what happened to the original macro-event idea

## I.1 The original two-part conception

The original P1 idea was one economic question split in two: around firm-specific news
(earnings), price discovery happens in the individual stock and the ETF lags; around
economy-wide news (FOMC, CPI, employment), price discovery happens in index products and the
individual stock lags. The micro half became Chapter 1 (P1) after Sammon (MS 2025) occupied
the passive-ownership × pre-earnings price-discovery cell; P1's pivot to the mutual-fund→ETF
conversion natural experiment, with the permanent-vs-reversal fingerprint, is approved and
in execution. This plan is the macro half, upgraded.

## I.2 Why the naive macro design fails, twice

**Old news.** "ETFs/index products move first on macro news" has been a mechanical fact since
Hasbrouck (JF 2003): ~90% of index price discovery initiates in futures/ETFs. Documenting
lead-lag around FOMC would be rejected as known.

**The saturated conduit.** The natural upgrade — a causal estimate of how the wrapper changes
the *speed* of common macro-news incorporation into constituents — fails on economics: the
macro-arbitrage conduit into a treated stock already exists before conversion, through its
Russell/sector/factor ETF ownership, which is typically several times larger than the
conversion exposure (ConvExp ≈ 0.5–2% on top of pre-existing ETF ownership that P1's T2
already measures). One more arbitrage-linked wrapper barely moves the transmission channel
for *common* information; a design built on that margin predicts its own null. It also
requires intraday TAQ quality precisely for DFA-style small/mid caps — the worst sample —
placing the only new build and the binding data risk on the same critical path, and its
apparent power (~300 announcement days) is outcome repetition, not treatment variation.

## I.3 The open cell this plan occupies

The conversion's one genuinely **new** object is the **basket**: an arbitrage-enforced,
exchange-traded claim on the fund's portfolio that did not exist before the flip. Existing
index ETFs cannot saturate this channel because they are different baskets. The literature
around the cell:

| Verified paper | What it established | What it leaves open |
|---|---|---|
| Hasbrouck (JF 2003) | Index products lead aggregate price discovery, mechanically | Constituent-level consequences; anything causal about the wrapper |
| Greenwood (RFS 2008); Da–Shive (EFM 2018) | Index weight / ETF activity correlates with excess comovement; reversal inferred from autocorrelations | Endogenous weights; unconditional windows; "excess" inferred indirectly |
| Barberis–Shleifer–Wurgler (JFE 2005); Boyer (JF 2011) | Habitat/category comovement theory; index-membership evidence | Membership changes are committee-selected; no delegation-constant experiment |
| Marta–Riva (WP) `[VERIFY-CHANNEL-B]` | Synthetic→physical replication switch (Europe) moves comovement — nearest causal neighbor | Unconditional outcomes; no stock-level signed lever; no information verdict |
| Savor–Wilson (JFQA 2013; JFE 2014) | Macro days carry a premium; beta prices returns only on those days | Whether market structure *causes* announcement-day pricing tightness |
| Andersen–Thyrsgaard–Todorov (QE 2021); Bodilsen et al. (JBF 2021) `[VERIFY-CHANNEL-B]` | Announcement windows restructure cross-sectional systematic risk economy-wide; betas are state-dependent | The differential, wrapper-caused restructuring |
| Ben-David–Franzoni–Moussawi (JF 2018); Greenwood–Thesmar (JFE 2011); Dannhauser–Hoseinzade (RFS 2021) | Pressure/fragility channels exist (unconditional; bond-ETF stress episode) | Whether pressure or discipline dominates at scheduled macro moments, causally |
| Bhattacharya–O'Hara (SSRN) | Theory: market makers learn from ETF prices; herding possible | The empirical test, with the learning vs. arbitrage conduits separated |
| Brogaard–Heath–Huang (JFQA 2025) `[VERIFY-CHANNEL-B]` | ETFs sample/customize baskets; arbitrage effects liquidity-heterogeneous | Treated here as attenuation + measured heterogeneity in a conversion design |
| "ETF Ownership and the Transmission of Monetary Policy" (JFR 2025) | Endogenous ownership levels × MP-surprise return amplification, asymmetry | Causal wrapper wedge; cross-sectional allocation; any efficiency verdict |
| Saglam–Tuzun (FEDS Note 2025) | Conversions → volatility/liquidity (validates first stage at stock level) | Anything information-side; anything announcement-conditioned |
| Sammon (MS 2025) | Passive erodes micro (pre-earnings) discovery | The macro mirror cell — which his result makes sharper |

**The cell:** *a causal estimate of whether a newly wrapped basket refracts scheduled
macroeconomic news into its constituents — tilting each stock's announcement response away
from its own macro exposure toward the basket's — and whether the refracted component is
information or noise.* Collision sweeps on (conversion × comovement), (ETF basket ×
macro-announcement cross-section), and (passive ownership × announcement-day beta pricing)
found the cell open as of 2026-07-12 (single channel; channel-B pending per R2).

---

# Part II — Research design

## 0. Positioning and race clock

Saglam–Tuzun validated the first stage; P1 claims the earnings-information cell; the JFR 2025
paper shows macro-transmission questions are being asked with endogenous ownership; Marta–Riva
shows causal-comovement designs are being sought. Execution assumes the P1 race clock:
working paper circulating within ~11 months of Gate 0 passing.

## 1. Research question and contributions

**One sentence.** When a mutual fund becomes an ETF — manager, strategy, holdings, and
delegation unchanged; only the wrapper changes — does the newly tradable, arbitrage-enforced
basket refract scheduled macroeconomic news (FOMC, CPI, employment) into its constituents,
tilting each stock's announcement response away from its own macro exposure (β_i × surprise)
toward the basket's common response; and is the refracted component information (discipline)
or noise (fragility)?

**Three contributions.**

1. **First causal switch-on of the basket-comovement channel, conditioned on identified
   information events.** Greenwood, Da–Shive, and BSW establish correlation and theory with
   endogenous weights and unconditional windows; Marta–Riva's replication switch is causal
   but unconditional and lever-less. Here the basket is switched on by a delegation-constant
   natural experiment, and each event carries a measured fundamental benchmark (β_i × S_a)
   against which "excess" is defined directly, announcement by announcement.
2. **Arbitration of efficiency vs. fragility at the moments the cross-section prices risk.**
   Savor–Wilson show macro days are when beta should price; the intraday-beta literature
   shows announcement moments restructure cross-sectional risk economy-wide — the exact
   background against which a wrapper-caused *differential* restructuring is defined. The
   refraction coefficient, the wedge fingerprint, and the fundamental-anchoring test decide
   the verdict with opposite-signed predictions; every main exit is a positive result.
3. **Policy input on market resilience at macro events.** With 203 conversions (~$260B) by
   end-2025 and the dual-share-class wave beginning 2026, whether wrapper migration makes the
   cross-section of macro responses noisier or more disciplined exactly when macro
   uncertainty resolves is first-order for the SEC/Fed market-functioning agenda already
   engaged by Saglam–Tuzun.

**Boundary vs. Chapter 1 (P1):** P1 asks how the wrapper changes the *time-series
incorporation of firm-specific information* (GNZ–ILS arbitration; quarterly panel; earnings
events). This chapter asks how the wrapper changes the *cross-sectional allocation of common
information* (BSW-habitat vs. Savor–Wilson arbitration; announcement-day cross-sections; the
basket as the treatment's own new object). Different information type, outcome geometry,
theory family, and identifying variation (the three-way ConvExp × L × S interaction has no
analogue in P1). Full anti-salami defense in §11.

## 2. Institutional background and events

**Conversion side (identical event set to P1, frozen contract).** SEC Rule 6c-11 (2019)
cleared the path; Guinness Atkinson first (2021-03); **DFA 2021-06-11 anchor wave** (~$30B
US equity in one day); 203 cumulative conversions ~$260B through 2025; SEC dual-share-class
relief (2025-12) opens the second wave — the out-of-sample extension and this chapter's
sample right-boundary. Honest framing carried from P1: one large-mass event plus a
time-series of smaller replications, not textbook staggered adoption. Reuse
events_merged.csv and conv_exposure.parquet as-is.

**Custom-basket fact-finding (mechanism prerequisite).** Under Rule 6c-11, ETFs may use
custom creation baskets that are subsets of holdings. The institutional section will
document, from N-CEN and prospectus language, whether the anchor-wave ETFs used
full-replication or custom baskets — a mechanism fact the paper states, not assumes.

**Macro side.** Scheduled FOMC statements (8/yr, 14:00 ET), CPI (monthly, 08:30 ET,
pre-open), Employment Situation (monthly, 08:30 ET, pre-open). Surprises: FOMC from the
SF Fed U.S. Monetary Policy Event-Study Database (public); CPI/NFP as actual-minus-consensus,
normalized (`NEED_HUMAN: confirm consensus license — Bloomberg ECO at BU vs. WRDS
alternative`; FOMC-only results are unblocked regardless). The 08:30/14:00 split gives two
microstructure regimes (opening-auction vs. continuous-session absorption) — a built-in
replication — and the 08:30 releases additionally give a free daily-data timing split
(§7 spine 1).

Sample: announcements 2017-01–2026-06; conversions 2021-03–2025-12, US equity only (P1
filter; fixed income and international excluded); stock × announcement panel, daily
frequency on the critical path.

## 3. Conceptual framework and hypotheses

**Objects.**

- **β_i — announcement-regime beta.** Stock i's macro-response coefficient estimated from its
  *pre-conversion announcement-day* responses (r_i on S_a, pooled over all pre-period
  announcements, Vasicek-shrunk toward a characteristics-implied prior). Announcement betas
  are state-dependent (ATT 2021; Bodilsen et al. 2021; Chen–Jiang 2024), so the lever must be
  measured in the regime where the outcome lives; unconditional rolling betas would make it
  partly stale noise.
- **β_b^LOO(i) — leave-one-out basket response** of the converting fund's portfolio
  (leave-one-out kills the mechanical own-component; with thousands of holdings it is
  precisely estimated — estimated, never assumed ≈ 1).
- **L_i = β_b^LOO(i) − β_i — the refraction lever**, a signed, stock-specific mismatch
  measure, **decomposed** into a market-pull component and a basket-tilt component:
  L_i = (1 − β_i) + (β_b^LOO − 1) ≡ L^mkt_i + L^tilt_b. This decomposition addresses the
  design's deepest interpretive threat (the **basket ≈ market problem**): for a broadly
  diversified converting fund, β_b^LOO ≈ 1, so L_i ≈ 1 − β_i and "refraction toward the
  basket" is observationally close to generic compression of betas toward the market. The
  two directions are separable only where the basket is *tilted* — β_b ≠ 1 and/or the
  basket carries non-market factor exposures whose announcement responses differ from the
  market's (small/value baskets react differently to rate and inflation news). The
  DFA-style anchor funds are small-cap-value tilted, and many later conversions are
  factor/dividend/thematic — but the empirical mass of basket distinctiveness
  D_b = |β_b^LOO − 1| plus factor-tilt magnitude across waves is a Gate-0 fact
  `[VERIFY-IN-GATE-0]`, and a **framing gate** in §10 downgrades the paper's language to
  "wrapper-induced beta compression" if distinctiveness fails.
- **F'λ_b — basket factor tilt.** The basket's non-market announcement response: the
  component of the basket's S_a-response not explained by β_b times the market response
  (estimated from the basket's pre-period announcement-day returns orthogonalized to the
  market). Refraction toward *this* component is uniquely basket-specific — no
  market-compression story can generate it.

**Mechanism.** Pre-conversion, a surprise S_a reaches stock i only through direct trading;
its response ≈ β_i·S_a. Post-conversion the ETF price updates within seconds (Hasbrouck) by
≈ β_b·S_a, opening two conduits that push i toward the *basket's* response: (i) the
**arbitrage conduit** — AP/HFT creation-redemption trades, weighted by creation-basket
inclusion and liquidity, not uniformly pro-rata (Brogaard–Heath–Huang; unobserved sampling
attenuates the estimate, which is conservative); (ii) the **learning conduit** — the stock's
market makers re-quote off the observable ETF tape (Bhattacharya–O'Hara), strongest for
illiquid, high-information-asymmetry names. Because typical converting baskets hold thousands
of names, refraction has a crisp observable signature: **differential compression of the
cross-section of announcement-day responses toward the basket mean** — always stated
treated-vs-control *within* announcement, because announcement days compress beta dispersion
economy-wide (ATT 2021) and only the differential is the estimand.

**Hypotheses (each bound to a signature; the signature is the referee).**

- **H1 (refraction — the headline).** Under the pressure/habitat view, the coefficient γ on
  Post × ConvExp × (L_i·S_a) is positive: responses tilt toward the basket. Under the
  efficiency view γ ≈ 0: arbitrage brings the stock to its *own* beta-implied value faster
  and more precisely. Sign, not just significance, discriminates — the two camps predict
  different coefficients, not the same "faster." **H1 is estimated in decomposed form:**
  γ_mkt on Post×ConvExp×(L^mkt_i·S_a), γ_tilt on Post×ConvExp×(L^tilt_b·S_a), and γ_fac on
  Post×ConvExp×(basket factor-tilt response). The *basket-specific* refraction claim rests
  on γ_tilt and γ_fac; γ_mkt alone supports only the weaker "wrapper-induced beta
  compression" claim (still a result — the wrapper homogenizes macro-day responses — but
  framed as such, per the §10 framing gate). A hostile referee's "this is just beta
  mean-reversion" is answered structurally: the economy-wide Post×(L·S) lower-order term is
  in the specification (§6), so any generic mean-reversion common to treated and control
  stocks is absorbed, and γ_fac cannot be generated by any market-direction story.
- **H2 (wedge fingerprint with triangulated verdict — the heart).** Construct the fitted
  basket-induced wedge W_{i,a} = γ̂·Post·ConvExp_i·L_i·S_a. The verdict rests on three legs:
  1. **Reversal path** of W over {+1d, +5d, +20d, +60d} — the +60d horizon prevents
     misclassifying *slow* information incorporation as permanence. Because the own-beta
     response is differenced out, pre-FOMC drift and macro momentum load on λ_a and β_i·S_a,
     not on the wedge — a cleaner fingerprint than any total-move reversal.
  2. **Discipline (H3)** must move the same direction as the verdict.
  3. **Fundamental anchoring:** does W predict the refracted stocks' *subsequent fundamental
     news* (next-quarter earnings surprises, analyst revisions — P1's IBES machinery
     re-targeted)? Basket-carried information should forecast fundamentals; pressure should
     not.
  Efficiency requires (no reversal ∧ discipline↑ ∧ anchoring > 0); fragility requires
  (reversal ∧ anchoring ≈ 0), with the Greenwood-style wedge-reversal portfolio alpha as the
  dollar exhibit. Partial patterns are decomposition results, mapped in §10.
- **H3 (discipline — the Savor–Wilson sharpening).** Announcement-day cross-sectional
  regression of realized responses on β_i·S_a: does slope→1 and R²↑ for high-ConvExp stocks
  post-conversion (efficiency), or does fit against *own* beta fall while fit against
  *basket* beta rises (fragility)? Same daily panel; the second independent discriminator,
  and it does not run through L̂ — so it carries the efficiency case where attenuation makes
  γ conservative only for rejecting zero.
- **H4 (dose–response and mechanism separation).** γ scales with |S_a| (zero on no-surprise
  days — built-in placebo), ConvExp, |L_i| (stocks whose betas sit far from the basket
  refract most — a prediction unavailable to endogenous-ownership designs), and
  post-conversion measured arbitrage activity (creation/redemption frequency,
  premium/discount half-life; Bloomberg-dependent → enhancement layer, floor-design rule:
  main results may not depend on it). **Pre-registered heterogeneity set, frozen at Gate 0,
  interactions capped at triple, Romano–Wolf within family:** Amihud illiquidity and analyst
  coverage (learning conduit should dominate here); basket weight and creation-basket
  inclusion where observable (arbitrage conduit); pre_etf_ownership (saturation — a *signed
  dampening* prediction: pre-existing basket connectivity should mute marginal refraction).
- **H1′/H5′ (gated enhancement spines).** The full intraday program — speed (share of move in
  5/15/30/60 min; intraday IPT) and announcement-window liquidity (effective/quoted spreads,
  depth, price impact in [−15m, +60m]) — runs iff the TAQ pilot passes its non-blocking gate
  (§9). Reported as mechanism color, never load-bearing: identification of H1–H4 is defined
  at daily horizons and does not require minute-level resolution.

## 4. Data

| Data | Source | Use | Risk |
|---|---|---|---|
| Conversion events, ConvExp, pre_etf_ownership | **Reuse P1** T1/T2 frozen outputs (events_merged.csv, conv_exposure.parquet) | Treatment; saturation control | None new |
| Macro calendar + FOMC surprises | SF Fed USMPD (public); FOMC/BLS/BEA schedules | Event set; S_a | Low |
| CPI/NFP consensus | Bloomberg ECO at BU or WRDS alternative | S_a for 08:30 releases | Gate-0 `NEED_HUMAN`; FOMC-only results unblocked |
| Daily prices incl. **open** | CRSP | All core spines; timing splits | Standard |
| Announcement-regime betas (β_i, β_b^LOO) | Constructed from pre-period announcement-day responses; Vasicek shrinkage; characteristics-implied prior | Refraction lever L | Estimation noise → §6 battery; Gate-0 estimability check |
| Earnings surprises / analyst revisions | IBES (P1 T3 pipeline re-targeted) | Fundamental-anchoring test | None new |
| Creation-basket composition (daily) | Issuer files / ETF Global | Arbitrage-conduit inclusion (H4) | Enhancement; `NEED_HUMAN: coverage` |
| Intraday TAQ | WRDS | H1′/H5′ enhancements only | Off the critical path by design |
| ETF mechanics (shares outstanding, premium/discount) | Bloomberg; N-CEN | H4 dose | Enhancement layer |
| Controls | Compustat; CRSP MF flows; 13F/N-PORT; Russell constituents | P1 control set carried over | Standard |

## 5. Treatment definition and controls

**Treatment (P1 frozen contract).** ConvExp_i,e = Σ_f (converting fund f's pre-conversion
holdings of stock i) / shares outstanding, per wave e; continuous main treatment; binary
(≥0.5%) in robustness.

**Three control layers.**

1. **Within-holdings intensity gradient (main table):** top vs. bottom terciles of ConvExp
   among held stocks — family- and fund-level shocks (fees, brand, flows, clientele)
   difference out; only stock-level exposure differs. Selection chooses *funds*, not the
   within-portfolio ranking of exposure and lever.
2. **Twin unconverted same-family funds — upgraded to a mechanism falsification:** compute
   the *twin basket's* lever L^twin_i for the same stocks and show **no refraction toward a
   basket that was never wrapped**, plus pseudo-event-date placebos. Same selection machine,
   no wrapper: the sharpest falsification available.
3. **Characteristic-matched non-held stocks** (size × B/M × industry × pre-ETF ownership ×
   Amihud nearest neighbor).

All three must agree; layer 1 is the main table, layers 2–3 the appendix.

## 6. Identification

**Main specification** (stock i, announcement a with surprise S_a, wave e; stacked by wave
with clean controls; never bare TWFE):

r_{i,a} = b₁·(β_i S_a) + b₂·(Post_{e,a} × ConvExp_{i,e})·(β_i S_a)
        + b₃·Post_{e,a}·(β_i S_a) + b₄·Post_{e,a}·(L_i S_a)
        + **γ·(Post_{e,a} × ConvExp_{i,e})·(L_i S_a)**
        + λ_a + δ_{ind×a} + α_i + θ'X_{i,t(a)} + ε_{i,a}

λ_a absorbs the common shock entirely; δ_{ind×a} kills industry macro loadings. The
lower-order Post terms (b₃, b₄) are load-bearing, not boilerplate: **b₄ absorbs
economy-wide beta mean-reversion** — true betas drifting toward 1 over time, or stale
pre-period β̂ error, generates positive loading on Post×(L·S) for *all* stocks; γ is
identified only off the ConvExp gradient on top of it. Identification is purely
cross-sectional within announcement, off the three-way continuous interaction
ConvExp × L_i × S_a. The main table reports γ in decomposed form (γ_mkt, γ_tilt, γ_fac per
§3 H1); the pooled γ is a summary row. Callaway–Sant'Anna and Sun–Abraham adaptations as
robustness (P1 T5 blueprints).

**Beta measurement (the design's one new threat, engineered down).** L̂ attenuates γ and its
error can correlate with size/liquidity. Battery: (i) announcement-regime estimation with
Vasicek shrinkage (§3); (ii) **portfolio-level replication of every main table** —
L-quintile portfolios of treated stocks kill idiosyncratic estimation noise; (iii)
errors-in-variables check instrumenting announcement-regime beta with unconditional beta
from an independent pre-period window; (iv) randomized-L placebo — permute L within the
treated set, γ must die. Attenuation is conservative for rejecting γ = 0 but not for the
efficiency verdict; the discipline and anchoring legs, which do not run through L̂, carry
the efficiency case. **Shrinkage coupling (a hidden tension, now explicit):** shrinkage
buys β̂ precision but mechanically compresses the cross-sectional dispersion of β̂ and hence
SD(L̂) — the two Gate-0 pass lines (lever dispersion; estimability) are traded off through
the same knob. Gate 0 therefore runs a **shrinkage-intensity sweep** and requires a
non-empty, non-knife-edge window of shrinkage weights in which both lines hold
simultaneously; the main-spec weight is chosen inside that window and frozen, and the §8.4
battery spans the window's endpoints. If the window is empty, the stock-level design fails
jointly, not line-by-line, and the portfolio-level design becomes primary.

**Pre-trends on the response object itself.** Three exhibits: (a) event-time γ̂ over 8+
pre-quarters of announcements; (b) pre-conversion trends in treated stocks'
announcement-regime betas vs. matched controls; (c) **placebo-in-time** — the full design
re-estimated on 2017–2020 with fake conversion dates; γ must be zero.

**Inference (honesty first).** Effective treatment shocks = conversion waves (few,
DFA-heavy), stated in the text, not a footnote; announcement days multiply outcomes, not
treatment variation. Four-way suite, randomization inference in the main table: (i) two-way
clustering (announcement day × wave/industry); (ii) wild cluster bootstrap; (iii) RI
permuting conversion dates; (iv) RI permuting announcement labels (vs. matched
non-announcement days) and basket assignment L across treated stocks.

**Threats and answers.**

- **T1 — fund selection into conversion.** Layer-1 gradient + estimand stated narrowly
  ("the effect along the exposure/lever gradient within converted holdings"); the §6
  pre-trend triple is the direct evidence that macro-day response patterns, not just fund
  characteristics, were parallel.
- **T2 — anticipation.** The macro calendar is exogenous and scheduled; conversion
  anticipation handled by excluding each wave's announce-to-effective transition window
  (P1 rule).
- **T3 — 2021-06 confounds (Russell reconstitution two weeks after DFA; meme aftershocks).**
  Less binding here because outcomes are announcement-conditioned cross-sectional *tilts*,
  orthogonal to reconstitution level effects — but run the P1 reconstitution controls and
  the drop-2021Q2–Q3 robustness anyway; non-June waves are the pure replication.
- **T4 — flows and fees (C3/C4).** P1 controls carried over: fund net flows, Lou-style
  flow-induced trading (FIT). FIT matters more here because it is itself pro-rata — so show
  refraction survives the FIT control, and note FIT cannot generate |S_a|- or L-scaling;
  the no-surprise-day placebo separates flow days from information days.
- **T5 — pre-existing baskets (the saturation control).** Treated stocks already sit in
  Russell/sector baskets whose levers may correlate with the conversion basket's. Control
  Post × pre_etf_ownership × (L^Russell_i · S_a) directly — the critique that kills the
  naive speed design becomes a control variable here — and exploit the signed heterogeneity:
  refraction should be strongest where the conversion basket is most distinct from the
  stock's existing habitat (low basket-overlap subsample).
- **T6 — creation-basket sampling.** Unobserved custom-basket exclusion attenuates γ
  (conservative); where daily basket files exist, inclusion is measured and becomes a signed
  heterogeneity test; the institutional section documents anchor-wave basket practice from
  filings.
- **T7 — announcement-day algorithmic-trading trends.** Secular growth in machine reaction
  speed could differentially touch index-connected names; layer-1 comparisons are within the
  same announcement and holdings pool, and the placebo-in-time bounds any trend loading.

## 7. Outcome spines (four core — all daily data; two gated enhancements)

1. **Refraction spine (H1).** γ at the announcement-day horizon; the compression exhibit —
   treated-stock responses plotted against β_i·S_a, pre vs. post, within announcement: the
   visual "rotation toward the basket line." **Daily timing decomposition:** CPI/NFP (08:30)
   — close→open (auction absorbs the release) vs. open→close; FOMC (14:00) —
   prev-close→close (contains the release) vs. close→next-open vs. subsequent days. This is
   the maximum timing content daily data supports; finer resolution lives in H1′.
2. **Wedge-fingerprint spine (H2 — main evidence).** Cumulative wedge response at
   {0, +1d, +5d, +20d, +60d}; treated−control wedge plot in the P1 T6 visual grammar
   (horizon in days); the wedge-reversal long-short portfolio (alpha = the dollar cost of
   refraction, if fragility wins); **fundamental-anchoring regressions** (wedge →
   next-quarter SUE and analyst revisions).
3. **Discipline spine (H3).** Announcement-day cross-sectional R² and slope on own beta vs.
   basket beta, treated vs. control, pre vs. post — the Savor–Wilson security-market line as
   an *outcome variable*.
4. **Dose/heterogeneity spine (H4).** |S_a|, ConvExp, |L|, arbitrage-activity gradients;
   the pre-registered heterogeneity set (§3) separating the learning and arbitrage conduits;
   saturation as signed dampening.
5. **Enhancements (gated, non-load-bearing):** H1′ intraday speed; H5′ announcement-window
   liquidity — the full original intraday program, promoted iff the TAQ pilot passes.

## 8. Robustness (referee-ordered)

1. **Drop DFA / DFA only** — the shared soft spot with Chapter 1; honest dual reporting;
   C exit pre-declared.
2. **Estimators:** stacked / Callaway–Sant'Anna / Sun–Abraham; event-study dynamics with 8+
   pre-quarters of announcements.
3. **Inference:** the four-way suite; RI in the main table.
4. **Beta-construction battery (headline robustness):** announcement-regime vs.
   unconditional vs. characteristics-implied betas; shrinkage on/off; window lengths;
   **portfolio-level replication of every main table.**
5. **Surprise measures:** futures-window vs. survey-based; sign splits — replicate the
   JFR 2025 asymmetry as validation, then show refraction is distinct; announcement types
   separately (FOMC / CPI / NFP) and pooled; 08:30 vs. 14:00 regimes.
6. **Exclusions:** 2021Q2–Q3 (meme + Russell); COVID; <$5 stocks. (P1 grid rows, config only.)
7. **Placebos:** no-surprise announcement days; matched non-announcement days (weekday/time);
   twin-basket falsification; randomized L; placebo-in-time (fake conversion dates,
   2017–2020); saturation gradient as a signed prediction.
8. **Multiple testing:** Romano–Wolf within each spine and within the heterogeneity family
   separately.

## 9. Gate 0 — five-week kill-switch (all core lines must pass before full commitment)

| Week | Task | Pass line |
|---|---|---|
| 1 | Macro calendar + surprise series (USMPD first; consensus license `NEED_HUMAN`) | ≥95% of 2017–2026 releases with usable S_a; FOMC series complete regardless |
| 1–2 | **Joint lever/estimability check via shrinkage-intensity sweep (decisive; the two lines are coupled — shrinkage buys SE(β̂) by compressing SD(L̂)):** sweep shrinkage weights; at each, compute SD(L̂) among ConvExp ≥ 0.5% stocks and shrinkage-adjusted SE(β̂_i) | A non-empty, non-knife-edge window of weights in which **simultaneously** SD(L̂) ≥ 0.25 `[VERIFY-IN-GATE-0]`, \|corr(L, ConvExp)\| ≤ 0.3, median pre-period announcements ≥ 30, and SE(β̂_i) ≪ SD(L̂) for ≥70% of treated names. Empty window → stock-level design fails jointly; portfolio-level becomes primary or kill |
| 2 | **Basket-distinctiveness check (the basket≈market gate):** distribution of D_b = \|β_b^LOO − 1\| and basket factor-tilt announcement responses across waves | Sufficient treatment mass with D_b ≥ 0.1 and/or economically meaningful factor-tilt responses `[VERIFY-IN-GATE-0]` to power γ_tilt/γ_fac — else the §10 framing gate binds ex ante: claims pre-committed to "wrapper-induced beta compression," basket-specific language dropped |
| 2–3 | Power simulation (reuse P1 T2a machinery) on the joint (ConvExp, L, S) distribution, wave-clustered, run separately for γ pooled, γ_tilt, and γ_fac | MDE(γ) ≤ 0.5σ of announcement responses at baseline priors; else kill. **The power sim also gates exit D:** a null is claimable as evidence only if the realized design could detect γ of the magnitude implied by the Da–Shive/Greenwood correlations — this bar is computed and archived at Gate 0, before any outcome is seen |
| 3–4 | **Pre-trend triple:** event-time γ̂; announcement-beta trends; placebo-in-time | All three flat/zero over 8 pre-quarters |
| 4–5 | *Parallel, non-blocking:* TAQ pilot (30 treated + 30 control × 20 announcement days) | ≥70% usable coverage incl. small caps → promote H1′/H5′; fail → drop enhancements, core unaffected |

Any core-line failure → exit matrix, no forcing. Incremental cost above P1: ~one seat-week
(daily announcement panel + beta construction, +2–3 seat-days for regime betas and
diagnostics); TAQ pilot only if pursuing enhancements.

## 10. Exit matrix (every main exit is a positive result)

- **A (discipline win):** γ ≈ 0 ∧ own-beta pricing tightens ∧ the (small) wedge anchors to
  fundamentals → *"the wrapper enforces the CAPM on the days it is supposed to hold"* —
  Savor–Wilson sharpened as a market-structure result. Target JF/JFE/RFS.
- **B (refraction-as-pressure win):** γ > 0 ∧ wedge reverses by +60d ∧ no fundamental
  anchoring → causal confirmation of Bhattacharya–O'Hara herding at macro moments; the
  reversal-portfolio alpha is the quotable cost; *"the index revolution compresses and
  distorts the macro cross-section."* Equally publishable; higher policy salience.
- **B′ (refraction-as-information):** γ > 0 ∧ no reversal ∧ anchoring > 0 → the basket
  *delivers* macro-relevant information the stock's own market lacked — a genuinely novel
  positive verdict available only under the triangulated design. Strong paper.
- **C (DFA-only):** effects confined to the 2021-06 anchor → single-event study of the
  largest wrapper migration; JFQA/MS tier with honest external-validity boundary.
- **D (precise zero — contingent, not a standing safe exit):** a tight γ = 0 is claimable
  as evidence *against* the causal reading of the comovement correlations (Greenwood,
  Da–Shive) **only if** the Gate-0 power bar was cleared — the archived, pre-outcome
  demonstration that the design could detect γ of the magnitude those correlations imply.
  "Didn't find it" without that bar is low power, not refutation, and is reported as such
  (an honest non-result feeding the dual-share-class second wave, not a paper). With the
  bar cleared, D is a short-paper exit that contradicts an existing literature.

**Framing gate (binds across all exits):** if the Gate-0 basket-distinctiveness check
fails — the treatment mass has β_b^LOO ≈ 1 and negligible factor tilts — the paper's claims
are pre-committed to the weaker, still-true estimand **"wrapper-induced beta compression of
macro-day responses"** and all "basket-specific refraction" language is dropped, because
market-pull and basket-pull are then observationally indistinguishable. The twin-basket
falsification still rules out non-wrapper channels; only the *direction* claim narrows.
This commitment is made ex ante precisely so the framing cannot be chosen after seeing γ.

## 11. Dissertation fit, anti-salami defense, contingency, timeline

**Contingency logic:** DAX (approved) + P1 (approved) + {E2 if approved, else this chapter}.
Gate 0 runs weeks 1–5 from approval-to-start, reuses the P1 seat and pipeline, and the
chapter holds at "Gate-0-passed, spec-frozen" standby at near-zero carrying cost (no
intraday pipeline to maintain) until the E2 verdict. If E2 passes, this becomes the natural
fourth paper / job-market spare. Operationally, this maps to a dormant `refraction/` task
family: the Gate-0 kill-switch encoded in the queue but blocked behind a `GATE-E2-VERDICT`
human gate, consuming zero budget until flipped.

**Timestamped public pre-registration (the pre-commitment IS the credibility).** At Gate-0
freeze, register on OSF (or the AEA registry): the main specification with the γ
decomposition; the frozen shrinkage weight and its feasibility window; the heterogeneity
set; the triangulated verdict rules and the full exit matrix including the framing gate and
the exit-D power bar; the pre-period placebo results. Five exits plus decomposition
reporting creates narrative degrees of freedom that only a public timestamp neutralizes —
a hostile referee reads un-registered multi-exit designs as ex-post storytelling, and this
design's honesty architecture is its main asset.

**Anti-salami defense (structural, not rhetorical):** (i) disjoint information events
(firm earnings vs. scheduled macro releases); (ii) disjoint outcome geometry (time-series
incorporation in a quarterly panel vs. cross-sectional allocation within announcements);
(iii) disjoint theory targets (GNZ–ILS vs. BSW-habitat/Savor–Wilson/Bhattacharya–O'Hara);
(iv) disjoint identifying variation (the three-way ConvExp × L × S interaction has no P1
analogue); (v) precedent — the Fed's own team splits market-quality and information papers
on the same conversion events; (vi) jointly the chapters answer what neither can alone:
**the index revolution reallocates price discovery across the micro–macro boundary** —
Chapter 1 measures what the wrapper does to a stock's own news; this chapter measures what
it does to everyone's news. Samuelson's dictum (Jung–Shiller 2005) as the thesis arc:
Sammon shows passive erodes micro efficiency; this chapter asks whether the same revolution
disciplines or distorts the macro cell at the stock level. This is the advisor's original
two-chapter request, upgraded to causal designs twice over.

**Timeline:** M0–M1.25 Gate 0; M2–M6 main results (heaviest possible reuse of P1 T5–T8);
M7–M11 draft + two red-team rounds (P1 T10 protocol: non-Claude referees, cold-start second
round); SSRN by M11. Compatible with the P1 race clock — the marginal frontier-model load
concentrates in spec design and writing.

**Monthly collision monitor (extends P1 T0 phase B):** keywords [ETF basket comovement
announcement; conversion comovement; announcement day beta ETF; ETF replication switch
comovement; creation basket transmission; passive macro news cross-section]; track Da/Shive,
Greenwood, Marta–Riva, Brogaard–Heath–Huang, the JFR 2025 authors, Sammon, Ernst, and
Saglam–Tuzun–Wermers. ALERT threshold ≥60% overlap — **except Marta–Riva at ≥40%**: as the
nearest causal neighbor, their moving from WP to published or extending to conditional
(announcement) windows is the single external event that most changes this design's novelty
claim, so it gets a hair trigger and the channel-B verification of their current status runs
*before* positioning is finalized, not merely before submission.

## 12. Referee FAQ (pre-drafted responses)

1. *"Comovement from ETFs is known (Da–Shive, Greenwood)."* → Known as an endogenous-weight
   correlation with indirectly inferred excess. Here: a delegation-constant switch-on, a
   measured fundamental benchmark per event, sign-separated hypotheses, and a
   fundamentals-anchored verdict. The prior literature cannot even state H2.
2. *"Your treated stocks were already in ETFs; the channel is saturated."* → That critique
   kills the speed-of-common-news design — agreed, and it is why this is not that design.
   It does not touch basket refraction, whose conduit is created by the event; saturation
   enters as a control (T5) and a signed dampening prediction (§7.4).
3. *"Betas are state-dependent and measured with error."* → They are estimated *in* the
   announcement regime with shrinkage; economy-wide announcement-day restructuring is
   absorbed by λ_a; the beta battery (§8.4) and portfolio-level replication bracket the
   residual; attenuation is conservative where it matters and the discipline/anchoring legs
   do not run through L̂.
4. *"Creation baskets are custom; transmission isn't pro-rata."* → Correct; unobserved
   sampling attenuates γ (conservative), measured inclusion is a signed heterogeneity test,
   and the anchor-wave ETFs' basket practice is documented from filings.
5. *"DFA one family dominates; few waves → fake stars."* → Same honest dual reporting as
   Chapter 1; effective-cluster count in the text; randomization inference in the main
   table; C exit pre-declared.
6. *"How is this not Chapter 1 again?"* → §11: different information type, geometry, theory,
   and identifying variation; the Fed precedent.
7. *"Isn't refraction just flow-induced trading?"* → Lead with the scaling argument, the
   cleanest separator from every pressure-mechanic confound: no flow story generates effects
   that scale with the *surprise* |S_a| and with the *lever* L — flows are not functions of
   the announcement's information content or of a stock's beta mismatch. FIT is additionally
   controlled directly, and the no-surprise-day placebo separates flow days from information
   days.
8. *"Non-reversal doesn't prove efficiency."* → Agreed — which is why the verdict is
   triangulated: reversal path to +60d, discipline, and fundamental anchoring must agree
   before either headline is claimed; partial patterns are reported as decompositions.
9. *"Your basket is ≈ the market; this is just beta compression toward 1 / generic beta
   mean-reversion."* → Three structural answers. (i) Economy-wide mean-reversion (true or
   estimation-stale) loads on the Post×(L·S) lower-order term in the specification; γ is
   the ConvExp gradient on top of it. (ii) The claim is decomposed: γ_tilt and γ_fac load
   only on the basket's departure from the market (β_b ≠ 1; non-market factor responses),
   which no market-direction story can generate — Gate 0 verifies the treatment carries
   enough tilted-basket mass to power them. (iii) If it doesn't, the framing gate binds
   ex ante and the paper claims only "wrapper-induced beta compression" — pre-committed and
   publicly timestamped, so the stronger language cannot be adopted after the fact.

## 13. Self-scores (house standard)

- **Academic feasibility 9/10.** Critical path is CRSP-daily plus public FOMC surprises;
  every identification asset is already built and validated by P1; the one license item
  (CPI/NFP consensus) is non-blocking for FOMC-only results; incremental cost ≈ one
  seat-week. Deduction: the race clock and the Gate-0 unknowns — which are now three,
  coupled, and honestly stated as such (joint shrinkage window; basket distinctiveness;
  power bar).
- **Agenda extension 8.5/10.** The dual-share-class wave replicates the design out of
  sample; the refraction frame extends to basket-peer earnings (bridging back to P1's peer
  spine), options listing, and bond-ETF baskets at CPI releases.
- **Identification rigor 8.5/10.** Delegation-constant treatment; within-announcement
  cross-sectional identification off three-way continuous variation; announcement-regime
  betas; the pre-trend triple; a triangulated verdict. Residual weaknesses, stated: wave
  concentration (shared with Chapter 1, same mitigations) and lever measurement error
  (bracketed by the §8.4 battery).

**All-in judgment: build to Gate-0-passed standby immediately. The two decisive new facts
this design needs from the world — lever-arm dispersion and per-stock beta estimability —
are answerable in weeks 1–2 from data P1 already holds. Promote to full execution the moment
the E2 verdict arrives, either way.**

---

## Appendix A — citation list

**Verified with working links (2026-07-12, single channel; channel-B sweep required per R2
before submission):**

- Sammon, "Passive Ownership and Price Informativeness," Management Science 71(6), 2025:
  https://pubsonline.informs.org/doi/10.1287/mnsc.2023.00836
- Glosten, Nallareddy, Zou, Management Science 67(1), 2021:
  https://pubsonline.informs.org/doi/10.1287/mnsc.2019.3427
- Ernst, "Stock-Specific Price Discovery From ETFs" (WP):
  https://terpconnect.umd.edu/~ternst/docs/Ernst_ETF.pdf
- Hasbrouck, "Intraday Price Formation in U.S. Equity Index Markets," JF 58(6), 2003:
  https://onlinelibrary.wiley.com/doi/abs/10.1046/j.1540-6261.2003.00609.x
- Savor, Wilson, "Asset Pricing: A Tale of Two Days," JFE 113(2), 2014:
  https://www.sciencedirect.com/science/article/abs/pii/S0304405X14000890
- Savor, Wilson, JFQA 48, 2013 (announcement premium) — cite from P1 pack.
- Lucca, Moench, "The Pre-FOMC Announcement Drift," NY Fed SR 512 / JF 2015:
  https://www.newyorkfed.org/research/staff_reports/sr512.html
- Ben-David, Franzoni, Moussawi, "Do ETFs Increase Volatility?" JF 73, 2018:
  https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12727
- Baltussen, van Bekkum, Da, JFE 132(1), 2019:
  https://www.sciencedirect.com/science/article/abs/pii/S0304405X18302034
- Bhattacharya, O'Hara, "Can ETFs Increase Market Fragility?" SSRN:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2740699
- "ETF Ownership and the Transmission of Monetary Policy," J. Financial Research, 2025:
  https://onlinelibrary.wiley.com/doi/10.1111/jfir.70015
- Jung, Shiller, "Samuelson's Dictum and the Stock Market," Economic Inquiry 43(2), 2005:
  https://onlinelibrary.wiley.com/doi/abs/10.1093/ei/cbi015
- Saglam, Tuzun, FEDS Note 2025-11-19:
  https://www.federalreserve.gov/econres/notes/feds-notes/implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-conversions-20251119.html
- SF Fed U.S. Monetary Policy Event-Study Database:
  https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/
- Hou, Moskowitz, RFS 18(3), 2005:
  https://academic.oup.com/rfs/article-abstract/18/3/981/1617714
- Da, Shive, "Exchange Traded Funds and Asset Return Correlations," EFM 24(1), 2018:
  https://onlinelibrary.wiley.com/doi/abs/10.1111/eufm.12137
- Greenwood, "Excess Comovement of Stock Returns," RFS 21(3), 2008 (Nikkei weights).

**Admitted pending verification `[VERIFY-CHANNEL-B]`** (surfaced via external review; DOIs
as supplied, links unverified by this document):

- Andersen, Thyrsgaard, Todorov, "Recalcitrant Betas," Quantitative Economics 12, 2021
  (doi:10.3982/qe1570); Bodilsen, Eriksen, Grønborg, JBF 2021
  (doi:10.1016/j.jbankfin.2021.106163); Brogaard, Heath, Huang, "ETF Sampling and Index
  Arbitrage," JFQA 2025 (doi:10.1017/s0022109025102378); Marta, Riva, "…Switch in ETF
  Replication Technique," SSRN 4079302; Greenwood, Thesmar, "Stock Price Fragility," JFE
  102, 2011; Dannhauser, Hoseinzade, RFS 2021; Todorov, Review of Finance 2023; Chen, Jiang,
  Financial Review 2024; Staer 2017; Liao, Coakley, Kellard, IRFA 2022; Barberis, Shleifer,
  Wurgler, "Comovement," JFE 75, 2005; Boyer, "Style-Related Comovement," JF 2011.

**Rejected as citation noise (do not cite; from machine-assembled review references):**
Prasad (2026); Sun (2025); Brière–Ramelli (irrelevant to this design); Cui et al. (2023);
the mangled "(2019) Arbitrage Comovement" entry.

Methods papers (Callaway–Sant'Anna; Sun–Abraham; Romano–Wolf; Vasicek; Lou 2012) — cite
from the P1 pack.

## Appendix B — pipeline reuse map (for ops/ when promoted to a task family)

| Need | Source | New work? |
|---|---|---|
| Conversion events / ConvExp / pre_etf_ownership | P1 T1/T2 frozen outputs | No |
| Macro calendar + surprises | New task M1 (dual-channel extraction per R2: USMPD + consensus) | Yes, cheap tier |
| Daily announcement panel + announcement-regime betas (incl. LOO basket beta, estimability diagnostics) | New task M2 (Claude Code) — CRSP only | Yes — the main new build, ~one seat-week |
| Fundamental-anchoring test | P1 T3 IBES machinery, re-targeted | Config only |
| Power simulation | P1 T2a, re-parameterized to (ConvExp, L, S) | Light |
| Estimation blueprints | P1 T5 spec + three-way-interaction amendment (frontier, dual-channel per R2) | Light |
| Pre-trend triple / placebo-in-time | M2 + P1 T5 event-study templates | Config only |
| Wedge plots | P1 T6 visual grammar, horizon in days | Config |
| Creation-basket files | New extraction task, cheap tier, dual-channel | Optional; `NEED_HUMAN` coverage first |
| TAQ intraday module (H1′/H5′) | Gated; only on pilot pass | Optional |
| Robustness grid / figures / writing / red team | P1 T7–T10 templates verbatim | Config only |

## Appendix C — revision history (one paragraph, for the record)

v0 (2026-07-12 morning) designed the macro half as "speed of common macro-news incorporation,
intraday"; killed on three structural grounds: the saturated arbitrage conduit (the design's
own placebo predicted a null main effect), the binding small-cap TAQ risk on the critical
path, and oversold power (announcement repetition counted as treatment variation). v1
relocated the estimand to the one object the conversion creates — the arbitrage-enforced
basket — yielding the refraction lever, sign-separated hypotheses, a daily-data critical
path, and honest inference. v1.1 adjudicated two external reviews: adopted
announcement-regime betas, the triangulated verdict (reversal to +60d + discipline +
fundamental anchoring, creating exit B′), creation-basket sampling as attenuation +
heterogeneity, the pre-trend triple with placebo-in-time, and a capped pre-registered
heterogeneity set; rejected moving intraday data onto the critical path (reinstates v0's
fatal flaw; kept as gated enhancement) and unbounded interaction fishing. v2.0 integrated
all of the above as the complete standalone plan. v2.1 adjudicated a second external
review and adopted all four of its substantive points: (1) the basket≈market threat —
answered with the lever decomposition (γ_mkt / γ_tilt / γ_fac), the b₄ lower-order term
absorbing generic beta mean-reversion, the Gate-0 basket-distinctiveness check, and an
ex-ante framing gate that downgrades claims to "wrapper-induced beta compression" if
distinctiveness fails; (2) the hidden coupling of the two Gate-0 pass lines through the
shrinkage knob — replaced with a joint shrinkage-intensity-sweep gate requiring a non-empty
simultaneous-feasibility window; (3) exit D downgraded from standing safe exit to
contingent on an archived, pre-outcome power bar; (4) the Gate-0 freeze converted into a
timestamped public pre-registration (OSF/AEA). Also adopted: leading FAQ 7 with the
|S_a|/L-scaling argument, a ≥40% hair-trigger ALERT for Marta–Riva with channel-B
verification moved ahead of positioning, and the dormant-task-family operational note.
Nothing in the second review was rejected.
