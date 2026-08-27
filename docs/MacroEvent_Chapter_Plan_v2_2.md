# Rewiring the Conduit: Wrapper Conversion and the Propagation of Monetary-Policy News
## Standby dissertation chapter — complete research plan (v2.2, 2026-08-19)
### (formerly "One Shock, Many Prices: ETF Baskets and the Refraction of Macroeconomic News")

> **Purpose.** Advisor-facing, self-contained plan. Chapters approved: P1 (fund conversions ×
> earnings information) and DAX. E2 is pending. This chapter is designed to top-field standard
> as a standby replacement should E2 not be approved, and as the natural fourth paper /
> job-market spare if it is. It descends from the advisor's original "Project 1 as two
> chapters" idea — micro events (earnings) and macro events — with the macro half rebuilt
> four times: to escape the mechanical lead-lag fact (v0→v1), to absorb the first external
> review (v1→v1.1), to absorb a second review that surfaced the basket≈market threat and the
> Gate-0 shrinkage coupling (v2.0→v2.1), and — in this version — to answer a collision review
> that found the "does the ETF wrapper speed macro information into prices" framing too close
> to published work. This document supersedes all prior versions and stands alone.
>
> **v2.2 in one line.** The estimand moves from *how much* macro news reaches a stock to *how
> the wrapper rewires the architecture through which it arrives* — and the network measure at
> the centre of that claim must now be validated against observable arbitrage activity before
> the paper is allowed to use it.
>
> **Two commitments this revision makes that v2.1 did not.** (i) Intraday ETF + constituent
> data move ONTO the critical path; §4.1 records that this reverses a decision v1.1 took
> deliberately, and what changes to make the reversal safe. (ii) L_tilt may not be called a
> network or arbitrage measure until §6.1's first stage says it is; that first stage is the
> chapter's highest-priority kill test.
>
> **Citation discipline (house rules R1/R2).** Core citations were verified with working
> links on 2026-07-12 (Appendix A); entries added from external review are flagged
> `[VERIFY-CHANNEL-B]` pending the second-channel sweep, which must run before advisor
> submission. **Every reference added in v2.2 is OWNER-SUPPLIED and carries
> `[OWNER-SUPPLIED · UNVERIFIED]`** — it was transcribed from the 2026-08-19 revision memo,
> not fetched, and REFR-R0's sweep still owes first-hand verification of every field and of
> each characterisation of findings. No number in this document comes from model memory;
> priors requiring data are marked `[VERIFY-IN-GATE-0]`.
>
> **Pre-registration status at revision time: NOTHING IS REGISTERED.**
> `frozen_config.yaml` carries `prereg.osf_timestamp: null` and `beta.w_shrink: null`, and no
> Gate-0 line has been measured. This revision is therefore a free redesign, not a
> pre-registration deviation. That stops being true at REFR-GATE-OSF.

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

Saglam–Tuzun validated the first stage; P1 claims the earnings-information cell. The
2026-08-19 collision review established that the macro cell as v2.1 framed it — *does ETF
structure speed macro news into constituent prices* — is now crowded: monetary transmission
through ETF ownership, institutional rebalancing as a transmission channel, and ETF-arbitrage
heterogeneity all have close recent work (Appendix A, v2.2 block). v2.2 therefore moves the
claim off *quantity of transmission* and onto *architecture of transmission*, where the
wrapper switch — not ownership levels — is the identifying asset.

Execution assumes the P1 race clock: working paper circulating within ~11 months of Gate 0
passing.

## 1. Research question and contributions

**One sentence.** When a mutual fund becomes an ETF — manager, strategy, holdings, and
delegation unchanged; only the trading, creation/redemption and arbitrage architecture
changes — does that wrapper switch **rewire how aggregate public information propagates
through the ETF–constituent system**, and is the rewiring governed by the fund's
pre-existing basket/holdings/arbitrage network?

