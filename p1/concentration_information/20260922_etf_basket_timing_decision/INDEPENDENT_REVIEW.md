# Independent result review

## Judgment

**Usable for the stated decision, with an important stale-quote caveat.** I independently decoded the raw SCC holdings and native DBN files in `/scratch/qluo/etf_basket_timing_20260922`; the project CSVs were used only afterward for comparison. The fixed-set counts and weights, all 28 baseline/+5/+30 endpoint combinations, all main and supplemental lag maxima, and every reported issuer amplification agree with my reconstruction at displayed precision (endpoint differences below `1e-15` return units; maximum correlation difference `8.9e-16`; no lag mismatch).

The arithmetic outputs can stand without rerunning the project. The scientific conclusion also stands: the two AAPL variants and the MSFT availability-notice variant are minute-scale simultaneous on all four venue/grid settings, while the four XOM/UNH clock variants are mixed or grid/venue-sensitive. There is no stable ETF-earlier or basket-earlier result across XNAS/ARCX and 0/30-second grids. This does not justify more events, more purchases, or a leadership claim. It does justify the stated `ADVANCE_BOUNDED_RESEARCH` action only in its narrow form: one predeclared one-second onset comparison using already-owned data, as a final resolution test that stops the leadership narrative if venue-stable direction still cannot be established.

One apparent positive-lag result is demonstrably fragile: the July 28 XOM 06:00 ET XNAS +5 basket move is almost entirely a stale/wide ICE state. That strengthens the mixed/not-stable conclusion, but means the corresponding XNAS basket level must not be described as a clean contemporaneous market move.

## Independent reconstruction method

I separately:

1. Read the CRSP holdings rows for SPY for the three report dates and retained ordinary-stock rows with a positive share count and usable permanent identifier.
2. Decoded all 12 basket DBNs and all 12 SPY supplement DBNs directly, replaying each symbol's last state at or before each UTC target.
3. Treated undefined/zero-sided and crossed states as invalid, rejected conflicting same-timestamp terminal states, and treated targets at or beyond archive end as unavailable.
4. Formed each variant's fixed intersection from symbols valid at baseline and every minute from -5 through +30 for both XNAS/ARCX and both 0/30-second grids. Report weights were retained without survivor renormalization.
5. Recomputed ETF and fixed-basket paths, cross-spread bounds, fixed-pair lag correlations for lags -5 through +5, leave-one-largest-+5-component sensitivity, and issuer residuals.

The historical UTC conversions are correct: 2023-01-31 11:30Z and 2023-02-02 21:30Z are 06:30 and 16:30 EST; 2023-04-14 09:55Z, 2023-04-25 20:07Z, 2023-07-28 10:00Z/10:30Z, and 2023-08-03 20:30Z are 05:55, 16:07, 06:00/06:30, and 16:30 EDT.

## Holdings, fixed support, and missing weight

The raw report totals and fixed intersections reproduced as follows. `Gap` is report total weight minus fixed common weight; it is disclosed rather than redistributed.

| Variant | Raw rows | Ordinary-stock rows | Report total | Ordinary-stock weight | Fixed names | Fixed weight | Gap | Issuer weight | 1 / issuer weight |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XOM Jan 31 06:30 | 505 | 501 | 1.0038 | 0.9955 | 125 | 0.5760998294 | 0.4276998721 | 0.0140999985 | 70.92199349 |
| XOM Jul 28 06:00 | 504 | 500 | 1.0029 | 0.9961 | 129 | 0.6411998090 | 0.3616999014 | 0.0116999912 | 85.47014956 |
| XOM Jul 28 06:30 | 504 | 500 | 1.0029 | 0.9961 | 171 | 0.7117997934 | 0.2910999170 | 0.0116999912 | 85.47014956 |
| UNH Apr 14 05:55 | 505 | 501 | 1.0028 | 0.9957 | 112 | 0.5698998607 | 0.4328998838 | 0.0128999996 | 77.51938214 |
| AAPL Feb 2 16:30 | 505 | 501 | 1.0038 | 0.9955 | 363 | 0.8382997483 | 0.1654999532 | 0.0604999924 | 16.52892770 |
| AAPL Aug 3 16:30 | 504 | 500 | 1.0029 | 0.9961 | 185 | 0.6446998201 | 0.3581998903 | 0.0771999741 | 12.95337223 |
| MSFT Apr 25 16:07 notice | 505 | 501 | 1.0028 | 0.9957 | 496 | 0.9777997477 | 0.0249999967 | 0.0625000000 | 16.00000000 |

The fixed ticker list and its weight are identical across both venues and both grids for each variant. There are 28 setting groups, each with 36 complete main-window states; within -5..+30 every group has one constant coverage weight and zero missing ETF or basket returns. All 28 baseline ETF and basket returns equal zero exactly. Across the full 91-minute display path, 260 of 1,540 out-of-main basket cells are correctly null because one or more fixed names is unavailable; the code does not silently turn those states into zero or publish a varying-subset return.

