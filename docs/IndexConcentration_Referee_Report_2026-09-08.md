# Independent referee report

## "Index Concentration and the Architecture of Price Discovery"

**Reviewed documents:** the original research-agent assignment and the completed research plan, both as reproduced verbatim in the referee package dated 8 September 2026.
**Review date:** 8 September 2026.
**Reviewer posture:** independent, adversarial, non-deferential. The plan's own contribution matrix, its disclosed gap register, and its source crosswalk were treated as claims to be audited, not as an answer key. Where the register is right, I say so; where it mislabels the severity or the remedy, I say that too.

---

## 0. Evidence basis and access limitations (read this before Section 2)

This must be stated plainly, because it bounds every literature claim below.

**Direct retrieval of primary sources was unavailable in this session.** Outbound web access is restricted by an egress policy that refused connections to every publisher, repository, regulator and exchange domain I attempted, including `academic.oup.com`, `onlinelibrary.wiley.com`, `papers.ssrn.com`, `www.nber.org`, `www.sciencedirect.com`, `pubsonline.informs.org`, `www.aeaweb.org`, `link.springer.com`, `doi.org`, `www.federalreserve.gov`, `www.frbsf.org`, `www.nyse.com`, `www.cmegroup.com`, `www.spglobal.com`, `indexes.nasdaqomx.com`, `ir.nasdaq.com`, `terpconnect.umd.edu` and `archive.nyu.edu`. Each returned a policy denial at the CONNECT stage.

Consequently:

- **No full paper was inspected in this review. No abstract page was inspected either.** My verification channel was a web search index that returns titles, URLs, and machine-generated summaries of page content.
- Every literature statement below is therefore labelled **[SEARCH-INDEX]**. That is a weaker basis than the package's own "full paper" and "abstract/metadata" labels, and I do not adopt the package's access labels as my own.
- Where the search index returned specific numbers or findings, I report them as what the index returned, not as facts I confirmed at the source.
- **"Not found in this search" is not "does not exist."** My novelty sweep is weaker than it should be and cannot support a strong originality finding in either direction.

Two further consequences the authors should note:

1. My literature findings below are **sufficient to establish problems** (a citation error found through a search index is still a citation error) but **not sufficient to clear the novelty boundary**. Nothing in this report should be read as certifying that the proposed contribution is new.
2. The package's SHA-256 integrity claims are **not verifiable by any recipient of the package alone**. A hash of a file is only useful to someone who holds that file. Transmitting hashes of documents that are supplied only as inline reproductions inside the same document provides no integrity guarantee. This is a process defect in the package, not in the plan; it should be fixed by shipping the two source files alongside the package.

Everything in Sections 3–10 that does *not* depend on external literature — the internal mathematics, the estimand's invariance properties, the horizon/support tension, the multiplicity structure, the training-sample logic — was derived from the plan's own text and equations and does not depend on the access limitation.

---

## 1. Executive verdict

**REDESIGN.**

The question is real, the writing is disciplined, and the measurement apparatus — exact fixed-quantity decomposition, alternative-weight replay on identical price paths, leave-signal-out forecasting targets, matched non-giant signals, and a full-pipeline frozen-network null — is better than most published work in this area. But the plan's headline design fails on a structural tension it never names: **the measurement horizon at which "architecture" is economically meaningful and the sample length required to obtain concentration variation are in direct conflict, and no gate in the plan can resolve that conflict because it is not a data-quality problem.** Search-index summaries of Chordia, Green and Kottimukkalur (RFS 2018) report that SPY and ES respond to macro announcement surprises **within five milliseconds** [SEARCH-INDEX]; the plan's primary outcome is a five-*second*-ahead forecast, three orders of magnitude coarser, so it is measuring residual constituents' quote-refresh catch-up rather than the allocation of price discovery. Meanwhile the identifying variation — issuer HHI across roughly one hundred FOMC statements over thirteen years — is a near-monotone function of calendar time, collinear with at least five documented regime changes inside the confirmatory window, and the plan's *preferred* remedy (calendar-year fixed effects) makes the endogeneity worse, not better: within-year residual HHI is, by construction, the recent relative return of the top-ten issuers. On top of that, the primary architecture statistic is not invariant to the one thing that most plausibly changed — the giant basket's precision as an estimator of the common shock — and the plan's own formal model, taken together with its own §7.1 derivation, generates the H2 signature under a pure arithmetic null. The strongest prospective contribution is not the historical HHI gradient at all; it is the within-stock, across-basket design the plan dismisses as unavailable, and which the rule-based index-capping mechanisms of the Select Sector and Nasdaq-100 families in fact supply repeatedly. The greatest unresolved vulnerability is that the paper as specified cannot distinguish a change in information transmission from a change in how well the giants' prices measure the news.

---

## 2. Independent contribution assessment

### 2.1 The best defensible contribution, in one statement

> Using rule-assigned, formula-triggered reallocations of index weight that change a stock's arithmetic role in one traded basket while leaving its weight in another basket, its fundamentals, and its own quote process unchanged, show whether that stock's incremental predictive content for the *leave-itself-out* remainder of the reweighted basket moves with its assigned weight — and whether the reweighted basket's own pricing quality moves with it.

This is not the plan's headline. The plan's headline is a conditional historical gradient in issuer HHI. That version's best defensible statement is materially weaker and should be written down as such:

> Over 2013–2025, conditional on a small predetermined state vector and net of matched non-announcement windows, the incremental out-of-sample forecasting content of a weight-invariant giant-issuer factor score for a leave-signal-out constituent basket, relative to an equally complex matched non-giant score, **co-moved with** issuer concentration — a descriptive time-series association that cannot be separated from contemporaneous changes in the giants' signal precision, in the FOMC announcement package, or in market-data measurement regimes.

That second statement is honest and is roughly what the plan says it will deliver. My judgement is that it is not enough to carry a paper at the tier the plan is aiming for, and that the machinery deserves a better identifying variation.

### 2.2 Closest-literature table

Access basis for **every** row: **[SEARCH-INDEX]** — web search index summaries only; no publisher page, repository page, or PDF was retrievable (see Section 0). Links are recorded as located, not as inspected.