**What is deliberately NOT claimed.** Not "ETFs make macro news arrive faster." Not that AP
arbitrage improves efficiency. Not that the ETF leads its constituents. Each of those is a
hypothesis this design tests and can reject; the third has published minute-level evidence
against it (Box–Davis–Evans–Lynch), which is exactly why direction of price discovery is an
outcome here rather than an assumption.

**Three contributions.**

1. **A rewiring experiment, not an ownership cross-section.** Existing work identifies from
   *variation in ETF ownership levels* across stocks, which is endogenous to the stock. Here
   the same portfolio, same manager and same delegation pass through a discrete change in
   trading architecture, and the object of study is the propagation structure itself —
   direction of price discovery, adjustment half-life, premium/discount convergence — before
   and after. Ownership designs cannot separate "who holds the stock" from "how the stock
   trades"; the wrapper switch does.
2. **Mechanism measured, not named.** The network lever L_tilt is not permitted to be called
   an arbitrage or network measure on the strength of its construction. §6.1 makes it earn
   the label against observable manifestations of the basket/arbitrage channel — and if it
   fails, §10's exit E redefines or retires it rather than building the paper on an
   unvalidated construct. This is the chapter's highest-priority kill test.
3. **Identified policy shocks, decomposed.** The shock is the unexpected component of policy
   (Bernanke–Kuttner), further separated from central-bank information effects
   (Jarociński–Karadi), with the modern caution about that separation carried explicitly
   (Bauer–Swanson). An announcement-day dummy is not used as the treatment, anywhere.

**Boundary vs. Chapter 1 (P1) — sharpened in v2.2.** The split is now by *information type*,
stated as a single line each:

> **P1 — firm-specific information:** how wrapper conversion changes incorporation of
> firm-specific fundamental news (earnings surprises).
>
> **Refraction — common information:** how wrapper conversion changes propagation of
> aggregate information through the ETF–constituent network (identified FOMC surprises).

Earnings and idiosyncratic news appear in this chapter only as **contrast tests** (§7 spine
5): if the wrapper rewires propagation of *common* information but not *firm-specific*
information, that asymmetry is itself evidence about the arbitrage-basket channel, since the
basket carries common exposure and not firm-specific news. Refraction does not become a
second earnings paper. Full anti-salami defense in §11.

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
| Conversion events, ConvExp, pre_etf_ownership | **Reuse P1** T1/T2 frozen outputs | Treatment; saturation control | None new |
| **Identified FOMC policy surprises, decomposed** | SF Fed USMPD (public) + the sign-restriction decomposition of §5.1 | **S^mp and S^cbi — the shock** | Decomposition is a modelling choice; §5.1 pre-registers it and §8 sweeps alternatives |
| **Intraday ETF + constituent quotes/trades** | TAQ (WRDS) **or** a validated vendor equivalent (Databento BBO/trades) | **Spines 1–3: lead-lag, information share, half-life, premium/discount convergence** | **ON THE CRITICAL PATH as of v2.2 — see §4.1.** Small-cap coverage is the binding risk |
| ETF mechanics: shares outstanding, creation/redemption, premium/discount | Issuer files / N-CEN / vendor | **§6.1 first stage** and H4 dose | Was "enhancement layer" in v2.1; now first-stage evidence |
| Creation-basket composition (daily) | Issuer files / ETF Global | **§6.1 first stage** — basket inclusion and weight | Was a non-blocking bypath; now load-bearing for the mechanism validation. `NEED_HUMAN: coverage` |
| Daily prices incl. **open** | CRSP | Spine 4 dynamics; all daily robustness; the fallback estimand of §4.1 | Standard |
| Announcement-regime betas (β_i, β_b^LOO) | Constructed pre-period; Vasicek shrinkage; characteristics-implied prior | Network lever L_tilt | Estimation noise → §6 battery; Gate-0 estimability |
| Earnings surprises / analyst revisions | IBES (P1 T3 pipeline re-targeted) | **Spine 5 contrast test**; anchoring diagnostics | None new |
| CPI/NFP consensus | Bloomberg ECO at BU or WRDS alternative | **Generalization only (§7.6), never the core** | `NEED_HUMAN`; FOMC-only is now the design, not a fallback |
| Controls | Compustat; CRSP MF flows; 13F/N-PORT; Russell constituents | P1 control set carried over | Standard |

