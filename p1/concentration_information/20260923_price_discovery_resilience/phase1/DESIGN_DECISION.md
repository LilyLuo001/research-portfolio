# Phase 1 design decision: one ecology, one channel-loss case

Date: 2026-09-23. Decision: `SELECT_NYSE_2015_VENUE_CAPACITY_LOSS_CASE / MEASUREMENT_PROTOTYPE_COMPLETE / FULL_EVENT_DATA_NOT_YET_PRESENT`.

## The selected economic comparison

The paper studies whether price discovery concentrated in a convenient trading channel remains **replaceable** when that channel loses capacity. The first ecology is the S&P 500 complex: a complete contemporaneous cash basket, SPY (and later IVV/VOO where supported), and the active ES contract. The first case is the 8 July 2015 NYSE/NYSE MKT incident.

The treatment is not “the stock market closed.” It is the documented deterioration and subsequent removal of NYSE and NYSE American/MKT matching/connectivity capacity; NYSE Arca was not the affected exchange in this incident. The main empirical population is NYSE-listed S&P 500 securities, while simultaneous American/MKT impairment is recorded as an accompanying treatment rather than an untreated comparison. The state sequence is: gateway degradation from about 10:45 ET; formal suspension at 11:32; reopening at 15:10. The formal interval is precise to the minute in the retained regulatory evidence; the public-awareness clock and security-level effective boundaries still require direct-feed/status reconstruction.

Other cash venues, the ETF, and ES are **substitution outcomes**, not untreated controls. The primary comparison is their absolute activity and the whole ecology's normalized adjustment/consistency path across the pre-degradation, degradation, formal suspension and recovery states, relative to pre-specified same-clock normal days. With one incident this is a documented state-transition case, not a clean causal ATT.

Evidence counts as successful substitution only when both conditions line up:

1. surviving channels add absolute updating/trading capacity rather than merely gaining a mechanical share after NYSE disappears; and
2. cross-channel price adjustment and consistency do not suffer a persistent deterioration.

A larger remaining-channel share alone is not success. A temporary activity migration accompanied by persistent cross-instrument divergence is evidence of incomplete substitution. Little divergence and stable adjustment despite venue loss is evidence of resilient, replaceable concentration.

## Why this is not another ordinary lead–lag paper

| Existing object | What is already known | Distinct object required here |
|---|---|---|
| Ernst and related ETF/company-news work | ETF trades can contain stock-specific information; weights matter | Whether a disabled operating channel is replaced in absolute activity without system-level adjustment loss |
| Box et al. ETF–portfolio intraday arbitrage | ETF and basket have dynamic lead/lag and arbitrage links | A pre-documented capacity-loss state, fixed ecology, and channel activity plus system consistency jointly |
| SEC analysis of the 2015 NYSE suspension | Cash trading migrated to other venues; spreads/depth changed | Cross-asset substitution involving ETF, complete basket and ES, and whether migration preserved joint adjustment |
| Cespa–Foucault / liquidity contagion | Cross-asset learning can generate fragility | Direct operational evidence on replacement and recovery in a named index ecology |
| Rappoport–Tuzun | ETF/basket liquidity and arbitrage are linked | Not another deviation/spread VAR: loss of a channel, absolute replacement, and system loss are separate outcomes |

The contribution remains a **candidate** until the 2015 event data are measured. If the final evidence only reproduces cash-volume migration or an average ETF/ES lead, this case is not an independent main paper.

## Event screen and why only one case is retained

`EVENT_CANDIDATES.csv` records four operator/regulator-sourced incidents without selecting on market response. NYSE 2015 is retained because the formal boundary and alternative cash venues are documented. Xetra 2018 lacks an auditable start/resumption clock; Euronext 2020 jointly affected cash and derivatives and includes cancelled/corrected closing records; ISE Mercury 2016 lacks adequate instrument and substitute-venue scope. They remain in the record rather than disappearing after exclusion.

## Main measurement and one sensitivity

The main measurement is non-structural: normalized price paths, absolute midpoint-update activity, displayed spread/depth, and cross-channel relative-return divergence. A fixed pre-event SPY-on-ES mapping provides a scale diagnostic; absent carry and full basket inputs, this is only a relative-return divergence proxy—not NAV discount, arbitrage profit, permanent information share or pure information delay.

The only planned sampling sensitivity is the same one-second grid shifted by 500 ms. Short event windows do not support a large VECM/IS exercise. Common-price models remain a later extension only if complete economic mappings, longer development support and cointegration diagnostics pass.

## Phase 1 actual demonstration

The code was run on the two earliest 2023 FOMC event/control pairs already present on SCC: 2023-02-01/2023-01-25 and 2023-03-22/2023-03-15. Selection used chronology and file support, not responses. The inputs are SPY XNAS venue BBO and ES GLBX venue BBO, not a national NBBO or complete cash basket.

All eight date×grid observations have 60/60 valid joint return bins. The primary grid covers `(t0,t0+60s]`; the 500 ms sensitivity covers `(t0+0.5s,t0+60.5s]` and is not treated as an identical-clock replication. Both FOMC dates show far more updating than their fixed controls and large, broadly aligned interval-end moves. The residual SPY–ES divergence does not behave uniformly across the two news events: it shrinks relative to the first-ten-bin peak on 2023-02-01 but grows afterward on 2023-03-22. This proves the measurement produces economically interpretable, non-identical activity and consistency outputs. It does not test a channel loss, identify permanent contribution, or establish the paper's hypothesis.

## Inferential status

- FOMC measurement implementation: `COMPLETE_REAL_EXISTING_DATA_DEMO`.
- Main 2015 event data and complete ecology: `NOT_YET_PRESENT`.
- Information share: `NOT_ESTIMATED`.
- Channel-substitution causal effect: `NOT_ESTIMATED`.
- Paper result: `OPEN`; neither supported nor rejected by the Phase 1 demo.
