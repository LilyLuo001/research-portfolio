# Post-V3 research-decision memo — 2026-09-06

**Decision: NOT YET on fund-level construction; NO on a full Gate 0/1 rewrite now.**

V3 is accepted as the completed data-contract checkpoint. It is not reopened by
this memo. All production locks remain in force, all earlier Gate 0/1 results
remain invalid, and Gate 2 remains prohibited. This memo makes a scientific
priority decision only; it authorizes no SCC run, outcome regression, or code
amendment.

## 1. Keep the three workstreams separate

| Workstream | Question | Decision |
|---|---|---|
| Former stock-level conversion design | Does conversion exposure change how held stocks incorporate earnings news? | Not viable as the headline because dose and independent-wave information are inadequate; retain only as a possible secondary mechanism. |
| Active fund-level architecture design | What changes in demand and portfolio implementation when an existing strategy acquires ETF architecture? | Potentially viable only after the contribution and primary estimand below are frozen and shown feasible. |
| ETF basket-routing design | Does the shape of an actual daily creation/redemption basket route pressure across non-announcing stocks? | A distinct, parked project requiring actual baskets and daily primary flow; periodic holdings and V3 do not supply its treatment. |

A correct pooled-portfolio/share-class contract is reusable infrastructure. It
does not make these questions, treatments, or required data interchangeable.

## 2. Novelty verdict