### 4.1 Intraday moves onto the critical path — a reversal, recorded as one

v1.1 considered exactly this move and **rejected** it, on the grounds that it reinstated v0's
fatal flaw: a binding small-cap TAQ risk sitting on the critical path. v2.2 reverses that
decision. The reversal is defensible only because the *estimand changed with it*, and it
carries three conditions:

1. **Why the reversal is not a return to v0.** v0 asked whether macro news arrives *faster*
   under the wrapper — a question whose own placebo predicted a null, because the arbitrage
   conduit was already saturated. v2.2 asks whether the wrapper *rewires the direction and
   structure* of propagation. Direction and information share can change with no change in
   speed at all, so the saturation argument that killed v0 does not apply to the v2.2
   estimand.
2. **The TAQ risk is real and is now a blocking gate, not a bypath.** In v2.1 the intraday
   pilot's failure mode was "drop the enhancements, core unaffected." That escape no longer
   exists: if intraday coverage fails, the stock-level architecture claims cannot be made.
   The pilot therefore becomes **Gate-0 line G7** (§9) and its failure routes to §10 exit F,
   the daily/portfolio-level fallback estimand — a smaller paper, declared in advance, not a
   silent retreat.
3. **A vendor substitute is admissible, on one condition.** Databento (or equivalent)
   intraday BBO/trades may replace TAQ if and only if a **coverage-and-agreement validation**
   passes: on a sampled overlap, the vendor's quotes must reproduce the reference source's
   spread and lead-lag statistics within a pre-registered tolerance. Cheaper data is allowed;
   unvalidated data is not.

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

### 5.1 Macro shock construction (new in v2.2)

**No `MacroDay = 1` dummy appears anywhere in this design.** The treatment intensity is the
*unexpected* component of policy, and it is decomposed before use.

1. **Raw surprise.** High-frequency change in the policy-sensitive instrument in a tight
   window around the FOMC announcement, taken from USMPD's registered field (R1a fixes which
   field, quoting the official definition; the choice is registered before estimation).
2. **Decomposition into two shocks.** Following the sign-restriction logic of
   Jarociński–Karadi `[OWNER-SUPPLIED · UNVERIFIED]`, the announcement-window co-movement of
   the policy instrument and the equity index separates
   - **S^mp** — a pure monetary-policy shock (rates and equities move oppositely), and
   - **S^cbi** — a central-bank information shock (they move together).
3. **The modern caveat, carried explicitly.** Bauer–Swanson `[OWNER-SUPPLIED · UNVERIFIED]`
   argue the "Fed information effect" admits an alternative explanation, so the S^cbi leg is
   reported as a *decomposition*, never as a structural claim about central-bank private
   information. Where the two readings imply different interpretations, both are stated.
4. **Which shock is primary.** **S^mp is the registered primary.** S^cbi enters as a
   companion series with its own coefficient, because the architecture question — does the
   wrapper rewire propagation — should not depend on which flavour of news is propagating.
   A finding that rewiring appears for one shock and not the other is a result, and §7 spine 3
   reports it as one.
5. **Scope discipline.** CPI and NFP surprises are **generalization exercises (§7.6)**, run
   only after the FOMC design works end to end. v2.2 explicitly rejects an
   "all macro announcements" panel as the core: an unfocused shock set was one of the
   crowding problems the collision review identified.

## 6. Identification

**Main specification (SPEC-MAIN-v2.2).** For stock i, FOMC event a, wave e, at intraday or
daily horizon h:

Y_{i,a,h} = b₁·(β_i S_a) + b₂·(Post × ConvExp)·(β_i S_a)
          + b₃·Post·(β_i S_a) + b₄·Post·(NetExp_i S_a)
          + **γ·(Post_{e,a} × ConvExp_{i,e}) × (NetExp_i × S_a)**
          + λ_a + δ_{ind×a} + α_i + θ'X_{i,t(a)} + ε_{i,a,h}