| Closest work (status as returned) | Independently returned result | Overlap with the proposal | Exact remaining increment | Collapse risk | Located at |
|---|---|---|---|---|---|
| **Hasbrouck (2003)**, *JF* 58, 2375–2400 | Index searches report: for the S&P 500 and Nasdaq-100, **most price discovery occurs in the E-mini**; E-mini leads regular futures and ETFs; for S&P 400 MidCap it is shared; **the S&P 500 ETF contributes markedly to price discovery in the sector ETFs with only minor reverse effects** | Very high on the system definition; and the sector-ETF result means Hasbrouck already studied index-instrument-versus-component-portfolio direction and found index→component dominance | Time variation in the direction, conditioned on issuer concentration, with a mechanical-weight null | **High.** If the result is "the E-mini still leads and giants matter more now," this is Hasbrouck plus a newer sample | onlinelibrary.wiley.com/doi/abs/10.1046/j.1540-6261.2003.00609.x |
| **Chan (1992)**, *RFS* 5, 123–152 | Futures lead component stocks; the lead is stronger when stocks move together, consistent with market-wide information | Very high on the economics: cross-stock lead–lag driven by common information is the object | A concentration gradient in that lead, plus a residual target that excludes the signal group | **High.** "Giants lead the rest on macro news" is close to Chan's stronger-when-common-information result | academic.oup.com/rfs/article-abstract/5/1/123/1599654 |
| **Stoll and Whaley (1990)**, *JFQA* 25(4), 441–468 — **omitted from the plan** | Index futures lead cash by ~5 minutes, occasionally 10+, **even after purging stock index returns of infrequent-trading effects** | Direct: this is the canonical statement that measured cash-side lags survive naive staleness corrections and the canonical warning that they may not survive better ones | Nothing, unless the plan's staleness treatment is demonstrably stronger | **Moderate.** Not a collapse risk for the contribution, but its absence weakens the plan's claim to have confronted nonsynchronous trading | cambridge.org/core (JFQA archive) |
| **Greenwood (2008)**, *RFS* 21(3), 1153– — **omitted from the plan** | Uses **cross-sectional variation in Nikkei 225 index weights** and the April 2000 redefinition; index betas of additions rose ~+0.45 and of deletions fell ~−0.63 over 300 days; strong positive relation between index overweighting and comovement with other index members, negative with non-members; excess comovement predictably reverts | **Severe.** This is the existing "index weight, not fundamentals, drives cross-stock return relationships" paper, with a genuine reweighting experiment | Intraday/common-news timing, a directional predictive estimand rather than contemporaneous comovement, and a system-quality outcome | **High.** A referee who knows this paper will ask why a higher-frequency, weaker-identified version of it is a new contribution | academic.oup.com/rfs/article-abstract/21/3/1153/1563300 |
| **Baltussen, van Bekkum and Da (2019)**, *JFE* 132(1), 26–48 — **omitted from the plan** | Index return **serial dependence** switched from positive to negative since the 2000s across 20 indexes in 15 countries; the change is linked to the rising popularity of index products | **Severe.** This is "index products changed the time-series structure of index returns," i.e. a change in the architecture of information incorporation attributed to indexation | Weights and concentration rather than index-product popularity; constituent-level and event-time rather than daily index-level | **High.** The plan's H2/H3 could be read as a concentration-flavoured restatement | sciencedirect.com/science/article/abs/pii/S0304405X18302034 |
| **Chordia, Green and Kottimukkalur (2018)**, *RFS* 31(12), 4650–4687 | **SPY and ES respond to macro announcement surprises within five milliseconds**; trading intensity rises >100-fold; profits ≈ $50,000 per event; **speed of information incorporation has increased in recent years**; order flow has become less informative | High, and worse than the plan admits: it fixes the timescale at which index instruments finish, and documents a *secular speed trend* collinear with concentration | Cross-security completion beyond the index pair | **Not a novelty collapse but a design collapse.** It implies the plan's 5-second primary outcome is not about who incorporates news first | academic.oup.com/rfs/article-abstract/31/12/4650/4956248 |
| **Box, Davis, Evans and Lynch (2021)**, *JFE* 141(3), 1078–1095 | Arbitrage opportunities are **initiated by shocks to the underlying and corrected through ETF quote updates**; little evidence that arbitrage opportunities precede trading in the underlying; correction via market-maker quote adjustment rather than arbitrage trades | High. "Cash-side shocks propagate into ETF quotes" is the plan's direction of interest, already established at minute frequency | Five-second resolution, a concentration gradient, and a target excluding the signal names | **High.** If the giant→index result dominates and the giant→residual result is weak, this is Box et al. at a faster clock | sciencedirect.com/science/article/abs/pii/S0304405X21001537 |
| **Ernst**, *Stock-Specific Price Discovery From ETFs*, working paper | Investors with stock-specific information trade **both** the stock and the ETF simultaneously and in the same direction; relationships stronger for larger ETF weights; SPDR and Sector SPDR data. **Status: the search index surfaces a "Revise and Resubmit at the *Review of Financial Studies*" line from an author CV, alongside 2020 and March-2022 draft versions** | High on the weight-dependence of stock–ETF information linkage — the plan's core intuition | Common public news rather than stock-specific information; concentration as treatment; residual-basket direction | **High.** "High-weight stocks and ETFs move together informatively" is Ernst | terpconnect.umd.edu/~ternst/ (blocked); versions mirrored elsewhere |
| **Fang and Sanger**, *Index Price Discovery in the Cash Market* | Search index confirms a **Midwest Finance Association 2012 meeting paper**, SSRN-posted 2011; **no journal publication located**. I could not retrieve the abstract, so I can neither confirm nor deny the plan's characterisation of its results (a reconstructed second-by-second cash index, ETF contributing ~half, cash contribution rising with ETF private information) | If the plan's characterisation is right, overlap is severe on "reconstruct the cash basket and measure its price-discovery share" | Time variation with concentration; leave-giants-out targets; mechanical null | **High**, conditional on the plan's own summary being accurate — which I could not check | papers.ssrn.com/sol3/papers.cfm?abstract_id=1926287 |
| **Glosten, Nallareddy and Zou (2021)**, *Management Science* 67(1), 22–47 | ETF **activity** raises informational efficiency of underlying securities **for stocks with weak information environments and imperfectly competitive markets**, via **timely incorporation of systematic earnings information**; the effect is attributable to systematic, not idiosyncratic, information | Moderate–high: "index vehicles speed systematic-information incorporation into constituents" is the plan's H2 in slower clothing | High-frequency common-news timing; concentration rather than ETF activity | **Moderate.** The plan correctly separates activity from weights; the risk is that a concentration proxy is really an activity proxy | pubsonline.informs.org/doi/10.1287/mnsc.2019.3427 |
| **Jiang, Vayanos and Zheng (2025)**, *RFS* 38(12), 3461–3496 | Passive flows **disproportionately raise prices of the largest firms**, especially those in high noise-trader demand; **flows increase the idiosyncratic risk of large firms**, which discourages correction; prices and idiosyncratic volatilities of the largest S&P 500 firms rise most following flows | High on the mega-firm object, and it supplies a **competing prediction the plan does not consider**: rising giant idiosyncratic volatility should make the giant basket a *noisier*, not cleaner, signal of common news | Intraday assimilation of public news rather than valuation levels | **Moderate** as a collapse risk; **high** as a source of an untested rival mechanism | academic.oup.com/rfs/article/38/12/3461/8280528 |
| **Cong, Huang and Xu**, NBER w32016 (Jan 2024) | Composite securities let investors trade common factors; **composite-security trading impounds more systematic information into prices**, producing greater informational efficiency, price variability and comovement, with **heterogeneous effects on asset-specific information depending on factor importance**. Author research page reports **JF R&R, second round** | High on the theory: this *is* a model in which index-vehicle design changes systematic-information processing | Comparative statics in the concentration of an existing index and event-time discrimination | **High** on the mechanism side. The plan's q(C) story is a special case of the composite-security channel | nber.org/papers/w32016; papers.ssrn.com/sol3/papers.cfm?abstract_id=4687021 |
| **Farboodi, Matray, Veldkamp and Venkateswaran (2022)**, *RFS* 35(7), 3101–3138 | **Data divergence**: large growth stock prices increasingly reflect information about future earnings while small and value firms' informativeness was flat or declining; structural model attributes it to big firms getting bigger | Moderate; supplies the long-horizon version of "information concentrated on the giants" | Intraday public-news processing rather than long-horizon informativeness | **Moderate.** The plan may be documenting the intraday shadow of a known secular reallocation | academic.oup.com/rfs/article-abstract/35/7/3101/6373388 |
| **Sammon (2025)**, *Management Science* 71(6), 4582–4598 — **omitted from the plan** | Passive ownership **reduces** the information incorporated into prices ahead of earnings announcements; the 30-year rise in passive ownership caused a decline of about one-quarter of the whole-sample mean | Moderate. It is the leading "indexation degrades price discovery" result and sits in direct tension with the plan's H2/H3 | Common public news and concentration rather than ownership and firm news | **Low** as collapse risk, **high** as an omission: a referee will ask why the paper's mechanism runs opposite to Sammon's | pubsonline.informs.org/doi/10.1287/mnsc.2023.00836 |
| **Coles, Heath and Ringgenberg (2022)**, *JFE* 145(3), 665–683 — **omitted from the plan** | Post-banding Russell RD: switching into the Russell 2000 raises passive ownership ~2% of market cap and lowers active by a similar amount; **information production falls (Google searches, EDGAR views, analyst reports) while price informativeness is unchanged**; indexing adds noise without changing long-run efficiency | High relevance to the plan's §15 "precisely estimated stability" fallback, and to the standard of proof for index-related identification | The plan needs to explain why an architecture change would be visible where informativeness changes were not | **Moderate.** Also the reference standard for what a credible index-identification design looks like | sciencedirect.com/science/article/abs/pii/S0304405X22001143 |
| **Chang, Hong and Liskovich (2015)**, *RFS* 28(1), 212–246 — **omitted from the plan** | Russell 1000/2000 RD; additions to the Russell 2000 raise prices, deletions lower them, ~5% magnitude | Method relevance: it is the canonical index-rule RD the plan's §8.4 gestures at without citing | — | **Low** collapse risk; a citation gap | academic.oup.com/rfs/article-abstract/28/1/212/1680962 |

Rows for Wallace–Kalev–Lian, Dimpfl–Schweikert, Brennan–Jegadeesh–Swaminathan, Bhojraj–Mohanram–Zhang, Huang–O'Hara–Zhong, Ben-David–Franzoni–Moussawi, Israeli–Lee–Sridharan, Khomyn–Putniņš–Zoican, Haddad–Huebner–Loualiche, Subrahmanyam and Gorton–Pennacchi were **not independently re-verified in this session**. I decline to restate the package's summaries of them as though I had checked them. The authors should treat those rows as still carrying only the package's own evidence.

### 2.3 Citation, status and attribution errors found

Three are substantive and one is structural.

1. **Jiang, Vayanos and Zheng — author names are wrong in the plan's reference list.** The plan writes "Jiang, Zhengyang, Dimitri Vayanos, and Zheyu Zheng." The search index consistently returns the authors as **Hao Jiang, Dimitri Vayanos and Lu Zheng** (RFS 38(12), 3461–3496; NBER w28253; SSRN 4851266) [SEARCH-INDEX]. Both the first author's given name and the third author's given name are incorrect. "Zhengyang Jiang" is a different, real financial economist; "Zheyu Zheng" does not appear in any record I located. Notably, the package's own crosswalk instructs the referee to "use the final three-author publisher record" — it caught that something was off about the authorship and still did not catch that two of three names are wrong. This is a concrete demonstration that the disclosed gap register is not an answer key.