Mapped stock weight is feed-specific but the final cross-feed intersection is not: XNAS/ARCX mapped weights are 0.9767/0.9778 for the December report, 0.9781/0.9794 for June, and 0.9780/0.9792 for March. The report-to-fixed gaps therefore include cash/other, unmapped/unusable rows, and symbols failing the common state requirement. No survivor renormalization is applied.

## Endpoint reproduction

The following are independent values. `SPY base` is the midpoint in dollars at minute -5. `E5/B5` and `E30/B30` are SPY/fixed-basket returns in basis points from that baseline.

| Variant | Venue/grid | SPY base | E5 | B5 | E30 | B30 |
|---|---|---:|---:|---:|---:|---:|
| XOM Jan 31 06:30 | XNAS 0s | 398.620 | -8.6549 | -9.1274 | 16.1808 | -1.0656 |
|  | XNAS 30s | 398.605 | -6.3973 | -9.1460 | 21.9516 | 7.6627 |
|  | ARCX 0s | 398.630 | -9.0309 | -8.7148 | 16.3058 | -0.6650 |
|  | ARCX 30s | 398.610 | -7.0244 | -8.9680 | 21.7004 | 5.6741 |
| XOM Jul 28 06:00 | XNAS 0s | 454.605 | -3.5195 | 3.0439 | -4.1795 | 3.7895 |
|  | XNAS 30s | 454.600 | -2.9696 | 2.5778 | -4.9494 | 3.4096 |
|  | ARCX 0s | 454.600 | -3.1896 | 0.9476 | -4.2895 | -0.4414 |
|  | ARCX 30s | 454.600 | -3.1896 | 0.0754 | -4.8394 | -2.1242 |
| XOM Jul 28 06:30 | XNAS 0s | 454.430 | -5.8315 | -4.7972 | 1.4304 | -3.9248 |
|  | XNAS 30s | 454.400 | -4.5114 | -4.0699 | 1.2104 | -6.7656 |
|  | ARCX 0s | 454.435 | -5.7214 | -5.5281 | 1.4303 | -1.5143 |
|  | ARCX 30s | 454.400 | -4.4014 | -5.0472 | 0.9903 | -3.6108 |
| UNH Apr 14 05:55 | XNAS 0s | 412.790 | 1.4535 | 0.1469 | -0.1211 | -2.7532 |
|  | XNAS 30s | 412.790 | -1.5747 | -0.0456 | 0.6056 | -1.6111 |
|  | ARCX 0s | 412.780 | 1.6958 | 1.5014 | -0.1211 | -1.0475 |
|  | ARCX 30s | 412.785 | -1.5747 | 0.7895 | 0.6056 | -1.2636 |
| AAPL Feb 2 16:30 | XNAS 0s | 414.895 | -31.6948 | -30.3922 | -22.6563 | -25.5883 |
|  | XNAS 30s | 415.010 | -32.4089 | -34.1078 | -25.7825 | -27.8517 |
|  | ARCX 0s | 414.890 | -31.9362 | -29.9937 | -21.4515 | -21.9783 |
|  | ARCX 30s | 415.030 | -33.0097 | -32.2095 | -25.7813 | -23.0293 |
| AAPL Aug 3 16:30 | XNAS 0s | 450.505 | -16.4260 | -11.7711 | -29.8554 | -22.3814 |
|  | XNAS 30s | 450.525 | -19.9767 | -14.4365 | -29.0772 | -20.9316 |
|  | ARCX 0s | 450.510 | -16.3148 | -13.9903 | -28.1903 | -25.8063 |
|  | ARCX 30s | 450.520 | -19.8659 | -15.9346 | -29.2995 | -23.9870 |
| MSFT Apr 25 16:07 notice | XNAS 0s | 406.715 | 18.3175 | 18.3003 | 18.5634 | 20.3163 |
|  | XNAS 30s | 407.115 | 11.4218 | 6.0998 | 9.5796 | 7.9789 |
|  | ARCX 0s | 406.720 | 18.1943 | 8.0410 | 18.4402 | 15.8830 |
|  | ARCX 30s | 407.115 | 11.1762 | 3.2558 | 9.4568 | 8.9292 |

## Lag reproduction and event counting

Positive lag means SPY earlier. Each of the 308 main lag rows uses exactly 25 return-change pairs (`t=1..25`) and each of the 308 supplemental rows exactly 20 (`t=6..25`), independent of lag. The table gives `main best lag (correlation); supplemental best lag`.