where **Y is a propagation outcome (§7), not a raw return**, and **NetExp_i is the validated
network exposure of §6.1** — L_tilt only if the first stage licenses it.

Three things carry over from v2.1 unchanged because they survived review: λ_a absorbs the
common shock entirely; δ_{ind×a} kills industry macro loadings; and the lower-order Post terms
b₃/b₄ are load-bearing rather than boilerplate — b₄ absorbs economy-wide beta mean-reversion,
so γ is identified only off the ConvExp gradient on top of it. Identification remains purely
cross-sectional within announcement, now off the three-way ConvExp × NetExp × S interaction.

### 6.1 The first stage: NetExp must be measured, not named (new in v2.2, highest priority)

v2.1 used L_tilt = β_b^LOO − β_i as the mechanism variable on the strength of its
construction. v2.2 forbids that. Before L_tilt may be described as arbitrage exposure,
network leverage, or basket exposure anywhere in the paper, it must predict **observable
manifestations of the arbitrage/basket channel**, measured pre-conversion:

| First-stage outcome | Source | Prediction if L_tilt is a network measure |
|---|---|---|
| Creation/redemption-linked activity | ETF mechanics / issuer files | higher \|L_tilt\| → stronger loading on creation-redemption flow |
| Basket inclusion / basket weight | Creation-basket files | higher \|L_tilt\| → systematic relation to inclusion and weight |
| Premium/discount convergence speed | Intraday ETF quotes + NAV | higher \|L_tilt\| → faster arbitrage closure |
| ETF–stock lead-lag strength | Intraday | higher \|L_tilt\| → stronger cross-dependence, direction not signed ex ante |
| Constituent order imbalance around ETF flows | Intraday | higher \|L_tilt\| → larger imbalance response |

**Decision rule, registered before estimation.**

- **Licensed.** If L_tilt predicts a pre-registered majority of these first-stage outcomes
  with the sign the arbitrage-basket channel implies, it is used as NetExp and may be named a
  network measure in the paper.
- **Redefined.** If it fails, NetExp is **rebuilt directly from the observables that did
  work** — basket weight and creation-basket inclusion are the natural candidates — and the
  paper says plainly that the theory-implied lever did not survive validation. The chapter
  continues with a measured network variable.
- **Retired.** If no candidate network measure predicts any arbitrage observable, the network
  claim is dropped entirely: §10 exit E.

**This first stage runs on PRE-CONVERSION data only**, so it is a Gate-0-legal diagnostic and
carries no lookahead: it asks whether the measure is a network measure in the world as it was
before the wrapper changed.

## 7. Outcome spines (v2.2: propagation first, returns second)

**Spine 1 — Direction of price discovery (H1, headline).** Does the wrapper switch change
*which side leads*? Measures: ETF→constituent vs constituent→ETF lead-lag at the
announcement window; information-share / component-share decompositions where the
econometrics are appropriate (cointegrated price system, stated assumptions, reported
sensitivity to sampling interval). **Sign is not assumed.** Box–Davis–Evans–Lynch
`[OWNER-SUPPLIED · UNVERIFIED]` report minute-level evidence that ETF trading does *not*
generally lead the underlying and that constituent order imbalances often move first. H1 is
therefore two-sided: the wrapper may shift discovery toward the ETF, toward the constituents,
or not at all, and each is a reportable finding.

**Spine 2 — Speed and completeness of adjustment (H2).** Adjustment half-life to the
identified shock; the share of the eventual response completed at fixed intraday horizons;
premium/discount convergence. Again unsigned: Brogaard–Heath–Huang `[OWNER-SUPPLIED ·
UNVERIFIED]` give grounds to expect arbitrage to *worsen* efficiency for some names, so
"faster" is a hypothesis, not the maintained assumption.

**Spine 3 — Network governance (H3, the mechanism spine).** Does the validated NetExp of
§6.1 govern the rewiring — i.e. is γ concentrated where the pre-existing basket/arbitrage
network is strongest? Reported separately for S^mp and S^cbi. This is the spine that makes
the paper about architecture rather than about ETFs in general.

