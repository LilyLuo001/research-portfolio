# Independent review of the native-tick interpretation computation

Date: 2026-09-22. Verdict: **PASS_WITH_LIMITATIONS** for this new computation only.

The final corrected activity and matched-bin response aggregates reproduce from an independent SCC-side DBN decoder. All 160 finite primary AAPL matched RTH-minus-control estimates at 50 microseconds, 200 microseconds, 1 millisecond, 10 milliseconds, and 5 seconds match within `6.67e-16` bp. The other 80 requested primary rows are the XOM low-support combinations: the independent calculation finds zero common five-minute bins in every one, and the final engineering file now reports all 80 explicitly with a blank estimate, `support_bins=0`, and `dropped_bins=12`. Support-bin counts and the separate RTH/control paired and unpaired trade totals match exactly.

The verdict does not validate the full research design, causal interpretation, contribution, other files from prior stages, or a claim about price-discovery direction. It says that the corrected new aggregation implements the stated event-time, native-only, direction-separated calculation on these 12 RTH/control files.

## Independent scope and method

I decoded the 12 already purchased RTH/control DBNs in `/scratch/qluo/native_tick_pilot_20260922/` using `code/independent_native_tick_review.py`. The review code does not import the engineering script. It independently:

- resolves dated instrument mappings and applies the manifest-derived fixed one-hour center bounds;
- sorts by event timestamp, sequence, and original file order;
- assigns native `B/A` aggressor signs before any midpoint fallback;
- reads the BBO strictly before each trade, clears state on `R` or an invalid/undefined BBO, and performs an as-of lookup at each response endpoint;
- implements stock-centered `[-20,+20)` microsecond matching and the algebraically reversed SPY-centered interval `(t_SPY-20,t_SPY+20]`;
- requires both legs to have native direction and the same `B` or `S` sign for the primary paired group;
- constructs paired-minus-unpaired signed-mid changes separately for buys and sells in fixed five-minute bins; and
- forms matched RTH-minus-control estimates only on common clock bins, using either equal weights or the sum of RTH and control paired counts as a single common-bin weight.

No data were bought or downloaded. Raw inputs were not modified, and no raw row, timestamp, price, or quote was exported. The independent aggregate files are `INDEPENDENT_ACTIVITY_RECOMPUTATION.csv`, `INDEPENDENT_RESPONSE_RECOMPUTATION.csv`, and `INDEPENDENT_REVIEW_RECEIPT.json`.

## Four AAPL activity and denominator reconstructions

All near counts, background counts, excess counts, trade denominators, stock- and SPY-normalized rate differences, and fixed-order decomposition terms match the final `ACTIVITY_DECOMPOSITION.csv`. The displayed decomposition is in excess pairs per 1,000 stock trades:

`rate difference = level term + activity/denominator term`, where

`level term = 1000(E_R-E_C)/N_C`

and

`activity term = 1000 E_R(1/N_R-1/N_C)`.

| Event / venue | RTH minus control excess pairs | RTH minus control per 1,000 stock | Level term | Activity term | RTH minus control per 1,000 SPY |
|---|---:|---:|---:|---:|---:|
| AAPL February / ARCX | +255.8 | -20.9729 | +34.2391 | -55.2120 | +0.9177 |
| AAPL February / XNAS | +236.7 | -11.7161 | +12.4586 | -24.1746 | +1.5481 |
| AAPL August / ARCX | +10.3 | -41.9321 | +1.4487 | -43.3807 | +0.9535 |
| AAPL August / XNAS | -129.0 | -38.3143 | -9.4181 | -28.8962 | -13.6255 |

Thus the arithmetic supports the bounded interpretation: absolute background-adjusted coactivity rises in three of four cells, while the stock-normalized rate falls in all four because stock trading expands faster. The SPY-denominator result rises in the same three cells. The decomposition is an order-dependent accounting identity, not a causal allocation.

## Matched five-minute response reconstruction

`INDEPENDENT_RESPONSE_RECOMPUTATION.csv` contains all 240 requested primary rows: three event comparisons, two venues, two response instruments, five horizons, two directions, and two weighting schemes. The final engineering estimates, common-bin support, and RTH/control group counts agree with every independently finite row.

Common-bin support is horizon-invariant within these requested horizons:

| Event / venue | Buy bins | Sell bins |
|---|---:|---:|
| AAPL February / ARCX | 5 | 11 |
| AAPL February / XNAS | 8 | 11 |
| AAPL August / ARCX | 10 | 9 |
| AAPL August / XNAS | 7 | 10 |
| XOM January / either venue | 0 | 0 |

For AAPL the equal-bin RTH-minus-control estimates are heterogeneous, not uniformly positive. Across the five audited horizons they range from `-1.4755` to `+2.5617` bp across venue, instrument, and direction cells. Buy and sell rows are never pooled; their signs sometimes differ, especially in August. The paired-count sensitivity also uses one combined RTH-plus-control paired count per common bin, so the same weight is applied to both sides of the cross-day subtraction. These are descriptive conditional differences, not evidence that either the stock or ETF produced the information.

## Raw-trade and endpoint audit

I inspected 48 deterministically selected raw native trades, two per instrument in each RTH/control file, exceeding the requested minimum of 20. For all 48:

- the raw `B/A` side mapped to the expected native buy/sell sign;
- a finite, non-crossed prior BBO was available and the trade did not use its own post-message state;
- optimized oriented half-open pair membership equaled explicit pair enumeration; and
- endpoint lookup bracketed the target correctly at all five reviewed horizons.

This produced 240 endpoint checks, all with a valid returned BBO. The 12 reviewed files contain zero `R` clears and zero invalid/undefined BBO messages, so those two state transitions cannot be empirically exercised on this sample; I instead verified that the final code explicitly clears both cases. The code separately records age since the last message carrying a valid BBO and age since an actual BBO tuple change. It no longer treats the two as the same diagnostic.

## Engineering issues found and final resolution

The initial engineering artifacts had four review-relevant defects:

1. fixed-order decomposition terms were in pairs per trade beside a per-1,000 rate difference, a factor-1,000 unit mismatch;
2. XOM zero-common-bin primary comparisons were omitted rather than explicitly reported;
3. cross-day support columns described only the RTH side even though the paired-count weight used RTH plus control counts; and
4. quote age represented only the last BBO-carrying message, while the requested true-change age was absent. An invalid non-clear BBO also lacked an explicit state clear in the reusable script.

The final files correct all five points: decomposition column names and values are per 1,000 stock trades; XOM zero-support rows are explicit; RTH/control support totals are separate; the two age metrics are separately named; and clear/invalid states both remove the prior book. The local validator passes. These corrections do not change the 160 finite primary signed-mid estimates.

## Data boundary and routing

The fine table remains only at `/scratch/qluo/native_tick_pilot_20260922/interpretation_20260922/WITHIN_BIN_FINE_SCC_ONLY.csv` (24,193 lines including its header). No DBN, compressed DBN, or fine-cell CSV is present in the local interpretation result directory.

Requested reviewer routing was `gpt-5.6-sol / high`. No independently verifiable backend model or effort telemetry was exposed, so actual routing is recorded as **`NOT_OBSERVED`**. I used no nested delegation and made no commit or push.

## Scoped conclusion

The corrected computation is internally reproducible. It establishes that the requested native-only, direction-separated matched-bin response estimates can be measured for AAPL and that XOM has no common-bin support under this specification. It also establishes the denominator fact that three absolute AAPL excess counts rise while all four stock-normalized rates fall. It does not establish an earnings causal effect, ETF-to-stock or stock-to-ETF leadership, information production, full-basket transmission, or a distinctive research contribution.
