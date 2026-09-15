# P1 feasibility audit

**Run:** 20260913  
**Outcome boundary:** enforced. No actual or uncertain post-conversion earnings-response outcome, coefficient or curve was opened or estimated.

## 1. Runtime, repository and provenance

The installed CLI is `codex-cli 0.143.0` at `/opt/homebrew/bin/codex`. `codex features list` reports native `multi_agent` as stable and enabled. The local CLI model catalogue exposed by `codex debug models` contains `gpt-5.5` and `gpt-5.3-codex-spark`, whereas the desktop collaboration runtime exposed and successfully routed `gpt-5.6-luna`, `gpt-5.6-terra` and `gpt-6-astra`. This discrepancy is recorded rather than treating the CLI catalogue as the desktop runtime. The coordinator's configured default is `gpt-6-astra`/medium, but its actual backend model and token usage are `NOT_OBSERVED`. Authentication and configuration were not changed.

The original checkout `/Users/lilyluo/research-portfolio` began at `35361cc5a8c6360e1d48da9a2aa4fd40458b0e04` on `task/prepurchase-wrds-20260906`, tracking `origin/main` while ahead 16 / behind 116. Its pre-existing untracked `.DS_Store` files and `p1/etf_weight_shape_gates/` were not touched. A fetch-only discovery was performed; there was no merge or push. This adjudication lives in a separate worktree and branch:

- `/Users/lilyluo/research-portfolio-p1-feasibility-20260913`
- `task/p1-feasibility-adjudication-20260913`, based on `35361cc5a8c6360e1d48da9a2aa4fd40458b0e04`

Advanced P1 exposure evidence is read-only in a detached worktree at `cb36417304b282cda5e38ede13d1af872ad9f346`. That snapshot is not an ancestor of the output branch. It is evidence, not silently merged authority. No `AGENTS.md` was found. Optional custom-agent templates were not supplied in the repository or attached document directory, so none were installed. Native subagent routing was used without overwriting configuration.

SCC was not treated as available merely because earlier documents named it. Noninteractive SSH authentication did not succeed in preflight, and no SCC file or job was opened or launched. The feasibility audit therefore follows the prompt's missing-data branch. No password, token, licensed raw row or connection string is reproduced here.

## 2. Source-of-authority map

| Artifact | Provenance class | What it controls / proves | Authority result |
|---|---|---|---|
| Supplied `P1_Feasibility_Codex_Prompt.md` | Current user execution instruction | Scope, sealed outcome, workflow, deliverables and admissible verdicts | `SIGNED` for this audit |
| `docs/基金转换实验_博士研究计划.md` | Current documentary research plan | Stock × earnings-event object; signed `CAR^h` family; tercile priority; equal-wave target; session separation | Highest research-plan authority according to blueprint, but several cited V-decisions lack receipts |
| `p1/t3_spec/变量规格书.md` | Current variable specification / proposal | `CAR^h` primary, `Speed^h` secondary; six horizons; quote midpoint and clock conventions | Documentary constraints; open SUE, data and literature items remain |
| `p1/t5_spec/估计蓝图.md` | Current Channel-A estimator proposal | Stacked design, clean controls, terciles, bootstrap family | It explicitly says the plan prevails (`:31–39`); conflicts and deferred decisions remain |
| `ops/decisions.md:84–104` | Located owner receipt | Historical T0/T2a approval and 0.1 residual-SD ambition | Signed historical decision, not a signed timing contrast or equivalence margin |
| `ops/decisions.md:394–417` | Executed blocker log | Literature package and CRSP/TAQ/IBES outcome inputs were missing | Historical receipt, consistent with current data audit |
| `p1/t2_free/*`, `p1/exposure/*` at `cb36417` | Executed measured artifacts | Event/Gate0 and exposure metadata, lineages and coverage | `MEASURED_NOW` after recomputation; not outcome evidence |
| `p1/viability/audit_viability.py` at `cb36417` | Historical code / scenario | Raw-dose concentration and imposed variance exercise | Method reproduced and rejected as estimator-correct power evidence |
| `p1/strategic_pivot/*` and later ETF-weight-shape work | Proposal / unrelated branch | Alternative projects or endpoints | Not authority for P1; not imported |
| `news_price_discovery/prepurchase_wrds/*` on current branch | Unrelated project | Separate measurement/data-purchase work | Excluded |

The exact fully executable estimand is **not signed**. The most authoritative documentary object is a six-horizon signed stock earnings-response curve after conversion, with dose terciles primary and continuous dose secondary. But the plan's high-versus-low comparison among positive converted holdings conflicts with the blueprint's `D>=0.005` tiers against zero-dose controls. The exposure snapshot uses latest PRE-effective holdings, while the blueprint requires PRE-announcement holdings. The cited V-1/V-2/V-3/V-6 decisions are not present in the located owner log. These are `HOLD_DESIGN`, not formatting issues.

## 3. Measurement and sample support

Recomputation against `cb36417` gives:

| Arm | Positive primary stock-wave cells | Unique stocks | Positive waves | Cells / stocks / waves at ownership >=0.5% |
|---|---:|---:|---:|---:|
| All sponsors | 8,801 | 3,440 | 30 | 583 / 573 / 4 |
| Dimensional only | 3,503 | 2,548 | 2 | 561 / 559 / 2 |
| Excluding Dimensional | 5,638 | 2,979 | 29 | 21 / 21 / 2 |