The broad active question is **not sufficiently novel as written**. Two current
working papers occupy much of it. Du, Starks, and Xiaolan study cloned **and
converted** active ETFs. They find reputation and clientele/distribution-channel
effects for clones and report preliminary post-conversion net-flow evidence
([SSRN, revised 2026-04-14](https://doi.org/10.2139/ssrn.4653702)). Chau,
Todorov, and Yegen use converted funds and matched mutual funds to study
flow-performance sensitivity and short-selling discipline, plus greater momentum
exposure after conversion ([BIS Working Paper 1261](https://www.bis.org/publications/working-paper-1261-etfs-disciplinary-device)).
Moussawi, Shen, and Velthuis establish taxes and clientele as drivers of ETF
migration and provide an appendix list of 79 conversions as of 2023
([RFS 2025](https://doi.org/10.1093/rfs/hhaf044)). Saglam and Tuzun document 125
as the industry count through 2024, but their empirical design exploits one
June 11, 2021 wave of four DFA equity-fund conversions to study underlying-stock
liquidity and volatility, directly occupying and substantially weakening the
novelty of that old headline
([Federal Reserve 2025](https://doi.org/10.17016/2380-7172.3909)).

| Closest project | Treatment/sample in inspected version | Occupied outcome/claim | Remaining distinction for P1 |
|---|---|---|---|
| Du–Starks–Xiaolan | Clones plus 70 conversions, 37 active, in the [December 31, 2024 draft posted for AFA 2025](https://www.aeaweb.org/conference/2025/program/paper/KrASeRD8) | Converted-ETF net flow, preliminary post-conversion flow, reputation; clone clientele | P1's proposed transfer reconciliation and same-pool implementation design were not found in this inspected version; reverify the latest full revision. |
| Chau–Todorov–Yegen | 22 converted active funds in the inspected May 2025 BIS version | Flow-performance sensitivity, short selling and greater post-conversion momentum exposure | P1's joint transfer reconciliation and granular pooled-portfolio implementation design were not found in this version; reverify the [2026 SSRN revision](https://doi.org/10.2139/ssrn.5069499). |
| P1 candidate | 156-register starting census; usable pre-treatment-eligible/common-support count unknown | Proposed strategy-boundary capital reconciliation plus secondary implementation outcomes | Novelty remains conditional; no usable sample or causal design has passed. |

P1 therefore must not claim to be the first conversion study, the first
post-conversion flow study, or the first study of strategy changes. A potentially
unoccupied contribution is narrower:

> For a pre-treatment identity-eligible existing strategy, does ETF access generate
> **net capital at the strategy boundary** beyond documented inherited or
> transferred assets, and how does the strategy/portfolio
> alter implementation when that capital arrives?

The contribution would be the audited reconciliation and triangulation, not a
generic positive-flow coefficient. Public fund data generally cannot identify
the investor origin of capital or every family-internal transfer. Each component
must therefore be labelled **observed**, **documented**, or **unidentified
residual**; the residual must not be called external capital or a clientele
effect. The design must distinguish full conversion, ETF cloning, and verified
pro-rata ETF-share-class addition. It is promising, not yet established; a
current full-text claim-by-sample-by-outcome comparison against both direct
working papers must survive before data construction is promoted.

## 3. Proposed estimand and identification boundary

The candidate primary estimand is the effect of acquiring ETF architecture on
**strategy-boundary net capital flow, net of observed and documented transfers**,
during complete post-ETF months for converted strategies whose legal identity,
mandate, benchmark, manager, and announced concurrent changes satisfy rules
frozen before treatment, on announcement-date common support. Inherited
conversion AUM, documented merger
transfers, sponsor seed capital, and documented class transfers are not new boundary
flow; any unresolved remainder stays an unidentified residual. The comparison
group is never-converting and not-yet-**announced** funds in the same calendar
risk set; an announced future converter is no longer untreated.

For conversions, the defensible treatment is the **eligible conversion
package**, not a pure-wrapper effect: fees, distribution, tax treatment,
disclosures, and marketing may change together. A material mandate, manager,
or asset-class change disclosed by the assignment date makes the event a bundled
transformation and excludes it from the clean estimand. A change discovered only
from realized post-event holdings is an outcome/diagnostic, not a retrospective
eligibility exclusion. First public filing/announcement starts assignment and
anticipation; legal effectiveness and first ETF trade are separate implementation
clocks. Portfolio implementation (cash, holdings turnover, concentration,
entries/exits, derivatives, and tax distributions) is a secondary outcome
family, not part of the primary demand estimand.

True ETF-share-class additions form a separate validation estimand. ETF-class
growth may reflect migration from mutual classes; total pooled-strategy demand
is the strategy-boundary outcome. Class accounting shows offsets but identifies
migration only where source documents do. The class and conversion coefficients
must never be pooled. Share-class adoption improves portfolio continuity but
remains selected.

Matching alone cannot remove sponsors' private demand forecasts or selection on
tax overhang, prior outflows, performance, scalable holdings, and distribution
opportunity. A credible design therefore requires pre-announcement flow levels,
slopes and volatility; returns, fees, tax distributions, AUM, age, objective,
family size and holdings characteristics; explicit concurrent-change flags;
common-support and pretrend diagnostics; adviser/wave-level inference; and
leave-one-sponsor-out results. Causal language remains unavailable until those
checks pass.

## 4. Inputs actually needed

The fund-level headline needs: (i) a source-verified conversion/activation
register; (ii) predecessor-successor identities at SEC-series, pooled-portfolio,
share-class, and ETF-security levels; (iii) filing, announcement, vote, last-MF,
effective, and first-trade clocks; (iv) monthly TNA, returns, expenses,
distributions, turnover, objectives and adviser history; (v) transfer/merger,
seed, fee, mandate, benchmark, name and manager-change flags; and (vi) periodic
holdings for post-treatment continuity diagnostics and secondary implementation
outcomes. ETF shares outstanding could support an uptake measure only after
source/schema/coverage validation and reconciliation for splits, NAV, and class
migration; it is not the primary flow measure.

Investor-information timestamps are required for announcements/filings and any
predictor claimed known before treatment. Correct historical economic dates are
sufficient for retrospective monthly TNA/flow and holdings outcomes. The missing
exact TNA publication timestamp bars point-in-time TNA-scaled exposure claims;
it does not bar correctly dated retrospective fund outcomes. TAQ and actual
daily baskets are not dependencies for this headline.

## 5. Would the full Gate 0/1 rewrite answer the decisive question?

**No.** It would repair periodic-holdings entity mapping, exact-date TNA scaling,
availability rules, and stock-exposure accounting. Those are useful later for
continuity or a secondary transmission result. It would not establish novelty,
reconcile inherited AUM with strategy-boundary flow, complete event clocks,
classify concurrent changes, solve endogenous adoption, demonstrate donor
support, or provide actual baskets. Rebuilding it now risks producing a correct
answer to a non-decisive question.

## 6. Smallest justified next module—and stop

First finish a bounded full-text claim matrix for Du–Starks–Xiaolan and
Chau–Todorov–Yegen. If the narrower contribution survives, the next proposed
module is an **at-least-20-event `F0_FUND_FLOW_BRIDGE` golden pilot**. Before
selection, freeze strata for sponsor, event year, asset class, pre-event AUM
band, and one-to-one versus many-to-one conversion. It should, without
estimating any post-treatment coefficient:

1. reconcile closing predecessor pooled TNA to opening successor pooled TNA;
2. label inherited assets, mergers, seed capital, and documented
   within-class/family moves, leaving all other sources unidentified;
3. verify all clocks and pre-treatment identity/announced-change eligibility,
   retaining realized post-holdings continuity only as a diagnostic; and
4. construct announcement-date donor risk sets and report coverage, common
   support, balance, and pre-event flow paths.

Its definitions and pass/fail criteria must be frozen in a **separate fund-flow
machine contract** before execution, with its own golden sample and pilot. This
does not amend or relax the V3 ETF weight-shape contract. No full Gate 0/1
rewrite should begin unless F0 demonstrates that the primary outcome and
counterfactual both exist.

## Bounded ten-journal search ledger

Search frozen 2026-09-06: AER—[Poterba–Shoven (2002)](https://doi.org/10.1257/000282802320191732),
tax architecture; QJE—[Hortaçsu–Syverson (2004)](https://doi.org/10.1162/0033553041382184),
homogeneous-fund differentiation; JPE—[Berk–Green (2004)](https://doi.org/10.1086/424739),
flow-performance theory; Econometrica—no qualifying direct hit;
REStud—[Egan–MacKay–Yang (2022)](https://doi.org/10.1093/restud/rdab086),
index-fund demand; JF—[Ben-David–Franzoni–Moussawi (2018)](https://doi.org/10.1111/jofi.12727),
underlying-stock effects; JFE—[Dannhauser (2017)](https://doi.org/10.1016/j.jfineco.2017.06.002),
corporate-bond ETF eligibility/ownership effects;
RFS—[Moussawi–Shen–Velthuis (2025)](https://doi.org/10.1093/rfs/hhaf044),
the nearest published conversion context;
JFQA—[Brogaard–Heath–Huang (2025, online)](https://doi.org/10.1017/S0022109025102378),
index-ETF sampling and arbitrage; Review of Finance—[Easley–Michayluk–O'Hara–Putniņš
(2021)](https://doi.org/10.1093/rof/rfab021), cross-sectional active-in-form ETF
flow-performance sensitivity and portfolio turnover. No peer-reviewed article
located in these ten journals, in this bounded search, jointly uses
existing-strategy ETF conversion/share-class adoption to study reconciled
strategy-boundary capital flow and granular portfolio implementation. “No hit”
is a scoped search result, not proof of absence.