**Spine 4 — Wedge fingerprint (H4, DEMOTED to dynamic diagnostic).** The +60d cumulative
wedge and the reversal portfolio are retained, and their construction is unchanged, but they
are no longer headline identification. Two claims v2.1 made are **withdrawn**:

- **"Reversal = mispricing" is withdrawn.** Long-horizon reversal is consistent with
  temporary price pressure, time-varying risk, factor exposure, index rebalancing, liquidity
  provision and its recovery, and mispricing. The paper enumerates these and, where possible,
  discriminates (e.g. reversal conditional on flow, on rebalancing dates, on liquidity
  recovery), and where it cannot, it says so.
- **"Factor decomposition separates macro from micro pricing error" is withdrawn.** A
  systematic return component is not automatically mispricing and a residual is not
  automatically idiosyncratic mispricing. The decomposition is reported as a variance
  decomposition, with no error interpretation attached.

**Spine 5 — Firm-specific contrast (new).** The same architecture outcomes around *earnings*
announcements. If the wrapper rewires propagation of common information but not firm-specific
information, the asymmetry is evidence for the basket channel, since the basket carries
common exposure and not firm-specific news. This is the boundary with P1 made empirical
rather than rhetorical — and it is a contrast test, never a second earnings paper.

### 7.6 Generalization (after the FOMC design works, not before)

CPI and NFP surprises; the dual-share-class wave as out-of-sample replication. Neither is
allowed to enter before spines 1–3 are complete on FOMC.

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

## 9. Gate 0 — kill-switch (all core lines must pass before full commitment)

| Week | Task | Pass line |
|---|---|---|
| 1 | Macro calendar + **identified, decomposed** FOMC surprises (§5.1); CPI/NFP consensus is generalization-only | ≥95% of scheduled FOMC events with a usable S^mp; the S^mp/S^cbi decomposition executes on the full sample |
| 1–2 | **Joint lever/estimability check via shrinkage-intensity sweep** (unchanged from v2.1; the two lines are coupled through one knob) | A non-empty, non-knife-edge window of weights in which SD(L̂) ≥ 0.25 `[VERIFY-IN-GATE-0]`, \|corr(L, ConvExp)\| ≤ 0.3, median pre-period announcements ≥ 30, and SE(β̂_i) ≪ SD(L̂) for ≥70% of treated names |
| 2 | **Basket-distinctiveness check** (unchanged) | Sufficient treatment mass with D_b ≥ 0.1 `[VERIFY-IN-GATE-0]`; else the §10 framing gate binds ex ante |
| 2–3 | Power simulation on the joint (ConvExp, NetExp, S) distribution, wave-clustered, separately for γ pooled, γ_tilt and γ_fac | MDE(γ) ≤ 0.5σ at baseline priors; the exit-D power bar computed and archived before any outcome is seen |
| 3–4 | Pre-trend triple | All three flat/zero: joint p ≥ 0.10 and no Holm-adjusted individual lead |
| **2–3** | **G7 — INTRADAY COVERAGE (new in v2.2, now BLOCKING).** Pilot: 30 treated + 30 control × 20 announcement days, incl. small caps. If a vendor substitutes for TAQ, its coverage-and-agreement validation (§4.1 condition 3) runs here | **≥70% usable coverage including small caps.** FAIL → the stock-level architecture claims cannot be made; route to §10 **exit F**, the daily/portfolio fallback. This line was a non-blocking bypath in v2.1 |
| **2–3** | **G8 — FIRST-STAGE MECHANISM VALIDATION (new in v2.2, HIGHEST PRIORITY).** §6.1 run on pre-conversion data | L_tilt predicts a pre-registered majority of the arbitrage observables with the implied sign → **licensed**. Partial → **redefine** NetExp from what did work. None → §10 **exit E** |

Any core-line failure → exit matrix, no forcing. **G8 is the line to run first**: it is
cheap, it uses pre-period data only, and a failure changes what the paper is about rather
than merely narrowing it.

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

