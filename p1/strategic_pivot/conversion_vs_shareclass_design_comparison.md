# Conversion versus ETF-share-class designs

Frozen on 2026-09-03. This is an ex-ante design comparison. No outcome or treatment coefficient was inspected.

| Design | Treatment and estimand | Realized independent timing | Main strength | Binding threat | Classification |
|---|---|---:|---|---|---|
| Broad underlying-stock MF→ETF conversion | `Post × Exposure_pre`; effect on securities held by converted funds | 30 positive-exposure waves; effective information is far below the 8,801 stock-wave rows | Continuous predetermined dose | Median ownership dose is 0.0299%; one sponsor/wave supplies most identifying mass | **NOT VIABLE as headline** |
| High-dose underlying-stock conversion | Same estimand restricted at frozen `Exposure_pre ≥ 0.5%` | 4 waves; 583 cells; only 21 ex-Dimensional cells in 2 waves | Economically nontrivial dose | Few-shock inference and sponsor concentration | **SECONDARY / MECHANISM ONLY** |
| Converted-fund outcomes | Effect of a full wrapper change on the treated fund relative to matched nonconverters | 156 completed funds; 74 exact-day; 71 N-PORT Gate0 PASS across 47 dates | Treatment is 100% at fund level and sample is materially larger | Conversion selection; strategy and clientele may change | **HEADLINE CANDIDATE** |
| Historical Vanguard ETF-class activation | Add ETF trading to an unchanged underlying portfolio while mutual classes continue | 19 clean activations on 9 distinct dates from the 70 shared portfolios | Exact same legal portfolio is unusually clean | Small number of independent dates; adoption clustering; old-data outcome limits | **HEADLINE CANDIDATE / validation design** |
| Modern ETF-class activation | Same portfolio gains an ETF class under modern disclosure and market structure | 10 confirmed ETF activations by cutoff; 1 reverse event kept separate | Cleanest contemporary institutional experiment | Short postperiod and sponsor/date concentration | **SECONDARY NOW; future headline candidate** |
| Unified architecture project | Fund conversions provide scale; exact-portfolio share classes validate mechanism | 47 conversion dates plus 9 historical and 7 modern ETF-activation dates before de-duplication | One economic question with complementary designs | Becomes an omnibus paper if estimands are pooled or outcomes proliferate | **RECOMMENDED PRIMARY ARCHITECTURE** |

## What each design can claim

The conversion design identifies the consequences of replacing the mutual-fund wrapper with an ETF wrapper, conditional on credible controls and pretrends. It does **not** mechanically hold strategy, shareholders, fees, disclosure, and portfolio composition fixed. Those are treatment components or possible confounds that must be measured.

The share-class design identifies the consequence of adding exchange trading, creation/redemption, and ETF distribution to the **same underlying portfolio** while conventional mutual shares remain. It offers cleaner portfolio continuity, but it does not identify a full wrapper replacement and does not eliminate endogenous launch selection.

The designs therefore should not be pooled into a single treatment coefficient. The publishable structure is triangulation: a powered fund-level conversion design for the principal fact, exact-portfolio share-class activations for mechanism and external validity, and stock-level dose results only as secondary transmission evidence.

## Frozen decision rule

Promote the fund-level design only after matched-control overlap, no differential pretrend, and event-level portfolio-continuity diagnostics pass. Promote a historical share-class design to co-headline only if at least six of the nine activation dates retain usable pre/post outcomes and leave-one-date-out estimates do not reverse sign. Modern events stay prospective until a minimum one-year postperiod exists. No threshold may be changed after outcomes are seen.
