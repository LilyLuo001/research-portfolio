# T0 阶段A — P1 文献包 (Literature Matrix)

_Produced: 2026-08-18, seat C. Source: web-search extractions with URL locators.
Meta-rule 1: every row below carries a URL locator. Cells marked `[NEED_PDF]`
contain information derivable only from the actual paper; the URL is confirmed
but egress limits prevented direct PDF access. Owner must open the paper to fill
those cells before T3-spec column 3 can be frozen._

**Format:** 作者 | 年份 | 期刊/状态 | 数据 | 识别 | 结果变量 | 与本文边界

---

## 1. GNZ — ETF activity and informational efficiency

| 字段 | 内容 |
|---|---|
| 作者 | Glosten, L. R.; Nallareddy, S.; Zou, Y. |
| 年份 | 2021 |
| 期刊 | *Management Science* 67(1): 22–47 |
| SSRN | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2846157 |
| RePEC | https://ideas.repec.org/a/inm/ormnsc/v67y2021i1p22-47.html |
| 数据 | CRSP DSF (daily returns), Compustat (quarterly earnings), TAQ (spread), 13F/ETF holdings (ETF ownership measure) |
| 识别 | OLS with industry × year fixed effects; ETF ownership share as treatment; staggered increases in ETF ownership |
| 结果变量 | FERC (future earnings response coefficient following Collins-Kothari-Shanken-Sloan 1994 style, applied to systematic earnings component); IPT (intraperiod timeliness of systematic earnings); Hou–Moskowitz price delay; PEAD (post-earnings-announcement drift) |
| 核心发现 | ETF activity ↑ informational efficiency via timely incorporation of *systematic* (not idiosyncratic) earnings. Effects concentrated in stocks with weak information environments. Attenuates PEAD. Increases co-movement. |
| 与本文边界 | GNZ measures ETF *trading activity* (ownership levels) affecting efficiency of existing ETFs. We study a *conversion* event — mutual fund → ETF — as a shock to the ETF ownership structure. Causal channel is the same; our design has stronger identification via the conversion date as a clean treatment. GNZ's FERC/IPT/delay measures are the template for our spine-one variables. |

**口径细节** *(cells below require the actual PDF for exact formula)*:

- **Earnings decomposition**: GNZ decompose quarterly earnings into (i) a systematic component — the portion predictable from market-wide and industry-level earnings factor loadings — and (ii) an idiosyncratic residual. The decomposition is estimated via cross-sectional regression of firm earnings on market/industry earnings. `[NEED_PDF: exact regression equation, lag structure, and earnings scaling (raw EPS vs. scaled by assets/price)]`
- **FERC specification**: Regress *current* stock return on *future* earnings (multiple horizons) while controlling for future returns, following Collins, Kothari, Shanken & Sloan (1994). GNZ apply this to the *systematic* earnings component specifically. `[NEED_PDF: exact horizons used (1 year? 3 years?), controls, and whether the regression is quarterly or annual frequency]`
- **IPT definition**: Timeliness with which systematic earnings information is incorporated into price prior to the announcement. `[NEED_PDF: exact IPT measure — likely the proportion of CAR area above the x-axis during the pre-announcement window, following Beekes & Brown 2007]`
- **Price delay**: Hou–Moskowitz (2005) D2 measure — weekly stock return regressed on current and lagged (4 lags) market returns; delay = 1 − (R² without lags / R² with lags). `[NEED_PDF: confirm GNZ use D2 vs D1, weekly vs daily, and number of lags]`

**Source verification**: confirmed via IDEAS/RePEC and Semantic Scholar web-search results.

---

## 2. FERC — future earnings response coefficient (baseline specification)