2. **Cong, Huang and Xu — two distinct papers have been merged.** The plan's reference list gives the title *"The Rise of Factor Investing: Asset Prices, Informational Efficiency, and Security Design"* (2026), attributes it to Cong, Huang and Xu, and links **NBER w32016**. The search index returns w32016 as *"The Rise of Factor Investing: 'Passive' Security Design and Market Implications"* by Cong, Huang and Xu (January 2024), while *"Rise of Factor Investing: Asset Prices, Informational Efficiency, and Security Design"* is a **separate, earlier, two-author SSRN paper by Cong and Xu** (abstract 2800590) [SEARCH-INDEX]. The plan has attached an older two-author title to the current three-author paper. The JF R&R (second round) status the package reports is corroborated by the author research page as returned by the index, and the package is right that an R&R is not an acceptance.

3. **Ernst — the status label is unresolved and may be stale in the direction that matters.** The plan and crosswalk both say "working paper." The search index surfaces an author-CV line reporting **Revise and Resubmit at the *Review of Financial Studies***, together with draft versions dated 2020, 2022 and later [SEARCH-INDEX]. I could not reach the author page to adjudicate. If Ernst is at R&R or forthcoming at RFS, the novelty boundary is *closer* than the plan assumes, and the "current author page still lists it under working papers" sentence in §2.1 should not survive to submission without a same-day check.

4. **Structural: the plan's reference list contains an entry that appears nowhere in its argument.** Hasbrouck (1995), *One Security, Many Markets*, is listed but never used; conversely the information-share methodology discussion in §6.6 invokes "Hasbrouck ordering bounds" without citing it at the point of use. Minor, but in a plan whose whole posture is citation discipline it is the kind of thing a referee notices.

5. **Internal link inconsistency.** Israeli, Lee and Sridharan is linked to a Wharton-hosted manuscript in the crosswalk and to a `runi.ac.il`-hosted PDF in the plan's reference list; Ben-David et al. is linked to an `/abs/` page in the crosswalk and a `/pdf/` page in the references. Harmless, but it shows the crosswalk and the plan were not built from one source register — which is exactly the failure mode that produces error (1).

---

## 3. Fatal issues

### F1. The primary architecture statistic is not invariant to signal precision, and the predicted concentration gradient is generated by precision alone

**Classification:** FATAL.
**Location:** §6.1 (GLS factor score), §6.2 (definition of `A_e = L^M_e − L^G_e` and of `Δ^arch`), Gate 3 in §1, Gate 5 in §14.

**Why fatal.** The giant signal is the GLS score

```
z_A(t) = (B_A' Ω_A⁻¹ B_A)⁻¹ B_A' Ω_A⁻¹ r_A(t),
```

whose sampling variance is `(B_A' Ω_A⁻¹ B_A)⁻¹`. Adding `z_A` to a baseline that already contains SPY and ES improves the forecast of a target that loads on the same common shock θ in proportion to `z_A`'s precision as an estimator of θ. The forecast gain is therefore a monotone function of `B_A' Ω_A⁻¹ B_A` — that is, of the group's loadings on the announcement factor and the inverse of its residual and quote-noise covariance.

Now consider what changed between 2013 and 2025 with no change whatsoever in cross-market conductance:

- the top-ten issuers' loadings on rate news rose, as long-duration growth firms displaced others at the top of the index;
- the top-ten issuers' quote noise fell relative to ranks 11–20 (tighter relative spreads, higher quote intensity, greater depth) as trading concentrated in the same names;
- both raise `B_G' Ω_G⁻¹ B_G` relative to `B_M' Ω_M⁻¹ B_M`.

`A_e` rises. `Δ^arch` is positive. `q'(C) = 0` throughout.

**Weight invariance does not defend against this**, and this is the crux. The plan's entire defence of `A_e` against the arithmetic objection is that `z_G` does not use index weights as aggregation coefficients. But the channel above runs through **β and Ω**, not through **w**. Making the estimator weight-free removes the wrong contaminant.

**The matched-group comparison does not defend against it either.** `M_e` is chosen as ranks 11–20, or matched on pre-event sector, market beta, rate-news beta, spread, dollar volume, quote intensity, price and quote age. None of those is the estimated precision `B' Ω⁻¹ B` of the group's factor score; matching on the *level* of liquidity does not equalise the *precision of a ten-name GLS common-factor estimate*. Worse, the divergence between ranks 1–10 and ranks 11–20 on exactly these dimensions **is** what rising concentration is, so the matched comparison's precision deficit grows mechanically with the treatment.

**This is not a variant of the plan's H4.** H4 as written is about weights, betas, sectors, liquidity, staleness and feed quality "generating apparent leadership," and its rejection criterion is that the observed slope lies outside the mechanical-null distribution. But the plan's own microfoundation *defines* the conductance `q(C)` to include price-measurement noise `σ_ξ²` in the denominator of `a_i*`. So the structural object the paper wants to estimate already contains the measurement channel. **H2 and H4 are observationally equivalent under the proposed statistic**, not merely hard to separate.

**Decisive remedy.** Make precision the object that is held fixed, not liquidity:

1. Report `B_G' Ω_G⁻¹ B_G` and `B_M' Ω_M⁻¹ B_M` for every event; show their ratio's time path against HHI. If that ratio trends with concentration, the raw `Δ^arch` is uninterpretable and must not be reported as the headline.
2. Construct a **precision-equalised** comparison: add independent Gaussian noise to whichever score has higher estimated precision in the training window so that both scores enter the forecast with identical estimated precision, and recompute `A_e`. This is a construction change requiring no new data.
3. Alternatively, select `M_e` by nearest-neighbour matching on estimated `B' Ω⁻¹ B` rather than on spread and volume.

**Pass criterion.** The 90th-minus-10th percentile contrast in *precision-equalised* `A_e` retains its sign and at least the prespecified minimum detectable effect, and the gap between raw and equalised contrasts is reported as a headline exhibit rather than an appendix note.

**Feasibility:** high — no new data, no new licensing.

**If it fails:** the "architecture" claim must be abandoned. The honest surviving statement is that *the giant basket became a better-measured proxy for the common shock*, which is a liquidity and measurement fact adjacent to Chan (1992) and Brennan–Jegadeesh–Swaminathan (1993), and is not publishable as evidence that concentration changed information processing.

---

### F2. The estimand is evaluated outside the support of the variation that identifies it

**Classification:** FATAL.
**Location:** §6.2 (`Δ^arch` defined as a fitted `c90 − c10` contrast; year fixed effects declared preferred), §8.1, §11 (`n_eff,C`), Gate 4.

**Why fatal.** `Δ^arch` is defined as the fitted difference between the 90th and 10th percentiles of the *raw* concentration distribution. The preferred specification includes calendar-year fixed effects. Those two choices are incompatible.

Issuer HHI over 2013–2025 is close to a monotone function of calendar time. Year fixed effects therefore remove nearly all of the variation that spans `c10` to `c90`; what remains is **within-year residual HHI**, whose range is a small fraction of the raw range. The coefficient `β_A` is identified on that small within-year range and then **extrapolated** to a `c90 − c10` gap it never sees. The reported "high-minus-low concentration contrast" is thus a linear extrapolation many times outside the support of its own identifying variation. That is not a robustness concern; it is a mis-specified estimand.

**And the within-year variation is the *most* endogenous variation available, not the least.** Within a calendar year, residual issuer HHI moves because the top-ten issuers outperformed or underperformed the rest since the January index file. Residual HHI is therefore, by construction, approximately a **lagged giant-momentum variable**. It is mechanically correlated with giant realised volatility, giant order-flow intensity, giant news intensity and giant valuation — precisely the omitted variables that would independently change how well giant quotes forecast anything. Conditioning on year does not clean the regressor; it distils it into its most contaminated component.

**The alternative specification is worse in a different way.** Without year effects, the HHI coefficient is a pure calendar trend, and inside the confirmatory window it is collinear with at least five documented regime changes, each of which I verified independently today:

| Regime change | Date | Verified basis |
|---|---|---|
| FOMC press conference after **every** meeting (previously only at SEP meetings) | January 2019 | [SEARCH-INDEX] Powell announced at the June 2018 press conference that press conferences would follow every meeting starting January 2019 |
| Daily TAQ timestamps: milliseconds → microseconds | 27 July 2015 (UTP), 3 August 2015 (CTA) | [SEARCH-INDEX] TAQ client-specification history |
| Daily TAQ timestamps: microseconds → nanoseconds | 24 October 2016 (UTP), 18 September 2017 (CTA) | [SEARCH-INDEX] same |
| Monetary-surprise instruments: Eurodollar → SOFR futures in the USMPD | January 2022 | [SEARCH-INDEX] SF Fed USMPD / Acosta et al. documentation summary |
| Secular decline in index-instrument response latency | continuous | [SEARCH-INDEX] Chordia et al. report the speed of information incorporation increased over their sample |

A regression on roughly one hundred events with year fixed effects and a seven-variable control set cannot separate an HHI slope from this set.

**Decisive remedy.** Two options, in order of preference:

1. **Move the identifying variation off the time series entirely** (see R1 in Section 10). This is my recommendation and the substance of the REDESIGN verdict.
2. If the historical design is retained, `Δ^arch` must be redefined as a contrast **within the observed support of the identifying variation** — i.e. the 90–10 contrast of *residualised* HHI, reported in HHI units — and the paper must present, side by side, the same regression with a smooth trend, with a January-2019 step, and with feed-regime steps, showing that the HHI coefficient is separately identified from each. It almost certainly is not.

**Pass criterion.** `n_eff,C ≥ 40`; no calendar block contributes more than 25% of concentration information (the plan's own threshold); and the HHI coefficient survives, with the same sign and magnitude, the simultaneous inclusion of a smooth calendar trend and a January-2019 indicator.

**Crucially, this test costs nothing.** Approximate issuer HHI can be built today from public constituent and market-capitalisation data at accuracy far exceeding what is needed to compute residual within-year support and block leverage. **This should be Gate 0, before any licensing decision.** The plan has it as Gate 4, behind the expensive licensing gate. That ordering is wrong.

**If it fails:** the continuous-HHI claim is dead in the historical design, and the paper must either move to R1 or become an explicitly descriptive two-regime comparison with no concentration gradient claimed.

---

### F3. The primary horizon is three orders of magnitude coarser than the adjustment it purports to measure, and the horizon that would be right has no concentration variation

**Classification:** FATAL (structural — not resolvable by any gate in the plan).
**Location:** §6.2 (five-second target, origins 0–25 s), §9 (the plan's own warning), Gate 2.

**Why fatal.** Search-index summaries of Chordia, Green and Kottimukkalur report that SPY and ES respond to macro announcement surprises **within five milliseconds** [SEARCH-INDEX]. Whatever allocation of price discovery exists among index instruments and giant stocks is therefore resolved long before the plan's first forecast horizon closes. At a five-second horizon the index side is finished; essentially all remaining variation in the leave-signal-out constituent basket is the residual names' own quote-refresh path. The forecasting comparison consequently ranks candidate signals by how well each proxies θ for a target dominated by measurement dynamics — which is precisely the failure mode of F1, and which the plan itself warns against in §9 ("Do not call one-second data evidence about who incorporates news first when the relevant adjustment may occur at much finer resolution") before adopting a five-second primary outcome in §6.2.

**The tension is structural, not a data-quality problem, and Gate 2 does not test for it.** Gate 2 asks whether five seconds is *measurable* given clock comparability. That is the wrong question. Five seconds is measurable. Five seconds is not *interpretable* as price-discovery allocation. Meanwhile the horizon that would be interpretable — 100 ms or finer, with venue-native data on both legs — exists only in a modern subsample which, by construction, has almost no concentration variation. Formally:

> the finest defensible horizon `h*` is decreasing in sample recency, while usable concentration variation is increasing in sample length. The design requires both simultaneously.

No robustness check reconciles this. The plan's structure hides it because the horizon question and the support question are assigned to separate gates (2 and 4) and are never evaluated jointly.

**Decisive remedy.** Choose one and accept its cost:

- **(a)** Keep the horizon, drop the framing. Relabel the primary outcome as what it is — a measure of **residual-constituent adjustment lag and breadth** — and the paper becomes a completion-speed paper, not an architecture paper. This is honest and feasible, and it is a smaller contribution.
- **(b)** Keep the framing, move to a modern high-resolution window, and obtain treatment variation cross-sectionally rather than temporally. That is R1.

**Pass criterion for (a):** the plan must demonstrate, on the pilot, that the 0–30 s residual-basket path is not simply a quote-refresh hazard, e.g. that the path's shape survives conditioning on each name's post-announcement quote-update count. **Pass criterion for (b):** demonstrated cross-market clock bound well below the chosen horizon on both legs.

**If neither is adopted:** the paper's headline claim about "the architecture of price discovery" is not supported by its own outcome variable.

---

### F4. The formal mechanism generates the H2 signature under the plan's own arithmetic null, so the model does not discipline the hypotheses

**Classification:** FATAL for the hypothesis structure (MAJOR-FIXABLE for the paper if the model is corrected and the empirical implications are re-derived).
**Location:** §3.2 (comparative statics) read against §7.1 (index idiosyncratic content).

**Why fatal.** §3.2 derives

```
∂Var(θ | x_I, x_G)/∂C = − q'(C) / [A + q(C)]²
```

explicitly "holding the direct index precision `A` fixed," and concludes that both normal-state precision and impairment sensitivity rise with concentration **only if** `q'(C) > 0`. That derivative is declared to be "the model's empirical content."

But §7.1 of the same plan derives, correctly, that

```
Var(U_I) = Σ_i w_i² σ²_{u_i}
```

rises with concentration, and states in terms: "Concentration can also raise the idiosyncratic content of the index, so a concentrated index need not be a cleaner common-factor signal."

An index instrument whose payoff carries more idiosyncratic content is a **worse** signal of the common shock. Therefore `A'(C) < 0` by the plan's own §7.1. Substituting that into §3.2:

- **Reliance share.** `∂/∂C [ q/(A+q) ] = [q'A − qA'] / (A+q)²`. With `q' = 0` and `A' < 0`, the numerator is `−qA' > 0`. **The giant channel's reliance share rises with concentration under a pure arithmetic null.**
- **Impairment loss.** `∂/∂A [ 1/A − 1/(A+q) ] = −1/A² + 1/(A+q)² < 0`, and `A' < 0`, so the impairment loss also **rises** with concentration with `q' = 0`.

Both of the model's headline comparative statics — the ones the plan uses to motivate H2 and H3 — obtain **without any change in trader behaviour, attention, or cross-market conductance**. The model as written is therefore not a discriminating device; conditional on `C`, it is close to a tautology. The plan's claim that "a statistic that rises in that null does not identify `q'(C) > 0`" is right in spirit and is contradicted by its own mechanism section, which is doing the opposite.

**Decisive remedy.** Re-derive the comparative statics with `A = A(C)` endogenous, using the §7.1 expression for `Var(U_I(w))` to sign `A'(C)`. State the joint restriction that actually distinguishes H2 from H4 — which will be a restriction on `q'A − qA'` relative to what the arithmetic channel alone delivers, and which must then be **calibrated**, not assumed. Then re-check which of the four hypotheses remain separately identified. My expectation is that H2 versus H4 survives only if the empirical design can measure `A(C)` independently — which requires an independent estimate of the index instruments' own signal precision, and which the plan does not currently propose to construct.

**Pass criterion.** A written statement of the sign restriction that H2 imposes and H4 does not, once `A'(C) < 0` is admitted, together with a simulation showing the proposed statistic separates them at the sample size available.

**If it fails:** H2 and H4 are not separately testable and the paper cannot claim to have distinguished architecture from arithmetic — regardless of how well the replay and simulation exercises are executed.

---

## 4. Fixable major issues

### M1. The January-2019 press-conference change breaks package comparability inside the confirmatory sample

**Severity:** MAJOR. **Location:** §5.1, §5.2.

The plan verifies the March-2013 timing change and treats the 2013–2025 window as having "a common statement clock." It does. It does not have a common *package*. Search-index sources confirm that press conferences followed only meetings with a Summary of Economic Projections until January 2019, after which they follow every meeting [SEARCH-INDEX]. That means that before 2019 a non-SEP 2:00 pm statement was the entire release, whereas after 2019 every 2:00 pm statement is a partial release with a known 30-minute follow-on. This changes both the completeness of the 2:00 pm information set and the incentive to trade immediately versus wait — and it does so differentially across securities with different duration exposure, i.e. exactly along the giant/matched contrast. The break sits in the middle of the concentration rise.

**Required change.** Stratify by package type and state the primary result *within* a homogeneous stratum. Two coherent options: (i) SEP-and-press-conference meetings only, throughout 2013–2025 (roughly four per year, ≈52 events); (ii) post-January-2019 only (≈56 events). Both are homogeneous; both roughly halve the sample; option (ii) additionally destroys the low-concentration support. **Pass criterion:** the concentration gradient has the same sign and comparable magnitude in the homogeneous stratum, with the stratum's own MDE reported. **Remaining limit:** whichever stratum is chosen, the power problem in F2 becomes materially worse, and the plan must confront that jointly rather than in a separate gate.

### M2. The SPY–ES basis outcome is contaminated by the announcement's own effect on carry

**Severity:** MAJOR. **Location:** §6.4.

`b_e(t)` is defined as the log price difference minus a **pre-event constant** `b̄` averaged over [−10, −1] minutes. But the spot-equivalent conversion depends on financing and expected dividends to expiry, and an FOMC statement is *news about the financing rate*. A rate surprise mechanically shifts the fair basis by approximately (surprise) × (time to expiry), discontinuously at 2:00 pm. Demeaning by a pre-event constant does not remove a post-event level shift. The resulting `Q_e = ∫₀³⁰|b_e(t)|dt` therefore contains a deterministic component increasing in |surprise| and in days-to-expiry, and both of those vary across events in ways correlated with the sample period. Additionally, SPY's structure accrues dividends in cash between distributions, so the basis carries a predictable within-quarter sawtooth that also enters `∫|b|`.

The package's gap register flags this as item 14 but classes the remedy as "dynamic fair-value carry" robustness. It is not robustness; the primary outcome as specified is mis-defined.

**Required change.** Replace the pre-event constant with a carry model updated using the announced rate path, computed from the same rate instruments used for the surprise; residualise `Q_e` on |surprise| × days-to-expiry and on the accrued-dividend position within the distribution cycle. **Pass criterion:** after adjustment, `Q_e` is unrelated to days-to-expiry and to |surprise| in the placebo windows and in the pre-event window. **Remaining limit:** even corrected, `Q_e` measures quoted-midpoint disagreement, not accuracy or executable arbitrage — the plan already says this and should keep saying it.

### M3. The `t = 0` forecast origin contains no post-announcement information and should not be in the primary average

**Severity:** MAJOR (power). **Location:** §6.2.

Forecast origins are 0, 5, 10, 15, 20 and 25 seconds, with three **one-second** lags of every predictor. At `t = 0`, all three lags of every signal — target, SPY, ES, `z_G`, `z_M` — are pre-announcement. The `t = 0` model therefore has no information about the news, while its five-second target contains the entire announcement jump and hence by far the largest variance of the six origins. Because `L_e` is the unweighted mean of squared errors across origins, the `t = 0` origin dominates `L_e` and contributes a large common noise term to both `L^G_e` and `L^M_e`. It differences out of `A_e` in expectation but inflates its variance, directly degrading the power the design cannot spare.

**Required change.** Exclude the `t = 0` origin from the primary loss, or weight origins by inverse target variance estimated in the training sample. Report the excluded origin separately as the announcement-jump description it actually is. **Pass criterion:** prespecified before evaluation; the sensitivity of `A_e`'s variance to origin weighting is reported.

### M4. The training scheme either consumes the low-concentration support or transfers a model across regimes

**Severity:** MAJOR. **Location:** §1 (2010–2012 as training), §6.2 (expanding window, 24-event threshold).

The plan states that 2010–2012 is a **different timing and feed regime** which must never be silently pooled, and then uses it to freeze the feature list and ridge grid for models applied to 2013–2025. Fitting a forecasting model on one clock and message regime and applying it out-of-sample to another is a regime transfer, not a clean development/confirmation split; the "out-of-sample" label is doing less work than it appears to.

The stated fallback is worse. If fewer than 24 valid 2010–2012 events survive the audit, "confirmatory evaluation begins only when that threshold is met" — that is, evaluation begins later, and since concentration is monotone in time, **the evaluated sample is truncated from below in concentration**. The `c10` events the estimand needs would then be training-only and never evaluated. The plan acknowledges "the lost low-concentration support must then enter the power decision," but this is not a power adjustment; it changes which contrast is estimable at all.

**Required change.** Decide in advance, and state, whether 2010–2012 is usable. If it is, say why regime transfer is acceptable and show the model's stability across the 2013 break. If it is not, the confirmatory sample must be split *within* 2013–2025 in a way that preserves low-concentration events in the evaluation set — for example, by fitting on odd-numbered meetings and evaluating on even-numbered meetings within each year, which sacrifices the temporal-split property but preserves concentration support. That trade-off must be made explicitly and preregistered. **Pass criterion:** the evaluated sample's HHI range covers at least the `c10`–`c90` interval used to define `Δ^arch`.

### M5. The frozen-network null is calibrated in a regime it is not applied to

**Severity:** MAJOR. **Location:** §7.3 ("Calibration uses only the development sample").

The specificity gate — the plan's own most important gate — calibrates the no-transmission-change simulation on 2010–2012, a period with millisecond SIP timestamps, a different statement clock, pre-MDP-3.0 CME messaging, and different odd-lot and quote conventions. A null calibrated there cannot bound the distribution of a statistic computed on 2016–2025 data. Since the whole purpose of Gate 3 is to say whether the *observed slope over 2013–2025* lies outside the fixed-conductance distribution, calibrating the null in a single early regime biases the comparison in an unknown direction and, plausibly, in the direction of finding the observed slope "outside" the null.

**Required change.** Recalibrate the null **per regime**, using non-announcement intraday windows from within each calendar year — which is available, cheap and outcome-blind — and evaluate the specificity criterion year by year as well as pooled. **Pass criterion:** the observed statistic lies outside the fixed-conductance distribution in the majority of individual years, not only in the pooled comparison.

### M6. The "matters" conclusion uses an OR-rule across two outcomes, which is a third primary endpoint

**Severity:** MAJOR. **Location:** §11 (two primary tests, Holm-adjusted) read against §11's own conjunctive sentence and §14's Gate 6.

The plan declares two primary outcomes with Holm adjustment. But the conclusion that centralisation "matters" is then allowed if architecture changes **and** *either* the SPY–ES disagreement outcome *or* the prespecified equal-weight breadth outcome changes consistently. An OR across two outcomes is a third test with an inflated rejection region; Holm on two endpoints does not control it. The package's own register flags this as items 16 and 19 and is right to.

**Required change.** Replace Holm-on-two with an explicit **hierarchical gatekeeping** sequence: architecture first; only if it passes, the quality outcome; only if that fails, the breadth outcome as a prespecified fallback with its own alpha. Preregister the order. **Pass criterion:** the multiplicity rule is written down before any confirmatory outcome is opened, and the reported family matches it exactly.

### M7. The 2023 Nasdaq episode is mischaracterised as discretionary, and the rule that generated it supplies the identification the plan says is unavailable

**Severity:** MAJOR — and it is the constructive core of this report. **Location:** §8.3, §8.4, §15.

The plan describes the July 2023 NDX special rebalance as an episode in which "the provider retained discretion," and concludes in §8.4 that a causal upgrade would require "a new design using many independent, stable-rule cap crossings across liquid index families" — treating that as hypothetical future work.

That characterisation understates the rule and overlooks families that already exist. Independently verified today:

- The 2023 NDX special rebalance was **triggered by a published numeric threshold**: the cumulative weight of constituents individually exceeding 4.5% of the index had reached **50.9% as of 3 July 2023**, against a methodology limit of **48%** [SEARCH-INDEX]. The plan's own §8.3 dates (announced 7 July; reference data 3 July; pro forma 14 July; effective before the open on 24 July; no securities added or removed) are corroborated [SEARCH-INDEX].
- The Nasdaq-100 applies **quarterly** weight adjustments in March, June, September and December, designed to keep any single issuer below **24%** and to keep issuers individually above 4.5% from collectively exceeding **48%**; a further annual rule applies when one company exceeds 15% or the top five reach 40% [SEARCH-INDEX].
- The **Select Sector** indices underlying the eleven Select Sector SPDR ETFs applied a repeated capping mechanism at quarterly rebalances — under the pre-September-2024 rule the sum of constituents weighing more than 4.8% could not exceed 50% — replaced on **20 September 2024** by a "New Capping Mechanism" reducing that aggregate to **45%** [SEARCH-INDEX]. The **June 2024 XLK rebalance** moved Apple from roughly 22% to roughly 4.5% and Nvidia from roughly 6% to roughly 21%, forcing on the order of **$10 billion** of Apple sales and comparable Nvidia purchases [SEARCH-INDEX].

This is not one anticipated intervention. It is a **repeated, formula-triggered, pre-announced reweighting mechanism operating across eleven sector indices plus the Nasdaq-100, quarterly, with an observable running variable and a published threshold**. And it has a property the plan's S&P design lacks and cannot manufacture: it changes a stock's arithmetic role **in one traded basket while leaving its weight in another traded basket, its fundamentals, and its own quote process unchanged**.

That property answers the plan's own opening symmetry objection more cleanly than anything in the current design. See R1 in Section 10 for the design specification, its threats, and its data implications.

**Required change.** Demote the 2023 NDX event from "secondary intervention audit" to one instance of the capping mechanism, and elevate the mechanism itself to the primary identification strategy. **Pass criterion:** an assignment audit showing (i) the number of quarters in which a cap actually bound, by index family; (ii) the distribution of assigned |Δw| conditional on binding; (iii) that the running variable's crossings are not perfectly predictable from a small set of pre-period observables. **Remaining limit:** anticipation is real (pro forma files are published in advance), rebalancing flows are large and are part of the total effect rather than a controllable confound, and the same stocks appear in both the treated and comparison baskets, so interference must be bounded rather than assumed away.

### M8. Rising giant idiosyncratic volatility is an untested rival mechanism with the opposite sign

**Severity:** MAJOR. **Location:** §3.3 (hypothesis set), §6.1.

Search-index summaries of Jiang, Vayanos and Zheng report that passive flows **increase the idiosyncratic risk of large firms in high demand**, and that the idiosyncratic volatilities of the largest S&P 500 firms rise most following flows into the index [SEARCH-INDEX]. If that holds over the plan's sample, the giant basket becomes a **noisier** estimator of the common shock as concentration rises — pushing `A_e` *down*. The plan's hypothesis set has no cell for "concentration degrades the giant channel's signal quality through demand-induced idiosyncratic risk," and its H1 (`q'(C) ≈ 0`) is not the same thing as `q'(C) < 0`.

**Required change.** Add the negative-conductance alternative explicitly, with its own prediction and rejection criterion; and, because this mechanism operates through exactly the `Ω` term identified in F1, report the giants' idiosyncratic variance path alongside the concentration path. **Pass criterion:** the sign of `Δ^arch` is interpreted against a measured, not assumed, path of giant idiosyncratic variance.

### M9. Nonsynchronous-trading precedent is under-cited and the corresponding defence is under-specified

**Severity:** MAJOR (framing and referee risk). **Location:** §7.1, §9, §12.

The single oldest and most damaging critique of any cash-versus-index lead–lag finding is that measured cash lags reflect infrequent trading. Stoll and Whaley (1990) reported futures leading cash by about five minutes and occasionally ten or more **even after purging cash returns of infrequent-trading effects** [SEARCH-INDEX] — i.e. the standard correction was already known to be insufficient in 1990. The plan's residual basket is exactly the portfolio for which this bias is largest, and its giant basket is exactly the portfolio for which it is smallest. The plan's defences (quote-age thresholds, previous-tick versus synchronised-grid estimators, coverage weights) are the right instruments but are listed among a dozen falsifications rather than treated as the first-order threat to the primary outcome.

**Required change.** Promote the staleness treatment to a primary-exhibit status: report the primary result as a function of a quote-age cap, and show the concentration gradient at each cap. **Pass criterion:** the gradient does not vanish monotonically as the quote-age cap tightens. **Remaining limit:** tightening the cap changes the composition of the residual basket, which is the plan's own gap item 12 — so composition must be held fixed while the cap varies.

### M10. Gate inconsistency, and the gate order puts the expensive test first

**Severity:** MAJOR (process). **Location:** §1 (four gates) versus §14 (six gates plus a resilience gate).

The register flags the count mismatch (item 19) and is right; but the more consequential problem is the **order**. Gate 1 is licensed point-in-time index composition — the most expensive item in the project. Gate 4 is power and effective support — computable today, for free, from approximate weights, because the question is whether *within-year residual HHI has any support at all*, and that is invariant to small weight-measurement error. Gate 3's mechanical null likewise needs only realistic price paths, not official index shares, for a first pass.

**Required change.** One preregistered ordered sequence, cheapest-decisive-first. See Section 10.

---

## 5. Minor issues

1. **Log versus simple returns.** §5 correctly insists that the fixed-quantity basket identity holds in simple returns and warns against presenting weighted log returns as an index identity. §6.2 then defines the primary target `Y_{e,t}` as a *log* return of a basket constructed from simple-return weights. Harmless numerically over five seconds, but it is an internal inconsistency in a document whose §5 makes a point of it.
2. **Six origins per event, one cluster.** §6.2's six origins and §11's meeting-level aggregation are consistent, but the plan should state explicitly that the effective number of independent observations for the primary test is the number of *meetings*, not meetings × origins, in every exhibit that reports a standard error.
3. **"Approximately eight scheduled meetings per year."** Correct as an order of magnitude, but the plan should publish the exact eligible count after the calendar audit before any power statement, since the entire inference rests on it. Arithmetic on the plan's own figure gives roughly 100–104 events for 20 March 2013 through December 2025 before exclusions.
4. **Hasbrouck (1995) is listed but unused**; the ordering-bounds discussion in §6.6 cites no source at the point of use.
5. **Link inconsistencies** between the crosswalk and the reference list (Israeli et al., Ben-David et al.) indicate two separately maintained citation registers.
6. **Package integrity claims are not checkable by the recipient.** See Section 0.
7. **Exhibit shells are good but under-specify units.** Table 3 promises "economic units"; the plan should fix now whether the headline number is percentage points of baseline MSE or basis points of RMSE, because the two invite different readings of the same result.
8. **"Technology plus communication-services weight" as a control** is a point-in-time GICS construct that changed definition during the sample (the 2018 GICS restructuring moved several of the largest constituents). The plan uses point-in-time GICS elsewhere; it should say explicitly that this control is not comparable across the 2018 boundary.
9. **The equal-issuer-weight residual basket** is described as measuring breadth. It also mechanically changes the staleness profile of the target (small names dominate), so its comparison with the value-weighted residual confounds breadth with quote freshness. Report both under a common quote-age cap.
10. **The resilience section is correctly quarantined**, and I endorse the plan's own conclusion that deleting quotes in a simulation is not an impairment. No change needed beyond keeping it out of the headline.

---

## 6. Claim audit

| Headline claim | Estimand | Identifying variation | Outcome | Required data | Strongest falsification | Remaining interpretation limit | Confidence the design supports it |
|---|---|---|---|---|---|---|---|
| Giant-channel architecture changed with concentration | Fitted `c90 − c10` contrast in placebo-differenced `A_e` | Within-year residual issuer HHI across ~100 FOMC statements | Five-second leave-signal-out forecast loss difference | Official point-in-time weights; full-constituent NBBO; SPY; actual ES contract; matched windows | **Precision-equalised** `A_e` shows no gradient (F1); or the gradient is indistinguishable from a trend plus a January-2019 step (F2, M1) | Even if it survives, it is incremental *leading information*, not learning, not causation | **Low.** F1 and F2 are both live and either is sufficient to void the claim |
| Same-payoff synchronisation changed | `c90 − c10` contrast in placebo-adjusted 30-second ∫\|basis\| | Same | Basis-point-seconds | SPY and ES quotes; carry, dividend and roll inputs | Correlation of `Q_e` with days-to-expiry or \|surprise\| after adjustment (M2) | Quoted-midpoint agreement only; no accuracy, arbitrage or welfare content | **Low–moderate**, and only after the carry correction |
| Information incorporation broadened or narrowed | `c90 − c10` contrast in equal-issuer residual completion loss | Rate-news response across events and concentration | Seconds to fitted 120-second response | Residual quotes; external rate factors; pre-event exposures | Terminal response signal-to-noise fails; or the equal-weight result is driven by quote-age composition (M9, minor 9) | Completion relative to a *fitted* later response, not to value | **Moderate.** This is the most robust of the three, and is the natural headline under remedy F3(a) |
| The 2023 NDX reweighting altered local links | Post × archived pro forma Δw | One system-wide, anticipated, staged intervention | Stock-to-NDX predictive contribution | Historical NDX shares; QQQ/NQ/stock quotes | Pseudo-dates or S&P-side links show the same change | One vector, one date; total local association including flows | **Very low as specified; moderate-to-high if generalised to the repeated capping mechanism (M7/R1)** |
| Concentration *caused* any of the above | — | — | — | — | — | — | **Not supported.** The plan says so; I agree, and note that its own §8.1 language ("architecture beyond contemporaneous liquidity") is close enough to causal phrasing that it should be tightened |

---

## 7. Mechanism and hypothesis audit

**The formal mechanism is incorrect as stated.** See F4: holding `A` fixed is not innocuous, because the plan's own §7.1 implies `A'(C) < 0`, and with that admission both headline comparative statics obtain at `q'(C) = 0`. The comparative statics must be re-derived.

**Which observations uniquely distinguish the four hypotheses, as the plan currently stands:**

| Observation | H1 (index dominance) | H2 (giant–index interaction) | H3 (centralisation + dependence) | H4 (mechanical/exposure) |
|---|---|---|---|---|
| `A_e` rises with `C` | ✗ | ✓ | ✓ | **✓ — see F1, F4** |
| Rise survives precision equalisation | ✗ | ✓ | ✓ | ✗ |
| Rise survives exact weight replay on identical paths | ✗ | ✓ | ✓ | partly ✓ (replay does not touch β or Ω) |
| Rise survives fixed-conductance simulation with heterogeneous β and calibrated quote noise | ✗ | ✓ | ✓ | ✗ **if and only if** the simulation reproduces the *time path* of relative precision |
| Asymmetry: giant→residual gradient exceeds residual→giant and index→giant | ✗ | ✓ | ✓ | ✗ |
| Independently timed giant-channel impairment produces larger deterioration at high `C` | ✗ | ✗ | ✓ | ✗ |
| Giant idiosyncratic variance rises with `C` | — | tension | tension | ✓ (M8) |

The table shows the problem compactly: **only two rows currently discriminate H2 from H4** — precision equalisation (which the plan does not do) and the fixed-conductance simulation (whose ability to discriminate depends entirely on whether it reproduces the observed time path of relative signal precision, which the plan does not require of it). Every other listed observation is consistent with H4. The plan's claim in §9 that nine tests are "headline-essential" overstates how much discrimination they collectively deliver, because most of them address the *weight* channel, and the live contaminant is the *precision* channel.

**Assumed signs.** `φ > 0` (cross-venue inference effectiveness) is assumed, not derived; `q' > 0` is the object of interest and is not separately identified from `A' < 0`; the claim in §3.1 that "a highly liquid giant stock or giant basket can become a lower-basis-risk proxy for the index's common exposure as its weight rises" is asserted — basis risk of a giant basket against the index is `Var(Σ_{i∈G} ω_i u_i)` plus factor-mismatch, and whether it falls with concentration depends on the giants' idiosyncratic variance path, which M8 suggests may move the other way.

**Tautologies.** As written, "concentration raises the reliance share on the giant channel" is close to true by construction once `A(C)` is endogenous. That must be removed from the paper's motivation.

**Untestable links.** The step from "giant quotes predict residual quotes" to "traders infer the common interpretation from giant prices" is not testable in this design, and the plan correctly says so. I endorse its restriction to "incremental earlier predictive information." That restriction should also propagate to the abstract, which currently says the paper asks whether incorporation "become[s] more dependent on information transmission between those companies' shares and index instruments" — dependence is not what the design measures.

---

## 8. Measurement and data-feasibility verdict

**Finest defensible time horizon.**

- **Full 2013–2025 sample, SIP data on the equity leg: 30 seconds.** The binding constraints are (i) millisecond SIP timestamps before late July / early August 2015 [SEARCH-INDEX], (ii) the absence of a directly comparable exchange-side clock on the equity leg for the early years, and (iii) an unknown and *trending* SIP dissemination latency across a sample whose whole point is a time trend. A constant relative-clock perturbation, which is what the plan proposes, cannot address a latency trend.
- **Modern subsample with venue-native data on both legs: 1 second is arguable; 100 milliseconds only with a demonstrated cross-clock bound well under 100 ms on both legs.**
- **The five-second primary horizon is measurable but not interpretable as price-discovery allocation** (F3). It is interpretable as residual-constituent adjustment lag.

**Indispensable data.**

| Item | Status | If unavailable |
|---|---|---|
| Official point-in-time index shares, float factors, membership, corporate actions | Licensed, unacquired. The register's item 1 is correct: this is a hard stop **for the S&P historical headline design** | No exact HHI, no exact basket, no replay |
| Full-constituent NBBO with quote-condition and participant fields, 2013–2025 | Licensed, unacquired | No breadth claim, no leave-signal-out target |
| Actual quarterly ES contracts with exchange event time, plus roll metadata | Licensed, unacquired | No directional cross-market result |
| Independent cross-clock bound between equity venues and CME, **by year** | Untested, and the plan proposes a constant-shift test that is insufficient | No directional claim at any horizon finer than the bound |
| Date-level FOMC release times and package composition, including SEP and press-conference indicators | Public; the plan's March-2013 fact is corroborated [SEARCH-INDEX], and the January-2019 package change must be added (M1) | Events excluded; strata mis-specified |
| Real-time short-rate futures quotes for a live rate control | Licensed, unacquired; the USMPD's own instruments changed from Eurodollar to SOFR futures in January 2022 [SEARCH-INDEX] | The design cannot rule out heterogeneous direct responses; the claim narrows to predictive lead |

**Optional.** Sector ETF holdings, order imbalance, depth, firm-news calendars, ETF cash and fee data, three-way cash dispersion, VECM information shares.

**Hard-stop list.** (i) No official point-in-time index composition → the S&P historical headline design stops. (ii) No per-year cross-clock bound → no directional claim. (iii) Within-year residual HHI has no support → the continuous-concentration claim stops (and this is testable now, for free). (iv) The precision-equalised statistic shows no gradient → the architecture claim stops.

**Feasible lower-data redesign — and this is the important finding.** For the R1 design in Section 10, the treatment variable is *the traded basket's own weights*, and Select Sector SPDR and QQQ holdings are **published daily by the issuers**. For that design, ETF holdings are not an inferior proxy for official index weights — they *are* the object, because the arbitrage-relevant basket is the fund's basket. R1 therefore **removes the plan's most expensive gate from the critical path**: it needs no licensed historical index-share file to define treatment. It still needs TAQ and CME data, but over a shorter, more recent, higher-resolution window, which is cheaper and measurement-cleaner than 2013–2025.

---

## 9. Inference and power verdict

**The effective-sample-size problem is worse than the plan's framing.** The plan says the meeting is the independent unit and that roughly eight meetings a year do not supply eight independent draws of concentration. Correct, and insufficient. The deeper problem is F2: after year fixed effects, the identifying variation is within-year residual HHI, whose range is a small fraction of the raw range, while the estimand `Δ^arch` is defined on the raw range. So there are two distinct quantities to report and the plan reports neither separately:

1. `n_eff,C` — the plan's leverage-based effective sample size, which can look reassuringly large even when the *range* of identifying variation is tiny;
2. the **range** of residualised HHI relative to the `c90 − c10` gap the estimand extrapolates to.

A design can pass (1) and be hopeless on (2). Both must be reported, and the paper should report `Δ^arch` **on the residualised support**, in HHI units, as the primary quantity.

**The proposed inference.** Studentised moving-block bootstrap over adjacent meetings or calendar-year blocks, with block length chosen in development and coverage calibrated by simulation, is the right family. Two corrections: (i) with roughly thirteen calendar-year blocks, block-bootstrap coverage for a *trend-like* regressor is poor, and the simulation must verify coverage specifically for the residualised-HHI coefficient, not for a generic mean; (ii) the plan's statement that "no bootstrap can turn one Nasdaq rebalance into multiple policy interventions" is correct and should be extended — no bootstrap can turn one monotone concentration regime into multiple concentration draws either.

**Full-pipeline simulation.** The design is right in structure and wrong in calibration (M5). Recalibrate per regime and require year-by-year specificity.

**MDE calculation.** The plan's screening formula is appropriate:

```
MDE(80%, 5%) = (z_0.975 + z_0.80) · σ_eff / √N_eff = 2.80 · σ_eff / √N_eff.
```

I decline to supply `σ_eff`; it must come from the measurement pilot and nothing in this session could calibrate it honestly. What can be stated now is the **break-even condition**, which the authors can check the moment the pilot returns:

> With the plan's own meaningful threshold of **5 percentage points of relative baseline MSE**, the design is powered at 80% only if
> `σ_eff ≤ (5 / 2.80) · √N_eff ≈ 1.79 · √N_eff` percentage points.
> At `N_eff = 25`, that requires `σ_eff ≤ 8.9` pp; at `N_eff = 40`, `σ_eff ≤ 11.3` pp.

Because `A_e` is a **double difference** — (matched loss − giant loss), then (FOMC − mean of four placebos) — its event-level standard deviation is the accumulation of four noisy loss estimates, and the pilot should be expected to return a large `σ_eff`. The single most informative number the pilot can produce is `σ_eff`, and it should be produced before, not after, the licensing decision.

**Equivalence.** For a two-one-sided-test equivalence claim at the same 5 pp bound with 80% power, the requirement is approximately `σ_eff/√N_eff ≤ 5/(1.645+0.84) ≈ 2.01` pp, i.e. `σ_eff ≤ 2.01·√N_eff`. This is a *tighter* requirement than detection.

**Is a precisely estimated null realistically possible?** On the historical design: **no, not at the 5 pp bound**, unless `σ_eff` comes back surprisingly small. The plan's fallback 3 ("a powered equivalence result") should not be advertised as an available outcome until `σ_eff` is measured; at present it is an aspiration, and presenting it as a fallback overstates the design's insurance. Under R1, where treatment is cross-sectional and repeated, a powered equivalence result is genuinely attainable.

**Multiplicity.** See M6. As written, the family is larger than declared.

---

## 10. Scientific continuation gates

Ordered, cheapest-decisive-first. Each gate is a stop-or-redesign point, and no gate may be skipped because a later one looks more interesting. This sequence replaces both the four-gate list in §1 and the six-gate list in §14.

**Gate 0 — Concentration support. Cost: days, no licensing, no purchase.**
Build approximate issuer HHI over 2010–2025 from public constituent and market-capitalisation data. Residualise on calendar year. Report: the range of residualised HHI against the raw `c90 − c10` gap; `n_eff,C`; block leverage; the share of concentration information from the first and last two years; and the partial correlation between residualised HHI and trailing top-ten relative return.
*Pass:* `n_eff,C ≥ 40`, no block above 25%, and residualised HHI range at least half the raw `c90 − c10` gap.
*Fail:* the continuous-HHI historical design is abandoned. Go to R1. **Do not** proceed to licensing.
*Note:* I expect this gate to fail, and it is the reason the verdict is REDESIGN rather than proceed-after-gates. Failing it costs a week; discovering it after Gate 1 costs the data budget.

**Gate 1 — Mechanical and precision null. Cost: low; needs realistic price paths, not official weights.**
Run the exact alternative-weight replay and the fixed-conductance simulation, calibrated **per regime**, through the complete pipeline. Separately, compute `B_G' Ω_G⁻¹ B_G` and `B_M' Ω_M⁻¹ B_M` on any adequate constituent sample and plot their ratio against concentration.
*Pass:* the simulated statistic does not reproduce the observed slope in the majority of individual years, **and** the precision ratio shows no trend, **or** the precision-equalised statistic retains the slope.
*Fail:* stop, or reframe explicitly as measurement and technology evolution. Controls cannot rescue the statistic.

**Gate 2 — Package homogeneity and event count.**
Complete the date-by-date calendar audit including SEP and press-conference indicators. Fix the homogeneous stratum (M1). Report the eligible event count within it.
*Pass:* a homogeneous stratum with an event count consistent with Gate 3's MDE requirement.
*Fail:* the FOMC-only design cannot support a concentration claim; either add a separately justified, institutionally homogeneous event class as a *separate stratum*, or stop.

**Gate 3 — Power. Requires only the measurement pilot.**
Estimate `σ_eff` for the double-differenced `A_e` on the pilot. Apply the break-even condition in Section 9.
*Pass:* `σ_eff ≤ 1.79·√N_eff` pp.
*Fail:* neither detection nor equivalence is available; do not proceed to a licensed full build.

**Gate 4 — Measurement.** Per-year cross-clock bounds between equity venues and CME; quote-freshness audit; declare the finest stable horizon. *Fail at 30 s:* stop the directional design.

**Gate 5 — Composition.** Licensed point-in-time index inputs; end-of-day reconstruction reconciling to official returns within the plan's stated tolerance. *Fail:* no headline S&P design.

**Gate 6 — Confirmatory architecture.** Precision-equalised, homogeneous-stratum, preregistered, with the hierarchical multiplicity rule of M6.

**Gate 7 — Consequence.** Only if Gate 6 passes; hierarchical, not an OR-rule.

### R1 — the recommended redesign

**Design.** Use rule-assigned index-weight reallocations as treatment.

- **Assignment mechanism:** the published capping rules of the Select Sector indices (aggregate weight of constituents above the single-name threshold capped at 50% pre-September-2024, 45% thereafter) and of the Nasdaq-100 (24% single issuer; 48% aggregate for issuers above 4.5%; annual rules at 15% and top-five 40%) [SEARCH-INDEX]. These bind at scheduled quarterly rebalances across eleven sector families plus NDX.
- **Treatment:** the rule-assigned change in stock *i*'s weight in basket *B*, taken from the published pro forma file.
- **Estimand:** the change in stock *i*'s incremental out-of-sample predictive content for the **leave-*i*-out remainder of basket *B***, per unit of assigned Δw, **differenced against** the same stock's incremental predictive content for a basket *B'* (the S&P 500 system) whose weights were not reassigned.
- **Why it answers the symmetry objection the plan opens with:** same stock, same news, same clock, same quote process, same fundamentals. Only its arithmetic role in one traded basket changed. A pure arithmetic account predicts a change in *i*'s contribution to *B*'s own return and **no** change in its contribution to *B*'s leave-*i*-out remainder. A transmission account predicts both. This is the discriminating comparison the historical design cannot construct.
- **Why it survives F1:** the precision of *i*'s own price signal is held fixed by construction, because the same stock is the signal on both sides of the difference.
- **Why it survives F2 and F3:** treatment variation is cross-sectional and repeated, so the design does not need a long sample; it can live entirely inside the modern nanosecond-timestamp, direct-feed era where the horizon question has a defensible answer.
- **Data implication:** the treatment variable comes from issuer-published daily holdings and pro forma files, so the licensed point-in-time index-share gate leaves the critical path (Section 8).

**Threats that must be pre-declared and tested, not assumed away:** anticipation (pro forma published in advance — use announcement, pro forma, flow and effective dates as separate stages, as the plan already does well for 2023); rebalancing flows as part of the total effect rather than a controllable confound (separate by reversal signature over the following five to ten days, per Ben-David et al.'s propagation channel); interference, since treated stocks sit in both baskets (bound it, and note it attenuates rather than inflates the estimate); and an endogenous running variable, since caps bind because the largest names outperformed (use the discontinuity at the published threshold, not the level).

**What this design cannot do:** it identifies the effect of a weight reallocation in a *particular* basket under a *particular* rule. It does not identify "the effect of market-wide concentration." The paper must say so. That is still a far stronger claim than the historical gradient, and it is the version of this project I would referee favourably.

---

## 11. Publication assessment

No numerical probabilities. Thresholds only.

**Credible specialist journal** (e.g. *Journal of Financial Markets*, *Journal of Banking & Finance*, *Journal of Futures Markets*). Achievable with the plan's *machinery* even if the identification stays descriptive, provided: Gate 0 and Gate 1 pass; the precision-equalisation exercise of F1 is executed and reported as a headline exhibit; the primary outcome is honestly relabelled as residual-constituent completion rather than architecture (F3, remedy (a)); and the citation errors of Section 2.3 plus the omissions of Greenwood (2008), Baltussen et al. (2019), Stoll–Whaley (1990), Sammon (2025) and Coles et al. (2022) are repaired. The contribution would then be a careful measurement paper about how completion breadth around scheduled macro news co-moved with index composition — real, modest, and defensible.

**Broader finance journal** (*JFQA*, *Management Science*, lower-tier *RFS*). Requires the R1 identification: repeated, rule-assigned weight reallocation with a published threshold; the within-stock, across-basket difference; a demonstrated system-level consequence in the reweighted basket; and a mechanism test that separates processing from measurement precision. The plan's exact-replay and frozen-network apparatus would then be doing what it was designed to do — adjudicating between arithmetic and behaviour with real assignment variation behind it.

**Plausible top-three finance** (*JF*, *JFE*, *RFS* front line). Requires all of the above **plus** a consequence that is not merely relabelled leadership: either (i) an independently timed impairment of the reweighted channel, with valid substitute venues and support at both low and high assigned weight, or (ii) evidence bearing on information *production* rather than the processing of already-public news — which this event design cannot deliver — or (iii) a welfare-relevant object with an explicit model. The plan is right that resilience as currently specified cannot supply (i), and right that welfare is out of reach without further structure.

**Which tier is reachable by the present design, before results?** With the current headline design and no redesign: **specialist, at best, and only after F1 and F3 are resolved in the direction of remedy (a)**. The broader-finance tier is not reachable from the historical HHI gradient, because the identification problem it faces is not one that better robustness can fix. With R1 adopted now, before the data build, the broader-finance tier is genuinely reachable, and the top tier becomes a question about whether the consequence side lands.

---

## 12. Bottom line

**What evidence would distinguish a real change in how the market incorporates common information from a larger arithmetic role for the same stocks?**

Not a leave-signal-out target, not a weight-invariant score, and not a matched non-giant comparison — those defeat the *weight* channel, which was never the binding contaminant. The binding contaminant is that the giants' prices became **better measurements of the common shock**, through their loadings and their quote quality, and every statistic in the plan is increasing in that. The evidence that would actually distinguish the two is comparative in a dimension the plan does not currently use:

> **The same stock, the same news, the same clock, and the same quote process, with only its arithmetic weight in one traded basket reassigned by a published rule — and a change in its predictive content for the part of that basket it is not in, relative to its unchanged predictive content for a basket whose weights were not reassigned.**

Arithmetic predicts a change in the stock's contribution to the reweighted basket's own return and no change in its content for that basket's remainder. Transmission predicts both. Precision is differenced out because the signal is the same stock on both sides. That comparison exists, repeatedly, in the quarterly capping rules of the Select Sector and Nasdaq-100 families — which the plan encountered as a single anticipated episode in July 2023 and set aside.

**And what would establish that the change matters beyond relabeling the price-discovery leader?**

Three things, in this order, and only in this order. First, that adjustment **outside** the reweighted names changes — measured on an equal-issuer basis under a fixed quote-age cap, so that breadth is not quote freshness in disguise. Second, that disagreement among independent claims on the same basket changes, after the announcement's own effect on carry has been removed rather than demeaned away. Third — and this is the one that would make the paper matter rather than merely count — that the change is **reversible in the assigned direction**: when the rule reallocates weight *away* from a name, its channel contribution falls by a comparable amount. A leadership relabeling has no reason to be symmetric under reversal. A real change in the architecture of information transmission does.

Until that reversibility test is on the table, a positive finding in the design as written would be indistinguishable from the statement that the largest companies' prices are now measured better than everyone else's — which is true, already known, and not the paper.

---

### Reviewer's summary of the four things to do next

1. **Run Gate 0 this week.** It is free, it is decisive, and everything else is contingent on it.
2. **Compute the precision ratio `B_G'Ω_G⁻¹B_G / B_M'Ω_M⁻¹B_M` against concentration.** If it trends, F1 is confirmed and the headline statistic must be rebuilt before any data is bought.
3. **Re-derive §3.2 with `A(C)` endogenous** using the plan's own §7.1 result. The current comparative statics do not distinguish H2 from H4.
4. **Audit the capping rules as a treatment mechanism** — count binding quarters, assigned |Δw| distributions, and threshold crossings across the eleven Select Sector families and the Nasdaq-100 — before concluding that repeated rule-driven reweighting is unavailable.

---

*Prepared as an independent referee report. Literature verification in this session was limited to a web search index; no publisher page, repository page, or full text was retrievable (Section 0). All internal-consistency findings derive from the reviewed plan's own text and equations.*