- **E (mechanism not validated — new in v2.2):** G8 finds no candidate network measure that
  predicts any arbitrage observable. The network claim is dropped. What remains is an honest
  and still-publishable market-structure result — *the wrapper changes propagation, and we
  can say by how much but not through which network* — reported at the fallback tier, with
  the failed validation shown rather than buried. This is a positive contribution to a
  literature that names mechanisms more often than it measures them.
- **F (intraday coverage fails — new in v2.2):** G7 fails. Stock-level architecture claims
  are withdrawn; the chapter falls back to the daily/portfolio-level estimand of v2.1, whose
  machinery is already built. Declared in advance so the retreat is a pre-committed exit, not
  a silent change of question. Fallback tier.

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

## Appendix A2 — v2.2 additions and the literature-differentiation matrix

**Every entry below is `[OWNER-SUPPLIED · UNVERIFIED]`**: transcribed from the 2026-08-19
revision memo, not fetched. REFR-R0 must verify each field and each characterisation of
findings first-hand before any of it reaches a draft. Where a paper already appeared in
Appendix A (Ben-David–Franzoni–Moussawi; Brogaard–Heath–Huang; the JFR 2025 monetary
transmission paper, identified here as Rhodes–Hill-Kleespie), the v2.2 entry supersedes it
and inherits the same verification debt.

| # | Reference (owner-supplied) | Why it binds this design | How Refraction differs |
|---|---|---|---|
| 1 | Rhodes & Hill-Kleespie (2025), *ETF Ownership and the Transmission of Monetary Policy*, JFR, 10.1111/jfir.70015 | Nearest neighbour: orthogonalized policy surprises across 101 FOMC meetings; ETF ownership affects transmission; reports ETF→underlying transmission after expansionary surprises | They identify from ETF **ownership levels**, endogenous to the stock. We identify from a **wrapper switch** holding portfolio, manager and delegation fixed, and our outcome is the **direction and structure of discovery**, not the size of the response. Their result is a maintained hypothesis we test |
| 2 | Lu & Wu (2026), *Monetary Transmission and Portfolio Rebalancing*, JFE 183:104324 | Institutional rebalancing across asset classes transmits FOMC shocks to individual stocks; mechanism tests use dual shares and rebalancing timing | Makes any `MacroShock × InstitutionalHoldings` result insufficiently new — which is precisely why v2.2's estimand is architecture, not holdings intensity. Our treatment is not "more institutional ownership"; it is a change in the trading technology of the same owner |
| 3 | Brogaard, Heath & Huang (2026), *ETF Sampling and Index Arbitrage*, JFQA 61(2):547-579 | Basket sampling makes arbitrage effects heterogeneous; ETF trading can *reduce* liquidity and price efficiency and raise volatility/co-movement for liquid names | Forbids assuming AP arbitrage improves efficiency. Adopted directly: spines 1-2 are unsigned, and sampling heterogeneity enters §6.1 as a first-stage observable rather than as unmodelled attenuation |
| 4 | Box, Davis, Evans & Lynch (2021), *Intraday Arbitrage between ETFs and Their Underlying Portfolios*, JFE 141(3):1078-1095 | Minute-level: little support for ETF trading leading underlying returns; underlying imbalances/prices often move first and ETF quotes then close the gap | The single reason spine 1 exists as a **test** rather than an assumption. "ETF first, stocks second" is a null we can reject in either direction |
| 5 | Brown, Davies & Ringgenberg (2021), *ETF Arbitrage, Non-Fundamental Demand, and Return Predictability*, RoF 25(4):937-972 | Interpretation of creation/redemption, flows, relative mispricing; distinguishes closing a law-of-one-price gap from correcting fundamental mispricing | Disciplines §7 spine 4's withdrawn claims: convergence of a premium is not evidence of fundamental correction, and the wedge language now respects that distinction |
| 6 | Ben-David, Franzoni & Moussawi (2018), *Do ETFs Increase Volatility?*, JF 73(6):2471-2535 | Foundational: non-fundamental shocks propagate through arbitrage into underlying volatility | The channel whose *rewiring* we test. They show the conduit exists; we ask whether switching the wrapper on changes its architecture |
| 7 | Bernanke & Kuttner (2005), *What Explains the Stock Market's Reaction to Federal Reserve Policy?*, JF 60(3):1221-1257 | The shock must be the unexpected component of policy | Binding constraint on §5.1: no announcement-day dummy, anywhere |
| 8 | Jarocinski & Karadi (2020), *Deconstructing Monetary Policy Surprises*, AEJ:Macro 12(2):1-43 | Separates policy shocks from central-bank information shocks | Implemented as §5.1's S^mp / S^cbi decomposition |
| 9 | Bauer & Swanson (2023), *An Alternative Explanation for the "Fed Information Effect"*, AER 113(3):664-700 | Modern warning about interpreting the information channel | Carried as an explicit caveat: S^cbi is reported as a decomposition, never as a structural claim |
| 10 | Haddad, Huebner & Loualiche (2025), *How Competitive Is the Stock Market?*, AER 115(3):975-1018 | Benchmark for the economic importance of passive demand and incomplete offset | Supplies the economic-magnitude yardstick for §11's "so what": how large a rewiring must be to matter |