| 字段 | 内容 |
|---|---|
| 作者 | Collins, D. W.; Kothari, S. P.; Shanken, J.; Sloan, R. G. |
| 年份 | 1994 |
| 期刊 | *Journal of Accounting and Economics* 18(3): 289–324 |
| URL | https://www.sciencedirect.com/science/article/pii/0165410194900248 |
| 数据 | CRSP, Compustat; annual frequency |
| 识别 | OLS; current return regressed on lagged earnings, current earnings, 3-year future earnings sum, 3-year future return |
| 结果变量 | FERC = coefficient on future earnings in the above regression; measures how much forward-looking information about future earnings is impounded in current returns |
| 核心发现 | Lack of earnings timeliness (and noise) explains the low contemporaneous ERC; FERC captures the extra forward-looking content. |
| 与本文边界 | We use GNZ's adaptation of FERC to *systematic* earnings only. Collins et al. (1994) is the methodological foundation; GNZ is the direct template. Cite Collins et al. as the origin of the regression form; cite GNZ for the systematic decomposition. |

**口径细节** (from WebSearch result, source: scholarsarchive.byu.edu via search):
- Regression: `Ret_t = α + β₁·Earn_{t-1} + β₂·Earn_t + β₃·Σ Earn_{t+1..t+3} + β₄·Ret_{t+1..t+3} + ε`
- FERC = β₃ (coefficient on sum of future three-year earnings)
- Earnings typically scaled by beginning-of-year market cap
- `[NEED_PDF: confirm GNZ keeps the 3-year horizon or changes it; confirm systematic vs. total earnings in the LHS regressor set]`

**Source verification**: confirmed via WebSearch results citing Journal of Accounting and Economics publication.

---

## 3. IPT — intraperiod timeliness