| Variant | XNAS 0s | XNAS 30s | ARCX 0s | ARCX 30s | Classification |
|---|---|---|---|---|---|
| XOM Jan 31 06:30 | 0 (0.7713); 0 | -1 (0.4988); 0 | 0 (0.7975); 0 | 0 (0.6066); 0 | Mixed/grid-sensitive |
| XOM Jul 28 06:00 conflict | +1 (0.4078); +1 | -1 (0.3476); -1 | 0 (0.3740); 0 | +1 (0.3414); +1 | Mixed/grid-sensitive |
| XOM Jul 28 06:30 conflict | 0 (0.6165); 0 | 0 (0.5771); 0 | +3 (0.5736); +3 | 0 (0.4255); -5 | Mixed/grid-sensitive |
| UNH Apr 14 05:55 | 0 (0.3561); 0 | +3 (0.4839); +1 | 0 (0.3720); 0 | +3 (0.5100); +3 | Mixed/grid-sensitive |
| AAPL Feb 2 16:30 | 0 (0.9527); 0 | 0 (0.8535); 0 | 0 (0.9589); 0 | 0 (0.8848); 0 | Minute-scale simultaneous |
| AAPL Aug 3 16:30 | 0 (0.8673); 0 | 0 (0.8391); 0 | 0 (0.8763); 0 | 0 (0.8502); 0 | Minute-scale simultaneous |
| MSFT Apr 25 16:07 availability notice | 0 (0.5529); 0 | 0 (0.6432); 0 | 0 (0.6272); 0 | 0 (0.4652); 0 | Minute-scale simultaneous |

This is seven clock variants from six events, not seven independent events. The XOM July 06:00/06:30 pair is a clock-conflict sensitivity for one event, and the MSFT time is explicitly an availability notice rather than the original release.

## Issuer residual and cross-spread checks

For every finite row, the reconstructed residual obeys

`issuer_implied_return - issuer_return = (SPY return - fixed-basket return) / issuer_weight`

to a maximum absolute error of `1.04e-16`. The reported amplification values therefore are the correct `1 / issuer_weight`, but the XOM/UNH multipliers of roughly 71-85 also make the issuer residual highly sensitive to any ETF-basket discrepancy. Bid/ask cross-spread lower and upper bounds were recomputed from executable-side ratios; they ordered correctly wherever finite. Missing states remain null, not zero.

The quoted acquisition totals also reconcile: `$0.332191586494` for the component requests plus `$0.010294616223` for the SPY supplements. The receipts identify 24 downloaded native DBNs with hashes and sizes. A billing-ledger debit was not observable, so `billing_ledger_debit_usd: NOT_OBSERVED` is the correct status.

## Stale/high-weight constituent diagnostic

The decisive exception is ICE in the XOM July 28 06:00 XNAS setting:

- ICE report weight is only `0.00169999957` (about 0.17%). Its reconstructed return at +5 is `+18.11253197%`, contributing `+3.07912966 bp` to the reported `+3.0438698 bp` basket return. Excluding ICE leaves `-0.0352599 bp`.
- At the XNAS 0-second grid, ICE's baseline BBO is `75.50 / 120.00`, already 357 seconds old; the +5 BBO is `114.94 / 115.97`, 544 seconds old. The baseline spread is about 4,552 bp. This is a stale/wide observed state, not credible contemporaneous price discovery.
- Removing ICE changes the XNAS 0-second main best lag from `+1` to `0`. On the 30-second grid it changes `-1` to `+4`, which remains unstable rather than establishing direction. ARCX does not reproduce the ICE-driven basket jump.

The other simultaneous cases are not driven by one stale high-weight top +5 contributor: the largest contributors in the AAPL variants are AAPL with 0-1 second quote ages, and the best lag remains zero after removal. The MSFT-notice top contributors are GOOGL or MSFT with zero-second ages, and removal also leaves lag zero. For the XOM July 06:30 ARCX 0-second setting, INTU is stale (baseline 1,347 seconds, +5 427 seconds), but removing it leaves the +3 best lag unchanged; this is still a mixed setting, not a stable lead.

## Presentation limitations and final scientific interpretation

The figures are numerically consistent with the CSVs, including null gaps outside the complete fixed-support window. The path panels should nevertheless be read with their event metadata: the two `XOM 06:30_ET` panels are different January/July variants, the July panels are the issuer-wire conflict, and the MSFT panel is an availability notice. `EVENT_RESULTS.csv` preserves those labels, while the compact path-panel titles do not spell them out.

The evidence supports **three simultaneous variants and four mixed/grid-sensitive variants**, and supports **no stable minute-scale leader**. It does **not** support a claim that SPY, the lagged-report basket, or an implied issuer residual discovers the event first. The holdings are retrospective report snapshots rather than verified event-time holdings, fixed coverage ranges from about 0.57 to 0.98, and the low-weight issuer residual can magnify small discrepancies. Those are interpretation limits, not arithmetic failures.

Final usability judgment: **accept the arithmetic outputs, the overall simultaneous/mixed conclusion, and `ADVANCE_BOUNDED_RESEARCH` only for the already-owned, predeclared one-second onset test described in `RESULTS.md`; retain the ICE caveat and avoid directional price-discovery language.** The follow-up is a bounded resolution check, not evidence that either side leads. No full rerun is required.

Requested model/routing was specified externally, but runtime routing telemetry was not visible to this reviewer: **NOT_OBSERVED**. No commit or push was performed.