There are 71 Gate0-PASS events in 47 waves. The exposure rows separately retain raw and split-adjusted shares, ownership exposure, value/market-cap exposure, fund portfolio weight, market denominator, report-date range, effective date and accessions. Positive-ready rows have nonblank PERMNO, wave and adviser; factor and denominator flags pass. Twenty-five of 8,826 aggregated rows lack a positive denominator and are not primary-ready. Candidate-common-equity value coverage is 96.49%; overall N-PORT value coverage is 67.23%. Dimensional accounts for 64.15% of exact-matched PRE position value.

These facts do **not** establish the final treatment variable. The frozen build is PRE-effective, not demonstrably PRE-announcement; it has no completed earliest-anticipation/public-availability audit. Adviser strings are unsigned sponsor proxies. Strategy/manager/fee/clientele continuity is not yet verified. Post holdings can diagnose continuity but cannot define treatment or select the sample on an outcome.

No joined eligible earnings calendar, analyst-level forecast/actual panel, signed SUE, timezone-validated release time, market-session mask, quote midpoint panel, clean control stack, or pre-treatment/untreated response panel was accessible. Therefore support by stock × earnings event × wave × session × horizon, actual residual rank, control reuse after matching, covariance calibration, and empirical basis-point MDE are `NOT_AVAILABLE`. A legal-effective-date count is not an outcome design matrix.

## 4. Identification and estimator audit

The causal object is the conversion **package**. Conversion is selected by tax, distribution and clientele considerations and does not isolate AP arbitrage. Identification requires parallel conversion-absent changes in the **SUE response slope** for the chosen exposure groups, not merely parallel average returns. It also requires a stable or explicitly standardized analyst-coverage/SUE population; conversion-induced forecast coverage or measurement changes otherwise make the interaction condition on a treatment-affected regressor.

Within-fund dose comparisons remove additive fund shocks, but not fund shocks whose stock impact scales with exposure. Existing ETF saturation, overlapping baskets, other conversions, Russell coincidences, peer-information spillovers, and industry/date slope shocks remain. Post-conversion flows, fees, clientele and holdings are channels for a total package effect and must not be controlled away or used as continuity exclusions without redefining the estimand.

The documentary target is an equal average of wave-specific effects. A pooled regression with total row weight `1/(W*n_w)` does not deliver that target: after weighted nuisance residualization, its scalar wave weight is proportional to `A_w = Zr_w'Zr_w`, not `1/W`. Equal-wave effects require separately identified wave coefficients (or equivalent interactions) followed by an explicit equal-weight contrast with shared-stock/event covariance retained. Rank-deficient waves cannot be silently dropped.

Timing is not amplitude. A significant early coefficient or an early-minus-terminal coefficient can respond to a uniformly larger earnings reaction. The proposed design-only restriction uses a transported counterfactual response shape `f_h=b0_h/b0_T` and tests `q_h=beta_h-f_h beta_T` jointly. A pure timing interpretation additionally requires terminal-effect equivalence within a signed economic margin. No such margin is signed, and weak/uncertain `b0_T` invalidates normalization. Consequently detection and equivalence power for the actual scientific claim remain unavailable.

## 5. Historical power correction

`p1/viability/audit_viability.py::design_stats()` defines `x=Exposure/0.005`, weights rows by `1/(waves*cells_in_wave)`, uses `sum(weight*x^2)` without residualizing `SUE×Post×dose` on the declared nuisance/FE design, and imposes variance shares 30%/25%/20%/25% for wave/sponsor/stock/idiosyncratic components. The resulting raw-exposure information ESS and MDEs 1.508/2.334 residual-CAR SD are valid only for that simplified assumed through-origin exercise. They are not estimator-invariant, not empirically calibrated and not evidence that P1 intrinsically lacks power. The associated “1,300 events” rescue claim is likewise not a valid requirement for the authorized estimator.

The new compute artifact reports measured exposure concentration separately, blocks the absent actual design, and confines all synthetic calculations to `ASSUMED_SCENARIO` / `CONDITIONAL` rows. It does not convert conditional power into an empirical verdict.

## 6. Contribution and access deviations

Saglam–Tuzun is the direct conversion-setting predecessor but studies six-month volatility and spreads. GNZ, Huang–O'Hara–Zhong, Sammon, and Bhojraj–Mohanram–Zhang already occupy ETF/passive ownership × earnings efficiency, ERC, PEAD or information-transfer space. Grégoire–Martineau and Christensen–Timmermann–Veliyev make release-time and live-quote precision central. The former also shows why one-sided bid/ask adjustment can move a midpoint, so bid- and ask-side diagnostics are needed to distinguish information incorporation from spread resolution. The latter is a 2025 *JFE* publication (the arXiv posting is later), not a 2026 working paper. Box–Davis–Evans–Lynch warns against assuming ETF price leadership or an AP-only mechanism. The conditional increment is therefore a narrow conversion-package effect on an amplitude-proof own-stock earnings-response timing shape; generic “ETF improves price discovery” is not novel.

Publisher/full-version access was incomplete for several papers and is labeled in `literature_matrix.md`; absence was not inferred from search failure. The audit did not purchase data, alter raw inputs, run Stata/`boottest`, or claim SCC/WRDS integration. No prior blinding log sufficient to certify pristine preregistration was located, so prior blinding status is `UNKNOWN` rather than asserted.