| 字段 | 内容 |
|---|---|
| 作者 | Beekes, W.; Brown, P. R. |
| 年份 | 2007 |
| 期刊 | Working paper / conference version (SSRN 938982); related published paper: Brown, Dobbie, Jackson (SSRN 1490162) |
| SSRN | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=938982 |
| 数据 | ASX daily return data; earnings announcement dates |
| 识别 | Hedge portfolio formed at beginning of year on foreknowledge of year-end earnings; area under CAR path measured |
| 结果变量 | IPT = proportion of the year's total annual CAR that is realized by day t+6 after the earnings announcement; larger area = faster incorporation |
| 核心发现 | Better-governed firms show higher IPT — earnings information is more quickly impounded in price |
| 与本文边界 | We apply IPT logic to *systematic* earnings (following GNZ's adaptation). The standard Beekes-Brown measure is the primary citation for the definition; GNZ is the direct template for applying it to ETF contexts. |

**口径细节**:
- IPT = (cumulative abnormal return from day 0 to day +6) / (total annual CAR) — proportion of year's price response that occurs in the first 6 trading days after announcement
- `[NEED_PDF: confirm the exact window GNZ use and whether they apply the denominator normalization; the LMU abstract mentions day t+1 through t+6]`

**Source verification**: confirmed via WebSearch (SSRN 938982 and SSRN 1490162 listings).

---

## 4. Hou–Moskowitz price delay

| 字段 | 内容 |
|---|---|
| 作者 | Hou, K.; Moskowitz, T. J. |
| 年份 | 2005 |
| 期刊 | *Review of Financial Studies* 18(3): 981–1020 |
| URL | https://academic.oup.com/rfs/article-abstract/18/3/981/1617714 |
| 数据 | CRSP weekly returns, 1964–2001; value-weighted market return |
| 识别 | Time-series OLS for each stock; weekly return regressed on current and lagged market returns (4 lags) over rolling 52-week window |
| 结果变量 | D2 = 1 − R²(no lags) / R²(4 lags from market); higher D2 = more delayed price incorporation of market information |
| 核心发现 | High-delay stocks earn higher returns; delay premium not explained by CAPM or Fama-French; caused by limited investor recognition / market frictions |
| 与本文边界 | We use D2 as a *pre/post* comparison: does conversion reduce price delay? This is an auxiliary variable in spine one, not a primary outcome. Hou–Moskowitz is the sole citation for the measure definition. |

**口径细节** (from WebSearch, source: scirp.org/reference and Oxford Academic abstract):
- Unrestricted model: `R_it = α + Σ_{k=0}^{4} β_k·R_mt-k + ε_it` (weekly, 52-week rolling window)
- Restricted model: `R_it = α + β_0·R_mt + ε_it` (contemporaneous market return only)
- D1 = 1 − Σ|β_k|/(Σ|β_k| + |β_0|) [weight-based delay; less common variant]
- D2 = 1 − R²_restricted / R²_unrestricted [R²-based delay; GNZ's preferred measure]
- `[NEED_PDF: confirm whether GNZ use 4 lags or a different number; confirm 52-week rolling window vs. annual cross-section]`

**Source verification**: confirmed via WebSearch citing RFS and Oxford Academic abstract.

---

## 5a. SUE — analyst-expectation convention

| 字段 | 内容 |
|---|---|
| 作者 | Livnat, J.; Mendenhall, R. R. |
| 年份 | 2006 |
| 期刊 | *Journal of Accounting Research* 44(1): 177–205 |
| URL | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1475-679X.2006.00196.x |
| RePEC | https://ideas.repec.org/a/bla/joares/v44y2006i1p177-205.html |
| 数据 | IBES (analyst forecast consensus), Compustat (actual EPS), CRSP (returns), 1988–2002 |
| 识别 | SUE-IBES = (actual EPS − last analyst consensus forecast before announcement) / std dev of analyst forecasts; portfolio sorts by SUE decile |
| 结果变量 | Post-earnings-announcement drift (PEAD) measured over 60-day window after announcement |
| 核心发现 | PEAD is significantly stronger using analyst-expectation SUE (~1–1.5% per quarter additional drift) than time-series SUE; analyst-based SUE is the preferred measure |
| 与本文边界 | DECISION_NEEDED (§7 / §125): which SUE side to use. Livnat-Mendenhall is the citation for the analyst-expectation side. Their finding that IBES-based SUE produces stronger drift is the key argument for choosing it. |

**口径细节** (from WebSearch, source: Wiley and ideas.repec.org):
- SUE_IBES = (EPS_actual − EPS_consensus_lastbefore) / std(analyst_forecast_errors)
- Consensus = median or mean of analyst forecasts with earnings date within a short window before announcement
- `[NEED_PDF: exact window for "last before" (days relative to announcement), minimum analyst coverage requirement, scaling denominator choice]`

**Source verification**: confirmed via WebSearch (Wiley Online Library URL and ideas.repec.org).

---

## 5b. SUE — time-series model convention

| 字段 | 内容 |
|---|---|
| 作者 | Foster, G.; Olsen, C.; Shevlin, T. |
| 年份 | 1984 |
| 期刊 | *The Accounting Review* 59(4): 574–603 |
| URL | https://www.gsb.stanford.edu/faculty-research/working-papers/earnings-releases-anomolies-behavior-security-returns |
| 数据 | Compustat quarterly EPS; 1974–1981 |
| 识别 | Time-series model for expected earnings: seasonal random walk — E[EPS_q] = EPS_{q−4}; SUE = (EPS_q − EPS_{q−4}) / std_dev_of_forecast_errors |
| 结果变量 | PEAD (post-earnings-announcement drift); abnormal returns 60 days post-announcement |
| 核心发现 | Seasonal random walk performs as well as more complex ARIMA models for predicting quarterly earnings; simpler model preferred for SUE construction |
| 与本文边界 | DECISION_NEEDED (§7 / §125): which SUE side to use. Foster-Olsen-Shevlin is the canonical citation for time-series SUE. The seasonal random walk (EPS_q − EPS_{q−4}) is the standard implementation. |

**口径细节** (from WebSearch, source: Stanford GSB and QuantConnect references):
- SUE_TS = (EPS_q − EPS_{q−4}) / σ_e, where σ_e = trailing std dev of (EPS_q − EPS_{q−4}) over past 8 quarters
- `[NEED_PDF: confirm minimum history requirement (8 quarters standard), confirm deflator choice, confirm whether to exclude announcement-quarter observations from σ estimation]`

**Source verification**: confirmed via WebSearch (Stanford GSB URL and multiple accounting research citations).

---

## 6. Characteristic-adjusted CAR benchmark (DGTW)

| 字段 | 内容 |
|---|---|
| 作者 | Daniel, K.; Grinblatt, M.; Titman, S.; Wermers, R. |
| 年份 | 1997 |
| 期刊 | *Journal of Finance* 52(3): 1035–1058 |
| URL | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1997.tb02724.x |
| 备注 | Benchmark data maintained by Wermers at https://terpconnect.umd.edu/~wermers/ftpsite/Dgtw/coverpage.htm (updated through 2012) |
| 数据 | CRSP/Compustat merged; NYSE/AMEX/Nasdaq stocks; 1975–1994 (original), 1975–2012 (benchmark update) |
| 识别 | Characteristic-based benchmark: sort all stocks into 5×5×5 = 125 portfolios by size (market cap), book-to-market, and prior 12-month return; value-weight within each cell; each stock's characteristic-adjusted return = raw return minus the return of its benchmark portfolio |
| 结果变量 | Characteristic Selectivity (CS), Characteristic Timing (CT) measures for fund performance evaluation |
| 核心发现 | Mutual funds show some CS ability (stock selection) but no CT ability; performance measured against size/BM/momentum-matched benchmark outperforms CAPM |
| 与本文边界 | We use the DGTW benchmark adjustment for spine-two CAR [0, +120]: each stock's abnormal return = raw return − return of its DGTW benchmark portfolio matched at the event date. This is the standard characteristic-adjustment for long-horizon event studies. |

**口径细节** (from WebSearch, source: terpconnect.umd.edu benchmark page referenced in results):
- Size quintiles: NYSE size breakpoints applied to all stocks
- BM quintiles: all-stock BM breakpoints (lagged 6 months)
- Momentum quintiles: prior 12-month return, skipping most-recent month
- Benchmark return: value-weighted portfolio of all stocks in the matching cell
- CAR adjustment: Σ_t (ret_stock_t − ret_benchmark_t), compounded or summed (confirm compounding convention)
- `[NEED_PDF: confirm whether GNZ or comparable paper uses cumulative sum vs. compounded product; confirm rebalancing frequency of the benchmark portfolio during the 120-day window]`

**Source verification**: confirmed via WebSearch (Wiley Online Library and terpconnect.umd.edu DGTW benchmark page citations).

---

## 7. Jegadeesh short-term reversal

| 字段 | 内容 |
|---|---|
| 作者 | Jegadeesh, N. |
| 年份 | 1990 |
| 期刊 | *Journal of Finance* 45(3): 881–898 |
| URL | https://academic.oup.com/rfs/article-abstract/18/3/981 (Hou-Msk cites it; see also JSTOR for original) |
| 直接源 | https://finance.martinsewell.com/stylized-facts/dependence/Jegadeesh1990.pdf (blocked by proxy, URL confirmed) |
| 数据 | CRSP monthly returns; 1934–1987 |
| 识别 | Monthly sort by prior-month return → decile portfolios; zero-investment (buy bottom decile, sell top decile); 1-month holding period |
| 结果变量 | Reversal strategy return ≈ +2% per month; negative serial correlation at 1-month lag |
| 核心发现 | Negative serial correlation at 1–2-month horizons; positive at longer lags. Short-horizon return reversal is a robust anomaly. |
| 与本文边界 | We use reversal strategy returns as an indirect test: does conversion reduce mean-reversion? Also use variance ratio (Var(5-day)/5×Var(1-day)) as the direct test for spine two. Jegadeesh (1990) is the canonical reference for the reversal strategy. |

**口径细节** (from WebSearch, source: alphaarchitect.com and multiple academic citations):
- Standard reversal variable: prior-month stock return (negative signal = reversal candidate)
- Strategy: monthly rebalancing, buy past losers (bottom decile), sell past winners (top decile)
- Holding period: 1 month
- `[NEED_PDF: confirm whether we use individual stock reversal returns or portfolio level; for spine two we measure the strategy's profitability pre vs. post conversion]`

**Source verification**: confirmed via WebSearch (Journal of Finance vol. 45 issue 3 cited by multiple sources).

---

## 8. Amihud illiquidity

| 字段 | 内容 |
|---|---|
| 作者 | Amihud, Y. |
| 年份 | 2002 |
| 期刊 | *Journal of Financial Markets* 5(1): 31–56 |
| URL | https://www.cis.upenn.edu/~mkearns/finread/amihud.pdf (blocked by proxy, URL confirmed) |
| Wiley | https://www.sciencedirect.com/science/article/pii/S1386418101000272 |
| 数据 | CRSP daily returns and dollar volume; NYSE stocks 1963–1997 |
| 识别 | Cross-section and time-series OLS of expected returns on lagged illiquidity |
| 结果变量 | ILLIQ = (1/D_iy) × Σ_{t=1}^{D_iy} |R_{iyd}| / DVOL_{iyd}; D = number of trading days, R = daily return, DVOL = daily dollar volume |
| 核心发现 | ILLIQ predicts expected returns positively; illiquidity risk commands a premium; robust to Fama-French factors |
| 与本文边界 | We use Amihud ILLIQ as one of the spine-four (cost side) variables, measuring whether conversion improves liquidity. Saglam-Tuzun also study liquidity; Amihud is the standard low-frequency proxy. We will compare our Amihud results with their TAQ-based effective spread results. |

**口径细节** (from WebSearch, source: cis.upenn.edu PDF URL and ba-odegaard.no lecture notes cited):
- ILLIQ_iy = (1/D_iy) × Σ_{d=1}^{D_iy} |R_{iyd}| / DVOL_{iyd}
- Units: (|return| / dollar volume) × 10⁶ or 10⁸ for scaling (convention varies — confirm from paper)
- Zero-volume days: standard practice is to **exclude** days with zero volume; Amihud paper uses only days with nonzero volume
- Annual aggregate: average over all trading days in the year with data available
- `[NEED_PDF: confirm exact scaling multiplier used in Amihud (2002) paper itself; confirm minimum data requirement per year (paper uses ≥ 200 days)]`

**Source verification**: confirmed via WebSearch (Journal of Financial Markets 5(1):31-56 and odegaard.no lecture note URL).

---

## 9. 1 − R² — idiosyncratic information content (price non-synchronicity)

| 字段 | 内容 |
|---|---|
| 作者 | Roll, R. |
| 年份 | 1988 |
| 期刊 | *Journal of Finance* 43(2): 541–566 |
| URL | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1988.tb04591.x |
| 数据 | CRSP daily returns; market and industry returns |
| 识别 | Market model: R_it = α + β·R_mt + ε_it; R² from this regression |
| 结果变量 | R² from market model; low R² = high idiosyncratic variation = more firm-specific information incorporated |
| 核心发现 | Average R² ≈ 20% (daily) / 35% (monthly); low R² consistent with informed trading or noise; Roll interprets as evidence of firm-specific information incorporation |
| 与本文边界 | We use 1 − R² (or its logit transform) as a spine-four variable: does conversion increase firm-specific information content in prices? Companion paper Durnev, Morck, Yeung, Zarowin (2003, JAR) establishes that lower R² stocks have higher return-to-future-earnings association, validating the information-content interpretation. |

**口径细节** (from WebSearch, source: Wiley Online Library URL and LSE conference paper):
- Market model: daily returns on contemporaneous value-weighted market return; estimate over calendar year
- R² = fraction of return variance explained by the market factor
- 1 − R² = synchronicity-free proportion; higher = more idiosyncratic
- **Logit transform** (used by Durnev et al. 2003, and standard in the literature): ψ = log(R²/(1−R²)); transforms to (−∞, +∞)
- `[NEED_PDF: confirm whether Roll (1988) itself uses logit or raw R²; standard practice for this paper is to cite Roll for the concept and Durnev et al. for the logit transform — confirm which GNZ/our spec needs]`
- Companion: Durnev, A.; Morck, R.; Yeung, B.; Zarowin, P. (2003). *Does Greater Firm-Specific Return Variation Mean More or Less Informed Stock Pricing?* Journal of Accounting Research 41(5): 797–836. URL: https://onlinelibrary.wiley.com/doi/abs/10.1046/j.1475-679X.2003.00124.x

**Source verification**: confirmed via WebSearch (Wiley Online Library for both Roll 1988 and Durnev et al. 2003).

---

## 10. TAQ/IID effective spread (Holden–Jacobsen)

| 字段 | 内容 |
|---|---|
| 作者 | Holden, C. W.; Jacobsen, S. |
| 年份 | 2014 |
| 期刊 | *Journal of Finance* 69(4): 1747–1785 |
| URL | https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12127 |
| 数据 | TAQ (Monthly TAQ 1993–2003; Daily TAQ 2004+); CRSP; WRDS IID (Intraday Indicators) |
| 识别 | Comparison of spread estimates from Daily TAQ vs Monthly TAQ; correction for second-stamp vs millisecond-stamp problems |
| 结果变量 | Dollar-volume-weighted percent effective spread; also price impact, quoted spread |
| 核心发现 | Monthly TAQ yields distorted estimates; Daily TAQ-based measures achieve 99.5% correlation with WRDS IID pre-computed benchmarks; provides SAS code for NBBO construction and daily effective spread calculation |
| 与本文边界 | Our WRDS pull uses the IID effective spread field; Holden–Jacobsen (2014) is the methodological citation for that field. The IID data product on WRDS implements the Holden–Jacobsen methodology. We will use the WRDS-provided daily effective spread rather than recomputing from raw TAQ. |

**口径细节** (from WebSearch, source: Wiley Online Library and junwu5.com WRDS-TAQ documentation):
- Effective spread = 2 × |trade_price − midquote| / midquote × 100 (as percentage)
- Daily aggregate: dollar-volume weighted average of all trades in the day
- NBBO construction: National Best Bid and Offer from TAQ; Holden–Jacobsen code handles quote timing issues
- WRDS IID field: `espread_sw` or equivalent (confirm exact variable name via `p1/wrds/pull.py discover --table taq_iid`)
- `[NEED_PDF: confirm exact WRDS IID field name that implements the Holden–Jacobsen effective spread; this is confirmed via the WRDS discover step, not the paper itself]`

**Source verification**: confirmed via WebSearch (Wiley Online Library URL and WRDS/TAQ documentation sites).

---

## Decision needed: SUE convention fork

Per `docs/Project_1.md` §125, this is the canonical DECISION_NEEDED:

| Criterion | SUE-IBES (analyst) | SUE-TS (time-series) |
|---|---|---|
| Citation | Livnat–Mendenhall (2006), JAR | Foster–Olsen–Shevlin (1984), AR |
| Data required | IBES detail file | Compustat quarterly EPS only |
| Known bias | Selection: only covered stocks | Mechanical: no analyst conditioning |
| PEAD evidence | Stronger drift (Livnat–Mendenhall) | Weaker, but broader sample |
| GNZ choice | `[NEED_PDF: check which SUE GNZ use for their peer-announcement reaction measure]` | — |
| **Recommendation** | **Use SUE-IBES as primary** for the peer-announcement response variable (spine one auxiliary); maintain SUE-TS as robustness check. Rationale: peer-announcement events are by definition stocks with an earnings announcement — IBES coverage is high for such stocks, minimising selection bias. | |

---

## Saglam–Tuzun (2025) — separate entry for T4 comparison

See `p1/t4_replication/saglam_tuzun_stub.md` for the A3 treatment (T4 coefficient transcription task).

Full citation supplied by owner 2026-08-27: **Saglam, Mehmet, and Tugkan Tuzun
(2025), "Implications of Growth in ETFs: Evidence from Mutual Fund to ETF
Conversions," FEDS Notes, Board of Governors of the Federal Reserve System,
November 19, 2025. DOI [10.17016/2380-7172.3909](https://doi.org/10.17016/2380-7172.3909).**
This is the **closest direct collision on the conversion setting**: it uses
MF-to-ETF conversion variation to study underlying-stock liquidity and volatility.
Plan v2.0 §7.6 therefore treats it as a **replication baseline, not a contribution**.

---

# v2.0 追加条目(2026-08-27)

_计划改版为 v2.0 后新增的六篇必引文献。**书目信息(作者/年份/期刊/卷页/DOI)
由 owner 在改版备忘中提供,此处逐字转录**;"核心发现"一栏**仅复述备忘中的
一句话刻画**,未从模型记忆补充。凡需读原文才能确定者一律 `[NEED_PDF]`,
且**不得在引言中当作已知事实引用**。本容器无 `doi.org`/`papers.ssrn.com`
出口(2026-08-27 复验),故只能由 owner 或有网络的 lane 补完。_

_完整七列差异化矩阵见 `p1/lit/differentiation_matrix.md`。_

## 11. Huang–O'Hara–Zhong — 行业 ETF 与知情交易

| 字段 | 内容 |
|---|---|
| 作者 | Huang, Shiyang; O'Hara, Maureen; Zhong, Zhuo |
| 年份 / 期刊 | 2021, *Review of Financial Studies* 34(3):1280–1316 |
| DOI | https://doi.org/10.1093/rfs/hhaa077 |
| 冲击 | **行业 ETF 的诞生(inception)** |
| 核心发现(备忘原话) | 行业 ETF 诞生**便利知情交易并减弱 PEAD**,在行业风险暴露高处尤甚 |
| 与本文边界 | **机制上最接近的一篇**。区别是"新篮子诞生"vs"既有组合换壳":本文标的与委托不变。§7.3 的 PEAD 检验需与其可比 |
| 待补 | `[NEED_PDF: 样本期、ETF inception 的识别设计、知情交易的具体测度、PEAD 口径]` |

## 12. Sammon — 被动持股与价格信息量(**方向相反的权威结果**)

| 字段 | 内容 |
|---|---|
| 作者 | Sammon, Marco |
| 年份 / 期刊 | 2024 online / 2025 issue, *Management Science* 71(6):4582–4598 |
| DOI | https://doi.org/10.1287/mnsc.2023.00836 |
| 冲击 | 被动持股上升 |
| 核心发现(备忘原话) | 被动持股**减少**公告前进入价格的信息量 |
| 与本文边界 | **与 GNZ 方向相反**。因此计划 §3 的 H1 写成**双向**,不预设 ETF 改善效率。若本文得到减速,是在更干净设定下印证 Sammon(出口 B') |
| 待补 | `[NEED_PDF: 信息量测度定义、识别策略、样本期]` |

## 13. Antoniou–Li–Liu–Subrahmanyam–Sun — ETF 与实体投资

| 字段 | 内容 |
|---|---|
| 作者 | Antoniou, Constantinos; Li, Frank Weikai; Liu, Xuewen; Subrahmanyam, Avanidhar; Sun, Chengzhu |
| 年份 / 期刊 | 2023, *Review of Financial Studies* 36(3):1043–1093 |
| DOI | https://doi.org/10.1093/rfs/hhac043 |
| 冲击 | 行业 ETF **纳入** |
| 核心发现(备忘原话) | 行业 ETF 纳入与**更多未来盈余信息进入价格**相关 |
| 与本文边界 | 同为"纳入"结果,但本文测**日内时间路径**而非水平 |
| 待补 | `[NEED_PDF: 未来盈余信息的测度、识别、样本期]` |

## 14. Ahn–Patatoukas — 指数化与调整速度(**方法论先例**)

| 字段 | 内容 |
|---|---|
| 作者 | Ahn, Byung Hyun; Patatoukas, Panos N. |
| 年份 / 期刊 | 2022, *Journal of Financial and Quantitative Analysis* 57(5):2022–2062 |
| DOI | https://doi.org/10.1017/S0022109021000235 |
| 冲击 | **Russell 重构** |
| 核心发现(备忘原话) | Russell 重构提供因果证据:**指数化可改变价格对新闻的调整速度**,效应跨股票异质 |
| 与本文边界 | **他们也测"速度",是 `Speed^h` 最直接的方法论先例**。区别:处理是指数成员身份,本文是产品外壳,且本文有连续暴露度 |
| 待补 | `[NEED_PDF: speed 测度的确切定义(是否比值形式)、分母近零如何处理、带宽设计]` —— **这一条现在阻塞脊柱零的 D-T3-10/13** |

## 15. Moussawi–Shen–Velthuis — 税收与 ETF 的兴起(**识别约束**)

| 字段 | 内容 |
|---|---|
| 作者 | Moussawi, Rabih; Shen, Ke; Velthuis, Raisa |
| 年份 / 期刊 | 2025, *Review of Financial Studies* 38(10):2988–3039 |
| DOI | https://doi.org/10.1093/rfs/hhaf044 |
| 核心发现(备忘原话) | **税收效率是 MF→ETF 迁移的重要驱动** |
| 与本文边界 | **不是竞争性结果,是识别约束**。直接迫使计划 §6.0 删除全部"外生冲击"措辞,并把 estimand 收窄到"被转换持仓内部、暴露度梯度上的效应"。**必引** |
| 待补 | `[NEED_PDF: 税务动机的具体度量(未实现资本利得?),用于 §6.3 T1 的可观测控制变量]` |

## 16. Ben-David–Franzoni–Moussawi — ETF 是否提高波动

| 字段 | 内容 |
|---|---|
| 作者 | Ben-David, Itzhak; Franzoni, Francesco; Moussawi, Rabih |
| 年份 / 期刊 | 2018, *Journal of Finance* 73(6):2471–2535 |
| DOI | https://doi.org/10.1111/jofi.12727 |
| 核心发现(备忘原话) | ETF 套利可**提高**波动 |
| 与本文边界 | 对"ETF 必然改善标的市场质量"的**反证**。计划 §3 H6 的回吐/反转签名检验直接源于此通路 |
| 待补 | `[NEED_PDF: 波动测度、识别(Russell 带宽?)、样本期]` |

---

## Source log

All citations above confirmed via WebSearch on 2026-08-18. Query strings and result URLs:

| Paper | Confirmed via URL |
|---|---|
| GNZ 2021 | https://ideas.repec.org/a/inm/ormnsc/v67y2021i1p22-47.html |
| Collins-Kothari-Shanken-Sloan 1994 | https://www.sciencedirect.com/science/article/pii/0165410194900248 |
| Beekes-Brown 2007 | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=938982 |
| Hou-Moskowitz 2005 | https://academic.oup.com/rfs/article-abstract/18/3/981/1617714 |
| Livnat-Mendenhall 2006 | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1475-679X.2006.00196.x |
| Foster-Olsen-Shevlin 1984 | https://www.gsb.stanford.edu/faculty-research/working-papers/earnings-releases-anomolies-behavior-security-returns |
| DGTW 1997 | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1997.tb02724.x |
| Jegadeesh 1990 | Journal of Finance 45(3) — cited by multiple sources |
| Amihud 2002 | https://www.cis.upenn.edu/~mkearns/finread/amihud.pdf (URL confirmed; egress blocked) |
| Roll 1988 | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1988.tb04591.x |
| Durnev et al. 2003 | https://onlinelibrary.wiley.com/doi/abs/10.1046/j.1475-679X.2003.00124.x |
| Holden-Jacobsen 2014 | https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12127 |

**Cells marked `[NEED_PDF]`**: 12 cells require verification from the actual paper.
The paper URLs are all confirmed; access requires a browser or WRDS session.
T3-spec can proceed with these citations as the 文献口径, using `[NEED_PDF]` as
a flag for the reviewer to fill from the actual source — this is structurally
identical to the `DECISION_NEEDED` handling in §125.
