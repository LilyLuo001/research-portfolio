# Independent finite review

## Verdict

**Numerical implementation: PASS for the corrected aggregate model and path outputs.** I independently rebuilt all 288 held-out A2→A5 point-estimate cells, all 3,372 issuer/component deletion cells, and all 288 support cells from the four SCC `model_parts_v2` loss files. The final summary matches those calculations to floating-point precision. Eight selected component-bootstrap intervals match within `9.9e-17`; a direct clone-and-relabel bootstrap check, including draws in which an issuer is absent, matches the optimized bootstrap within `5.6e-16`.

**Scientific decision: `NO_REPRODUCIBLE_DISTINCT_SPY_SIGNAL`.** This is not a numerical failure and not a finding that SPY contains no company information. A localized positive after-hours result remains on the XNAS integer grid, but it is not stable to the 500 ms grid and becomes negative when AAPL is deleted. ARCX has a positive integer-grid point estimate and positive issuer-deletion estimates, but its interval includes zero and the estimate attenuates strongly on the shifted grid. Premarket results are essentially zero or mixed. The evidence therefore does not support a reproducible distinct SPY increment across the fixed venue/grid/issuer sensitivities.

The three final figures were inspected after the isolated Matplotlib font-cache failure was repaired. Figure 2 separates all four venue/grid cells and Figure 3 is TEST EVENT only. Figure 1 is explicitly a TEST EVENT XNAS issuer-path **session-median aggregate** using the fixed t=-1 baseline; it is not a per-event path plot and should not be described as one.

## Fixed design and data boundaries

- Removing `BF` from the inherited 24-name safe roster leaves the fixed 23 stocks. Stable weight ranks 1/5/9/14/18/23 reproduce AAPL, LLY, CVS, CMI, EBAY and NWSA. The event manifest has exactly four events per issuer-year, 48 total; the cap was not expanded.
- The 48 controls are the fifth prior open NYSE session, have the same candidate clock and fold as their event, and do not collide with another retained event date for the same issuer. The design contains 96 event/control windows and 288 requests.
- The SCC download receipt contains the same 288 request IDs as the fixed manifest: 96 each for XNAS.ITCH, ARCX.PILLAR and GLBX.MDP3, all nonempty and all marked complete. The credential is read from the environment and is absent from receipts and Git.
- All 48 clocks remain `NOT_YET_VERIFIED`. Winter and summer fixed-file audits confirm the recorded New York-to-UTC conversions and raw half-open request bounds, but do not establish first-public time or even a ±1 minute error bound. `PRE`/`POST` mean offsets from a candidate minute, not verified pre-news/post-news states.
- The two equity datasets are venue-native BBO/trade feeds, not SIP NBBO. In 53 of 96 samples, at least one fixed basket member is absent (maximum seven). The corrected coverage columns use the fixed rest-of-22 denominator; the weighted rest-stock mean remains an observed-member mean and cannot be described as a fully observed basket.

## Model implementation checks

- The target is the issuer's future midpoint log return. Predictor intervals are causal `(start, end]` histories ending at the grid center; target endpoints are assigned only when both the predictor center and future endpoint remain in the named window.
- Native trade sign is consistently `B = +1` buyer aggressor and `A = -1` seller aggressor. Unknown-side volume and no-trade indicators remain separate.
- A2 is `B+C`; A5 is `B+C+Q+P`. Thus A2→A5 is the joint increment from SPY quote and SPY trade history conditional on issuer/rest-stock/ES information. It is not a structural ETF information share.
- Medians, missing indicators and standardization are learned from TRAIN; lambda is selected on VALID; the final fit uses TRAIN+VALID; HISTORY and 2024 TEST are scored without refit, rescaling or lambda selection.
- The original row weights were wrong when an event retained one event/control sample and another retained two. The corrected hierarchy is issuer → event → available sample → target row. SCC `WEIGHT_SUPPORT.csv` files show zero within-issuer event-mass spread (maximum numerical residual `9.8e-17`).
- Connected components join event IDs sharing any event/control economic date. Component bootstrap and component deletion preserve that shared-date dependence. Equal-issuer/event aggregation and leave-one-issuer-out checks address issuer concentration, but the bootstrap does not separately cluster an issuer's dependence across dates.
- The actual UTC membership audit checked 299,520 distinct centers per horizon/window and found zero differences between integer-index and timestamp membership on both 0 and 500 ms grids. No boundary-driven refit was required.

## Primary corrected numbers

The table reports equal-issuer/equal-event `G = 1 - loss(A5)/loss(A2)` for 2024 EVENT, next-second, `POST_0_60S`, own-lambda fits. Values are fractions, not percentage points.

| Venue | Grid | Session | G | 95% component bootstrap interval |
|---|---:|---|---:|---:|
| XNAS.ITCH | 0 ms | After hours | 0.00114790 | [0.00040737, 0.00449072] |
| XNAS.ITCH | 500 ms | After hours | -0.00001034 | [-0.00006724, 0.00008249] |
| ARCX.PILLAR | 0 ms | After hours | 0.00210028 | [-0.00070060, 0.00673426] |
| ARCX.PILLAR | 500 ms | After hours | 0.00031682 | [-0.00000169, 0.00083551] |
| XNAS.ITCH | 0 ms | Premarket | -0.00002345 | [-0.00014427, 0.00099436] |
| XNAS.ITCH | 500 ms | Premarket | 0.00000319 | [-0.00000129, 0.00001930] |
| ARCX.PILLAR | 0 ms | Premarket | -0.00013336 | [-0.00066733, 0.00062547] |
| ARCX.PILLAR | 500 ms | Premarket | 0.00005450 | [-0.00003548, 0.00019019] |

For XNAS/0 ms/after-hours, deleting AAPL changes G to `-0.00014065`; the full issuer-deletion range is `[-0.00014065, 0.00282656]`. ARCX/0 ms/after-hours remains positive under issuer deletion (`[0.00052797, 0.00252094]`) but not under its bootstrap interval. Own-lambda and fixed-A2-lambda focal point estimates are identical because the selected lambdas coincide; they are not independent robustness confirmations.

Across all 288 corrected primary cells, G ranges from `-0.08485945` to `0.00898854`; 122 are positive and 166 negative. This broad range reinforces the need to report the fixed sensitivity set rather than select the one positive cell.

## Path and support checks

- The corrected path detail materializes all `2,688` intended cells: `2,544` valid fixed-minus-one-second responses, `77` explicit `NO_SOURCE_PANEL` rows and `67` invalid baseline/endpoint rows. The labelled legacy anchor response exactly recovers the historical path wherever finite (maximum serialization difference `8.9e-12` bp).
- Fixed-minus-one-second persistence has 726 comparable pairs: 608 nonzero, 385 same-direction nonzero and 48 zero-to-zero. The anchor sensitivity has 728/603/383/54 respectively. Zero-to-zero moves are not counted as directional persistence.
- Recomputed path aggregates, coverage and persistence match their final files to CSV floating precision. Raw price levels, fitted objects, per-center predictions and detailed licensed rows remain on SCC.

## Interpretation boundary

The numerical conclusion is only that the corrected code and aggregate tables implement the declared conditional prediction comparison. The scientific conclusion is narrower: this six-issuer, candidate-clock, native-venue pilot does not produce a distinct SPY increment that is reproducible across the prespecified grid/venue/issuer sensitivities. It does not identify causality, permanent price discovery, verified announcement absorption, ETF leadership, fundamental pricing accuracy, or a universal absence of ETF information.