### Why this is not Rhodes-Hill-Kleespie + Lu-Wu + the ETF-arbitrage literature

Three separations, each testable rather than rhetorical.

1. **Identification.** Both neighbours identify from *who owns the stock* — ETF ownership
   share, institutional holdings — which investors choose partly in response to the stock's
   own characteristics. This design identifies from a change in *how the same shares trade*,
   with the holder, portfolio, manager and delegation contract held fixed. That is the one
   variation neither neighbour has.
2. **Estimand.** Both estimate the *magnitude* of transmission. This chapter estimates its
   *structure*: which side leads, how fast the gap closes, how the premium converges. A
   design can find a larger response with unchanged architecture, or an unchanged response
   magnitude with reversed direction of discovery — and those are different economics.
3. **Mechanism standard.** The ETF-arbitrage literature typically names the arbitrage channel
   and infers it from outcomes. §6.1 requires the network variable to predict observable
   arbitrage activity *before* it is used, and §10 exit E makes failure publishable rather
   than concealed. If the neighbours' mechanism claims are right, our first stage should
   confirm them; if it fails, that is informative about the literature, not only about us.

**Where the design remains vulnerable, stated plainly.** If G8 licenses NetExp but spine 1
finds no change in the direction of discovery and spine 2 none in speed, the paper reduces to
"wrapper conversion does not rewire propagation" — an exit-D-style precise null, claimable
only if the archived power bar supports it. That is the honest downside, and it is why G8
runs first.

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

v2.2 (2026-08-19) answered a collision review that judged the v2.1 framing too close to
published work on ETF ownership and monetary transmission, institutional rebalancing, and
ETF-arbitrage heterogeneity. It moved the estimand from the quantity of macro transmission to
the **architecture** of it; replaced the announcement-day treatment with **identified,
decomposed FOMC surprises** (S^mp / S^cbi); made **price-discovery direction, adjustment
speed and premium/discount convergence** the primary outcomes; **demoted the wedge
fingerprint** to dynamic diagnostic and withdrew its two interpretive claims
(reversal = mispricing; factor decomposition = macro/micro pricing error); required the
network lever to **earn its mechanism interpretation** through a pre-conversion first stage
(new Gate-0 line G8, the highest-priority kill test, with exit E on failure); and — reversing
v1.1 deliberately — moved **intraday data onto the critical path**, converting the TAQ pilot
into blocking Gate-0 line G7 with exit F as the pre-declared fallback. Ten owner-supplied
references were incorporated, all flagged `[OWNER-SUPPLIED · UNVERIFIED]` pending REFR-R0's
first-hand sweep. Nothing was pre-registered at the time of this revision, so it is a
redesign and not a deviation.
